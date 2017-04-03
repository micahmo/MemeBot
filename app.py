import os
from flask import Flask, request
import telepot
import pprint
import time
from random import randint

LOW_MAGIC_NUMBER = 25
HIGH_MAGIC_NUMBER = 50

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

    content_type, chat_type, chat_id = telepot.glance(msg)

    if ("valid" == msg["text"].lower()):
        BOT.sendPhoto(chat_id, open("image.jpg", "rb"))
    elif ("valid" in msg["text"].lower()):
        BOT.sendMessage(chat_id, "Valid")
    elif (num == rand_num and rand_num % 2 == 0):
        BOT.sendMessage(chat_id, "Valid")
        num = 0
        rand_num = randint(LOW_MAGIC_NUMBER,HIGH_MAGIC_NUMBER)
    elif (num == rand_num and rand_num % 2 == 1):
        BOT.sendPhoto(chat_id, open("image.jpg", "rb"))
        num = 0
        rand_num = randint(LOW_MAGIC_NUMBER,HIGH_MAGIC_NUMBER)



BOT = telepot.Bot(TOKEN)
UPDATE_QUEUE = Queue()

# BOT.setWebhook(URL + SECRET)

num = 0
rand_num = randint(LOW_MAGIC_NUMBER,HIGH_MAGIC_NUMBER)

BOT.message_loop({"chat": handle}, source=UPDATE_QUEUE)


if (URL + SECRET) != BOT.getWebhookInfo()['url']:
    BOT.setWebhook(URL + SECRET)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0', port=PORT, debug=True)