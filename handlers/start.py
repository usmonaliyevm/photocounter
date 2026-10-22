"""/start, /help, /id buyruqlari (shaxsiy chatda)."""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()
IN_PRIVATE = F.chat.type == "private"

HELP_TEXT = (
    "Bot guruhda rasmlarni sanaydi. Hisobot buyruqlari shaxsiy chatda ham, guruhda ham ishlaydi "
    "(guruhda — adminlar uchun; /mening ni har bir agent yoza oladi).\n\n"
    "<b>Hisobotlar:</b>\n"
    "/bugun — bugun kim nechta rasm tashlagan\n"
    "/kecha — kecha\n"
    "/hafta — shu hafta (dushanba–yakshanba): fakt / plan (%)\n"
    "/hafta oldingi, /hafta 15.10.2026 — o'tgan hafta / shu sana kirgan hafta\n"
    "/oy — shu oy (1-sanadan): fakt / plan (%)\n"
    "/oy oldingi, /oy sentabr, /oy 9, /oy 09.2025 — boshqa oy\n"
    "/hisobot 01.10.2026 15.10.2026 — ixtiyoriy davr\n"
    "/guruhlar — bir nechta guruh bo'lsa, qaysi biri bo'yicha hisobot\n"
    "/mening — o'z natijalarim (agentlar uchun)\n\n"
    "<b>Sozlash (adminlar):</b>\n"
    "/plan — haftalik planni ko'rish; /plan 100 — umumiy; /plan @username 120 — agentga\n"
    "/ism @username Muhammadillo — hisobotlarda shu ism chiqadi; /ism @username - — qaytarish\n"
    "/agent_off @username, /agent_on @username — agentni hisobotdan yashirish / qaytarish\n"
    "Username o'rniga ID ham bo'ladi.\n\n"
    "Har bir rasm = 1 ta foto otchyot. Bir xil rasm qayta tashlansa sanalmaydi: bot guruhda "
    "'avval yuborilgan' deb javob yozadi, rasmga 👎 bosadi, admin shaxsiy xabar oladi.\n"
    "Soxta (AI yasagan) rasm bo'lsa, guruhda o'sha rasmga reply qilib /fake yozing — hisobdan chiqadi "
    "(/unfake — qaytarish). "
    "Hisobotda agent yonida @username, bo'lmasa ID ko'rsatiladi; sanash doim ID bo'yicha, "
    "username o'zgarsa ham hisob bo'linmaydi.\n"
    "Har kuni kechqurun bugungi hisobot shu yerga o'zi keladi, yakshanba kuni haftalik ham."
)


@router.message(CommandStart(), IN_PRIVATE)
async def cmd_start(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "do'st"
    await message.answer(
        f"Assalomu alaykum, <b>{name}</b>! 👋\n\n"
        "Men agentlar guruhidagi foto otchyotlarni sanayman va natijani shu yerda, shaxsiy chatda beraman.\n\n"
        "<b>Ulash:</b>\n"
        "1. Meni agentlar guruhiga qo'shing.\n"
        "2. Guruhda meni <b>admin</b> qiling (aks holda rasmlarni ko'ra olmayman).\n"
        "3. Shu yerda /bugun yoki /hafta deb yozing.\n\n"
        "Guruhda men hech narsa yozmayman. Barcha buyruqlar: /help"
    )


@router.message(Command("help"), IN_PRIVATE)
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("id"), IN_PRIVATE)
async def cmd_id(message: Message) -> None:
    if message.from_user:
        await message.answer(f"Sizning ID: <code>{message.from_user.id}</code>")
