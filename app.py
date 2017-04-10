import os
from flask import Flask, request
import telepot
import pprint
import time
from random import randint

LOW_MAGIC_NUMBER = 10
HIGH_MAGIC_NUMBER = 25

PORT = int(os.environ.get('PORT', 5000))
TOKEN = "378332395:AAG1Brzgor5YKYAUuqtek4Tknv1xasbsJXE"
SECRET = "/BOT" + TOKEN
URL = "https://validBOT.herokuapp.com/"

try:
    from Queue import Queue
except ImportError:
    from queue import Queue

app = Flask(__name__)
@app.route(SECRET, methods=['GET', 'POST'])
def pass_update():
    UPDATE_QUEUE.put(request.data)  # pass update to BOT
    return 'OK'

def handle(msg):
    global num, rand_num
    num += 1

    print("num " + str(num))
    print("rand_num " + str(rand_num))
    pprint.pprint(msg)

    content_type, chat_type, chat_id = telepot.glance(msg)

    # don't let randos use teh Bot
    if (chat_id != -27946567 and chat_id != -4506728 and chat_id != -164436920):
        BOT.sendMessage(chat_id, "You must receive permission from the developer, @micahmo, to use this bot.")
        print("Sent because INVALID chat")
        return
    
    if ("valid" == msg["text"].lower()):
        BOT.sendPhoto(chat_id, open("image.jpg", "rb"))
        print("Sent because \"valid\" was exact message of text")
    elif (num == rand_num):
        BOT.sendMessage(chat_id, "Valid")
        print("Sent because we reached the random number " + str(rand_num))
        num = 0
        rand_num = randint(LOW_MAGIC_NUMBER, HIGH_MAGIC_NUMBER)
    elif str(msg["from"]["id"]) == "55712750" and len(msg["text"]) > 100:
        BOT.sendMessage(chat_id, "Valid")
        print("Sent because long message from Tim")
    elif len(msg["text"]) > 200:
        BOT.sendMessage(chat_id, "Valid")
        print("Sent because message long af")
    elif (num % 2 == 0):
        if ("valid" in msg["text"].lower()):
            BOT.sendMessage(chat_id, "Valid")
            print("Sent because \"valid\" in message text and it's an even interval")
        elif ("nintendo" in msg["text"].lower() or "switch" in msg["text"].lower()):
            BOT.sendMessage(chat_id, "Valid")
            print("Sent because \"nintento\" or \"switch\" in message text and it's an even interval")
        elif ("tfw" in msg["text"].lower()):
            BOT.sendMessage(chat_id, "Valid")
            print("Sent because \"tfw\" in message text and it's an even interval")
        elif ("tim" in msg["text"].lower() and "time" not in msg["text"].lower()):
            BOT.sendMessage(chat_id, "Valid")
            print("Sent because \"tim\" (but not \"time\") in message text and it's an even interval")


BOT = telepot.Bot(TOKEN)
UPDATE_QUEUE = Queue()

# BOT.setWebhook(URL + SECRET)

num = 0
rand_num = randint(LOW_MAGIC_NUMBER,HIGH_MAGIC_NUMBER)

BOT.message_loop(handle, source=UPDATE_QUEUE)


if (URL + SECRET) != BOT.getWebhookInfo()['url']:
    BOT.setWebhook(URL + SECRET)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0', port=PORT, debug=True)