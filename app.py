import os
import os.path
from flask import Flask, request
import telepot
import pprint
import time
from random import randint
import pickle
import boto
import boto.s3
import sys
from boto.s3.key import Key

MICAHMO_ID = '76034823'

PORT = int(os.environ.get('PORT', 5000))
TOKEN = "554574433:AAE6O2v3sm7yEQ9kJYW7GPp-JGnrUSyUMGM"
SECRET = "/BOT" + TOKEN
URL = "https://memebot42.herokuapp.com/"



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

# private fields
memes_in_progress = {} #make this local

#some "consts"
MESSAGE_STATUS_FILENAME = 'message_status.json'
MEME_DATA_FILENAME = 'meme_data.json'

# message status "enum"
class MessageStatus:
    Unknown = 0
    WaitingForMeme = 1
    WaitingForMemeName = 2
    PendingApproval = 3

class MemeStatus:
    PendingApproval = 0
    Approved = 1
    Rejected = 2
    Removed = 3

class Files:
    MessageStatus = 0
    MemeData = 1

# bot logic
def handleChat(msg):
    # load our message status
    message_status = load(Files.MessageStatus)
    meme_data = load(Files.MemeData)

    #get our chat data
    content_type, chat_type, chat_id = telepot.glance(msg)

    chat_id = str(chat_id) #if it's not already a string...
    
    print(content_type)
    pprint.pprint(msg)

    if msg["chat"]["type"] == "private":

        if chat_id != MICAHMO_ID and message_status.get(chat_id) == MessageStatus.PendingApproval:
            BOT.sendMessage(chat_id, "Hang on, your meme is pending approval. I'll let you know as soon as it's been added!")

        if content_type == 'text':
            if chat_id == MICAHMO_ID and msg.get("text").lower().startswith("yes"):
                # see if the given chat number is pending approval
                pending_apprval_chat_id = msg.get("text").split(' ')[1]
                if message_status.get(pending_apprval_chat_id) == MessageStatus.PendingApproval:
                    BOT.sendMessage(MICAHMO_ID, "Alright, it's been accepted.")
                    message_status[pending_apprval_chat_id] = MessageStatus.Unknown

                    memeName = ""

                    # update our meme data
                    for memeName, meme in meme_data.items():
                        if (meme.submitter == pending_apprval_chat_id and meme.status == MemeStatus.PendingApproval):
                            memeName = meme.name
                            meme.status = MemeStatus.Approved
                            break

                    # notify the user!
                    if (memeName != ""):
                        BOT.sendMessage(pending_apprval_chat_id, "Congratulations, your meme \"{}\" has been approved!".format(memeName))


            elif chat_id == MICAHMO_ID and msg.get("text").lower().startswith("no"):
                # see if the given chat number is pending approval
                pending_apprval_chat_id = msg.get("text").split(' ')[1]
                if message_status.get(pending_apprval_chat_id) == MessageStatus.PendingApproval:
                    BOT.sendMessage(MICAHMO_ID, "Alright, it's been rejected.")
                    message_status[pending_apprval_chat_id] = MessageStatus.Unknown

                    memeName = ""

                    # update our meme data
                    for memeName, meme in meme_data.items():
                        if (meme.submitter == pending_apprval_chat_id and meme.status == MemeStatus.PendingApproval):
                            # remove it from the dictionary
                            meme_data.pop(memeName, None)
                            break

                    #notify the user!
                    BOT.sendMessage(pending_apprval_chat_id, "Unfortunately, your meme has been rejected. :(")

            elif chat_id == MICAHMO_ID and msg.get("text").lower() == "/list":
                BOT.sendMessage(chat_id, pprint.pformat(meme_data, indent=4))

            elif chat_id == MICAHMO_ID and msg.get("text").lower().startswith("/delete"):
                memeToDelete = msg.get("text").lower().split(' ')[1]
                for memeName, meme in meme_data.items():
                    if (memeName == memeToDelete):
                        meme_data.pop(memeName, None)
                        BOT.sendMessage(chat_id, "Meme {} deleted.".format(memeName))
                        break

            elif msg.get("text").lower() == "/start" or msg.get("text").lower() == "/help":
                BOT.sendMessage(chat_id, "Hi {}! I am a customizable meme bot. :) Send me memes with the /addmeme command, and I'll add them to my collection!".format(msg["chat"]["first_name"]))

            elif msg.get("text").lower().startswith("/addmeme"):
                BOT.sendMessage(chat_id, "Awesome! Send me the meme!")
                upload_file('app.py')
                message_status[chat_id] = MessageStatus.WaitingForMeme

            elif msg.get("text").lower().startswith("/cancel") and message_status.get(chat_id) != MessageStatus.Unknown:
                BOT.sendMessage(chat_id, "Alright, consider it cancelled!")
                message_status[chat_id] = MessageStatus.Unknown

            elif msg.get("text").lower().startswith("/cancel") and message_status.get(chat_id) == MessageStatus.Unknown:
                BOT.sendMessage(chat_id, "Well, there's nothing to cancel, but ok. :)")
            
            elif message_status.get(chat_id) == MessageStatus.WaitingForMeme: # we're waiting for a meme, but they didn't send a picture
                BOT.sendMessage(chat_id, "Hmm, I didn't get a picture. Try again!")

            elif message_status.get(chat_id) == MessageStatus.WaitingForMemeName:
                memeName = msg["text"].replace(' ', "_")
                memeFileName = chat_id + ".png" # right now, the meme has the same name as the user
                memeNewFileName = memeName + ".png" # this is the new name we're gonna give it

                if (memeName in meme_data):
                    BOT.sendMessage(chat_id, "Ooh sorry! The name \"{}\" is already taken. Try a different name.".format(msg["text"]))
                
                else:
                    BOT.sendMessage(chat_id, "Alright, I'll call it \"{}\". Now just wait a little while while I add it to my collection!".format(msg["text"]))
                    message_status[chat_id] = MessageStatus.PendingApproval

                    # download the meme
                    open_file(memeFileName)

                    # rename and re-upload the meme
                    os.rename(memeFileName, memeNewFileName)
                    upload_file(memeNewFileName)

                    # add the meme to our meme data
                    meme_data[memeName] = Meme(memeName, memeNewFileName, MemeStatus.PendingApproval, chat_id)

                    # send the picture to Micah for approval
                    BOT.sendPhoto(MICAHMO_ID, open(memeNewFileName, 'rb'))
                    BOT.sendMessage(MICAHMO_ID, "{} {} (@{}) is trying to add the above meme... Reply \"yes {}\" or \"no {}\" to approve or disapprove.".format(msg["chat"]["first_name"], msg["chat"]["last_name"], msg["chat"]["username"], chat_id, chat_id))

            else:
                BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")
        
        elif content_type == 'photo':
            
            if message_status.get(chat_id) == MessageStatus.WaitingForMeme:
                BOT.sendMessage(chat_id, "Great, I got it! Now, what do you want to call it? Be as descriptive as possible!")
                message_status[chat_id] = MessageStatus.WaitingForMemeName

                # save the meme
                pictureName = chat_id + '.png' # for now, use the chatter's id as the filename
                BOT.download_file(msg['photo'][-1]['file_id'], pictureName)
                upload_file(pictureName)

            elif message_status.get(chat_id) == MessageStatus.WaitingForMemeName: # we're waiting for a meme name, but they didn't sent a picture...
                BOT.sendMessage(chat_id, "Hmm, I'm still waiting for you to send me a name for the meme...")

        else:
            BOT.sendMessage(chat_id, "wat")


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

    # do our "find" logic

    # construct our list of results
    photos = [dict(tpye='photo', id='blinking', photo_url=r'https://s3.us-east-2.amazonaws.com/meme42bot/blinking.png?response-content-disposition=inline&X-Amz-Security-Token=FQoDYXdzEMX%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaDH7XmQdoX5OEq5FaSCK4A8pwA1JbPukkPOqDXNrn0UmdBiW0RLWJRX6wl7dEJ%2BVmFtLurcbBgH551fMW8jLwPnzOOSY2siGJ0GNdcWfl%2Bm8FGdPAqQFPuqiIRXtBXA5FSwnD83Dk%2B6uECfiuP5hWOZcj8gjuF4bjj9G8%2BoqxyYVDU9qbrUseSqsQD2WqulNaQuwyvhvRFQaYDZ6xFyEYI%2FHOvOZuJQB66ysCRDl0aPLzpaADw7rexuKIxVlICRL9H0y0%2BEzt9SS%2BD9P%2B1xpPSjckQgWlXgP7YC%2Fjs2Hlo45J0nWWsB11egzDMZj%2Fg2K1YY4Yobf4GRa1fh%2Bnv69fTHGbjyb1bzkiSphPAZRVbNuyGh0dCdnQERkrTPRxqR1Hbtph0jVu3ZMeklY3dtWFsAvG2s8onBamLoRdM2VynM%2FvTDIv21m47nPigKRU5%2BQ6ZYJmRKg7F%2B1SInCuLlDZwN%2FBVEug0OO%2FrlGuSEHfpo78q%2BKOF%2Bjzo7YTWP%2B0lLC1XDG6%2BXgYEvOuc65IahZzN%2BYb875z99LPl6dwQ2CHrrGAsm8BUIW%2FaOKcRmZKB0WWU%2FopnkmbflAL%2BwdY%2BUCcUi7nNCJ92MgJKM%2FB3tYF&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20180418T201838Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAJYKPUTYRSTUBZEHQ%2F20180418%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Signature=ec26340b13a133db6795a932924f5a03cc2fc4d41ee5889f7326fd71ce29344c', thumb_url=photo1_url)]#, dict(type='photo', id='67890', photo_url=photo2_url, thumb_url=photo2_url)]


