__version__ = (2, 0, 0)

# meta developer: modif. by @the_farkhodov
# scope: nino_min 4.1.17

import asyncio
import datetime
import logging
import re
import time

import requests
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    DeleteChannelRequest,
    EditPhotoRequest,
)
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class TempChatsMod(loader.Module):
    """Creates temprorary chats"""

    strings = {
        "name": "TempChats",
        "chat_is_being_removed": "<b>🚫 Чат удаляется...</b>",
        "args": "🚫 <b>Капец с аргументами: </b><code>.help TempChats</code>",
        "chat_not_found": "🙄 <b>Чат не найден</b>",
        "tmp_cancelled": "🚫 <b>Чат </b><code>{}</code><b> будет жить вечно!</b>",
        "delete_error": "😐 <b>Произошла ошибка удаления чата. Сделай это вручную.</b>",
        "temp_chat_header": "<b>😄 Привет я Amore Этот чат</b> (<code>{}</code>)<b> является временным и будет удален {}.</b>",
        "chat_created": '✅ <b><a href="{}">Чат</a> создан</b>',
        "delete_error_me": "🚫 <b>Ошибка удаления чата {}</b>",
    }
            
    @staticmethod
    def s2time(t: str) -> int:
        """
        Tries to export time from text
        """
        try:
            if not str(t)[:-1].isdigit():
                return 0

            if "d" in str(t):
                t = int(t[:-1]) * 60 * 60 * 24

            if "h" in str(t):
                t = int(t[:-1]) * 60 * 60

            if "m" in str(t):
                t = int(t[:-1]) * 60

            if "s" in str(t):
                t = int(t[:-1])

            t = int(re.sub(r"[^0-9]", "", str(t)))
        except ValueError:
            return 0

        return t

    @loader.loop(interval=0.5, autostart=True)
    async def chats_handler_async(self):
        for chat, info in self.get("chats", {}).copy().items():
            if int(info[0]) > time.time():
                continue

            try:
                await self._client.send_message(
                    int(chat),
                    self.strings("chat_is_being_removed"),
                )
                await asyncio.sleep(1)
                await self._client(DeleteChannelRequest(int(chat)))
            except Exception:
                logger.exception("Failed to delete chat")
                await self.inline.bot.send_message(
                    self._tg_id,
                    self.strings("delete_error_me").format(utils.escape_html(info[1])),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )

            chats = self.get("chats")
            del chats[chat]
            self.set("chats", chats)

    async def client_ready(self, client, db):
        self._db = db
        self._client = client

    async def tmpcmd(self, message: Message):
        """<time> <chat name> - Create new temp chat"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("args"))
            return

        if len(args.split()) < 2:
            await utils.answer(message, self.strings("args"))
            return

        temp_time = args.split()[0]
        tit = args.split(maxsplit=1)[1].strip()

        until = self.s2time(temp_time)
        if not until:
            await utils.answer(message, self.strings("args"))
            return

        res = (
            await self._client(
                CreateChannelRequest(
                    tit,
                    "Temporary chat",
                    megagroup=True,
                )
            )
        ).chats[0]

        await self._client(
            EditPhotoRequest(
                channel=res,
                photo=await self._client.upload_file(
                    (
                        await utils.run_sync(
                            requests.get,
                            f"https://github.com/NinoZOOM/assets/raw/main/Nino-tempchat.png",
                        )
                    ).content,
                    file_name="photo.png",
                ),
            )
        )

        link = (await self._client(ExportChatInviteRequest(res))).link

        await utils.answer(message, self.strings("chat_created").format(link))
        cid = res.id

        await self._client.send_message(
            cid,
            self.strings("temp_chat_header").format(
                cid,
                datetime.datetime.utcfromtimestamp(
                    time.time() + until + 10800
                ).strftime("%d.%m.%Y %H:%M:%S"),
            ),
        )
        self.set(
            "chats", {**self.get("chats", {}), **{str(cid): [until + time.time(), tit]}}
        )