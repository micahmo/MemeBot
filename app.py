import os
import os.path
from flask import Flask, request
import telepot
from telepot.namedtuple import InlineQueryResultCachedPhoto, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
import pprint
import time
from random import randint
import pickle
import boto
import boto.s3
import sys
from boto.s3.key import Key
import operator

MICAHMO_ID = '76034823'

# set some consts that we'll need later on for the bot
PORT = int(os.environ.get('PORT', 5000))
TOKEN = "554574433:AAE6O2v3sm7yEQ9kJYW7GPp-JGnrUSyUMGM"
SECRET = "/BOT" + TOKEN
URL = "https://memebot42.herokuapp.com/"

# get some environment variables that we'll need later
S3_BUCKET = os.environ.get('S3_BUCKET')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

# do some S3 setup
os.environ['S3_USE_SIGV4'] = 'True'
os.environ['REGION_HOST'] = 's3.us-east-2.amazonaws.com'

# set up Flask
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

app = Flask(__name__)
@app.route(SECRET, methods=['GET', 'POST'])
def pass_update():
    UPDATE_QUEUE.put(request.data)  # pass update to BOT
    return 'OK'

#some "consts"
MESSAGE_STATUS_FILENAME = 'message_status.pickle'
MEME_DATA_FILENAME = 'meme_data.pickle'

# message status "enum"
class MessageStatus:
    Unknown = 0
    WaitingForMeme = 1
    WaitingForMemeName = 2
    WaitingToDeleteMeme = 3

# list of files "enum"
class Files:
    MessageStatus = 0
    MemeData = 1

