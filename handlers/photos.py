"""Guruhga tashlangan rasmlarni foto otchyot sifatida sanash."""
import logging

from aiogram import F, Router
from aiogram.types import Message, ReactionTypeEmoji

import dates
from config import REACT_EMOJI
from db import db

log = logging.getLogger(__name__)
router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(F.photo | F.document)
async def on_photo(message: Message) -> None:
    user = message.from_user
    # Kanal nomidan yoki anonim admin sifatida yuborilganini kimga yozishni bilmaymiz
    if user is None or user.is_bot or message.sender_chat is not None:
        return

    if message.photo:
        file_uid = message.photo[-1].file_unique_id
    else:
        doc = message.document
        if doc is None or not (doc.mime_type or "").startswith("image/"):
            return  # rasm bo'lmagan fayl
        file_uid = doc.file_unique_id

    local = dates.to_local(message.date)
    await db.upsert_chat(message.chat.id, message.chat.title or "")
    await db.upsert_agent(user.id, user.full_name, user.username)
    result = await db.add_report(
        chat_id=message.chat.id,
        message_id=message.message_id,
        user_id=user.id,
        file_unique_id=file_uid,
        media_group_id=message.media_group_id,
        sent_at=local.isoformat(timespec="seconds"),
        day=local.date().isoformat(),
    )

    if result == "duplicate":
        await message.reply("⚠️ Bu rasm avval yuborilgan, hisobga olinmadi.")
        return
    if result == "ok" and REACT_EMOJI:
        try:
            await message.react([ReactionTypeEmoji(emoji=REACT_EMOJI)])
        except Exception as e:  # noqa: BLE001
            log.debug("Reaksiya qo'yilmadi: %s", e)
