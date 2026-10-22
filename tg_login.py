"""Bir martalik: Telegram akkauntiga kirish (eski rasmlarni import qilish uchun).

Ishga tushirish:  ./venv/bin/python tg_login.py
Telefon raqam (+998...) va Telegramga kelgan kodni so'raydi, kirish 'history.session'
fayliga saqlanadi. Shundan keyin import_history.py hech narsa so'ramasdan ishlaydi.
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    try:
        from telethon import TelegramClient
    except ImportError:
        sys.exit("Telethon o'rnatilmagan: ./venv/bin/pip install telethon")
    api_id = os.getenv("TG_API_ID", "").strip()
    api_hash = os.getenv("TG_API_HASH", "").strip()
    if not api_id.isdigit() or not api_hash:
        sys.exit(
            "Avval .env ga TG_API_ID va TG_API_HASH ni yozing.\n"
            "Ularni https://my.telegram.org/apps dan olasiz (telefon raqam bilan kirib, ilova yaratasiz)."
        )
    client = TelegramClient("history", int(api_id), api_hash)
    await client.start()
    me = await client.get_me()
    print(f"\n✅ Kirildi: {me.first_name or ''} {me.last_name or ''} (@{me.username})".strip())
    print("Endi import qilish mumkin: ./venv/bin/python import_history.py --dry-run")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