# bot logic
def handleChat(msg):
    #get our chat data
    content_type, chat_type, chat_id = telepot.glance(msg)

    if chat_type == "private":

        # load our message status
        message_status = load(Files.MessageStatus)
        meme_data = load(Files.MemeData)

        chat_id = str(chat_id) #if it's not already a string...
        
        # print the message info out, for debugging
        print(content_type)
        pprint.pprint(msg)

        if content_type == 'text':
            # a couple of special commands for me
            if chat_id == MICAHMO_ID and msg.get("text").lower() == "/sudolist":
                BOT.sendMessage(chat_id, pprint.pformat(meme_data, indent=4))

            elif chat_id == MICAHMO_ID and msg.get("text").lower().startswith("/sudodelete"):
                memeToDeleteFileId = msg.get("text").split(' ')[1]
                for key, value in meme_data.items():
                    if (value.fileId == memeToDeleteFileId):
                        meme_data.pop(key, None)
                        BOT.sendMessage(chat_id, "Deleted.")
                        break

            elif msg.get("text").lower() == "/start" or msg.get("text").lower() == "/help":
                BOT.sendMessage(chat_id, "Hi {}! I am a customizable meme bot. :) Send me memes with the /addmeme command, and I'll add them to your collection!".format(msg["chat"]["first_name"]))

            elif msg.get("text").lower().startswith("/addmeme"):
                BOT.sendMessage(chat_id, "Awesome! Send me the meme!")
                message_status[chat_id] = MessageStatus.WaitingForMeme

            elif msg.get("text").lower().startswith("/cancel") and message_status.get(chat_id) != MessageStatus.Unknown:
                BOT.sendMessage(chat_id, "Alright, consider it cancelled!", reply_markup=ReplyKeyboardRemove())
                message_status[chat_id] = MessageStatus.Unknown

            elif msg.get("text").lower().startswith("/cancel") and message_status.get(chat_id) == MessageStatus.Unknown:
                BOT.sendMessage(chat_id, "Well, there's nothing to cancel, but ok. :)", reply_markup=ReplyKeyboardRemove())

            elif msg.get("text").lower().startswith("/listmymemes"):
                result = ""
                for key, value in meme_data.items():
                    if (value.submitter == chat_id):
                        result += "\n" + value.name.replace("_", " ")
                
                if (len(result) > 0):
                    BOT.sendMessage(chat_id, result)
                else:
                    BOT.sendMessage(chat_id, "Looks like you don't have any memes yet! Feel free to add one with /addmeme.")

            elif msg.get("text").lower().startswith("/deletememe"):
                # send the user a list of their memes as a "custom keyboard"
                custom_keyboard = []

                for key, value in meme_data.items():
                    if (value.submitter == chat_id):
                        custom_keyboard.append([
                            KeyboardButton(text=value.name.replace('_', ' '))
                        ])
                
                keyboard = ReplyKeyboardMarkup(keyboard=custom_keyboard, one_time_keyboard=True)
                BOT.sendMessage(chat_id, "Tell me which meme you want to delete...", reply_markup=keyboard)

                # put the user in "deleting meme" mode
                message_status[chat_id] = MessageStatus.WaitingToDeleteMeme
            
            elif message_status.get(chat_id) == MessageStatus.WaitingToDeleteMeme:
                memeDeleted = False
                try:
                    memeToDeleteName =  msg.get("text").replace(' ', '_')
                    for key, value in meme_data.items():
                        if (value.submitter == chat_id and value.name == memeToDeleteName):
                            meme_data.pop(key, None)
                            memeDeleted = True
                            break
                except:
                    pass
                finally:
                    if memeDeleted:
                        # tell the user we deleted their meme
                        BOT.sendMessage(chat_id, "Deleted!", reply_markup=ReplyKeyboardRemove())
                    else:
                        # tell the user we couldn't find their meme
                        BOT.sendMessage(chat_id, "Meme name not found.", reply_markup=ReplyKeyboardRemove())

                # put the user in back in "unknown" mode
                message_status[chat_id] = MessageStatus.Unknown
            
            elif message_status.get(chat_id) == MessageStatus.WaitingForMeme: # we're waiting for a meme, but they didn't send a picture
                BOT.sendMessage(chat_id, "Hmm, I didn't get a picture. Try again!")

            elif message_status.get(chat_id) == MessageStatus.WaitingForMemeName:
                userMemeName = msg["text"].lower().replace(' ', "_")

                duplicateName = False

                for key, value in meme_data.items():
                    if (value.submitter == chat_id and value.name == userMemeName):
                        BOT.sendMessage(chat_id, "Ooh, looks like you've already added a meme with the name \"{}\" to your library. Try another one!".format(msg["text"]))
                        duplicateName = True
                
                if not duplicateName:
                    # find the meme in our meme_data
                    memeObject = {}
                    for key, value in meme_data.items():
                        if (key == chat_id): # this is the meme pending a name
                            memeObject = value
                            meme_data.pop(key, None)
                            break

                    # rename it
                    memeObject.name = userMemeName

                    # add it back under the correct key
                    meme_data[memeObject.fileId] = memeObject

                    # and notify the user
                    BOT.sendMessage(chat_id, "Alright, I'll call it \"{}\" and add it to your library of memes!".format(msg["text"]))
                    message_status[chat_id] = MessageStatus.Unknown

            else:
                BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")
        
        elif content_type == 'photo':
            
            if message_status.get(chat_id) == MessageStatus.WaitingForMeme:
                BOT.sendMessage(chat_id, "Great, I got it! Now, what do you want to call it? Be as descriptive as possible!")
                message_status[chat_id] = MessageStatus.WaitingForMemeName

                # save the meme under the user's id
                meme_data[chat_id] = Meme("", msg['photo'][-1]['file_id'], chat_id, msg.get("chat").get("username"))

            elif message_status.get(chat_id) == MessageStatus.WaitingForMemeName: # we're waiting for a meme name, but they didn't sent a picture...
                BOT.sendMessage(chat_id, "Hmm, I'm still waiting for you to send me a name for the meme...")

        elif content_type == 'document':
            if message_status.get(chat_id) == MessageStatus.WaitingForMeme:
                BOT.sendMessage(chat_id, "At this time, the file format that you sent ({}) is not supported. :( Please send a photo.".format(msg.get("document").get("mime_type")))
            else:
                BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")
        
        else:
            if message_status.get(chat_id) == MessageStatus.WaitingForMeme:
                BOT.sendMessage(chat_id, "You sent an unrecognized message type ({}). Please try again.".format(content_type))
            else:
                BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")
            

        # save our important objects
        save(Files.MessageStatus, message_status)
        save(Files.MemeData, meme_data)

        #print our received message, for debugging purposes
        pprint.pprint(message_status)   


