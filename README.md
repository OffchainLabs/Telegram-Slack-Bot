# Telegram Slack Bot 🚀

This script allows you to send messages to multiple Telegram and Slack channels at once.

## Features
✅ Send messages to multiple Telegram channels and Telegram groups
✅ Send messages to multiple Slack channels  
✅ Send image with your message
✅ Uses your **Telegram account** (not a bot)  
✅ Secure API credentials with `.env` file  

## Installation and Use
1. Clone this repo
2. Install requirements:
   ```bash
   pip install -r requirements.txt 
   ```
3. Copy ```config.env``` file and remove ```config``` from the file name
4. Add ```TELEGRAM_API_ID```, ```TELEGRAM_API_HASH```,```SLACK_BOT_TOKEN```, ```TELEGRAM_CHANNELS```, and ```SLACK_CHANNELS``` to the ```.env``` file. Also add name of the Telegram groups you want to send messages in ```TELEGRAM_GROUPS``` in ```.env``` file seprating them with ```,``` without spaces between group names.
5. Run the script with this command:
   ```bash
   python main.py   
    ```
6. Write message you want to send on a ```txt``` file.
7. Drag the ```.txt``` file in the terminal when you see the message ```Enter the message file path (or press Enter to type manually):```
8. Answer ```y``` to ```Send to Telegram? (y/n): ``` if you want to send to Telegram
9. Answer ```y``` to ```Send to Slack? (y/n): ``` if you want to send to Slack
10. Answer ```y``` to ```Do you want to send an image? (y/n): ``` if you want to send an image with your message
11. If you decided to send an image, drop the image in your terminal after this message otherwise skip: ```Enter image file path (or press Enter to skip): ```
12. Done with message: ✅ Message sent to ... 🎉

