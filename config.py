"""Konfiguratsiya: .env faylidan token va admin ID larni o'qiydi."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

_admin_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in _admin_raw.replace(" ", "").split(",") if x.strip().isdigit()]

if not BOT_TOKEN or "your-token-here" in BOT_TOKEN:
    sys.exit(
        "XATO: BOT_TOKEN topilmadi.\n"
        ".env faylini oching va @BotFather dan olingan tokenni BOT_TOKEN= qatoriga yozing."
    )
