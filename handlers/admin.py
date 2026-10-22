"""Admin buyruqlari (shaxsiy chatda): /plan, /agent_off, /agent_on. Agent @username yoki ID bilan ko'rsatiladi."""
from html import escape as _escape
from typing import Optional, Tuple

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from access import is_admin_user
from db import db
from reports import agent_label

router = Router()
IN_PRIVATE = F.chat.type == "private"


def escape(text: str) -> str:
    return _escape(text, quote=False)


async def resolve_agent(token: str) -> Optional[aiosqlite.Row]:
    """'@username' yoki '123456' -> agents jadvalidagi yozuv."""
    t = token.strip()
    if t.lstrip("-").isdigit():
        return await db.get_agent(int(t))
    if t.startswith("@") or t:
        return await db.find_agent_by_username(t)
    return None


def _label(agent: aiosqlite.Row) -> str:
    return agent_label(agent["display_name"] or agent["full_name"], agent["username"], int(agent["user_id"]))


async def _guard(message: Message) -> bool:
    if await is_admin_user(message.bot, message.from_user.id):
        return True
    await message.reply("Bu buyruq faqat adminlar uchun.")
    return False


def _split_target(args: str) -> Tuple[Optional[str], str]:
    """'@user 120' -> ('@user', '120'); '120' -> (None, '120')."""
    parts = args.split(maxsplit=1)
    if not parts:
        return None, ""
    if parts[0].startswith("@") or (len(parts) == 2 and parts[0].lstrip("-").isdigit() and len(parts[0]) > 6):
        return parts[0], parts[1] if len(parts) > 1 else ""
    return None, args


@router.message(Command("plan"), IN_PRIVATE)
async def cmd_plan(message: Message, command: CommandObject) -> None:
    if not await _guard(message):
        return
    args = (command.args or "").strip()
    target_token, value = _split_target(args)

    if not args:
        default_plan = await db.get_default_plan()
        lines = [f"📌 Umumiy oylik plan: <b>{default_plan}</b> ta (har bir agent uchun)"]
        custom = await db.list_agents_with_plan()
        if custom:
            lines.append("\nAlohida plan:")
            for a in custom:
                lines.append(f"• {agent_label(a['full_name'], a['username'], int(a['user_id']))} — {a['monthly_plan']} ta/oy")
        lines.append(
            "\n<b>O'zgartirish:</b>\n"
            "<code>/plan 80</code> — umumiy oylik plan\n"
            "<code>/plan @username 100</code> — shu agent uchun oylik plan\n"
            "<code>/plan @username 0</code> — umumiy planga qaytarish\n"
            "Username o'rniga ID ham bo'ladi: <code>/plan 123456789 100</code>\n"
            "Haftalik ko'rsatkich oylik plandan hisoblanadi (80/oy ≈ 18/hafta)."
        )
        await message.answer("\n".join(lines))
        return

    if not value.strip().isdigit():
        await message.reply("Plan butun son bo'lishi kerak. Masalan: <code>/plan 80</code> yoki <code>/plan @username 100</code>")
        return
    plan = int(value.strip())

    if target_token is not None:
        agent = await resolve_agent(target_token)
        if agent is None:
            await message.reply(f"Agent topilmadi: {escape(target_token)}. U guruhga kamida bitta rasm tashlagan bo'lishi kerak.")
            return
        if plan == 0:
            await db.set_agent_plan(int(agent["user_id"]), None)
            await message.reply(f"✅ {_label(agent)} umumiy planga qaytarildi.")
        else:
            await db.set_agent_plan(int(agent["user_id"]), plan)
            await message.reply(f"✅ {_label(agent)} uchun oylik plan: <b>{plan}</b> ta")
        return

    if plan <= 0:
        await message.reply("Umumiy plan 0 dan katta bo'lishi kerak.")
        return
    await db.set_default_plan(plan)
    await message.reply(f"✅ Umumiy oylik plan: <b>{plan}</b> ta (har bir agent uchun)")


async def _toggle_agent(message: Message, command: CommandObject, active: bool) -> None:
    if not await _guard(message):
        return
    token = (command.args or "").strip()
    agent = await resolve_agent(token) if token else None
    if agent is None:
        cmd = "agent_on" if active else "agent_off"
        await message.reply(f"Agentni ko'rsating: <code>/{cmd} @username</code> yoki <code>/{cmd} 123456789</code>")
        return
    await db.set_agent_active(int(agent["user_id"]), active)
    if active:
        await message.reply(f"✅ {_label(agent)} hisobotlarga qaytarildi.")
    else:
        await message.reply(f"🚫 {_label(agent)} hisobotlardan yashirildi.")


@router.message(Command("agent_off"), IN_PRIVATE)
async def cmd_agent_off(message: Message, command: CommandObject) -> None:
    await _toggle_agent(message, command, active=False)


@router.message(Command("agent_on"), IN_PRIVATE)
async def cmd_agent_on(message: Message, command: CommandObject) -> None:
    await _toggle_agent(message, command, active=True)
