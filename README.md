# MemeBot
A Telegram Bot written in Python using [telepot](https://github.com/nickoala/telepot). Allows users to upload and store media images by name, which can be searched and sent to other chats via inline message to the bot. Uses Amazon S3 for persistent storage. Runs in a Docker container.

Give it a try by messaging [@meme42bot](https://t.me/meme42bot) to upload some memes, and then @ the bot inline in another chat to send a previously uploaded meme. Or build and set up an instance of your own.

# Usage
To set up your meme collection, message the bot directly.

![](https://i.imgur.com/2dN470M.png)

To send an uploaded meme, message the bot inline in another chat. Matching memes will be displayed. Tap one to send it to the current chat.

![](https://i.imgur.com/JY5rYAG.png)