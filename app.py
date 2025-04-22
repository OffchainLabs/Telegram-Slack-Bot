import os
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, AuthRestartError
from PyQt6 import QtWidgets, QtCore
from ui_mainwindow import Ui_MainWindow
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from notion_client import Client  # Notion SDK
import qasync  # Integrates asyncio with the Qt event loop

# Your Notion DB ID (hardcoded)
NOTION_DATABASE_ID = "1d001a3f59f881c09cf2fc79f57ac4ac"

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        if hasattr(self.ui, "loginStatusLabel"):
            self.ui.loginStatusLabel.setText("Not logged in")

        self.ui.pushButton.clicked.connect(self.send_message_telegram)
        self.ui.pushButton_2.clicked.connect(self.send_message_slack)
        self.ui.pushButton_3.clicked.connect(self.select_image)
        self.ui.useNotionCheckbox.stateChanged.connect(self.toggle_notion_mode)

        if hasattr(self.ui, "removeImageButton"):
            self.ui.removeImageButton.clicked.connect(self.remove_image)
            self.ui.removeImageButton.setVisible(False)

        self.ui.notionTagSelector.setEnabled(False)
        self.ui.notionApiTokenInput.setEnabled(False)

        self.imagePath = None
        self._tg_lock = asyncio.Lock()
        self.tg_client = None

        self.ui.notionApiTokenInput.editingFinished.connect(self.load_notion_tags)

    def load_notion_tags(self):
        notion_token = self.ui.notionApiTokenInput.text().strip()
        if not notion_token:
            return
        try:
            client_notion = Client(auth=notion_token)
            db = client_notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
            tags = db["properties"]["Category"]["multi_select"]["options"]

            self.ui.notionTagSelector.clear()
            for tag in tags:
                item = QtWidgets.QListWidgetItem(tag["name"])
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
                self.ui.notionTagSelector.addItem(item)
        except Exception as e:
            print(f"[ERROR] Failed to load tags from Notion: {e}")

    def toggle_notion_mode(self):
        is_checked = self.ui.useNotionCheckbox.isChecked()
        self.ui.notionTagSelector.setEnabled(is_checked)
        self.ui.notionApiTokenInput.setEnabled(is_checked)
        self.ui.telegramGroupsInput.setEnabled(not is_checked)
        self.ui.telegramChannelsInput.setEnabled(not is_checked)
        self.ui.slackChannelsInput.setEnabled(not is_checked)

    def select_image(self):
        if self.imagePath and hasattr(self.ui, "removeImageButton"):
            reply = QtWidgets.QMessageBox.question(
                self,
                "Change Image",
                "An image is already selected. Do you want to change it?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return
        file_dialog = QtWidgets.QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.imagePath = file_path
            if hasattr(self.ui, "imageFileNameLabel"):
                self.ui.imageFileNameLabel.setText(f"Selected: {os.path.basename(file_path)}")
            else:
                self.ui.label.setText(f"Selected: {os.path.basename(file_path)}")
            if hasattr(self.ui, "removeImageButton"):
                self.ui.removeImageButton.setVisible(True)

    def remove_image(self):
        self.imagePath = None
        if hasattr(self.ui, "imageFileNameLabel"):
            self.ui.imageFileNameLabel.setText("No image selected.")
        else:
            self.ui.label.setText("No image selected.")
        if hasattr(self.ui, "removeImageButton"):
            self.ui.removeImageButton.setVisible(False)

    async def async_get_text(self, prompt: str) -> str:
        dialog = QtWidgets.QInputDialog(self)
        dialog.setLabelText(prompt)
        dialog.setWindowTitle("Login Required")
        dialog.setModal(True)
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def finished(result):
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
                {"property": "Category", "multi_select": {"contains": tag}}
                for tag in selected_tags
            ]
            response = client_notion.databases.query(
                database_id=NOTION_DATABASE_ID,
                filter={
                    "and": [
                        {"property": "Platform", "select": {"equals": "Telegram"}},
                        {"or": tag_filters},
                    ]
                },
            )
            groups = []
            for result in response["results"]:
                contact_prop = result["properties"].get("Contact Name / Channel ID", {})
                rt = contact_prop.get("rich_text", [])
                if rt:
                    groups.append(rt[0]["plain_text"])
            return groups
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to fetch groups from Notion: {e}")
            return []

    def get_slack_channels_by_tags(self, notion_token, selected_tags):
        client_notion = Client(auth=notion_token)
        try:
            tag_filters = [
                {"property": "Category", "multi_select": {"contains": tag}}
                for tag in selected_tags
            ]
            response = client_notion.databases.query(
                database_id=NOTION_DATABASE_ID,
                filter={
                    "and": [
                        {"property": "Platform", "select": {"equals": "Slack"}},
                        {"or": tag_filters},
                    ]
                },
            )
            channels = []
            for result in response["results"]:
                contact_prop = result["properties"].get("Contact Name / Channel ID", {})
                rt = contact_prop.get("rich_text", [])
                if rt:
                    channels.append(rt[0]["plain_text"])
            return channels
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to fetch Slack channels from Notion: {e}")
            return []

    async def get_tg_client(self):
        if self.tg_client is not None:
            return self.tg_client

        telegram_api_id = self.ui.telegramApiIdInput.text().strip()
        telegram_api_hash = self.ui.telegramApiHashInput.text().strip()
        if not telegram_api_id or not telegram_api_hash:
            raise ValueError("Telegram API credentials are missing!")

        session_dir = os.path.join(os.path.expanduser("~"), ".TelegramSlackApp")
        os.makedirs(session_dir, exist_ok=True)
        session_file = os.path.join(session_dir, "my_account.session")

        client = TelegramClient(session_file, telegram_api_id, telegram_api_hash)
        await client.connect()

        client._update_loop_running = False
        client._keepalive_loop_running = False

        if not await client.is_user_authorized():
            phone = await self.async_get_text("Enter your phone number (with country code):")
            if not phone:
                raise Exception("Phone number is required!")
            await client.send_code_request(phone)
            await asyncio.sleep(1.0)
            code = await self.async_get_text("Enter the code sent to you:")
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                pw = await self.async_get_text("Two-step verification is enabled. Enter your password:")
                await client.sign_in(password=pw)
            except AuthRestartError as e:
                raise Exception(f"Authorization restarted, please try again: {e}")
            except Exception as e:
                raise Exception(f"Failed to sign in: {e}")
            if hasattr(self.ui, "loginStatusLabel"):
                me = await client.get_me()
                self.ui.loginStatusLabel.setText(f"Logged in as: {me.first_name if me.first_name else me.username}")

        if hasattr(client, "_updates_task") and client._updates_task:
            client._updates_task.cancel()
        if hasattr(client, "_recv_loop") and client._recv_loop:
            client._recv_loop.cancel()

        self.tg_client = client
        return client

    async def send_message_telegram_async(self):
        async with self._tg_lock:
            self.ui.pushButton.setEnabled(False)
            success_list = []
            error_list = []
            client = None
            try:
                message = self.ui.plainTextEdit.toPlainText().strip()
                telegram_channels = self.ui.telegramChannelsInput.toPlainText().strip().split("\n")
                if not message:
                    QtWidgets.QMessageBox.warning(self, "Warning", "Message cannot be empty!")
                    return

                try:
                    client = await self.get_tg_client()
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Error", str(e))
                    return

                if self.ui.useNotionCheckbox.isChecked():
                    notion_token = self.ui.notionApiTokenInput.text().strip()
                    selected_tags = [
                        self.ui.notionTagSelector.item(i).text()
                        for i in range(self.ui.notionTagSelector.count())
                        if self.ui.notionTagSelector.item(i).checkState() == QtCore.Qt.CheckState.Checked
                    ]
                    telegram_groups = self.get_telegram_groups_by_tags(notion_token, selected_tags)
                else:
                    telegram_groups = self.ui.telegramGroupsInput.toPlainText().strip().split("\n")

                group_ids = await self.get_group_ids(client, telegram_groups)
                recipients = [
                    r.strip() if isinstance(r, str) else r
                    for r in (telegram_channels + group_ids)
                    if (r if isinstance(r, int) else r.strip())
                ]
                for recipient in recipients:
                    try:
                        if self.imagePath:
                            await client.send_file(recipient, self.imagePath, caption=message)
                        else:
                            await client.send_message(recipient, message)
                        success_list.append(str(recipient))
                    except Exception as e:
                        error_list.append(f"{recipient}: {e}")

                if success_list:
                    QtWidgets.QMessageBox.information(self, "Success", "Telegram message sent to:\n" + ", ".join(success_list))
                if error_list:
                    QtWidgets.QMessageBox.critical(self, "Error", "Failed to send Telegram message to:\n" + "\n".join(error_list))
            finally:
                self.ui.pushButton.setEnabled(True)
                await asyncio.sleep(0.1)

    def send_message_telegram(self):
        asyncio.create_task(self.send_message_telegram_async())

    def send_message_slack(self):
        message = self.ui.plainTextEdit.toPlainText().strip()
        slack_bot_token = self.ui.slackBotTokenInput.text().strip()

        if self.ui.useNotionCheckbox.isChecked():
            notion_token = self.ui.notionApiTokenInput.text().strip()
            selected_tags = [
                self.ui.notionTagSelector.item(i).text()
                for i in range(self.ui.notionTagSelector.count())
                if self.ui.notionTagSelector.item(i).checkState() == QtCore.Qt.CheckState.Checked
            ]
            slack_channels = self.get_slack_channels_by_tags(notion_token, selected_tags)
        else:
            slack_channels = self.ui.slackChannelsInput.toPlainText().strip().split("\n")

        if not message:
            QtWidgets.QMessageBox.warning(self, "Warning", "Message cannot be empty!")
            return
        if not slack_bot_token:
            QtWidgets.QMessageBox.critical(self, "Error", "Slack bot token is missing!")
            return

        client = WebClient(token=slack_bot_token)
        success_channels = []
        error_messages = []
        for channel in slack_channels:
            try:
                if self.imagePath:
                    client.files_upload(
                        channels=channel,
                        file=self.imagePath,
                        title=message,
                        initial_comment=message,
                    )
                else:
                    client.chat_postMessage(channel=channel, text=message)
                success_channels.append(channel)
            except SlackApiError as e:
                error_messages.append(f"{channel}: {e.response['error']}")
        if success_channels:
            QtWidgets.QMessageBox.information(self, "Success", "Slack message sent to channels: " + ", ".join(success_channels))
        if error_messages:
            QtWidgets.QMessageBox.critical(self, "Error", "Failed to send Slack message to:\n" + "\n".join(error_messages))

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    def handle_exception(loop, context):
        exception = context.get("exception")
        if exception and "Cannot enter into task" in str(exception):
            print("Ignored reentrancy error:", exception)
        else:
            loop.default_exception_handler(context)

    loop.set_exception_handler(handle_exception)
    window = App()
    window.show()
    with loop:
        loop.run_forever()