"""Foto otchyot sanovchi bot — kirish nuqtasi. Ishga tushirish: python bot.py"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats

import scheduler
from config import ADMIN_IDS, BOT_TOKEN
from db import db
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")],
)
log = logging.getLogger("bot")

_background_tasks = set()

GROUP_COMMANDS = [
    BotCommand(command="bugun", description="Bugungi foto otchyotlar"),
    BotCommand(command="kecha", description="Kechagi foto otchyotlar"),
    BotCommand(command="hafta", description="Hafta (dush–yak): fakt / plan. /hafta oldingi"),
    BotCommand(command="oy", description="Oy (1-sanadan): fakt / plan. /oy sentabr, /oy oldingi"),
    BotCommand(command="mening", description="Mening natijalarim"),
    BotCommand(command="hisobot", description="Davr bo'yicha: /hisobot 01.10.2026 15.10.2026"),
    BotCommand(command="plan", description="Haftalik plan (admin)"),
    BotCommand(command="help", description="Yordam"),
]
PRIVATE_COMMANDS = [
    BotCommand(command="start", description="Botni ishga tushirish"),
    BotCommand(command="mening", description="Mening natijalarim"),
    BotCommand(command="help", description="Yordam"),
    BotCommand(command="id", description="Telegram ID im"),
]


async def on_startup(bot: Bot) -> None:
    await db.connect()
    me = await bot.get_me()
    log.info("Bot ishga tushdi: @%s", me.username)

    await bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())

    task = asyncio.create_task(scheduler.run(bot))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "✅ Bot ishga tushdi")
        except Exception as e:  # noqa: BLE001
            log.warning("Adminga xabar yuborilmadi (%s): %s", admin_id, e)


async def on_shutdown(bot: Bot) -> None:
    for task in list(_background_tasks):
        task.cancel()
    await db.close()
    log.info("Baza yopildi")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # drop_pending_updates=False: bot o'chiq turganda tashlangan rasmlar ham sanaladi
    # (Telegram ularni 24 soat saqlaydi)
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot to'xtatildi")
