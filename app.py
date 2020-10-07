import os
import os.path
import telepot
from telepot.namedtuple import InlineQueryResultCachedPhoto, InlineQueryResultCachedMpeg4Gif, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telepot.loop import MessageLoop
import pprint
import time
import pickle
import boto
import boto.s3
from boto.s3.key import Key
import operator

# Define our classes and methods first

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
        if (DEBUG):
            print(content_type)
            pprint.pprint(msg)

        if content_type == 'text':
            # a couple of special commands for me
            if chat_id == OWNER_CHAT_ID and msg.get("text").lower() == "/sudolist":
                for key, value in meme_data.items():
                    message = pprint.pformat(key, indent=4) + " " + pprint.pformat(value, indent=4)
                    BOT.sendMessage(chat_id, message)

            elif chat_id == OWNER_CHAT_ID and msg.get("text").lower().startswith("/sudodelete"):
                memeToDeleteFileId = msg.get("text").split(' ')[1]
                for key, value in meme_data.items():
                    if (value.fileId == memeToDeleteFileId):
                        meme_data.pop(key, None)
                        BOT.sendMessage(chat_id, "Deleted.")
                        break

            elif msg.get("text").lower() == "/start" or msg.get("text").lower() == "/help":
                BOT.sendMessage(chat_id, "Hi {}! I am a customizable meme bot. :) Send me memes with the /addmeme command, and I'll add them to your collection!".format(msg["chat"]["first_name"]))
                message_status[chat_id] = MessageStatus.Unknown

            elif msg.get("text").lower().startswith("/addmeme"):
                BOT.sendMessage(chat_id, "Awesome! Send me the meme!")
                message_status[chat_id] = MessageStatus.WaitingForMeme

            elif msg.get("text").lower().startswith("/cancel") and message_status.get(chat_id) != MessageStatus.Unknown:
                BOT.sendMessage(chat_id, "Alright, consider it cancelled!", reply_markup=ReplyKeyboardRemove())
                message_status[chat_id] = MessageStatus.Unknown

            elif msg.get("text").lower().startswith("/cancel") and message_status.get(chat_id) == MessageStatus.Unknown:
                BOT.sendMessage(chat_id, "Well, there's nothing to cancel, but ok. :)", reply_markup=ReplyKeyboardRemove())
                message_status[chat_id] = MessageStatus.Unknown

            elif msg.get("text").lower().startswith("/listmymemes"):
                result = ""
                for key, value in meme_data.items():
                    if (value.submitter == chat_id and value.name != ""):
                        result += "\n\n" + "🖼️  " + value.name.replace("_", " ")
                
                if (len(result) > 0):
                    BOT.sendMessage(chat_id, result)
                else:
                    BOT.sendMessage(chat_id, "Looks like you don't have any memes yet! Feel free to add one with /addmeme.")

                message_status[chat_id] = MessageStatus.Unknown

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

                # save the meme under the user's id
                meme_data[chat_id] = Meme("", msg['photo'][-1]['file_id'], chat_id, msg.get("chat").get("username"))

                message_status[chat_id] = MessageStatus.WaitingForMemeName

            elif message_status.get(chat_id) == MessageStatus.WaitingForMemeName: # we're waiting for a meme name, but they didn't sent a picture...
                BOT.sendMessage(chat_id, "Hmm, I'm still waiting for you to send me a name for the meme...")

            else:
                BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")

        elif content_type == 'document':
            if msg.get("document").get("mime_type") == "video/mp4":

                if message_status.get(chat_id) == MessageStatus.WaitingForMeme:
                    BOT.sendMessage(chat_id, "Great, I got it! Now, what do you want to call it? Be as descriptive as possible!")

                    # save the meme under the user's id
                    meme_data[chat_id] = Meme("", msg['document']['file_id'], chat_id, msg.get("chat").get("username"))

                    message_status[chat_id] = MessageStatus.WaitingForMemeName
                
                elif message_status.get(chat_id) == MessageStatus.WaitingForMemeName: # we're waiting for a meme name, but they didn't sent a picture...
                    BOT.sendMessage(chat_id, "Hmm, I'm still waiting for you to send me a name for the meme...")

                else:
                    BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")
            
            else:
                BOT.sendMessage(chat_id, "At this time, the file format that you sent ({}) is not supported. :( Feel free to contact the developer @micahmo to add support for this format.".format(msg.get("document").get("mime_type")))
        
        else:
            if message_status.get(chat_id) == MessageStatus.WaitingForMeme:
                BOT.sendMessage(chat_id, "You sent an unrecognized message type ({}). Please try again.".format(content_type))
            else:
                BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")
            

        # save our important objects
        save(Files.MessageStatus, message_status)
        save(Files.MemeData, meme_data)

        #print our received message, for debugging purposes
        if (DEBUG):
            pprint.pprint(message_status)

