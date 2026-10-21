"""Menyu tugmalari va inline callbacklar."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards import about_inline

router = Router()


@router.message(F.text == "ℹ️ Bot haqida")
async def about(message: Message) -> None:
    await message.answer(
        "Bu bot <b>aiogram 3</b> asosida yozilgan.\n"
        "Uni o'zingizga moslab kengaytirishingiz mumkin.",
        reply_markup=about_inline(),
    )


@router.message(F.text == "📞 Aloqa")
async def contact(message: Message) -> None:
    await message.answer("Aloqa uchun: @username  (o'zingiznikini yozing)")


@router.message(F.text == "❓ Yordam")
async def help_btn(message: Message) -> None:
    await message.answer("Yordam uchun /help buyrug'ini yuboring.")


@router.callback_query(F.data == "like")
async def like_cb(callback: CallbackQuery) -> None:
    await callback.answer("Rahmat! ❤️", show_alert=False)
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
