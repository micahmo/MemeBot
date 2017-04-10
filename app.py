import os
import os.path
from flask import Flask, request
import telepot
import pprint
import time
from random import randint
import json


# consts
LOW_MAGIC_NUMBER = 25
HIGH_MAGIC_NUMBER = 50

UNIX_ID = -27946567
LABMONS_ID = -4506728
BOTTESTS_ID = -164436920
MICAHMO_ID = 76034823
TIM_ID = 55712750

PORT = int(os.environ.get('PORT', 5000))
TOKEN = "378332395:AAG1Brzgor5YKYAUuqtek4Tknv1xasbsJXE"
SECRET = "/BOT" + TOKEN
URL = "https://validBOT.herokuapp.com/"



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
    global num, rand_num
    num += 1

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
        data[chat_id] = str(chat_id) + " is @" + msg["chat"]["username"]
    elif (msg["chat"]["type"] == "group"):
        data[chat_id] = str(chat_id) + " is group " + msg["chat"]["title"]

    # re-write the file
    with open('data.json', 'w') as f: # create or truncate file for writing
        json.dump(data, f)
        

    print("num " + str(num))
    print("rand_num " + str(rand_num))
    pprint.pprint(msg)

    # don't let randos use teh Bot
    if (chat_id != UNIX_ID and
        chat_id != LABMONS_ID and
        chat_id != BOTTESTS_ID and
        chat_id != TIM_ID and
        chat_id != MICAHMO_ID): # me
        BOT.sendMessage(chat_id, "You must receive permission from the developer, @micahmo, to use this bot.")
        print("Sent because INVALID chat")
        return


    if chat_id == MICAHMO_ID:# or chat_id == TIM_ID:
        if msg["text"].lower() == "help":
            with open('data.json', 'r') as f: # file WILL exist at this point; open for reading
                data = json.load(f)
                chatz = ""
                for key, value in data.items():
                    chatz += value + "\n"

                BOT.sendMessage(chat_id, "These are the chats that I know about: \n\n" + chatz + "\n Send a message to one of these chats by typing \"<ID>: <message>\"")
        else:
            try:
                parts = msg["txt"].split(":")
                parts[0] = parts[0].strip()
                parts[1] = parts[1].strip()
                print("Sending message \"" + parts[1] + "\" to chat " + str(int(parts[0])))
                BOT.sendMessage(int(parts[0]), parts[1])
                BOT.sendMessage(chat_id, "Message sent!")
            except Exception, e:
                print("Failed to send message: " + str(e))


    # let Tim send leet haxor messages
    if chat_id == TIM_ID and "valid" == msg["text"].lower():
        BOT.sendMessage(-27946567, msg["text"])
        print("Sent because of DM from Tim")
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


# set up bot
BOT = telepot.Bot(TOKEN)
UPDATE_QUEUE = Queue()

num = 0
rand_num = randint(LOW_MAGIC_NUMBER,HIGH_MAGIC_NUMBER)

BOT.message_loop(handle, source=UPDATE_QUEUE)

if (URL + SECRET) != BOT.getWebhookInfo()['url']:
    BOT.setWebhook(URL + SECRET)

if (__name__ == "__main__"):
    app.run(host='0.0.0.0', port=PORT, debug=True)