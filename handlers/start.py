"""/start, /help, /id buyruqlari."""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()

HELP_TEXT = (
    "<b>Guruhda ishlaydigan buyruqlar:</b>\n"
    "/bugun — bugungi foto otchyotlar\n"
    "/kecha — kechagi foto otchyotlar\n"
    "/hafta — shu hafta (dushanba–yakshanba): fakt / plan (%)\n"
    "/hafta oldingi, /hafta 15.10.2026 — o'tgan hafta / shu sana kirgan hafta\n"
    "/oy — shu oy (1-sanadan): fakt / plan (%)\n"
    "/oy oldingi, /oy sentabr, /oy 9, /oy 09.2025 — boshqa oy\n"
    "/hisobot 01.10.2026 15.10.2026 — ixtiyoriy davr\n"
    "/mening — o'z natijalarim (shaxsiy chatda ham ishlaydi)\n\n"
    "<b>Adminlar uchun:</b>\n"
    "/plan — haftalik planni ko'rish\n"
    "/plan 100 — umumiy haftalik plan\n"
    "/plan 120 (agent xabariga reply qilib) — shu agent uchun plan\n"
    "+ism Muhammadillo (agent xabariga reply qilib) — hisobotlarda shu ism chiqadi\n"
    "-ism (reply qilib) — Telegram ismiga qaytarish\n"
    "/agent_off, /agent_on (reply qilib) — agentni hisobotdan yashirish / qaytarish\n\n"
    "Bot guruhga tashlangan har bir rasmni foto otchyot deb sanaydi. "
    "Har kuni kechqurun bugungi hisobotni, yakshanba kuni haftalikni o'zi yuboradi."
)


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "do'st"
    await message.answer(
        f"Assalomu alaykum, <b>{name}</b>! 👋\n\n"
        "Men savdo agentlarining foto otchyotlarini sanayman.\n\n"
        "<b>Ulash:</b>\n"
        "1. Meni agentlar guruhiga qo'shing.\n"
        "2. Meni guruhda <b>admin</b> qiling (shunda barcha rasmlarni ko'ra olaman).\n"
        "3. Agentlar odatdagidek rasm tashlayveradi, men sanab boraman.\n\n"
        "Buyruqlar ro'yxati: /help"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    if message.from_user:
        await message.answer(f"Sizning ID: <code>{message.from_user.id}</code>")
