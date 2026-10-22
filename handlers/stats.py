"""Hisobot buyruqlari: /bugun /kecha /hafta /oy /hisobot /mening (shaxsiy chatda va guruhda), /guruhlar (shaxsiy)."""
from datetime import date, datetime, timedelta
from html import escape
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
import aiosqlite
from aiogram.types import CallbackQuery, Message

import dates
import reports
from access import allowed_chats, can_access, chat_keyboard, resolve_chat
from config import GROUP_REPORTS
from db import db

router = Router()
IN_PRIVATE = F.chat.type == "private"
IN_GROUP = F.chat.type.in_({"group", "supergroup"})

PREV_WORDS = {"oldingi", "otgan", "o'tgan", "o‘tgan", "o`tgan", "avvalgi"}
MONTHS = {
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avgust": 8, "sentabr": 9, "sentyabr": 9, "oktabr": 10, "oktyabr": 10,
    "noyabr": 11, "dekabr": 12,
}


def parse_week_arg(arg: str, today: date) -> Optional[date]:
    """'' -> shu hafta, 'oldingi' -> o'tgan hafta, sana -> shu sanani o'z ichiga olgan hafta."""
    a = arg.strip().lower()
    if not a:
        return today
    if a in PREV_WORDS:
        return today - timedelta(days=7)
    try:
        return dates.parse(a)
    except ValueError:
        return None


def parse_month_arg(arg: str, today: date) -> Optional[date]:
    """'' -> shu oy, 'oldingi' -> o'tgan oy, 'sentabr' / '9' / '09.2026' / '2026-09' -> shu oy."""
    a = arg.strip().lower()
    if not a:
        return today
    if a in PREV_WORDS:
        return today.replace(day=1) - timedelta(days=1)
    if a.isdigit() and 1 <= int(a) <= 12:
        return date(today.year, int(a), 1)
    if a in MONTHS:
        return date(today.year, MONTHS[a], 1)
    hits = {m for name, m in MONTHS.items() if len(a) >= 3 and name.startswith(a)}
    if len(hits) == 1:
        return date(today.year, hits.pop(), 1)
    for fmt in ("%m.%Y", "%Y-%m", "%m/%Y"):
        try:
            return datetime.strptime(a, fmt).date()
        except ValueError:
            continue
    return None


async def _target_chat(message: Message) -> Optional[aiosqlite.Row]:
    """Buyruq qaysi guruhga tegishli. Shaxsiyda: tanlangan guruh. Guruhda: shu guruh (GROUP_REPORTS bo'yicha)."""
    if message.chat.type == "private":
        return await resolve_chat(message)
    if GROUP_REPORTS == "off" or message.from_user is None:
        return None
    chat = await db.get_chat(message.chat.id)
    if chat is None:
        await db.upsert_chat(message.chat.id, message.chat.title or "")
        chat = await db.get_chat(message.chat.id)
    if GROUP_REPORTS != "all" and not await can_access(message.bot, message.from_user.id, chat):
        return None  # admin bo'lmaganlar uchun guruhda jim
    return chat


@router.message(Command("shu_yerga"), IN_GROUP)
async def cmd_report_here(message: Message, command: CommandObject) -> None:
    """Admin: avtomatik hisobotlar shu mavzuga (yoki umumiy bo'limga) yuborilsin. '/shu_yerga off' — o'chirish."""
    user = message.from_user
    chat = await db.get_chat(message.chat.id)
    if chat is None:
        await db.upsert_chat(message.chat.id, message.chat.title or "")
        chat = await db.get_chat(message.chat.id)
    if user is None or not await can_access(message.bot, user.id, chat):
        return
    if (command.args or "").strip().lower() in ("off", "yoq", "yo'q", "o'chir"):
        await db.set_report_thread(message.chat.id, None)
        await message.answer("Guruhga avtomatik hisobot yuborish o'chirildi. Shaxsiy chatga yuborilaveradi.")
        return
    thread = message.message_thread_id if message.is_topic_message and message.message_thread_id else 0
    await db.set_report_thread(message.chat.id, thread)
    where = "shu mavzuga" if thread else "guruhning umumiy bo'limiga"
    await message.answer(
        f"✅ Avtomatik hisobotlar endi {where} yuboriladi: har kuni 21:00 da kunlik, yakshanba kuni haftalik ham.\n"
        "Hozir ko'rish: /bugun. O'chirish: /shu_yerga off"
    )


