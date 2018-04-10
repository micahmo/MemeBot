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



# bot logic
def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    
    # keep track of whom the message is from
    data = {}
    if os.path.isfile("data.json"):
        with open('data.json', 'r') as f: # open for reading if file exists
            try:
                data = json.load(f)
            except:
                pass
    
    if (msg["chat"]["type"] == "private"):
        data[chat_id] = str(chat_id) + " is user @" + msg["chat"]["username"]
    elif (msg["chat"]["type"] == "group"):
        data[chat_id] = str(chat_id) + " is group " + msg["chat"]["title"]

    # re-write the file
    with open('data.json', 'w') as f: # create or truncate file for writing
        json.dump(data, f)

    pprint.pprint(msg)

    if msg["chat"]["type"] == "private" and msg["text"].lower() == "/start": #if we get a private message with "/start"
        BOT.sendMessage(chat_id, "Hi {}! I am a customizable meme bot. :) Send me memes with the /addmeme command, and I'll add them to my collection!".format(msg["chat"]["username"]))


# set up bot
BOT = telepot.Bot(TOKEN)
UPDATE_QUEUE = Queue()

BOT.message_loop(handle, source=UPDATE_QUEUE)

if (URL + SECRET) != BOT.getWebhookInfo()['url']:
    BOT.setWebhook() # unset if was set previously
    BOT.setWebhook(URL + SECRET)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0', port=PORT, debug=True)