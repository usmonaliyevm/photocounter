"""Agentga ism berish: xabariga reply qilib «+ism Muhammadillo», qaytarish «-ism»."""
import re
from html import escape

from aiogram import F, Router
from aiogram.types import Message

from db import db
from handlers.admin import is_admin

router = Router()
MAX_NAME = 64


async def _target(message: Message):
    """Reply bo'lsa o'sha odam (faqat admin), bo'lmasa yozuvchining o'zi."""
    r = message.reply_to_message
    if r is not None and r.from_user is not None and not r.from_user.is_bot:
        if not await is_admin(message):
            await message.reply("Boshqa agentga ism berish faqat adminlar uchun.")
            return None
        return r.from_user
    return message.from_user


@router.message(F.text.regexp(r"(?i)^\s*\+\s*ism\b\s*(.*)$").as_("m"))
async def set_name(message: Message, m: "re.Match[str]") -> None:
    name = " ".join(m.group(1).split())
    if not name:
        await message.reply("Ismni yozing: agent xabariga reply qilib <code>+ism Muhammadillo</code>")
        return
    if len(name) > MAX_NAME:
        await message.reply(f"Ism juda uzun (maks. {MAX_NAME} belgi).")
        return
    target = await _target(message)
    if target is None:
        return
    await db.upsert_agent(target.id, target.full_name, target.username)
    await db.set_display_name(target.id, name)
    await message.reply(
        f"✅ {escape(target.full_name, quote=False)} endi hisobotlarda "
        f"<b>{escape(name, quote=False)}</b> deb ko'rinadi."
    )


@router.message(F.text.regexp(r"(?i)^\s*-\s*ism\s*$"))
async def reset_name(message: Message) -> None:
    target = await _target(message)
    if target is None:
        return
    await db.upsert_agent(target.id, target.full_name, target.username)
    await db.set_display_name(target.id, None)
    await message.reply(
        f"✅ Endi Telegram ismi ishlatiladi: <b>{escape(target.full_name, quote=False)}</b>"
    )
