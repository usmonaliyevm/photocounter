"""Telegram bot — kirish nuqtasi. Ishga tushirish: python bot.py"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, ADMIN_IDS
from handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")],
)
log = logging.getLogger("bot")


async def on_startup(bot: Bot) -> None:
    me = await bot.get_me()
    log.info("Bot ishga tushdi: @%s", me.username)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "✅ Bot ishga tushdi")
        except Exception as e:  # noqa: BLE001
            log.warning("Adminga xabar yuborilmadi (%s): %s", admin_id, e)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot to'xtatildi")
