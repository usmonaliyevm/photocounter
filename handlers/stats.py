"""Hisobot buyruqlari: /bugun /kecha /hafta /oy /hisobot /mening."""
from datetime import date, datetime, timedelta
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import dates
import reports

router = Router()
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


@router.message(Command("bugun"), IN_GROUP)
async def cmd_today(message: Message) -> None:
    await message.answer(await reports.daily_text(message.chat.id, message.chat.title, dates.today()))


@router.message(Command("kecha"), IN_GROUP)
async def cmd_yesterday(message: Message) -> None:
    d = dates.today() - timedelta(days=1)
    await message.answer(await reports.daily_text(message.chat.id, message.chat.title, d, label="Kecha"))


@router.message(Command("hafta"), IN_GROUP)
async def cmd_week(message: Message, command: CommandObject) -> None:
    ref = parse_week_arg(command.args or "", dates.today())
    if ref is None:
        await message.reply(
            "Foydalanish:\n"
            "<code>/hafta</code> — shu hafta (dushanba–yakshanba)\n"
            "<code>/hafta oldingi</code> — o'tgan hafta\n"
            "<code>/hafta 15.10.2026</code> — shu sana kirgan hafta"
        )
        return
    await message.answer(await reports.weekly_text(message.chat.id, message.chat.title, ref))


@router.message(Command("oy"), IN_GROUP)
async def cmd_month(message: Message, command: CommandObject) -> None:
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
    await message.answer(await reports.monthly_text(message.chat.id, message.chat.title, ref))


@router.message(Command("hisobot"), IN_GROUP)
async def cmd_range(message: Message, command: CommandObject) -> None:
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
    await message.answer(await reports.range_text(message.chat.id, message.chat.title, d1, d2))


@router.message(Command("mening"))
async def cmd_mine(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    chat_id = message.chat.id if message.chat.type in ("group", "supergroup") else None
    await message.answer(await reports.mine_text(user.id, user.full_name, dates.today(), chat_id))


@router.message(Command("bugun", "kecha", "hafta", "oy", "hisobot"))
async def only_in_group(message: Message) -> None:
    await message.answer("Bu buyruq agentlar guruhida ishlaydi. Shaxsiy chatda /mening ni ishlating.")
