"""Tugmalar (klaviaturalar)."""
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def main_menu() -> ReplyKeyboardMarkup:
    """Asosiy menyu: pastki (reply) tugmalar."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ℹ️ Bot haqida"), KeyboardButton(text="📞 Aloqa")],
            [KeyboardButton(text="❓ Yordam")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Tugmani tanlang yoki xabar yozing...",
    )


def about_inline() -> InlineKeyboardMarkup:
    """Inline tugmalar misoli."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👍 Yoqdi", callback_data="like")],
            [InlineKeyboardButton(text="🌐 Telegram", url="https://telegram.org")],
        ]
    )
