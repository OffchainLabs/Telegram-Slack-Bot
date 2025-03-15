import os
import asyncio
from telethon import TelegramClient
from PyQt6 import QtWidgets
from ui_mainwindow import Ui_MainWindow  # ✅ Import UI
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # ✅ Load UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # ✅ Connect buttons to functions
        self.ui.pushButton.clicked.connect(self.send_message_telegram)  # Send to Telegram
        self.ui.pushButton_2.clicked.connect(self.send_message_slack)   # Send to Slack
        self.ui.pushButton_3.clicked.connect(self.select_image)         # Attach Image

        self.imagePath = None  # Store selected image path

    def select_image(self):
        """ Opens a file dialog to select an image. """
        file_dialog = QtWidgets.QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.imagePath = file_path
            self.ui.label.setText(f"Selected: {os.path.basename(file_path)}")

    async def get_group_ids(self, client, telegram_groups):
        """ Converts group names into group IDs for private groups. """
        group_ids = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group and dialog.name in telegram_groups:
                group_ids.append(dialog.id)
        return group_ids

    async def send_message_telegram_async(self):
        """ Sends a message (and optional image) to Telegram channels and private groups. """
        message = self.ui.plainTextEdit.toPlainText().strip()

        telegram_api_id = self.ui.telegramApiIdInput.text().strip()
        telegram_api_hash = self.ui.telegramApiHashInput.text().strip()
        telegram_channels = self.ui.telegramChannelsInput.toPlainText().strip().split("\n")
        telegram_groups = self.ui.telegramGroupsInput.toPlainText().strip().split("\n")

        if not message:
            QtWidgets.QMessageBox.warning(self, "Warning", "Message cannot be empty!")
            return

        if not telegram_api_id or not telegram_api_hash:
            QtWidgets.QMessageBox.critical(self, "Error", "Telegram API credentials are missing!")
            return

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
                    QtWidgets.QMessageBox.critical(self, "Error", f"Failed to send message to Telegram {recipient}: {e}")

    def send_message_telegram(self):
        """ Runs the Telegram send function asynchronously in PyQt. """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.send_message_telegram_async())

    def send_message_slack(self):
        """ Sends a message to Slack channels. """
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
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to send message to Slack {channel}: {e.response['error']}")

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = App()
    window.show()
    app.exec()
