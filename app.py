import os
import os.path
from flask import Flask, request
import telepot
import pprint
import time
from random import randint
import json
import boto
import boto.s3
import sys
from boto.s3.key import Key

MICAHMO_ID = 76034823

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

# message status "enum"
class MessageStatus:
    Unknown = 0
    WaitingForMeme = 1
    WaitingForMemeName = 2
    PendingApproval = 3

class Files:
    MessageStatus = 0
    MemeData = 1

# bot logic
def handle(msg):
    # load our message status
    message_status = load(Files.MessageStatus)

    #get our chat data
    content_type, chat_type, chat_id = telepot.glance(msg)
    chat_id = str(chat_id) #if it's not already a string...
    
    print(content_type)
    pprint.pprint(msg)

    if msg["chat"]["type"] == "private":

        if message_status.get(chat_id) == MessageStatus.PendingApproval:
            BOT.sendMessage(chat_id, "Hang on, your meme is pending approval. I'll let you know as soon as it's been added!")

        if content_type == 'text':
            if msg.get("text").lower() == "/start" or msg.get("text").lower() == "/help":
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
                BOT.sendMessage(chat_id, "Alright, I'll call it \"{}\". Now just wait a little while while I add it to my collection!")
                message_status[chat_id] = MessageStatus.Unknown

                
                BOT.sendMessage(MICAHMO_ID, "{} {} (@{}) is trying to add the following meme... Reply \"yes {}\" or \"no {}\" to approve or disapprove.".format(msg["chat"]["first_name"], msg["chat"]["last_name"], msg["chat"]["username"]), chat_id, chat_id)

            else:
                BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")
        
        elif content_type == 'photo':
            
            if message_status.get(chat_id) == MessageStatus.WaitingForMeme:
                BOT.sendMessage(chat_id, "Great, I got it! Now, what do you want to call it?")
                message_status[chat_id] = MessageStatus.WaitingForMemeName

                # save the picture with the id of this chatter
                pictureName = str(chat_id) + '.png'
                BOT.download_file(msg['photo'][-1]['file_id'], pictureName)
                upload_file(pictureName)

            elif message_status.get(chat_id) == MessageStatus.WaitingForMemeName: # we're waiting for a meme name, but they didn't sent a picture...
                BOT.sendMessage(chat_id, "Hmm, I'm still waiting for you to send me a name for the meme...")

        else:
            BOT.sendMessage(chat_id, "wat")


    # save our message status object
    save(Files.MessageStatus, message_status)

    #print our received message, for debugging purposes
    pprint.pprint(message_status)   


def save(file, object):

    fileName = get_filename_from_file(file)
    if (fileName == None): return

    # write our status to a file
    with open(fileName, 'w') as outfile:
        json.dump(object, outfile)

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
    with open(fileName) as json_data:
        object = json.load(json_data)

    # now delete our local file
    os.remove(fileName)

    #now return our new object
    return object

def get_filename_from_file(file):
    if (file == Files.MessageStatus): return MESSAGE_STATUS_FILENAME
    elif (file == Files.MemeData): return "bla"
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

    # get the file
    k = Key(bucket)
    k.key = fileName
    k.get_contents_to_filename(fileName)


# set up bot
BOT = telepot.Bot(TOKEN)
UPDATE_QUEUE = Queue()

BOT.message_loop(handle, source=UPDATE_QUEUE)

if (URL + SECRET) != BOT.getWebhookInfo()['url']:
    BOT.setWebhook() # unset if was set previously
    BOT.setWebhook(URL + SECRET)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0', port=PORT, debug=True)