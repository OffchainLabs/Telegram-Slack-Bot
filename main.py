import os
import sys
import asyncio
from telethon import TelegramClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)  # ✅ Force reload the .env file

# Telegram Credentials
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION_NAME = "my_account"

# Slack Credentials
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Channels and Groups (Loaded from .env file, separated by commas)
TELEGRAM_CHANNELS = os.getenv("TELEGRAM_CHANNELS", "").split(",") if os.getenv("TELEGRAM_CHANNELS") else []
TELEGRAM_GROUPS = os.getenv("TELEGRAM_GROUPS", "").split(",") if os.getenv("TELEGRAM_GROUPS") else []
SLACK_CHANNELS = os.getenv("SLACK_CHANNELS", "").split(",") if os.getenv("SLACK_CHANNELS") else []

def read_message_from_file():
    """ Ask user for a text file and read its content. """
    file_path = input("Enter the message file path (or press Enter to type manually): ").strip()

    # Remove unnecessary surrounding quotes (single or double)
    if file_path.startswith(("'", '"')) and file_path.endswith(("'", '"')):
        file_path = file_path[1:-1]

    if file_path:
        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {file_path}. Please enter a valid file path.")
            return read_message_from_file()  # Ask again if file does not exist
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read().strip()  # Read full content and remove extra spaces
    else:
        return input("Enter the message to send: ")  # Fallback to manual entry

def get_image_path():
    """ Ask user for the image file path and process it correctly to handle spaces and special characters. """
    image_path = input("Enter image file path (or press Enter to skip): ").strip().strip('"').strip("'")  # Remove surrounding quotes
    if image_path:
        image_path = os.path.expanduser(image_path)  # Handle ~ for home directory
        image_path = os.path.abspath(image_path)  # Convert to absolute path
        if not os.path.exists(image_path):
            print(f"⚠️ File not found: {image_path}. Please enter a valid image path.")
            return get_image_path()  # Ask again if file does not exist
    return image_path if image_path else None

async def get_group_ids(client):
    """ Converts group names into group IDs for private groups. """
    group_ids = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group and dialog.name in TELEGRAM_GROUPS:
            group_ids.append(dialog.id)
    return group_ids

async def send_message_telegram(message, image_path=None):
    """ Sends a message (and optional image) to Telegram channels and groups. """
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("⚠️ Telegram API credentials are missing! Skipping Telegram messages.")
        return
    if not TELEGRAM_CHANNELS and not TELEGRAM_GROUPS:
        print("⚠️ No Telegram channels or groups specified! Skipping Telegram messages.")
        return
    
    async with TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
        group_ids = await get_group_ids(client)

        # Combine channels and private group IDs
        recipients = TELEGRAM_CHANNELS + group_ids

        for recipient in recipients:
            try:
                if image_path:
                    await client.send_file(recipient, image_path, caption=message)
                    print(f"✅ Image + message sent to Telegram {recipient}")
                else:
                    await client.send_message(recipient, message)
                    print(f"✅ Message sent to Telegram {recipient}")
            except Exception as e:
                print(f"❌ Failed to send message to Telegram {recipient}: {e}")

def send_message_slack(message, image_path=None):
    """ Sends a message (and optional image) to Slack channels. """
    if not SLACK_BOT_TOKEN:
        print("⚠️ Slack Bot Token is missing! Skipping Slack messages.")
        return
    if not SLACK_CHANNELS:
        print("⚠️ No Slack channels specified! Skipping Slack messages.")
        return

    client = WebClient(token=SLACK_BOT_TOKEN)
    for channel in SLACK_CHANNELS:
        try:
            if image_path:
                response = client.files_upload(channels=channel, file=image_path, title=message)
                print(f"✅ Image + message sent to Slack {channel}: {response['file']['id']}")
            else:
                response = client.chat_postMessage(channel=channel, text=message)
                print(f"✅ Message sent to Slack {channel}: {response['ts']}")
        except SlackApiError as e:
            print(f"❌ Failed to send message to Slack {channel}: {e.response['error']}")

async def send_message_to_all(message, image_path=None, send_to_telegram=True, send_to_slack=True):
    """ Sends message (and optional image) to Telegram, Slack, or both. """
    if send_to_telegram:
        await send_message_telegram(message, image_path)
    if send_to_slack:
        send_message_slack(message, image_path)

if __name__ == "__main__":
    # Get message from file or manual input
    message_text = read_message_from_file()

    # Ask user where to send the message
    send_to_telegram = input("Send to Telegram? (y/n): ").strip().lower() == "y"
    send_to_slack = input("Send to Slack? (y/n): ").strip().lower() == "y"

    # Ask if they want to send an image
    add_image = input("Do you want to send an image? (y/n): ").strip().lower() == "y"
    image_path = get_image_path() if add_image else None

    if not send_to_telegram and not send_to_slack:
        print("⚠️ No destination selected. Exiting.")
        sys.exit(1)

    asyncio.run(send_message_to_all(message_text, image_path, send_to_telegram, send_to_slack))
