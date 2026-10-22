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

  3) Eksport HTML formatda bo'lsa (messages.html): foydalanuvchi ID lari yo'q, agentlar ISM bo'yicha
     bazadagi (bot ko'rgan) agentlarga bog'lanadi. Topilmagan ismlar ro'yxat qilib ko'rsatiladi:
        ./venv/bin/python import_history.py html ~/Downloads/ChatExport_Guruh
        ./venv/bin/python import_history.py html <papka> --map "Ism Familiya=123456789"   # qo'lda bog'lash

Qayta ishga tushirish xavfsiz: avval import qilingan yoki bot sanagan xabarlar qayta sanalmaydi.
Takror rasmlar bot bilan bir xil qoida bo'yicha (barmoq izi) aniqlanadi.
"""
import argparse
import asyncio
import html as htmllib
import json
import os
import re
import sys
from collections import Counter
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


# ---------------------------------------------------------------- 3) HTML export (ID siz, ism bo'yicha)
_MSG_SPLIT = re.compile(r'(?=<div class="message default clearfix(?: joined)?" id="message\d+">)')
_MSG_HEAD = re.compile(r'<div class="message default clearfix( joined)?" id="message(\d+)">')
_FROM = re.compile(r'<div class="from_name">(.*?)</div>', re.S)
_DATE = re.compile(r'class="pull_right date details" title="([^"]+)"')
_PHOTO = re.compile(r'<a class="photo_wrap[^"]*" href="([^"]+)"')
_TAGS = re.compile(r"<[^>]+>")


def _clean_name(raw: str) -> str:
    return " ".join(htmllib.unescape(_TAGS.sub("", raw)).split())


def _parse_html_date(text: str) -> datetime:
    """'20 October 2026, 08:34:29' (eksport qilgan kompyuter vaqti) -> TZ bo'yicha."""
    for fmt in ("%d %B %Y, %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
        try:
            return datetime.strptime(text.split(" UTC")[0].strip(), fmt).replace(tzinfo=TZ)
        except ValueError:
            continue
    raise ValueError(text)


async def _name_map(extra: dict) -> dict:
    """Ism (kichik harf) -> user_id: bazadagi agentlar (Telegram ismi va berilgan ism) + --map."""
    cur = await db.conn.execute("SELECT user_id, full_name, display_name FROM agents")
    names = {}
    for r in await cur.fetchall():
        for n in (r["full_name"], r["display_name"]):
            if n:
                names[" ".join(n.split()).lower()] = int(r["user_id"])
    for n, uid in extra.items():
        names[" ".join(n.split()).lower()] = uid
    return names


async def run_html(args: argparse.Namespace) -> None:
    folder = Path(args.export_dir).expanduser()
    pages = sorted(folder.glob("messages*.html"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 1))
    if not pages:
        sys.exit(f"messages.html topilmadi: {folder}")
    first = pages[0].read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<title>(.*?)</title>", first, re.S)
    title = _clean_name(m.group(1)) if m else ""

    chat_id = args.chat
    if chat_id is None:
        for c in await db.list_chats():
            if (c["title"] or "").strip().lower() == title.lower():
                chat_id = int(c["chat_id"])
                break
    if chat_id is None:
        sys.exit(f"Guruh bazada topilmadi: «{title}». --chat <id> bilan ko'rsating (masalan --chat -1004425642518).")
    print(f"== {title} ({chat_id}) == {len(pages)} ta sahifa")

    names = await _name_map(args.map or {})
    stats = Stats()
    unknown: Counter = Counter()
    seen = 0
    sender_name: Optional[str] = None
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        for block in _MSG_SPLIT.split(text):
            head = _MSG_HEAD.match(block)
            if head is None:
                continue
            joined, msg_id = bool(head.group(1)), int(head.group(2))
            if not joined:
                fm = _FROM.search(block)
                sender_name = _clean_name(fm.group(1)) if fm else None
            photos = _PHOTO.findall(block)
            if not photos:
                continue
            dm = _DATE.search(block)
            if dm is None:
                continue
            try:
                dt = _parse_html_date(dm.group(1))
            except ValueError:
                print(f"  sana o'qilmadi (msg {msg_id}): {dm.group(1)}")
                continue
            if args.since is not None and dt < args.since:
                continue
            seen += 1
            _progress(seen)
            if not sender_name:
                unknown["(ism yo'q)"] += 1
                continue
            uid = names.get(sender_name.lower())
            if uid is None:
                unknown[sender_name] += 1
                continue
            for i, rel in enumerate(photos):
                if i > 0:
                    print(f"  msg {msg_id}: bitta xabarda {len(photos)} ta rasm, faqat birinchisi sanaldi")
                    break
                image = None
                if not args.no_hash:
                    f = folder / htmllib.unescape(rel)
                    if f.is_file():
                        image = f.read_bytes()
                await import_photo(
                    stats, chat_id=chat_id, message_id=msg_id, user_id=uid,
                    full_name=sender_name, username=None, dt=dt, file_key=f"export:{msg_id}",
                    image=image, dry_run=args.dry_run,
                )
    print(f"Natija: rasmli xabarlar {seen}; {stats}")
    if unknown:
        print("\nBazada topilmagan ismlar (sanalmadi):")
        for n, c in unknown.most_common():
            print(f"  • {n} — {c} ta rasm")
        print(
            "Bu agentlar guruhga kamida 1 ta rasm tashlagach, importni qayta ishga tushiring, "
            "yoki qo'lda bog'lang: --map \"Ism=123456789\""
        )


def _parse_map(text: str) -> tuple:
    if "=" not in text:
        raise argparse.ArgumentTypeError("--map ko'rinishi: \"Ism Familiya=123456789\"")
    name, uid = text.rsplit("=", 1)
    if not uid.strip().isdigit():
        raise argparse.ArgumentTypeError(f"ID raqam bo'lishi kerak: {text}")
    return name.strip(), int(uid)


# ---------------------------------------------------------------- CLI
def _parse_since(text: str) -> datetime:
    d = dates.parse(text)
    return datetime(d.year, d.month, d.day, tzinfo=TZ).astimezone(timezone.utc)


def main() -> None:
    p = argparse.ArgumentParser(description="Eski rasmlarni bot bazasiga import qilish")
    p.add_argument("mode", nargs="?", default="telethon", choices=["telethon", "export", "html"])
    p.add_argument("export_dir", nargs="?", help="export/html rejimida: ChatExport papkasi")
    p.add_argument("--map", type=_parse_map, action="append", help='html rejimida ismni ID ga bog\'lash: --map "Ism=123456789"')
    p.add_argument("--chat", type=int, help="faqat shu guruh (bot ko'rinishidagi chat_id, masalan -1004425642518)")
    p.add_argument("--since", type=_parse_since, help="shu sanadan boshlab, masalan 01.10.2026")
    p.add_argument("--dry-run", action="store_true", help="bazaga yozmasdan faqat sanab ko'rish")
    p.add_argument("--no-hash", action="store_true", help="rasmlarni yuklamasdan (tezroq, lekin takrorlar aniqlanmaydi)")
    args = p.parse_args()
    if args.mode in ("export", "html") and not args.export_dir:
        p.error(f"{args.mode} rejimida papka ko'rsating: import_history.py {args.mode} <papka>")
    args.map = dict(args.map) if args.map else {}

    async def run() -> None:
        await db.connect()
        try:
            if args.mode == "export":
                await run_export(args)
            elif args.mode == "html":
                await run_html(args)
            else:
                await run_telethon(args)
            if args.dry_run:
                print("(dry-run: bazaga yozilmadi; takrorlar faqat bazada bor rasmlar bilan solishtirildi)")
        finally:
            await db.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
