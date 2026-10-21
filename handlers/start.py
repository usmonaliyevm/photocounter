"""/start va /help buyruqlari."""
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "do'st"
    await message.answer(
        f"Assalomu alaykum, <b>{name}</b>! 👋\n\n"
        "Botga xush kelibsiz. Quyidagi menyudan foydalaning.",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Buyruqlar:</b>\n"
        "/start — botni ishga tushirish\n"
        "/help — yordam\n"
        "/id — Telegram ID ingizni ko'rish\n\n"
        "Shuningdek, menyudagi tugmalardan foydalanishingiz mumkin."
    )


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(f"Sizning ID: <code>{message.from_user.id}</code>")
