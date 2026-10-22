"""Kim qaysi guruhning hisobotini ko'ra oladi va shaxsiy chatda qaysi guruh tanlangan."""
import logging
from typing import List, Optional

import aiosqlite
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_IDS
from db import db

log = logging.getLogger(__name__)


async def can_access(bot: Bot, user_id: int, chat: aiosqlite.Row) -> bool:
    """ADMIN_IDS, botni guruhga qo'shgan odam yoki guruh admini."""
    if user_id in ADMIN_IDS or chat["owner_id"] == user_id:
        return True
    try:
        member = await bot.get_chat_member(int(chat["chat_id"]), user_id)
        return member.status in ("creator", "administrator")
    except Exception:  # noqa: BLE001
        return False


async def allowed_chats(bot: Bot, user_id: int) -> List[aiosqlite.Row]:
    return [c for c in await db.list_chats() if await can_access(bot, user_id, c)]


async def is_admin_user(bot: Bot, user_id: int) -> bool:
    return user_id in ADMIN_IDS or bool(await allowed_chats(bot, user_id))


def recipients_for(chat: aiosqlite.Row) -> List[int]:
    """Guruh bo'yicha avtomatik xabarlar kimga boradi: ADMIN_IDS + guruhga qo'shgan odam."""
    ids = list(ADMIN_IDS)
    if chat["owner_id"] and chat["owner_id"] not in ids:
        ids.append(int(chat["owner_id"]))
    return ids


async def admin_recipients(bot: Bot, chat: aiosqlite.Row) -> List[int]:
    """Ogohlantirishlar kimga boradi: ADMIN_IDS + guruhga qo'shgan odam + guruhning barcha (odam) adminlari."""
    ids = recipients_for(chat)
    try:
        for member in await bot.get_chat_administrators(int(chat["chat_id"])):
            u = member.user
            if not u.is_bot and u.id not in ids:
                ids.append(u.id)
    except Exception as e:  # noqa: BLE001
        log.warning("Guruh adminlari olinmadi (%s): %s", chat["chat_id"], e)
    return ids


def chat_keyboard(chats: List[aiosqlite.Row], current: Optional[str] = None) -> InlineKeyboardMarkup:
    rows = []
    for c in chats:
        title = c["title"] or str(c["chat_id"])
        if current == str(c["chat_id"]):
            title = "✅ " + title
        rows.append([InlineKeyboardButton(text=title[:60], callback_data=f"chat:{c['chat_id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def resolve_chat(message: Message) -> Optional[aiosqlite.Row]:
    """Shaxsiy chatdagi buyruq qaysi guruhga tegishli: bitta bo'lsa o'sha, bo'lmasa tanlangani."""
    user_id = message.from_user.id
    chats = await allowed_chats(message.bot, user_id)
    if not chats:
        await message.answer(
            "Sizga tegishli guruh topilmadi.\n"
            "Botni agentlar guruhiga qo'shing va u yerda admin qiling, keyin qayta urinib ko'ring."
        )
        return None
    if len(chats) == 1:
        return chats[0]
    current = await db.get_setting(f"current:{user_id}")
    for c in chats:
        if str(c["chat_id"]) == current:
            return c
    await message.answer("Qaysi guruh bo'yicha? Tanlang:", reply_markup=chat_keyboard(chats))
    return None