def handleInline(msg):
    pprint.pprint(msg)

    # get our meme data
    meme_data = load(Files.MemeData)

    # get our chat data
    query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')

    # make the id a string, if it's not already
    from_id = str(from_id)

    photos = []

    # do our "find" logic
    keywords = query_string.lower().split(' ')
    fileIdsToRelevancy = {}

    for key, value in meme_data.items():
        if (value.submitter == from_id): # this is a meme for this person
            relevancy = 0
            for keyword in keywords:
                if (keyword in value.name):
                    relevancy = relevancy + 1
            if relevancy > 0:
                fileIdsToRelevancy[key] = relevancy

    # sort out dictionary by relevancy
    fileIdsToSortedRelevancy = sorted(fileIdsToRelevancy.items(), key=operator.itemgetter(1), reverse=True)
    
    # now we have a sorted list of tuples, so grab our fileIds and construct our actual results lists
    for (fileId, relevancy) in fileIdsToSortedRelevancy:
        photos.append(InlineQueryResultCachedPhoto(id=fileId, photo_file_id=fileId))

    # respond with our results
    res = BOT.answerInlineQuery(query_id, photos, cache_time=0)


def handleChosenInline(msg):
    pprint.pprint(msg)


def save(file, object):
    fileName = get_filename_from_file(file)
    if (fileName == None): return

    # write our status to a file
    with open(fileName, 'wb') as outfile:
        pickle.dump(object, outfile)

    #write our file to S3
    upload_file(fileName)

    #and remove our local copy
    os.remove(fileName)

def load(file):
    fileName = get_filename_from_file(file)
    if (fileName == None): return

    #first, open our configuration file
    open_file(fileName)

    #now convert the file to an object
    object = {}
    try :
        with open(fileName, 'rb') as json_data:
            object = pickle.load(json_data)
 
    except:
        object = {} # if we can't open it, leave it as an empty object

    # now delete our local file
    os.remove(fileName)

    #now return our new object
    return object

def get_filename_from_file(file):
    if (file == Files.MessageStatus): return MESSAGE_STATUS_FILENAME
    elif (file == Files.MemeData): return MEME_DATA_FILENAME
    else: return None

def get_url_to_file(fileName):
    # get the connection
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, host=os.environ.get('REGION_HOST'))
    
    # get the bucket
    bucket = conn.get_bucket(S3_BUCKET)
    
    # create the file
    k = Key(bucket)
    k.key = fileName

    url = k.generate_url(expires_in=50000, query_auth=True, force_http=True)
    
    return url

def upload_file(fileName, allowPublic=False):
    # get the connection
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, host=os.environ.get('REGION_HOST'))
    
    # get the bucket
    bucket = conn.get_bucket(S3_BUCKET)
    
    # create the file
    k = Key(bucket)
    k.key = fileName
    k.set_contents_from_filename(fileName)

    if (allowPublic):
        k.set_acl('public-read')

def open_file(fileName):
    # get the connection
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, host=os.environ.get('REGION_HOST'))
    
    # get the bucket
    bucket = conn.get_bucket(S3_BUCKET)

    try:
        # get the file
        k = Key(bucket)
        k.key = fileName
        k.get_contents_to_filename(fileName)
    except:
        open(fileName, 'a').close() #create an empty file if we can't find one on the server



# set up bot
BOT = telepot.Bot(TOKEN)
UPDATE_QUEUE = Queue()

BOT.message_loop({'chat': handleChat, 'inline_query': handleInline, 'chosen_inline_result': handleChosenInline}, source=UPDATE_QUEUE)

if (URL + SECRET) != BOT.getWebhookInfo()['url']:
    BOT.setWebhook() # unset if was set previously
    BOT.setWebhook(URL + SECRET)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0', port=PORT, debug=True)





class Meme:
    def __init__(self, name, fileId, submitter, submitterUsername):
        self.name = name
        self.fileId = fileId
        self.submitter = submitter
        self.submitterUsername = submitterUsername

    def __str__(self):
        return "name: {}, fileId: {}, submitter: {}, submitterUsername: {}".format(self.name, self.fileId, self.submitter, self.submitterUsername)

    def __repr__(self):
        return "name: {}, fileId: {}, submitter: {}, submitterUsername: {}".format(self.name, self.fileId, self.submitter, self.submitterUsername)
 