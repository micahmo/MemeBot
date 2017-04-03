import telepot
import pprint
import time
from random import randint

LOW_MAGIC_NUMBER = 25
HIGH_MAGIC_NUMBER = 50

def handle(msg):
    global num, rand_num
    num += 1

    print("num " + str(num))
    print("rand_num " + str(rand_num))

    content_type, chat_type, chat_id = telepot.glance(msg)

    if ("valid" == msg["text"].lower()):
        bot.sendPhoto(chat_id, open("image.jpg", "rb"))
    elif ("valid" in msg["text"].lower()):
        bot.sendMessage(chat_id, "Valid")
    elif (num == rand_num and rand_num % 2 == 0):
        bot.sendMessage(chat_id, "Valid")
        num = 0
        rand_num = randint(LOW_MAGIC_NUMBER,HIGH_MAGIC_NUMBER)
    elif (num == rand_num and rand_num % 2 == 1):
        bot.sendPhoto(chat_id, open("image.jpg", "rb"))
        num = 0
        rand_num = randint(LOW_MAGIC_NUMBER,HIGH_MAGIC_NUMBER)


bot = telepot.Bot("378332395:AAG1Brzgor5YKYAUuqtek4Tknv1xasbsJXE")
bot.message_loop(handle)
num = 0
rand_num = randint(LOW_MAGIC_NUMBER,HIGH_MAGIC_NUMBER)

while 1:
    time.sleep(10)