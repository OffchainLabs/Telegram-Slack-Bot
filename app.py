#!/usr/bin/env python3
# Telegram-Slack poster with Notion-page preview  •  2025-05 build
import re, os, asyncio, tempfile, requests, urllib.request
from urllib.parse import urlparse
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, AuthRestartError
from PyQt6 import QtWidgets, QtCore, QtGui
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from notion_client import Client
from ui_mainwindow import Ui_MainWindow
import qasync

# ────────────────────────── constants ──────────────────────────
NOTION_DATABASE_ID = "1d001a3f59f881c09cf2fc79f57ac4ac"

# ----------------------------------------------------------------------
# helper: download any URL into a safe-named temporary file
# ----------------------------------------------------------------------
def _download_temp_file(url: str) -> str:
    """
    Download *url* into a secure tmp file and return its local path.
    The original name is trimmed so it never exceeds the 255-char macOS limit.
    """
    parsed = urlparse(url)
    base   = parsed.path.split("/")[-1] or "file.bin"
    # strip query / fragment
    base   = base.split("?", 1)[0].split("#", 1)[0]
    suffix = os.path.splitext(base)[1] or ".bin"

    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with urllib.request.urlopen(url) as resp, open(tmp_path, "wb") as out:
        out.write(resp.read())
    return tmp_path

# ----------------------------------------------------------------------
# helper: pull the 32-char page-ID from any Notion URL
# ----------------------------------------------------------------------
_PAGE_ID_RE = re.compile(r"[0-9a-fA-F]{32}")
def extract_page_id(url: str) -> str | None:
    tail = urlparse(url).path.split("/")[-1]
    tail = tail.split("?", 1)[0].split("#", 1)[0]
    if "-" in tail:
        tail = tail.split("-")[-1]
    m = _PAGE_ID_RE.fullmatch(tail)
    return m.group(0) if m else None

async def fetch_notion_content(token: str, page_url: str):
    """
    Return (plain-text, image_path) for the given Notion page.
    The first image is downloaded via _download_temp_file().
    """
    page_id = extract_page_id(page_url)
    if not page_id:
        raise ValueError("Couldn’t parse a Notion page ID from that link 🤔")

    nc = Client(auth=token)
    txt_parts, img_local = [], None

    for blk in nc.blocks.children.list(page_id)["results"]:
        kind = blk["type"]

        if kind in ("paragraph", "heading_1", "heading_2", "heading_3"):
            rich = blk[kind]["rich_text"]
            if rich:
                txt_parts.append(rich[0]["plain_text"])

        if kind == "image" and img_local is None:
            src = (blk["image"]["file"]["url"]
                   if blk["image"]["type"] == "file"
                   else blk["image"]["external"]["url"])
            img_local = _download_temp_file(src)

    return "\n".join(txt_parts).strip(), img_local


