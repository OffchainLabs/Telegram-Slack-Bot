from telethon import TelegramClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Credentials (loaded from environment variables)
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION_NAME = "my_account"

# Slack Credentials
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Channels
TELEGRAM_CHANNELS = os.getenv("TELEGRAM_CHANNELS", "").split(",")
SLACK_CHANNELS = os.getenv("SLACK_CHANNELS", "").split(",")

async def send_message_telegram(message):
    """ Sends a message to multiple Telegram channels. """
    async with TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
        for channel in TELEGRAM_CHANNELS:
            try:
                await client.send_message(channel, message)
                print(f"✅ Message sent to Telegram {channel}")
            except Exception as e:
                print(f"❌ Failed to send message to Telegram {channel}: {e}")

def send_message_slack(message):
    """ Sends a message to multiple Slack channels. """
    client = WebClient(token=SLACK_BOT_TOKEN)
    for channel in SLACK_CHANNELS:
        try:
            response = client.chat_postMessage(channel=channel, text=message)
            print(f"✅ Message sent to Slack {channel}: {response['ts']}")
        except SlackApiError as e:
            print(f"❌ Failed to send message to Slack {channel}: {e.response['error']}")

async def send_message_to_all(message):
    """ Sends message to both Telegram and Slack. """
    await send_message_telegram(message)
    send_message_slack(message)

# Example usage
if __name__ == "__main__":
    message_text = "Hello! This is a test message sent to both Telegram & Slack."
    asyncio.run(send_message_to_all(message_text))