# ---------- guruh tanlash ----------
@router.message(Command("guruhlar"), IN_PRIVATE)
async def cmd_groups(message: Message) -> None:
    chats = await allowed_chats(message.bot, message.from_user.id)
    if not chats:
        await message.answer("Sizga tegishli guruh yo'q. Botni guruhga qo'shing va u yerda admin qiling.")
        return
    current = await db.get_setting(f"current:{message.from_user.id}")
    await message.answer(
        "Sizning guruhlaringiz. Hisobot qaysi guruh bo'yicha bo'lsin, tanlang:",
        reply_markup=chat_keyboard(chats, current),
    )


@router.callback_query(F.data.startswith("chat:"))
async def choose_chat(callback: CallbackQuery) -> None:
    chat_id = int(callback.data.split(":", 1)[1])
    chat = await db.get_chat(chat_id)
    if chat is None or not await can_access(callback.bot, callback.from_user.id, chat):
        await callback.answer("Bu guruhga ruxsat yo'q", show_alert=True)
        return
    await db.set_setting(f"current:{callback.from_user.id}", str(chat_id))
    await callback.answer("Tanlandi")
    if callback.message:
        await callback.message.edit_text(
            f"✅ Tanlandi: <b>{escape(chat['title'] or str(chat_id), quote=False)}</b>\n"
            "Endi /bugun, /kecha, /hafta, /oy yoki /hisobot yuboring."
        )


# ---------- hisobotlar ----------
@router.message(Command("bugun"))
async def cmd_today(message: Message) -> None:
    chat = await _target_chat(message)
    if chat is None:
        return
    await message.answer(await reports.daily_text(int(chat["chat_id"]), chat["title"], dates.today()))


@router.message(Command("kecha"))
async def cmd_yesterday(message: Message) -> None:
    chat = await _target_chat(message)
    if chat is None:
        return
    d = dates.today() - timedelta(days=1)
    await message.answer(await reports.daily_text(int(chat["chat_id"]), chat["title"], d, label="Kecha"))


@router.message(Command("hafta"))
async def cmd_week(message: Message, command: CommandObject) -> None:
    chat = await _target_chat(message)
    if chat is None:
        return
    ref = parse_week_arg(command.args or "", dates.today())
    if ref is None:
        await message.reply(
            "Foydalanish:\n"
            "<code>/hafta</code> — shu hafta (dushanba–yakshanba)\n"
            "<code>/hafta oldingi</code> — o'tgan hafta\n"
            "<code>/hafta 15.10.2026</code> — shu sana kirgan hafta"
        )
        return
    await message.answer(await reports.weekly_text(int(chat["chat_id"]), chat["title"], ref))


@router.message(Command("oy"))
async def cmd_month(message: Message, command: CommandObject) -> None:
    chat = await _target_chat(message)
    if chat is None:
        return
    ref = parse_month_arg(command.args or "", dates.today())
    if ref is None:
        await message.reply(
            "Foydalanish:\n"
            "<code>/oy</code> — shu oy (1-sanadan)\n"
            "<code>/oy oldingi</code> — o'tgan oy\n"
            "<code>/oy sentabr</code> yoki <code>/oy 9</code> — shu yilning oyi\n"
            "<code>/oy 09.2025</code> — aniq oy"
        )
        return
    await message.answer(await reports.monthly_text(int(chat["chat_id"]), chat["title"], ref))


@router.message(Command("hisobot"))
async def cmd_range(message: Message, command: CommandObject) -> None:
    chat = await _target_chat(message)
    if chat is None:
        return
    parts = (command.args or "").split()
    try:
        if len(parts) == 1:
            d1 = d2 = dates.parse(parts[0])
        elif len(parts) == 2:
            d1, d2 = dates.parse(parts[0]), dates.parse(parts[1])
        else:
            raise ValueError
    except ValueError:
        await message.reply(
            "Foydalanish: <code>/hisobot 01.10.2026 15.10.2026</code>\n"
            "yoki bitta kun: <code>/hisobot 05.10.2026</code>"
        )
        return
    if d1 > d2:
        d1, d2 = d2, d1
    await message.answer(await reports.range_text(int(chat["chat_id"]), chat["title"], d1, d2))


@router.message(Command("mening"))
async def cmd_mine(message: Message) -> None:
    """Agent o'z natijasi: guruhda shu guruh bo'yicha, shaxsiyda barcha guruhlar bo'yicha."""
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id if message.chat.type in ("group", "supergroup") else None
    await message.answer(await reports.mine_text(user.id, user.full_name, dates.today(), chat_id))
