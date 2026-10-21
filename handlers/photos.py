"""Guruhga tashlangan rasmlarni foto otchyot sifatida sanash (takrorlarni ushlab)."""
import asyncio
import io
import logging
from datetime import datetime, timedelta
from html import escape
from typing import List, Optional

import aiosqlite
from aiogram import F, Router
from aiogram.types import Message, PhotoSize, ReactionTypeEmoji

import dates
import imghash
from config import DUP_DAYS, DUP_THRESHOLD, REACT_EMOJI
from db import db

log = logging.getLogger(__name__)
router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# Tekshirish + yozish bir vaqtda ikki rasm uchun aralashib ketmasligi uchun
_lock = asyncio.Lock()
MAX_DOWNLOAD = 5 * 1024 * 1024  # fayl sifatida yuborilgan rasm uchun chegara


def _pick_size(sizes: List[PhotoSize]) -> PhotoSize:
    """Hash uchun ~320px li nusxa yetarli (kichikdan kattaga tartiblangan)."""
    for p in sizes:
        if (p.width or 0) >= 200:
            return p
    return sizes[-1]


async def _compute_hash(message: Message) -> Optional[str]:
    try:
        if message.photo:
            target = _pick_size(message.photo)
        else:
            doc = message.document
            if doc.thumbnail is not None:
                target = doc.thumbnail
            elif (doc.file_size or 0) <= MAX_DOWNLOAD:
                target = doc
            else:
                return None
        buf = io.BytesIO()
        await message.bot.download(target, destination=buf)
        return await asyncio.get_running_loop().run_in_executor(None, imghash.dhash, buf.getvalue())
    except Exception as e:  # noqa: BLE001
        log.warning("Rasm hash qilinmadi (chat %s, msg %s): %s", message.chat.id, message.message_id, e)
        return None


def _dup_text(message: Message, original: aiosqlite.Row) -> str:
    try:
        when = datetime.fromisoformat(original["sent_at"]).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        when = original["day"]
    who = escape(original["full_name"] or "noma'lum", quote=False)
    text = f"⚠️ Bu rasm avval yuborilgan ({who}, {when}), hisobga olinmadi."
    cid = str(message.chat.id)
    if message.chat.type == "supergroup" and cid.startswith("-100"):
        text += f'\n<a href="https://t.me/c/{cid[4:]}/{original["message_id"]}">Asl rasmga o\'tish</a>'
    return text


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

    phash = await _compute_hash(message)
    local = dates.to_local(message.date)
    day = local.date()
    since_day = (day - timedelta(days=DUP_DAYS)).isoformat()

    await db.upsert_chat(message.chat.id, message.chat.title or "")
    await db.upsert_agent(user.id, user.full_name, user.username)

    async with _lock:
        original = await db.find_by_file(message.chat.id, file_uid)
        distance = 0
        if original is None and phash is not None:
            found = await db.find_similar(message.chat.id, phash, DUP_THRESHOLD, since_day)
            if found is not None:
                original, distance = found
        if original is not None:
            await db.add_duplicate(
                chat_id=message.chat.id,
                message_id=message.message_id,
                user_id=user.id,
                original_id=int(original["id"]),
                distance=distance,
                day=day.isoformat(),
            )
            counted = False
        else:
            counted = await db.add_report(
                chat_id=message.chat.id,
                message_id=message.message_id,
                user_id=user.id,
                file_unique_id=file_uid,
                media_group_id=message.media_group_id,
                sent_at=local.isoformat(timespec="seconds"),
                day=day.isoformat(),
                phash=phash,
            )

    if original is not None:
        log.info("Takror rasm: chat %s, %s, farq %s bit", message.chat.id, user.full_name, distance)
        await message.reply(_dup_text(message, original), disable_web_page_preview=True)
        return
    if counted and REACT_EMOJI:
        try:
            await message.react([ReactionTypeEmoji(emoji=REACT_EMOJI)])
        except Exception as e:  # noqa: BLE001
            log.debug("Reaksiya qo'yilmadi: %s", e)
