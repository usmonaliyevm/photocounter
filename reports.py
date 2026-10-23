"""Hisobot matnlarini tayyorlash (HTML)."""
import calendar
from datetime import date, timedelta
from html import escape as _escape
from typing import Optional

import dates
from db import db


def escape(text: str) -> str:
    """Telegram HTML uchun: faqat & < > almashtiriladi (apostrof o'z holicha qoladi)."""
    return _escape(text, quote=False)


def agent_label(name: str, username: Optional[str], user_id: int) -> str:
    """Admin xabarlaridagi ko'rinish: Ism (@username) yoki Ism (id 123). Sanash har doim ID bo'yicha."""
    who = escape(name or str(user_id))
    return f"{who} (@{escape(username)})" if username else f"{who} (id {user_id})"


def report_label(name: str, username: Optional[str], user_id: int) -> str:
    """Hisobotdagi ko'rinish: Ism (@username); username bo'lmasa faqat ism (ID /id buyrug'i orqali)."""
    who = escape(name or str(user_id))
    return f"{who} (@{escape(username)})" if username else who


BAR_LEN = 10
MONTHS_UZ = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]


def bar(p: int) -> str:
    filled = max(0, min(BAR_LEN, round(p / 100 * BAR_LEN)))
    return "▓" * filled + "░" * (BAR_LEN - filled)


def _expected_pct(d1: date, d2: date) -> Optional[int]:
    """Davr hali tugamagan bo'lsa: bugungacha (shu kun bilan) qancha foiz bajarilishi kutiladi."""
    today = dates.today()
    if d1 <= today < d2:
        total = (d2 - d1).days + 1
        return pct((today - d1).days + 1, total)
    return None


def pct(fact: int, plan: int) -> int:
    return round(fact * 100 / plan) if plan > 0 else 0


def period_plan(monthly_plan: int, d1: date, d2: date) -> int:
    """Oylik plandan davr uchun plan: to'liq oy uchun aynan o'zi, hafta/kun uchun kunlarga mutanosib."""
    total = 0.0
    d = d1
    while d <= d2:
        total += monthly_plan / calendar.monthrange(d.year, d.month)[1]
        d += timedelta(days=1)
    return round(total)


async def period_text(
    chat_id: int, chat_title: Optional[str], header: str, d1: date, d2: date, with_plan: bool
) -> str:
    rows = await db.counts_by_agent(chat_id, d1.isoformat(), d2.isoformat())
    default_plan = await db.get_default_plan()

    lines = [f"<b>{header}</b>"]
    if chat_title:
        lines.append(escape(chat_title))
    if with_plan:
        dplan = period_plan(default_plan, d1, d2)
        days = (d2 - d1).days + 1
        if (d1, d2) == dates.month_range(d1):
            lines.append(f"Plan: har bir agentga <b>{dplan} ta</b> (oyiga)")
        else:
            lines.append(f"Plan: har bir agentga <b>{dplan} ta</b> ({days} kun uchun, oylik {default_plan} dan)")
        expected = _expected_pct(d1, d2)
        if expected is not None:
            lines.append(f"Bugungacha kutilgan bajarilish: ~{expected}%")
    lines.append("")

    if not rows:
        lines.append("Hali birorta foto otchyot yo'q.")
        return "\n".join(lines)

    total_fact = 0
    for i, r in enumerate(rows, 1):
        name = report_label(r["full_name"], r["username"], int(r["user_id"]))
        fact = int(r["cnt"])
        total_fact += fact
        dups = int(r["dups"]) if "dups" in r.keys() else 0
        fakes = int(r["fakes"]) if "fakes" in r.keys() else 0
        notes = (f" · ⚠️ takror {dups}" if dups else "") + (f" · ❌ soxta {fakes}" if fakes else "")
        if with_plan:
            custom = r["monthly_plan"]
            plan = period_plan(int(custom or default_plan), d1, d2)
            p = pct(fact, plan)
            extra = f" (plan {plan})" if custom else ""
            lines.append(f"{i}. {name}{extra}")
            done = " ✅" if p >= 100 else ""
            lines.append(f"      {bar(p)} <b>{fact} ta</b> — {p}%{done}{notes}")
        else:
            lines.append(f"{i}. {name} — <b>{fact} ta</b>{notes}")

    lines.append("")
    # Jami faqat son: agentlar soni o'zgarib turadi, umumiy plan ma'nosiz
    lines.append(f"<b>Jami: {total_fact} ta rasm</b> · {len(rows)} agent")
    return "\n".join(lines)


async def daily_text(chat_id: int, chat_title: Optional[str], d: date, label: str = "Bugun") -> str:
    return await period_text(chat_id, chat_title, f"📅 {label}, {dates.fmt(d)}", d, d, with_plan=False)


async def weekly_text(chat_id: int, chat_title: Optional[str], ref: date) -> str:
    d1, d2 = dates.week_range(ref)
    header = f"📊 Hafta: {d1.strftime('%d.%m')} – {dates.fmt(d2)}"
    return await period_text(chat_id, chat_title, header, d1, d2, with_plan=True)


async def monthly_text(chat_id: int, chat_title: Optional[str], ref: date) -> str:
    d1, d2 = dates.month_range(ref)
    header = f"🗓 {MONTHS_UZ[d1.month - 1]} {d1.year}"
    return await period_text(chat_id, chat_title, header, d1, d2, with_plan=True)


async def range_text(chat_id: int, chat_title: Optional[str], d1: date, d2: date) -> str:
    header = f"📋 Davr: {dates.fmt(d1)} – {dates.fmt(d2)}"
    return await period_text(chat_id, chat_title, header, d1, d2, with_plan=True)


async def mine_text(user_id: int, full_name: str, ref: date, chat_id: Optional[int]) -> str:
    agent = await db.get_agent(user_id)
    monthly_plan = int(agent["monthly_plan"]) if agent and agent["monthly_plan"] else await db.get_default_plan()
    full_name = await db.name_of(user_id, full_name)
    username = agent["username"] if agent else None

    today_n = await db.count_for_user(user_id, ref.isoformat(), ref.isoformat(), chat_id)
    w1, w2 = dates.week_range(ref)
    week_n = await db.count_for_user(user_id, w1.isoformat(), w2.isoformat(), chat_id)
    weekly_plan = period_plan(monthly_plan, w1, w2)
    m1, m2 = dates.month_range(ref)
    month_n = await db.count_for_user(user_id, m1.isoformat(), m2.isoformat(), chat_id)
    pw, pm = pct(week_n, weekly_plan), pct(month_n, monthly_plan)
    expected = _expected_pct(m1, m2)

    return (
        f"👤 <b>{report_label(full_name, username, user_id)}</b>\n\n"
        f"Bugun: <b>{today_n} ta</b>\n"
        f"Hafta: {bar(pw)} <b>{week_n} ta</b> / {weekly_plan} — {pw}%\n"
        f"Oy:      {bar(pm)} <b>{month_n} ta</b> / {monthly_plan} — {pm}%"
        + (f"\n(bugungacha kutilgan: ~{expected}%)" if expected is not None else "")
    )
