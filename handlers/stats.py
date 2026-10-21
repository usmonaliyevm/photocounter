"""Hisobot buyruqlari: /bugun /kecha /hafta /oy /hisobot /mening."""
from datetime import timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import dates
import reports

router = Router()
IN_GROUP = F.chat.type.in_({"group", "supergroup"})


@router.message(Command("bugun"), IN_GROUP)
async def cmd_today(message: Message) -> None:
    await message.answer(await reports.daily_text(message.chat.id, message.chat.title, dates.today()))


@router.message(Command("kecha"), IN_GROUP)
async def cmd_yesterday(message: Message) -> None:
    d = dates.today() - timedelta(days=1)
    await message.answer(await reports.daily_text(message.chat.id, message.chat.title, d, label="Kecha"))


@router.message(Command("hafta"), IN_GROUP)
async def cmd_week(message: Message) -> None:
    await message.answer(await reports.weekly_text(message.chat.id, message.chat.title, dates.today()))


@router.message(Command("oy"), IN_GROUP)
async def cmd_month(message: Message) -> None:
    await message.answer(await reports.monthly_text(message.chat.id, message.chat.title, dates.today()))


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
