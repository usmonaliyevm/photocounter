"""Guruhga tashlangan rasmlarni jimgina sanash (takrorlarni ushlab). Guruhda bot hech narsa yozmaydi."""
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
from access import admin_recipients
from config import DUP_DAYS, DUP_GROUP_REPLY, DUP_NOTIFY, DUP_REACT_EMOJI, DUP_THRESHOLD, REACT_EMOJI
from db import db
from reports import agent_label

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


def _msg_link(message: Message, message_id: int) -> Optional[str]:
    cid = str(message.chat.id)
    if message.chat.type == "supergroup" and cid.startswith("-100"):
        return f"https://t.me/c/{cid[4:]}/{message_id}"
    return None


async def _reply_duplicate_in_group(message: Message, original: aiosqlite.Row) -> None:
    """Guruhda: bu rasm avval yuborilgan, hisobga olinmadi; rasmga 👎."""
    try:
        when = datetime.fromisoformat(original["sent_at"]).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        when = original["day"]
    who = escape(original["full_name"] or "noma'lum", quote=False)
    text = f"⚠️ Bu rasm avval yuborilgan ({who}, {when}), hisobga olinmadi."
    link = _msg_link(message, int(original["message_id"]))
    if link:
        text += f'\n<a href="{link}">Asl rasm</a>'
    if DUP_GROUP_REPLY:
        try:
            await message.reply(text, disable_web_page_preview=True)
        except Exception as e:  # noqa: BLE001
            log.warning("Guruhga takror haqida yozib bo'lmadi: %s", e)
    if DUP_REACT_EMOJI:
        try:
            await message.react([ReactionTypeEmoji(emoji=DUP_REACT_EMOJI)])
        except Exception as e:  # noqa: BLE001
            log.debug("Takror rasmga reaksiya qo'yilmadi: %s", e)


async def claim_pending_and_notify(bot, chat_id: Optional[int], user_id: int, name: str, username: Optional[str]) -> int:
    """Eksportdan kutilayotgan (egasi noma'lum) rasmlarni shu agentga o'tkazadi va adminlarga xabar beradi."""
    try:
        result = await db.claim_pending(user_id, name, chat_id)
    except Exception as e:  # noqa: BLE001
        log.warning("Kutilayotgan rasmlarni o'tkazishda xato: %s", e)
        return 0
    total = 0
    for cid, (added, dups) in result.items():
        total += added + dups
        if added + dups == 0:
            continue
        chat = await db.get_chat(cid)
        if chat is None:
            continue
        who = agent_label(await db.name_of(user_id, name), username, user_id)
        text = (
            f"✅ <b>{escape(chat['title'] or str(cid), quote=False)}</b>\n"
            f"{who} aniqlandi: eksportdagi eski rasmlaridan <b>{added}</b> ta hisobga qo'shildi"
            + (f", {dups} ta takror" if dups else "") + "."
        )
        for uid in await admin_recipients(bot, chat):
            try:
                await bot.send_message(uid, text)
            except Exception as e:  # noqa: BLE001
                log.debug("Xabar yuborilmadi (%s): %s", uid, e)
    return total


async def _notify_duplicate(message: Message, original: aiosqlite.Row, distance: int) -> None:
    """Barcha adminlarga shaxsiy chatda: kim takror rasm tashladi, asli kimniki va qachon.

    Admin xabarni olishi uchun botga bir marta /start bosgan bo'lishi kerak.
    """
    chat = await db.get_chat(message.chat.id)
    if chat is None:
        return
    user = message.from_user
    who = agent_label(await db.name_of(user.id, user.full_name), user.username, user.id)
    try:
        when = datetime.fromisoformat(original["sent_at"]).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        when = original["day"]
    orig_who = agent_label(original["full_name"] or "noma'lum", original["username"], int(original["user_id"]))
    text = (
        f"⚠️ <b>{escape(chat['title'] or str(chat['chat_id']))}</b>\n"
        f"{who} takror rasm tashladi, hisobga olinmadi.\n"
        f"Asl rasm: {orig_who}, {when}"
    )
    new_link, old_link = _msg_link(message, message.message_id), _msg_link(message, int(original["message_id"]))
    if new_link and old_link:
        text += f'\n<a href="{new_link}">Takror</a> · <a href="{old_link}">Asl rasm</a>'
    for uid in await admin_recipients(message.bot, chat):
        try:
            await message.bot.send_message(uid, text, disable_web_page_preview=True)
        except Exception as e:  # noqa: BLE001
            log.debug("Takror haqida xabar yuborilmadi (%s): %s", uid, e)


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
    await claim_pending_and_notify(message.bot, message.chat.id, user.id, user.full_name, user.username)

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
        log.info("Takror rasm: chat %s, %s (id %s), farq %s bit", message.chat.id, user.full_name, user.id, distance)
        await _reply_duplicate_in_group(message, original)
        if DUP_NOTIFY:
            await _notify_duplicate(message, original, distance)
        return
    if counted and REACT_EMOJI:
        try:
            await message.react([ReactionTypeEmoji(emoji=REACT_EMOJI)])
        except Exception as e:  # noqa: BLE001
            log.debug("Reaksiya qo'yilmadi: %s", e)
