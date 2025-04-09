import os
import asyncio
from telethon import TelegramClient
from PyQt6 import QtWidgets
from ui_mainwindow import Ui_MainWindow
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from notion_client import Client  # ✅ Notion SDK

# Your Notion DB ID (safe to hardcode)
NOTION_DATABASE_ID = "your-database-id-here"  # 👈 Replace this

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # ✅ Load UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # ✅ Connect buttons to functions
        self.ui.pushButton.clicked.connect(self.send_message_telegram)
        self.ui.pushButton_2.clicked.connect(self.send_message_slack)
        self.ui.pushButton_3.clicked.connect(self.select_image)
        self.ui.useNotionCheckbox.stateChanged.connect(self.toggle_notion_mode)

        # ✅ Default state
        self.ui.notionTagSelector.setEnabled(False)
        self.ui.notionApiTokenInput.setEnabled(False)

        self.imagePath = None

    def toggle_notion_mode(self):
        is_checked = self.ui.useNotionCheckbox.isChecked()
        self.ui.notionTagSelector.setEnabled(is_checked)
        self.ui.notionApiTokenInput.setEnabled(is_checked)
        self.ui.telegramGroupsInput.setEnabled(not is_checked)

    def select_image(self):
        file_dialog = QtWidgets.QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.imagePath = file_path
            self.ui.label.setText(f"Selected: {os.path.basename(file_path)}")

    async def get_group_ids(self, client, telegram_groups):
        group_ids = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group and dialog.name in telegram_groups:
                group_ids.append(dialog.id)
        return group_ids

    def get_telegram_groups_by_tags(self, notion_token, selected_tags):
        client = Client(auth=notion_token)
        try:
            tag_filters = [{"property": "Tags", "multi_select": {"contains": tag}} for tag in selected_tags]
            response = client.databases.query(
                **{
                    "database_id": NOTION_DATABASE_ID,
                    "filter": {
                        "and": [
                            {"property": "Platform", "rich_text": {"contains": "Telegram"}},
                            {"or": tag_filters}
                        ]
                    }
                }
            )
            groups = []
            for result in response["results"]:
                name = result["properties"]["Chat Name"]["rich_text"][0]["plain_text"]
                groups.append(name)
            return groups
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to fetch groups from Notion: {e}")
            return []

    async def send_message_telegram_async(self):
        message = self.ui.plainTextEdit.toPlainText().strip()

        telegram_api_id = self.ui.telegramApiIdInput.text().strip()
        telegram_api_hash = self.ui.telegramApiHashInput.text().strip()
        telegram_channels = self.ui.telegramChannelsInput.toPlainText().strip().split("\n")

        if not message:
            QtWidgets.QMessageBox.warning(self, "Warning", "Message cannot be empty!")
            return

        if not telegram_api_id or not telegram_api_hash:
            QtWidgets.QMessageBox.critical(self, "Error", "Telegram API credentials are missing!")
            return

        # ✅ Determine how to get group list
        if self.ui.useNotionCheckbox.isChecked():
            notion_token = self.ui.notionApiTokenInput.text().strip()
            selected_tags = [item.text() for item in self.ui.notionTagSelector.selectedItems()]
            telegram_groups = self.get_telegram_groups_by_tags(notion_token, selected_tags)
        else:
            telegram_groups = self.ui.telegramGroupsInput.toPlainText().strip().split("\n")

        async with TelegramClient("my_account", telegram_api_id, telegram_api_hash) as client:
            group_ids = await self.get_group_ids(client, telegram_groups)
            recipients = telegram_channels + group_ids

            for recipient in recipients:
                try:
                    if self.imagePath:
                        await client.send_file(recipient, self.imagePath, caption=message)
                        QtWidgets.QMessageBox.information(self, "Success", f"Image + message sent to Telegram {recipient}")
                    else:
                        await client.send_message(recipient, message)
                        QtWidgets.QMessageBox.information(self, "Success", f"Message sent to Telegram {recipient}")
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Failed to send to {recipient}: {e}")

    def send_message_telegram(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.send_message_telegram_async())

    def send_message_slack(self):
        message = self.ui.plainTextEdit.toPlainText().strip()
        slack_bot_token = self.ui.slackBotTokenInput.text().strip()
        slack_channels = self.ui.slackChannelsInput.toPlainText().strip().split("\n")

        if not message:
            QtWidgets.QMessageBox.warning(self, "Warning", "Message cannot be empty!")
            return

        if not slack_bot_token:
            QtWidgets.QMessageBox.critical(self, "Error", "Slack bot token is missing!")
            return

        client = WebClient(token=slack_bot_token)
        for channel in slack_channels:
            try:
                response = client.chat_postMessage(channel=channel, text=message)
                QtWidgets.QMessageBox.information(self, "Success", f"Message sent to Slack {channel}")
            except SlackApiError as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to send to Slack {channel}: {e.response['error']}")

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = App()
    window.show()
    app.exec()
