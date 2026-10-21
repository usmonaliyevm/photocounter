"""Sana va vaqt yordamchilari (TIMEZONE bo'yicha, odatda Toshkent vaqti)."""
from datetime import date, datetime, timedelta, timezone
from typing import Tuple

from config import TZ


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()


def to_local(dt: datetime) -> datetime:
    """Telegramdan kelgan (UTC) vaqtni mahalliy vaqtga o'giradi."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ)


def week_range(d: date) -> Tuple[date, date]:
    """Dushanba - yakshanba."""
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def month_range(d: date) -> Tuple[date, date]:
    start = d.replace(day=1)
    if start.month == 12:
        nxt = start.replace(year=start.year + 1, month=1)
    else:
        nxt = start.replace(month=start.month + 1)
    return start, nxt - timedelta(days=1)


def fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def parse(text: str) -> date:
    """'2026-10-21', '21.10.2026' yoki '21.10.26' ko'rinishidagi sanani o'qiydi."""
    for f in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(text.strip(), f).date()
        except ValueError:
            continue
    raise ValueError(f"Sana noto'g'ri: {text}")
