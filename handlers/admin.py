"""Admin buyruqlari: /plan, /agent_off, /agent_on."""
from html import escape as _escape
from typing import Optional

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, User

from config import ADMIN_IDS
from db import db


def escape(text: str) -> str:
    """Telegram HTML uchun: faqat & < > almashtiriladi (apostrof o'z holicha qoladi)."""
    return _escape(text, quote=False)


router = Router()


async def is_admin(message: Message) -> bool:
    user = message.from_user
    if user is None:
        return False
    if user.id in ADMIN_IDS:
        return True
    if message.chat.type in ("group", "supergroup"):
        member = await message.bot.get_chat_member(message.chat.id, user.id)
        return member.status in ("creator", "administrator")
    return False


def _reply_target(message: Message) -> Optional[User]:
    r = message.reply_to_message
    if r is None or r.from_user is None or r.from_user.is_bot:
        return None
    return r.from_user


@router.message(Command("plan"))
async def cmd_plan(message: Message, command: CommandObject) -> None:
    if not await is_admin(message):
        await message.reply("Bu buyruq faqat adminlar uchun.")
        return

    args = (command.args or "").strip()
    target = _reply_target(message)

    if not args:
        default_plan = await db.get_default_plan()
        lines = [f"📌 Umumiy haftalik plan: <b>{default_plan}</b> ta"]
        custom = await db.list_agents_with_plan()
        if custom:
            lines.append("\nAlohida plan:")
            for a in custom:
                lines.append(f"• {escape(a['full_name'])} — {a['weekly_plan']} ta")
        lines.append(
            "\n<b>O'zgartirish:</b>\n"
            "/plan 100 — umumiy haftalik plan\n"
            "Agent xabariga reply qilib /plan 120 — shu agent uchun\n"
            "Agent xabariga reply qilib /plan 0 — umumiy planga qaytarish"
        )
        await message.answer("\n".join(lines))
        return

    if not args.isdigit():
        await message.reply("Plan butun son bo'lishi kerak. Masalan: <code>/plan 100</code>")
        return
    plan = int(args)

    if target is not None:
        await db.upsert_agent(target.id, target.full_name, target.username)
        tname = escape(await db.name_of(target.id, target.full_name))
        if plan == 0:
            await db.set_agent_plan(target.id, None)
            await message.reply(f"✅ {tname} umumiy planga qaytarildi.")
        else:
            await db.set_agent_plan(target.id, plan)
            await message.reply(f"✅ {tname} uchun haftalik plan: <b>{plan}</b> ta")
        return

    if plan <= 0:
        await message.reply("Umumiy plan 0 dan katta bo'lishi kerak.")
        return
    await db.set_default_plan(plan)
    await message.reply(f"✅ Umumiy haftalik plan: <b>{plan}</b> ta")


async def _toggle_agent(message: Message, active: bool) -> None:
    if not await is_admin(message):
        await message.reply("Bu buyruq faqat adminlar uchun.")
        return
    target = _reply_target(message)
    if target is None:
        await message.reply("Agentning xabariga reply qilib yuboring.")
        return
    await db.upsert_agent(target.id, target.full_name, target.username)
    await db.set_agent_active(target.id, active)
    tname = escape(await db.name_of(target.id, target.full_name))
    if active:
        await message.reply(f"✅ {tname} hisobotlarga qaytarildi.")
    else:
        await message.reply(f"🚫 {tname} hisobotlardan yashirildi.")


@router.message(Command("agent_off"))
async def cmd_agent_off(message: Message) -> None:
    await _toggle_agent(message, active=False)


@router.message(Command("agent_on"))
async def cmd_agent_on(message: Message) -> None:
    await _toggle_agent(message, active=True)
