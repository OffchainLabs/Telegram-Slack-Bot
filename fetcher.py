from telethon.sync import TelegramClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Credentials
API_ID = os.getenv("TELEGRAM_API_ID")  # Replace with your API ID if not using .env
API_HASH = os.getenv("TELEGRAM_API_HASH")  # Replace with your API Hash if not using .env
SESSION_NAME = "my_telegram"

OUTPUT_FILE = "telegram_groups.txt"  # File to save group list

def save_groups_to_file(groups):
    """ Save group list to a text file. """
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write("📌 Telegram Groups List\n")
        file.write("=" * 30 + "\n\n")
        for name, group_id in groups:
            file.write(f"📌 Group Name: {name}\n")
            file.write(f"   🔹 Group ID: {group_id}\n")
            file.write("-" * 40 + "\n")

    print(f"\n✅ Group list saved to {OUTPUT_FILE}\n")

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

        # Save groups to a file
        save_groups_to_file(group_list)