# ─────────────────────────── GUI class ───────────────────────────
class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow(); self.ui.setupUi(self)

        # ░░ status label ░░
        if hasattr(self.ui, "loginStatusLabel"):
            self.ui.loginStatusLabel.setText("Not logged in")

        # ░░ preview wiring ░░
        self.ui.previewButton.clicked.connect(
            lambda: asyncio.create_task(self.load_preview()))
        self.ui.previewPlainText.setReadOnly(True)
        self.ui.imagePreviewLabel.clear()

        # ░░ send buttons ░░
        self.ui.pushButton.clicked.connect(self.send_message_telegram)
        self.ui.pushButton_2.clicked.connect(self.send_message_slack)

        # ░░ notion tag / mode ░░
        self.ui.useNotionCheckbox.stateChanged.connect(self.toggle_notion_mode)
        self.ui.notionApiTokenInput.setEnabled(True)
        self.ui.notionTagSelector.setEnabled(False)
        self.ui.notionApiTokenInput.editingFinished.connect(
            self.load_notion_tags)

        # runtime holders
        self.cachedText: str = ""
        self.imagePath: str | None = None
        self._tg_lock = asyncio.Lock()
        self.tg_client = None

    # ───────────── tag selector ─────────────
    def load_notion_tags(self):
        token = self.ui.notionApiTokenInput.text().strip()
        if not token:
            return
        try:
            db = Client(auth=token).databases.retrieve(
                database_id=NOTION_DATABASE_ID)
            self.ui.notionTagSelector.clear()
            for opt in db["properties"]["Category"]["multi_select"]["options"]:
                it = QtWidgets.QListWidgetItem(opt["name"])
                it.setFlags(it.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(QtCore.Qt.CheckState.Unchecked)
                self.ui.notionTagSelector.addItem(it)
        except Exception as e:
            print("[TagLoad]", e)

    def toggle_notion_mode(self):
        """Checkbox only affects where channels/groups come from and
        whether the tag selector is enabled – the token field is always on."""
        on = self.ui.useNotionCheckbox.isChecked()

        # tag selector follows the checkbox
        self.ui.notionTagSelector.setEnabled(on)

        # manual inputs are disabled only when Notion-groups mode is on
        self.ui.telegramGroupsInput.setEnabled(not on)
        self.ui.telegramChannelsInput.setEnabled(not on)
        self.ui.slackChannelsInput.setEnabled(not on)

    # ───────────── preview helpers ─────────────
    async def load_preview(self):
        url   = self.ui.notionPageUrlInput.text().strip()
        token = self.ui.notionApiTokenInput.text().strip()

        if not url:
            QtWidgets.QMessageBox.warning(
                self, "Missing URL", "Paste a Notion page link first."); return
        try:
            txt, img = await fetch_notion_content(token, url)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Fetch error", str(exc)); return

        self.cachedText, self.imagePath = txt, img
        self.ui.previewPlainText.setPlainText(txt or "[No text]")
        if img:
            pix = QtGui.QPixmap(img).scaled(
                self.ui.imagePreviewLabel.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation)
            self.ui.imagePreviewLabel.setPixmap(pix)
        else:
            self.ui.imagePreviewLabel.clear()

    async def prepare_content(self):
        if self.cachedText or self.imagePath:
            return self.cachedText, self.imagePath
        url   = self.ui.notionPageUrlInput.text().strip()
        token = self.ui.notionApiTokenInput.text().strip()
        return await fetch_notion_content(token, url)

    # ───────────── Telegram routines ─────────────
    async def async_get_text(self, prompt):
        dlg = QtWidgets.QInputDialog(self); dlg.setLabelText(prompt)
        dlg.setModal(True); loop = asyncio.get_running_loop()
        fut = loop.create_future()
        dlg.finished.connect(lambda _: (fut.set_result(dlg.textValue().strip()),
                                        dlg.deleteLater()))
        dlg.show(); return await fut

    async def get_tg_client(self):
        if self.tg_client: return self.tg_client
        api_id  = self.ui.telegramApiIdInput.text().strip()
        api_hash= self.ui.telegramApiHashInput.text().strip()
        if not api_id or not api_hash:
            raise ValueError("Telegram API credentials missing.")
        sesdir = os.path.join(os.path.expanduser("~"), ".TelegramSlackApp")
        os.makedirs(sesdir, exist_ok=True)
        client = TelegramClient(
            os.path.join(sesdir, "my_account.session"), api_id, api_hash)
        await client.connect()
        client._update_loop_running = client._keepalive_loop_running = False
        if not await client.is_user_authorized():
            phone = await self.async_get_text("Phone (with country code):")
            if not phone: raise Exception("Phone required!")
            await client.send_code_request(phone); await asyncio.sleep(1)
            code = await self.async_get_text("Login code:")
            try:     await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                pw = await self.async_get_text("Password:")
                await client.sign_in(password=pw)
        self.tg_client = client; return client

    async def get_group_ids(self, cli, names):
        ids = []
        async for d in cli.iter_dialogs():
            if d.is_group and d.name in names: ids.append(d.id)
        return ids

    def _selected_tags(self):
        return [self.ui.notionTagSelector.item(i).text()
                for i in range(self.ui.notionTagSelector.count())
                if self.ui.notionTagSelector.item(i).checkState()
                   == QtCore.Qt.CheckState.Checked]

    def get_telegram_groups_by_tags(self, tok, tags):
        cli=Client(auth=tok); groups=[]
        filt=[{"property":"Category","multi_select":{"contains":t}} for t in tags]
        res=cli.databases.query(database_id=NOTION_DATABASE_ID,
              filter={"and":[{"property":"Platform","select":{"equals":"Telegram"}},{"or":filt}]})
        for r in res["results"]:
            rt=r["properties"]["Contact Name / Channel ID"]["rich_text"]
            if rt: groups.append(rt[0]["plain_text"])
        return groups

    async def send_message_telegram_async(self):
        async with self._tg_lock:
            self.ui.pushButton.setEnabled(False)
            try:
                txt, img = await self.prepare_content()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self,"Error",str(e)); return
            if not txt and not img:
                QtWidgets.QMessageBox.warning(self,"Empty","Nothing to send."); return

            client = await self.get_tg_client()
            ch_manual = self.ui.telegramChannelsInput.toPlainText().strip().split("\n")
            if self.ui.useNotionCheckbox.isChecked():
                grps = self.get_telegram_groups_by_tags(
                    self.ui.notionApiTokenInput.text().strip(), self._selected_tags())
            else:
                grps = self.ui.telegramGroupsInput.toPlainText().strip().split("\n")

            ids = await self.get_group_ids(client, grps)
            recipients = [r.strip() if isinstance(r,str) else r
                          for r in (ch_manual + ids)
                          if (r if isinstance(r,int) else r.strip())]

            ok, bad = [], []
            for r in recipients:
                try:
                    if img: await client.send_file(r, img, caption=txt or None)
                    else:   await client.send_message(r, txt)
                    ok.append(str(r))
                except Exception as e:
                    bad.append(f"{r}: {e}")

            if ok:  QtWidgets.QMessageBox.information(self,"Telegram",", ".join(ok))
            if bad: QtWidgets.QMessageBox.critical(self,"Errors","\n".join(bad))
            self.ui.pushButton.setEnabled(True)

    def send_message_telegram(self):
        asyncio.create_task(self.send_message_telegram_async())

    # ───────────── Slack routines ─────────────
    def get_slack_channels_by_tags(self, tok, tags):
        cli=Client(auth=tok); chans=[]
        filt=[{"property":"Category","multi_select":{"contains":t}} for t in tags]
        res=cli.databases.query(database_id=NOTION_DATABASE_ID,
              filter={"and":[{"property":"Platform","select":{"equals":"Slack"}},{"or":filt}]})
        for r in res["results"]:
            rt=r["properties"]["Contact Name / Channel ID"]["rich_text"]
            if rt: chans.append(rt[0]["plain_text"])
        return chans

    async def _send_slack(self):
        try: txt, img = await self.prepare_content()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self,"Error",str(e)); return
        token = self.ui.slackBotTokenInput.text().strip()
        if not token:
            QtWidgets.QMessageBox.critical(self,"Missing","Slack bot token"); return

        chans = (self.get_slack_channels_by_tags(
                    self.ui.notionApiTokenInput.text().strip(),
                    self._selected_tags())
                 if self.ui.useNotionCheckbox.isChecked()
                 else self.ui.slackChannelsInput.toPlainText().strip().split("\n"))

        cli = WebClient(token=token)
        ok, bad = [], []
        for c in chans:
            try:
                if img:
                    cli.files_upload(channels=c, file=img,
                                     title=txt or "Image", initial_comment=txt or "")
                else:
                    cli.chat_postMessage(channel=c, text=txt)
                ok.append(c)
            except SlackApiError as e:
                bad.append(f"{c}: {e.response['error']}")

        if ok:  QtWidgets.QMessageBox.information(self,"Slack",", ".join(ok))
        if bad: QtWidgets.QMessageBox.critical(self,"Errors","\n".join(bad))

    def send_message_slack(self):
        asyncio.run_coroutine_threadsafe(self._send_slack(),
                                         asyncio.get_event_loop())


# ───────────────────────── main ─────────────────────────
if __name__ == "__main__":
    qtapp = QtWidgets.QApplication([])
    loop = qasync.QEventLoop(qtapp); asyncio.set_event_loop(loop)
    window = App(); window.show()
    with loop: loop.run_forever()
