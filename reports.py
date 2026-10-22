"""Hisobot matnlarini tayyorlash (HTML)."""
from datetime import date
from html import escape as _escape
from typing import Optional

import dates
from db import db


def escape(text: str) -> str:
    """Telegram HTML uchun: faqat & < > almashtiriladi (apostrof o'z holicha qoladi)."""
    return _escape(text, quote=False)


def agent_label(name: str, username: Optional[str], user_id: int) -> str:
    """Hisobotdagi ko'rinish: Ism (@username) yoki Ism (id 123). Sanash har doim ID bo'yicha."""
    who = escape(name or str(user_id))
    return f"{who} (@{escape(username)})" if username else f"{who} (id {user_id})"


def pct(fact: int, plan: int) -> int:
    return round(fact * 100 / plan) if plan > 0 else 0


def period_plan(weekly_plan: int, d1: date, d2: date) -> int:
    """Haftalik plandan davr uchun plan: hafta uchun aynan o'zi, oy uchun kunlar soniga qarab."""
    days = (d2 - d1).days + 1
    return round(weekly_plan * days / 7)


async def period_text(
    chat_id: int, chat_title: Optional[str], header: str, d1: date, d2: date, with_plan: bool
) -> str:
    rows = await db.counts_by_agent(chat_id, d1.isoformat(), d2.isoformat())
    default_plan = await db.get_default_plan()

    title = f"<b>{header}</b>"
    if chat_title:
        title += f"\n{escape(chat_title)}"
    lines = [title, ""]

    if not rows:
        lines.append("Hali birorta foto otchyot yo'q.")
        return "\n".join(lines)

    total_fact = 0
    total_plan = 0
    for i, r in enumerate(rows, 1):
        name = agent_label(r["full_name"], r["username"], int(r["user_id"]))
        fact = int(r["cnt"])
        total_fact += fact
        dups = int(r["dups"]) if "dups" in r.keys() else 0
        fakes = int(r["fakes"]) if "fakes" in r.keys() else 0
        dup_note = (f"  ⚠️ takror: {dups}" if dups else "") + (f"  ❌ soxta: {fakes}" if fakes else "")
        if with_plan:
            plan = period_plan(int(r["weekly_plan"] or default_plan), d1, d2)
            total_plan += plan
            lines.append(f"{i}. {name} — {fact} / {plan} ({pct(fact, plan)}%){dup_note}")
        else:
            lines.append(f"{i}. {name} — {fact} ta{dup_note}")

    lines.append("")
    if with_plan:
        lines.append(f"<b>Jami:</b> {total_fact} / {total_plan} ({pct(total_fact, total_plan)}%)")
    else:
        lines.append(f"<b>Jami:</b> {total_fact} ta")
    return "\n".join(lines)


async def daily_text(chat_id: int, chat_title: Optional[str], d: date, label: str = "Bugun") -> str:
    return await period_text(chat_id, chat_title, f"📅 {label} ({dates.fmt(d)})", d, d, with_plan=False)


async def weekly_text(chat_id: int, chat_title: Optional[str], ref: date) -> str:
    d1, d2 = dates.week_range(ref)
    header = f"📊 Hafta ({dates.fmt(d1)} – {dates.fmt(d2)})"
    return await period_text(chat_id, chat_title, header, d1, d2, with_plan=True)


async def monthly_text(chat_id: int, chat_title: Optional[str], ref: date) -> str:
    d1, d2 = dates.month_range(ref)
    header = f"🗓 Oy ({dates.fmt(d1)} – {dates.fmt(d2)})"
    return await period_text(chat_id, chat_title, header, d1, d2, with_plan=True)


async def range_text(chat_id: int, chat_title: Optional[str], d1: date, d2: date) -> str:
    header = f"📋 Davr ({dates.fmt(d1)} – {dates.fmt(d2)})"
    return await period_text(chat_id, chat_title, header, d1, d2, with_plan=True)


async def mine_text(user_id: int, full_name: str, ref: date, chat_id: Optional[int]) -> str:
    agent = await db.get_agent(user_id)
    weekly_plan = int(agent["weekly_plan"]) if agent and agent["weekly_plan"] else await db.get_default_plan()
    full_name = await db.name_of(user_id, full_name)
    username = agent["username"] if agent else None

    today_n = await db.count_for_user(user_id, ref.isoformat(), ref.isoformat(), chat_id)
    w1, w2 = dates.week_range(ref)
    week_n = await db.count_for_user(user_id, w1.isoformat(), w2.isoformat(), chat_id)
    m1, m2 = dates.month_range(ref)
    month_n = await db.count_for_user(user_id, m1.isoformat(), m2.isoformat(), chat_id)
    month_plan = period_plan(weekly_plan, m1, m2)

    return (
        f"👤 <b>{agent_label(full_name, username, user_id)}</b>\n\n"
        f"Bugun: <b>{today_n}</b> ta\n"
        f"Shu hafta: <b>{week_n}</b> / {weekly_plan} ({pct(week_n, weekly_plan)}%)\n"
        f"Shu oy: <b>{month_n}</b> / {month_plan} ({pct(month_n, month_plan)}%)"
    )
