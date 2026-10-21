"""Boshqa barcha xabarlar uchun javob (echo)."""
from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.photo)
async def photo_handler(message: Message) -> None:
    await message.answer("Rasm qabul qilindi 📷")


@router.message(F.document)
async def doc_handler(message: Message) -> None:
    await message.answer(f"Fayl qabul qilindi: <b>{message.document.file_name}</b>")


@router.message(F.text)
async def echo_text(message: Message) -> None:
    await message.answer(f"Siz yozdingiz: {message.text}")


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Bu turdagi xabarni hali tushunmayman 🙂")
