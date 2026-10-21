"""Konfiguratsiya: .env faylidan sozlamalarni o'qiydi."""
import os
import sys
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

_admin_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in _admin_raw.replace(" ", "").split(",") if x.strip().isdigit()]

TIMEZONE = os.getenv("TIMEZONE", "").strip() or "Asia/Tashkent"
TZ = ZoneInfo(TIMEZONE)

DEFAULT_WEEKLY_PLAN = int(os.getenv("DEFAULT_WEEKLY_PLAN", "").strip() or 100)
REPORT_TIME = os.getenv("REPORT_TIME", "21:00").strip()
REACT_EMOJI = os.getenv("REACT_EMOJI", "👍").strip()
DB_PATH = os.getenv("DB_PATH", "").strip() or "data.db"

if not BOT_TOKEN or "your-token-here" in BOT_TOKEN:
    sys.exit(
        "XATO: BOT_TOKEN topilmadi.\n"
        ".env faylini oching va @BotFather dan olingan tokenni BOT_TOKEN= qatoriga yozing."
    )