def handleInline(msg):
    if (DEBUG):
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
        
        if meme_data[fileId].name != "": # check for empty name, meaning it's not saved yet and thus doesn't have a valid ID
            
            # first, get the file so we know what type it is
            file = BOT.getFile(fileId)
        
            # Note: For some crazy reason, file_ids longer than 64 character have to be trimmed, hence the [:64]
            # More info: https://github.com/telegraf/telegraf/issues/869#issuecomment-615930095

            if ("photo" in file.get("file_path")):
                # it's a photo
                photos.append(InlineQueryResultCachedPhoto(id=fileId[:64], photo_file_id=fileId))
            elif ("animation" in file.get("file_path")):
                # it's an mp4 gif
                photos.append(InlineQueryResultCachedMpeg4Gif(id=fileId[:64], mpeg4_file_id=fileId))

    # respond with our results
    if (photos != []):
        print(f"Found {photos.count()} results for query '{query_string}'' for user {from_id}.")
        BOT.answerInlineQuery(query_id, photos, cache_time=0)
    else:
        print(f"No results for query {query_string} for user {from_id}.")

def handleChosenInline(msg):
    if (DEBUG):
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
    try:
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
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, host=REGION_HOST)
    
    # get the bucket
    bucket = conn.get_bucket(S3_BUCKET)
    
    # create the file
    k = Key(bucket)
    k.key = fileName

    url = k.generate_url(expires_in=50000, query_auth=True, force_http=True)
    
    return url

def upload_file(fileName, allowPublic=False):
    # get the connection
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, host=REGION_HOST)
    
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
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, host=REGION_HOST)
    
    # get the bucket
    bucket = conn.get_bucket(S3_BUCKET)

    try:
        # get the file
        k = Key(bucket)
        k.key = fileName
        k.get_contents_to_filename(fileName)
    except:
        open(fileName, 'a').close() #create an empty file if we can't find one on the server


# Important Note: When pickle.load is executed, if there is a class referenced in the pickled data, there are two implications:
#   1. The referenced class (and corresponding module) must still exist! In this example, app.py:Meme must always exist to depickle meme_data.pickle.
#   2. The referenced module (if any) we be reloaded. This means, in order to avoid double execution, __main__ must be checked, as below,
#      otherwise all code in the module will be executed for every pickle.load.

if (__name__ == "__main__"):
    # Get our environment variables
    TOKEN = os.environ.get('BOT_TOKEN')
    OWNER_CHAT_ID = os.environ.get('OWNER_CHAT_ID')
    S3_BUCKET = os.environ.get('S3_BUCKET')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    REGION_HOST = os.environ.get('REGION_HOST')
    DEBUG = os.environ.get('DEBUG') == 'yes'

    #some "consts"
    MESSAGE_STATUS_FILENAME = 'message_status.pickle'
    MEME_DATA_FILENAME = 'meme_data.pickle'

    # set up bot
    BOT = telepot.Bot(TOKEN)

    MessageLoop(BOT, {'chat': handleChat, 'inline_query': handleInline, 'chosen_inline_result': handleChosenInline}).run_as_thread()
    print("Bot started successfully and is listening for messages.")

    # Infinite sleep main thread
    while 1:
        time.sleep(10)