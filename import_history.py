"""Guruhning eski tarixidagi rasmlarni bot bazasiga import qilish.

Bot guruhga qo'shilgunga qadar tashlangan rasmlarni Bot API ko'rmaydi, shuning uchun
tarix o'z Telegram akkauntingiz orqali o'qiladi. Ikki usul:

  1) Akkaunt orqali (Telethon). .env ga TG_API_ID va TG_API_HASH yozing (my.telegram.org),
     birinchi safar telefon raqam va kod so'raladi:
        ./venv/bin/python import_history.py                       # bot ulangan barcha guruhlar, to'liq tarix
        ./venv/bin/python import_history.py --since 01.10.2026    # shu sanadan boshlab
        ./venv/bin/python import_history.py --chat -1004425642518 # faqat bitta guruh
        ./venv/bin/python import_history.py --dry-run             # yozmasdan, faqat sanab ko'rish

  2) Telegram Desktop → guruh → ⋮ → "Export chat history" (Format: JSON, Photos belgilangan):
        ./venv/bin/python import_history.py export ~/Downloads/ChatExport_2026-10-21

Qayta ishga tushirish xavfsiz: avval import qilingan yoki bot sanagan xabarlar qayta sanalmaydi.
Takror rasmlar bot bilan bir xil qoida bo'yicha (barmoq izi) aniqlanadi.
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import dates
import imghash
from config import DUP_DAYS, DUP_THRESHOLD, TZ
from db import db


class Stats:
    def __init__(self) -> None:
        self.added = self.dups = self.known = self.failed_hash = 0

    def __str__(self) -> str:
        return (
            f"sanaldi: {self.added}, takror: {self.dups}, avvaldan bor edi: {self.known}"
            + (f", hash olinmadi: {self.failed_hash}" if self.failed_hash else "")
        )


async def import_photo(
    stats: Stats,
    *,
    chat_id: int,
    message_id: int,
    user_id: int,
    full_name: str,
    username: Optional[str],
    dt: datetime,
    file_key: str,
    image: Optional[bytes],
    dry_run: bool,
) -> None:
    if await db.is_known_message(chat_id, message_id):
        stats.known += 1
        return
    local = dates.to_local(dt)
    day = local.date()

    phash = None
    if image:
        try:
            phash = imghash.dhash(image)
        except Exception:  # noqa: BLE001
            stats.failed_hash += 1

    original = await db.find_by_file(chat_id, file_key)
    distance = 0
    if original is None and phash is not None:
        since_day = (day - timedelta(days=DUP_DAYS)).isoformat()
        found = await db.find_similar(chat_id, phash, DUP_THRESHOLD, since_day)
        if found is not None:
            original, distance = found

    if dry_run:
        stats.dups += 1 if original is not None else 0
        stats.added += 0 if original is not None else 1
        return

    await db.upsert_agent(user_id, full_name, username)
    if original is not None:
        await db.add_duplicate(
            chat_id=chat_id, message_id=message_id, user_id=user_id,
            original_id=int(original["id"]), distance=distance, day=day.isoformat(),
        )
        stats.dups += 1
    else:
        ok = await db.add_report(
            chat_id=chat_id, message_id=message_id, user_id=user_id, file_unique_id=file_key,
            media_group_id=None, sent_at=local.isoformat(timespec="seconds"), day=day.isoformat(), phash=phash,
        )
        stats.added += 1 if ok else 0


def _progress(n: int) -> None:
    if n % 50 == 0:
        print(f"  ... {n} ta rasm ko'rildi", flush=True)


# ---------------------------------------------------------------- 1) Telethon
async def run_telethon(args: argparse.Namespace) -> None:
    try:
        from telethon import TelegramClient
    except ImportError:
        sys.exit("Telethon o'rnatilmagan: ./venv/bin/pip install telethon")

    api_id = os.getenv("TG_API_ID", "").strip()
    api_hash = os.getenv("TG_API_HASH", "").strip()
    if not api_id.isdigit() or not api_hash:
        sys.exit(
            "TG_API_ID va TG_API_HASH topilmadi.\n"
            "https://my.telegram.org → API development tools → ilova yarating,\n"
            "api_id va api_hash ni .env fayliga yozing."
        )

    client = TelegramClient("history", int(api_id), api_hash)
    await client.start()  # birinchi safar telefon raqam va kodni so'raydi
    me = await client.get_me()
    print(f"Akkaunt: {me.first_name or ''} {me.last_name or ''} (@{me.username})".strip())
    await client.get_dialogs()  # guruhlarni keshga olish, aks holda ID bo'yicha topilmaydi

    chats = await db.list_chats()
    if args.chat is not None:
        chats = [c for c in chats if int(c["chat_id"]) == args.chat]
        if not chats:
            chats = [{"chat_id": args.chat, "title": ""}]
    if not chats:
        sys.exit("Bot hali birorta guruhga ulanmagan (chats jadvali bo'sh). --chat <id> bilan ko'rsating.")

    since = args.since
    for chat in chats:
        chat_id = int(chat["chat_id"])
        title = chat["title"] or str(chat_id)
        print(f"\n== {title} ({chat_id}) ==")
        try:
            entity = await client.get_entity(chat_id)
        except Exception as e:  # noqa: BLE001
            print(f"  Guruh topilmadi (akkauntingiz shu guruhda bo'lishi kerak): {e}")
            continue

        stats = Stats()
        seen = 0
        async for msg in client.iter_messages(entity, reverse=True, offset_date=since):
            is_photo = msg.photo is not None
            is_image_doc = (
                msg.document is not None and (msg.document.mime_type or "").startswith("image/")
            )
            if not (is_photo or is_image_doc):
                continue
            if msg.sender_id is None or msg.sender_id < 0:  # kanal / anonim admin
                continue
            sender = msg.sender
            if sender is not None and getattr(sender, "bot", False):
                continue
            if sender is not None:
                full_name = " ".join(filter(None, [sender.first_name, sender.last_name])) or f"ID {msg.sender_id}"
                username = sender.username
            else:
                full_name, username = f"ID {msg.sender_id}", None

            seen += 1
            _progress(seen)

            image = None
            if not args.no_hash:
                try:
                    if is_photo:
                        image = await client.download_media(msg, file=bytes, thumb=_pick_size(msg.photo.sizes))
                    else:
                        image = await client.download_media(msg, file=bytes, thumb=-1)
                except Exception as e:  # noqa: BLE001
                    print(f"  rasm yuklanmadi (msg {msg.id}): {e}")

            file_key = f"tg:{msg.photo.id if is_photo else msg.document.id}"
            await import_photo(
                stats, chat_id=chat_id, message_id=msg.id, user_id=msg.sender_id,
                full_name=full_name, username=username, dt=msg.date, file_key=file_key,
                image=image, dry_run=args.dry_run,
            )
        print(f"  Natija: ko'rildi {seen}; {stats}")

    await client.disconnect()


def _pick_size(sizes):
    """~320px li nusxa: eng kichik, lekin kengligi >= 200 bo'lgan o'lcham."""
    with_w = [s for s in sizes if getattr(s, "w", 0)]
    with_w.sort(key=lambda s: s.w)
    for s in with_w:
        if s.w >= 200:
            return s
    return with_w[-1] if with_w else -1


# ---------------------------------------------------------------- 2) Telegram Desktop export
def _export_chat_id(data: dict) -> int:
    raw = int(data["id"])
    ctype = data.get("type", "")
    if "supergroup" in ctype or "channel" in ctype:
        return int(f"-100{raw}")
    return -raw


async def run_export(args: argparse.Namespace) -> None:
    folder = Path(args.export_dir).expanduser()
    result = folder / "result.json"
    if not result.exists():
        sys.exit(f"result.json topilmadi: {folder}")
    data = json.loads(result.read_text(encoding="utf-8"))
    chat_id = args.chat if args.chat is not None else _export_chat_id(data)
    title = data.get("name", "")
    print(f"== {title} ({chat_id}) ==")
    if not args.dry_run:
        await db.upsert_chat(chat_id, title)

    stats = Stats()
    seen = 0
    for m in data.get("messages", []):
        if m.get("type") != "message":
            continue
        from_id = str(m.get("from_id", ""))
        if not from_id.startswith("user"):
            continue
        path = m.get("photo")
        if not path and (m.get("mime_type") or "").startswith("image/"):
            path = m.get("file")
        if not path:
            continue

        if "date_unixtime" in m:
            dt = datetime.fromtimestamp(int(m["date_unixtime"]), tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(m["date"]).replace(tzinfo=TZ)
        if args.since is not None and dt < args.since:
            continue

        seen += 1
        _progress(seen)
        user_id = int(from_id[4:])
        full_name = m.get("from") or f"ID {user_id}"
        image = None
        if not args.no_hash:
            f = folder / path
            if f.is_file():
                image = f.read_bytes()
        await import_photo(
            stats, chat_id=chat_id, message_id=int(m["id"]), user_id=user_id,
            full_name=full_name, username=None, dt=dt, file_key=f"export:{m['id']}",
            image=image, dry_run=args.dry_run,
        )
    print(f"Natija: ko'rildi {seen}; {stats}")


# ---------------------------------------------------------------- CLI
def _parse_since(text: str) -> datetime:
    d = dates.parse(text)
    return datetime(d.year, d.month, d.day, tzinfo=TZ).astimezone(timezone.utc)


def main() -> None:
    p = argparse.ArgumentParser(description="Eski rasmlarni bot bazasiga import qilish")
    p.add_argument("mode", nargs="?", default="telethon", choices=["telethon", "export"])
    p.add_argument("export_dir", nargs="?", help="export rejimida: ChatExport papkasi")
    p.add_argument("--chat", type=int, help="faqat shu guruh (bot ko'rinishidagi chat_id, masalan -1004425642518)")
    p.add_argument("--since", type=_parse_since, help="shu sanadan boshlab, masalan 01.10.2026")
    p.add_argument("--dry-run", action="store_true", help="bazaga yozmasdan faqat sanab ko'rish")
    p.add_argument("--no-hash", action="store_true", help="rasmlarni yuklamasdan (tezroq, lekin takrorlar aniqlanmaydi)")
    args = p.parse_args()
    if args.mode == "export" and not args.export_dir:
        p.error("export rejimida papka ko'rsating: import_history.py export <papka>")

    async def run() -> None:
        await db.connect()
        try:
            if args.mode == "export":
                await run_export(args)
            else:
                await run_telethon(args)
            if args.dry_run:
                print("(dry-run: bazaga yozilmadi; takrorlar faqat bazada bor rasmlar bilan solishtirildi)")
        finally:
            await db.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
