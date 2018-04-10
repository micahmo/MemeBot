import os
import os.path
from flask import Flask, request
import telepot
import pprint
import time
from random import randint
import json

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

# private field
message_status = {}

# message status "enum"
class MessageStatus:
    Unknown = 0
    WaitingForMeme = 1


# bot logic
def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    
    pprint.pprint(msg)
    pprint(message_status)

    if msg["chat"]["type"] == "private" and msg["text"].lower() == "/start": #if we get a private message with "/start"
        BOT.sendMessage(chat_id, "Hi {}! I am a customizable meme bot. :) Send me memes with the /addmeme command, and I'll add them to my collection!".format(msg["chat"]["first_name"]))

    elif msg["text"].lower() == "/addmeme":
        BOT.sendMessage(chat_id, "Awesome! Send me the meme!")
        message_status[chat_id] = MessageStatus.WaitingForMeme

    


# set up bot
BOT = telepot.Bot(TOKEN)
UPDATE_QUEUE = Queue()

BOT.message_loop(handle, source=UPDATE_QUEUE)

if (URL + SECRET) != BOT.getWebhookInfo()['url']:
    BOT.setWebhook() # unset if was set previously
    BOT.setWebhook(URL + SECRET)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0', port=PORT, debug=True)