"""Ikki bazani birlashtirish: boshqa data.db dagi yozuvlarni joriy bazaga qo'shadi (takrorlamasdan).

Qachon kerak: bot bir muddat ikki joyda (masalan Mac va server) alohida bazalar bilan ishlagan bo'lsa.
    ./venv/bin/python merge_db.py /yol/boshqa_data.db            # joriy DB_PATH ga qo'shadi
    ./venv/bin/python merge_db.py /yol/boshqa_data.db --dry-run  # faqat ko'rsatadi

Qoidalar: rasmlar (chat_id, message_id) bo'yicha takrorlanmaydi; agentning berilgan ismi / plani /
faol holati ikkala bazada bo'lsa joriy bazadagisi qoladi, bo'lmasa boshqasidan olinadi.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime

from config import DB_PATH


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("other", help="qo'shiladigan baza (data.db)")
    p.add_argument("--into", default=DB_PATH, help=f"qaysi bazaga (default: {DB_PATH})")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    if not a.dry_run:
        backup = f"{a.into}.bak-{datetime.now():%Y%m%d-%H%M%S}"
        shutil.copy2(a.into, backup)
        print(f"Zaxira: {backup}")

    con = sqlite3.connect(a.into)
    con.execute("ATTACH DATABASE ? AS o", (a.other,))
    cur = con.cursor()

    def count(sql: str) -> int:
        return cur.execute(sql).fetchone()[0]

    stats = {}
    before = count("SELECT COUNT(*) FROM main.reports")

    # jadval ustunlari (eski bazada yangi ustunlar bo'lmasligi mumkin)
    def cols(schema: str, table: str) -> list:
        return [r[1] for r in cur.execute(f"PRAGMA {schema}.table_info({table})").fetchall()]

    def common(table: str) -> str:
        c = [x for x in cols("main", table) if x in cols("o", table) and x != "id"]
        return ", ".join(c)

    # agentlar: yo'qlarini qo'shish; borlarida bo'sh maydonlarni to'ldirish
    cur.execute(f"INSERT OR IGNORE INTO main.agents ({common('agents')}) SELECT {common('agents')} FROM o.agents")
    stats["yangi agentlar"] = cur.rowcount
    for col in ("display_name", "monthly_plan"):
        if col in cols("o", "agents"):
            cur.execute(
                f"UPDATE main.agents SET {col} = (SELECT {col} FROM o.agents WHERE o.agents.user_id = main.agents.user_id) "
                f"WHERE {col} IS NULL AND EXISTS (SELECT 1 FROM o.agents WHERE o.agents.user_id = main.agents.user_id AND o.agents.{col} IS NOT NULL)"
            )
    # guruhlar
    cur.execute(f"INSERT OR IGNORE INTO main.chats ({common('chats')}) SELECT {common('chats')} FROM o.chats")
    stats["yangi guruhlar"] = cur.rowcount
    for col in ("owner_id", "report_thread_id"):
        if col in cols("o", "chats"):
            cur.execute(
                f"UPDATE main.chats SET {col} = (SELECT {col} FROM o.chats WHERE o.chats.chat_id = main.chats.chat_id) "
                f"WHERE {col} IS NULL AND EXISTS (SELECT 1 FROM o.chats WHERE o.chats.chat_id = main.chats.chat_id AND o.chats.{col} IS NOT NULL)"
            )
    # rasmlar
    cur.execute(f"INSERT OR IGNORE INTO main.reports ({common('reports')}) SELECT {common('reports')} FROM o.reports")
    stats["yangi rasmlar"] = cur.rowcount
    # takrorlar: original_id boshqa bazadagi id — mos rasmni message_id orqali topamiz
    if "duplicates" in [r[0] for r in cur.execute("SELECT name FROM o.sqlite_master WHERE type='table'")]:
        base = ["chat_id", "message_id", "user_id", "distance", "day"]
        # yangi ustunlar (admin qabul/rad qilishi uchun fayl ma'lumoti va qaror) — ikkala bazada bo'lsa ko'chiriladi
        extra = [c for c in ("file_unique_id", "media_group_id", "sent_at", "phash", "reply_message_id", "decision", "decided_by")
                 if c in cols("o", "duplicates") and c in cols("main", "duplicates")]
        sel = ", ".join(f"d.{c}" for c in base + extra)
        rows = cur.execute(
            f"SELECT {sel}, r.message_id AS orig_msg FROM o.duplicates d LEFT JOIN o.reports r ON r.id = d.original_id"
        ).fetchall()
        ins_cols = ", ".join(base + extra + ["original_id"])
        marks = ", ".join("?" * (len(base) + len(extra) + 1))
        n = 0
        for *vals, orig_msg in rows:
            chat_id = vals[0]
            orig = cur.execute("SELECT id FROM main.reports WHERE chat_id = ? AND message_id = ?", (chat_id, orig_msg)).fetchone()
            if orig is None:
                continue
            cur.execute(f"INSERT OR IGNORE INTO main.duplicates ({ins_cols}) VALUES ({marks})", (*vals, orig[0]))
            n += cur.rowcount
        stats["yangi takrorlar"] = n
    # kutishdagilar, sozlamalar
    if "pending_imports" in [r[0] for r in cur.execute("SELECT name FROM o.sqlite_master WHERE type='table'")]:
        cur.execute(f"INSERT OR IGNORE INTO main.pending_imports ({common('pending_imports')}) SELECT {common('pending_imports')} FROM o.pending_imports")
        stats["kutishdagi"] = cur.rowcount
    cur.execute("INSERT OR IGNORE INTO main.settings SELECT * FROM o.settings")

    after = count("SELECT COUNT(*) FROM main.reports")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print(f"rasmlar: {before} -> {after}")
    if a.dry_run:
        con.rollback()
        print("(dry-run: hech narsa yozilmadi)")
    else:
        con.commit()
        print("Birlashtirildi.")
    con.close()


if __name__ == "__main__":
    main()
