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

# private fields
message_status = {}
memes_in_progress = {}

# message status "enum"
class MessageStatus:
    Unknown = 0
    WaitingForMeme = 1
    WaitingForMemeName = 2


# bot logic
def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    
    print(content_type)
    pprint.pprint(msg)

    if "text" in msg and msg["chat"]["type"] == "private" and msg["text"].lower() == "/start": #if we get a private message with "/start"
        BOT.sendMessage(chat_id, "Hi {}! I am a customizable meme bot. :) Send me memes with the /addmeme command, and I'll add them to my collection!".format(msg["chat"]["first_name"]))

    elif "text" in msg and msg["text"].lower().startswith("/addmeme"):
        BOT.sendMessage(chat_id, "Awesome! Send me the meme!")
        message_status[chat_id] = MessageStatus.WaitingForMeme

    elif "text" in msg and msg["text"].lower().startswith("/cancel") and chat_id in message_status and message_status[chat_id] != MessageStatus.Unknown:
        BOT.sendMessage(chat_id, "Alright, consider it cancelled!")
        message_status[chat_id] = MessageStatus.Unknown

    elif "text" in msg and msg["text"].lower().startswith("/cancel") and chat_id in message_status and message_status[chat_id] == MessageStatus.Unknown:
        BOT.sendMessage(chat_id, "Well, there's nothing to cancel, but ok. :)")

    elif "photo" in msg and chat_id in message_status and message_status[chat_id] == MessageStatus.WaitingForMeme: # and message is picture...?
        BOT.sendMessage(chat_id, "Great, I got it! Now, what do you want to call it?")
        message_status[chat_id] = MessageStatus.WaitingForMemeName
    
    elif chat_id in message_status and message_status[chat_id] == MessageStatus.WaitingForMeme:
        BOT.sendMessage(chat_id, "Hmm, I didn't get a picture. Try again!")

    elif chat_id in message_status and message_status[chat_id] == MessageStatus.WaitingForMemeName and "text" in msg:
        BOT.sendMessage(chat_id, "Alright, I'll call it {}. Now you can send it to other people by using @meme42bot!".format(msg["text"].replace(" ", "_")))

    else:
        BOT.sendMessage(chat_id, "Hmm, I'm not sure what you want. :( Feel free to send me a new meme with /addmeme!")

    pprint.pprint(message_status)   


# set up bot
BOT = telepot.Bot(TOKEN)
UPDATE_QUEUE = Queue()

BOT.message_loop(handle, source=UPDATE_QUEUE)

if (URL + SECRET) != BOT.getWebhookInfo()['url']:
    BOT.setWebhook() # unset if was set previously
    BOT.setWebhook(URL + SECRET)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0', port=PORT, debug=True)