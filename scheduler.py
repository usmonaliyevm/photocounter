"""Har kuni REPORT_TIME da adminlarga shaxsiy chatda avtomatik hisobot yuborish."""
import asyncio
import logging
from datetime import timedelta

from aiogram import Bot

import dates
import reports
from access import recipients_for
from config import REPORT_TIME
from db import db

log = logging.getLogger("scheduler")


async def send_reports(bot: Bot) -> None:
    today = dates.today()
    for chat in await db.list_chats():
        chat_id = int(chat["chat_id"])
        title = chat["title"] or None
        texts = [await reports.daily_text(chat_id, title, today)]
        if today.weekday() == 6:  # yakshanba: hafta yakuni
            texts.append(await reports.weekly_text(chat_id, title, today))
        for uid in recipients_for(chat):
            for text in texts:
                try:
                    await bot.send_message(uid, text)
                except Exception as e:  # noqa: BLE001
                    log.warning("Hisobot yuborilmadi (guruh %s -> %s): %s", chat_id, uid, e)
        # Guruhning o'ziga (masalan "Hisobotlar" mavzusiga), /shu_yerga bilan sozlangan bo'lsa
        thread = chat["report_thread_id"]
        if thread is not None:
            for text in texts:
                try:
                    await bot.send_message(chat_id, text, message_thread_id=int(thread) or None)
                except Exception as e:  # noqa: BLE001
                    log.warning("Guruhga hisobot yuborilmadi (%s, mavzu %s): %s", chat_id, thread, e)


async def run(bot: Bot) -> None:
    if not REPORT_TIME:
        log.info("REPORT_TIME bo'sh, avtomatik hisobot o'chirilgan")
        return
    try:
        hh, mm = (int(x) for x in REPORT_TIME.split(":"))
    except ValueError:
        log.error("REPORT_TIME noto'g'ri: %r (masalan 21:00 bo'lishi kerak)", REPORT_TIME)
        return

    while True:
        now = dates.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        log.info("Keyingi avtomatik hisobot: %s", target.strftime("%d.%m.%Y %H:%M"))
        await asyncio.sleep((target - now).total_seconds())
        await send_reports(bot)
