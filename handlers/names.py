"""Agentga ism berish.

Shaxsiy chatda (admin): /ism @username Muhammadillo   |   /ism @username -  (Telegram ismiga qaytarish)
Guruhda (admin, jimgina): agent xabariga reply qilib «+ism Muhammadillo» yoki «-ism» — bot guruhga
javob yozmaydi, tasdiqni adminga shaxsiy chatda yuboradi.
"""
import logging
import re
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from access import is_admin_user
from db import db
from handlers.admin import resolve_agent
from handlers.photos import claim_pending_and_notify
from reports import agent_label

log = logging.getLogger(__name__)
router = Router()
MAX_NAME = 64


@router.message(Command("ism"), F.chat.type == "private")
async def cmd_name(message: Message, command: CommandObject) -> None:
    if not await is_admin_user(message.bot, message.from_user.id):
        await message.reply("Bu buyruq faqat adminlar uchun.")
        return
    parts = (command.args or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "Foydalanish:\n"
            "<code>/ism @username Muhammadillo</code> — hisobotlarda shu ism chiqadi\n"
            "<code>/ism @username -</code> — Telegram ismiga qaytarish\n"
            "Username o'rniga ID ham bo'ladi."
        )
        return
    agent = await resolve_agent(parts[0])
    if agent is None:
        await message.reply(f"Agent topilmadi: {escape(parts[0], quote=False)}. U guruhga kamida bitta rasm tashlagan bo'lishi kerak.")
        return
    name = " ".join(parts[1].split())
    uid = int(agent["user_id"])
    if name == "-":
        await db.set_display_name(uid, None)
        await message.reply(f"✅ Endi Telegram ismi ishlatiladi: {agent_label(agent['full_name'], agent['username'], uid)}")
        return
    if len(name) > MAX_NAME:
        await message.reply(f"Ism juda uzun (maks. {MAX_NAME} belgi).")
        return
    await db.set_display_name(uid, name)
    await message.reply(f"✅ Endi hisobotlarda: {agent_label(name, agent['username'], uid)}")
    await claim_pending_and_notify(message.bot, None, uid, name, agent["username"])


async def _group_target(message: Message):
    """Guruhda: admin reply qilgan odam. Bot guruhga hech narsa yozmaydi."""
    r = message.reply_to_message
    if r is None or r.from_user is None or r.from_user.is_bot:
        return None
    if not await is_admin_user(message.bot, message.from_user.id):
        return None
    return r.from_user


async def _notify_admin(message: Message, text: str) -> None:
    try:
        await message.bot.send_message(message.from_user.id, text)
    except Exception as e:  # noqa: BLE001
        log.debug("Adminga shaxsiy xabar yuborilmadi: %s", e)


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text.regexp(r"(?i)^\s*\+\s*ism\b\s*(.*)$").as_("m"))
async def group_set_name(message: Message, m: "re.Match[str]") -> None:
    name = " ".join(m.group(1).split())
    target = await _group_target(message)
    if target is None or not name or len(name) > MAX_NAME:
        return
    await db.upsert_agent(target.id, target.full_name, target.username)
    await db.set_display_name(target.id, name)
    await _notify_admin(message, f"✅ Endi hisobotlarda: {agent_label(name, target.username, target.id)}")
    await claim_pending_and_notify(message.bot, None, target.id, name, target.username)


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text.regexp(r"(?i)^\s*-\s*ism\s*$"))
async def group_reset_name(message: Message) -> None:
    target = await _group_target(message)
    if target is None:
        return
    await db.upsert_agent(target.id, target.full_name, target.username)
    await db.set_display_name(target.id, None)
    await _notify_admin(message, f"✅ Endi Telegram ismi ishlatiladi: {agent_label(target.full_name, target.username, target.id)}")
