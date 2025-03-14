from telethon.sync import TelegramClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Credentials
API_ID = os.getenv("TELEGRAM_API_ID")  # Replace with your API ID
API_HASH = os.getenv("TELEGRAM_API_HASH")  # Replace with your API Hash
SESSION_NAME = "my_telegram"

# Start Telethon client
with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
    print("\n📌 Fetching all groups you are a member of...\n")
    group_list = []
    
    for dialog in client.iter_dialogs():
        if dialog.is_group:
            group_list.append((dialog.name, dialog.id))
    
    if not group_list:
        print("❌ No groups found.")
    else:
        print("✅ Here are all the groups you are in:\n")
        for name, group_id in group_list:
            print(f"📌 Group Name: {name}")
            print(f"   🔹 Group ID: {group_id}")
            print("-" * 40)