def handleChosenInline(msg):
    pprint.pprint(msg)


def save(file, object):

    fileName = get_filename_from_file(file)
    if (fileName == None): return

    # write our status to a file
    with open(fileName, 'wb') as outfile:
        # json.dump(object, outfile) #todo go back to this if jsonpickle doesn't work
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
            # object = json.load(json_data)
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

def upload_file(fileName):
    # get our env vars
    S3_BUCKET = os.environ.get('S3_BUCKET')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    # set up some environment variables that boto will need
    os.environ['S3_USE_SIGV4'] = 'True'
    os.environ['REGION_HOST'] = 's3.us-east-2.amazonaws.com'

    # get the connection
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, host=os.environ.get('REGION_HOST'))
    
    # get the bucket
    bucket = conn.get_bucket(S3_BUCKET)
    
    # create the file
    k = Key(bucket)
    k.key = fileName
    k.set_contents_from_filename(fileName)

def open_file(fileName):
    S3_BUCKET = os.environ.get('S3_BUCKET')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

    # set up some environment variables that boto will need
    os.environ['S3_USE_SIGV4'] = 'True'
    os.environ['REGION_HOST'] = 's3.us-east-2.amazonaws.com'

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
    def __init__(self, name, fileName, status, submitter):
        self.name = name
        self.fileName = fileName
        self.status = status
        self.submitter = submitter

    def __str__(self):
        return "name: {}, fileName: {}, status: {}, submitter: {}".format(self.name, self.fileName, self.status, self.submitter)

    def __repr__(self):
        return "name: {}, fileName: {}, status: {}, submitter: {}".format(self.name, self.fileName, self.status, self.submitter)
