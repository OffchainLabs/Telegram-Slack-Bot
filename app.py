import os
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, AuthRestartError
from PyQt6 import QtWidgets
from ui_mainwindow import Ui_MainWindow
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from notion_client import Client  # Notion SDK
import qasync  # Integrates asyncio with Qt event loop

# Your Notion DB ID (hardcoded)
NOTION_DATABASE_ID = "1d001a3f59f881c09cf2fc79f57ac4ac"

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Load the UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # If present, initialize the login status label
        if hasattr(self.ui, "loginStatusLabel"):
            self.ui.loginStatusLabel.setText("Not logged in")
        
        # Connect buttons to functions
        self.ui.pushButton.clicked.connect(self.send_message_telegram)
        self.ui.pushButton_2.clicked.connect(self.send_message_slack)
        self.ui.pushButton_3.clicked.connect(self.select_image)
        self.ui.useNotionCheckbox.stateChanged.connect(self.toggle_notion_mode)
        
        # Default state: disable Notion fields
        self.ui.notionTagSelector.setEnabled(False)
        self.ui.notionApiTokenInput.setEnabled(False)
        
        self.imagePath = None
        
        # Create a lock to ensure only one telegram send task runs at a time
        self._tg_lock = asyncio.Lock()

    def toggle_notion_mode(self):
        is_checked = self.ui.useNotionCheckbox.isChecked()
        self.ui.notionTagSelector.setEnabled(is_checked)
        self.ui.notionApiTokenInput.setEnabled(is_checked)
        # Disable manual inputs when Notion mode is enabled
        self.ui.telegramGroupsInput.setEnabled(not is_checked)
        self.ui.telegramChannelsInput.setEnabled(not is_checked)
        self.ui.slackChannelsInput.setEnabled(not is_checked)

    def select_image(self):
        file_dialog = QtWidgets.QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.imagePath = file_path
            self.ui.label.setText(f"Selected: {os.path.basename(file_path)}")

    async def async_get_text(self, prompt: str) -> str:
        """
        Creates and shows a QInputDialog non-blockingly.
        Returns the text entered by the user (or an empty string if canceled).
        """
        dialog = QtWidgets.QInputDialog(self)
        dialog.setLabelText(prompt)
        dialog.setWindowTitle("Login Required")
        dialog.setModal(True)
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def finished(result):
            # QDialog returns an int code; if accepted, retrieve text.
            # Note: QInputDialog.textValue() returns the current text.
            future.set_result(dialog.textValue().strip())
            dialog.deleteLater()

        dialog.finished.connect(finished)
        dialog.show()
        return await future

    async def get_group_ids(self, client, telegram_groups):
        group_ids = []
        async for dialog in client.iter_dialogs():
            if dialog.is_group and dialog.name in telegram_groups:
                group_ids.append(dialog.id)
        return group_ids

    def get_telegram_groups_by_tags(self, notion_token, selected_tags):
        client_notion = Client(auth=notion_token)
        try:
            tag_filters = [
                {"property": "Tags", "multi_select": {"contains": tag}}
                for tag in selected_tags
            ]
            response = client_notion.databases.query(
                database_id=NOTION_DATABASE_ID,
                filter={
                    "and": [
                        {"property": "Platform", "rich_text": {"contains": "Telegram"}},
                        {"or": tag_filters},
                    ]
                },
            )
            groups = []
            for result in response["results"]:
                rt = result["properties"]["Chat Name"]["rich_text"]
                if rt:
                    groups.append(rt[0]["plain_text"])
            return groups
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to fetch groups from Notion: {e}"
            )
            return []

    async def send_message_telegram_async(self):
        async with self._tg_lock:
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

            # Prepare the session file path in the user's home directory.
            session_dir = os.path.join(os.path.expanduser("~"), ".TelegramSlackApp")
            os.makedirs(session_dir, exist_ok=True)
            session_file = os.path.join(session_dir, "my_account.session")

            client = TelegramClient(session_file, telegram_api_id, telegram_api_hash)
            await client.connect()

            if not await client.is_user_authorized():
                phone = await self.async_get_text("Enter your phone number (with country code):")
                if not phone:
                    QtWidgets.QMessageBox.critical(self, "Error", "Phone number is required!")
                    return
                await client.send_code_request(phone)
                # Wait a little longer to yield control and let Telethon finish its internal tasks
                await asyncio.sleep(1.0)
                code = await self.async_get_text("Enter the code sent to you:")
                try:
                    await client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    pw = await self.async_get_text("Two-step verification is enabled. Enter your password:")
                    await client.sign_in(password=pw)
                except AuthRestartError as e:
                    QtWidgets.QMessageBox.critical(
                        self, "Error", f"Authorization restarted, please try again: {e}"
                    )
                    return
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Failed to sign in: {e}")
                    return
                if hasattr(self.ui, "loginStatusLabel"):
                    me = await client.get_me()
                    self.ui.loginStatusLabel.setText(
                        f"Logged in as: {me.first_name if me.first_name else me.username}"
                    )

            # Determine how to get the group list.
            if self.ui.useNotionCheckbox.isChecked():
                notion_token = self.ui.notionApiTokenInput.text().strip()
                selected_tags = [item.text() for item in self.ui.notionTagSelector.selectedItems()]
                telegram_groups = self.get_telegram_groups_by_tags(notion_token, selected_tags)
            else:
                telegram_groups = self.ui.telegramGroupsInput.toPlainText().strip().split("\n")

            group_ids = await self.get_group_ids(client, telegram_groups)
            recipients = telegram_channels + group_ids

            for recipient in recipients:
                try:
                    if self.imagePath:
                        await client.send_file(recipient, self.imagePath, caption=message)
                        QtWidgets.QMessageBox.information(
                            self, "Success", f"Image + message sent to Telegram {recipient}"
                        )
                    else:
                        await client.send_message(recipient, message)
                        QtWidgets.QMessageBox.information(
                            self, "Success", f"Message sent to Telegram {recipient}"
                        )
                except Exception as e:
                    QtWidgets.QMessageBox.critical(
                        self, "Error", f"Failed to send to {recipient}: {e}"
                    )
            await client.disconnect()

    def send_message_telegram(self):
        # Schedule the Telegram coroutine on the running event loop.
        asyncio.create_task(self.send_message_telegram_async())

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
                QtWidgets.QMessageBox.information(
                    self, "Success", f"Message sent to Slack {channel}"
                )
            except SlackApiError as e:
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to send to Slack {channel}: {e.response['error']}"
                )

if __name__ == "__main__":
    import qasync
    app = QtWidgets.QApplication([])
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = App()
    window.show()
    with loop:
        loop.run_forever()
