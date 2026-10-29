"""Takror rasmni admin ko'rib chiqadi.

Takror topilganda guruhdagi "avval yuborilgan" xabari va adminlarga ketgan shaxsiy xabar ostida tugmalar bo'ladi:
✅ Qabul qilish — rasm hisobga o'tadi (masalan, boshqa do'kon, lekin rasm o'xshash chiqqan);
❌ Rad etish — hisobga olinmaganicha qoladi. Tugmalarni faqat adminlar bosa oladi.
"""
import logging
from datetime import datetime
from html import escape
from typing import List, Optional

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
    ReactionTypeEmoji,
)

from access import can_access
from config import ADMIN_IDS, REACT_EMOJI
from db import db

log = logging.getLogger(__name__)
router = Router()
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


def review_keyboard(dup_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"dup:ok:{dup_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"dup:no:{dup_id}"),
        ]]
    )


def msg_link(chat_id: int, message_id: int) -> Optional[str]:
    """Superguruhdagi xabarga havola (oddiy guruhda havola bo'lmaydi)."""
    cid = str(chat_id)
    if cid.startswith("-100"):
        return f"https://t.me/c/{cid[4:]}/{message_id}"
    return None


def fmt_when(sent_at: Optional[str], day: Optional[str]) -> str:
    try:
        return datetime.fromisoformat(sent_at or "").strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return day or ""


def group_text(
    chat_id: int, orig_name: Optional[str], orig_sent_at: Optional[str], orig_day: Optional[str], orig_message_id: Optional[int]
) -> str:
    """Guruhdagi "avval yuborilgan" xabarining matni (yuborishda ham, keyin tahrirlashda ham shu)."""
    who = escape(orig_name or "noma'lum", quote=False)
    text = f"⚠️ Bu rasm avval yuborilgan ({who}, {fmt_when(orig_sent_at, orig_day)}), hisobga olinmadi."
    link = msg_link(chat_id, int(orig_message_id)) if orig_message_id else None
    if link:
        text += f'\n<a href="{link}">Asl rasm</a>'
    return text


async def _strip_keyboard(message) -> None:
    if not isinstance(message, Message):
        return
    try:
        await message.edit_reply_markup(reply_markup=None)
    except Exception as e:  # noqa: BLE001
        log.debug("Tugmalar olinmadi: %s", e)


async def _apply_decision(callback: CallbackQuery, row, note: str, reaction: Optional[List[ReactionTypeEmoji]]) -> None:
    """Qaror chiqdi: guruhdagi xabar va bosilgan xabarga yozib, tugmalarni olib tashlash; rasm reaksiyasini yangilash."""
    bot = callback.bot
    chat_id, message_id = int(row["chat_id"]), int(row["message_id"])
    reply_id = row["reply_message_id"]
    if reply_id:
        text = group_text(chat_id, row["orig_full_name"], row["orig_sent_at"], row["orig_day"], row["orig_message_id"])
        try:
            await bot.edit_message_text(
                text + "\n\n" + note, chat_id=chat_id, message_id=int(reply_id),
                link_preview_options=NO_PREVIEW, reply_markup=None,
            )
        except Exception as e:  # noqa: BLE001
            log.debug("Guruhdagi takror xabari tahrirlanmadi: %s", e)
    m = callback.message
    if isinstance(m, Message) and not (m.chat.id == chat_id and reply_id and m.message_id == int(reply_id)):
        try:
            await m.edit_text(m.html_text + "\n\n" + note, link_preview_options=NO_PREVIEW, reply_markup=None)
        except Exception as e:  # noqa: BLE001
            log.debug("Bildirishnoma tahrirlanmadi: %s", e)
    if reaction is not None:
        try:
            await bot.set_message_reaction(chat_id, message_id, reaction)
        except Exception as e:  # noqa: BLE001
            log.debug("Rasm reaksiyasi yangilanmadi: %s", e)


@router.callback_query(F.data.startswith("dup:"))
async def on_review(callback: CallbackQuery) -> None:
    try:
        _, action, raw_id = (callback.data or "").split(":")
        dup_id = int(raw_id)
    except ValueError:
        await callback.answer()
        return

    row = await db.get_duplicate(dup_id)
    if row is None:
        await callback.answer("Bu yozuv topilmadi.", show_alert=True)
        await _strip_keyboard(callback.message)
        return

    user = callback.from_user
    chat = await db.get_chat(int(row["chat_id"]))
    allowed = await can_access(callback.bot, user.id, chat) if chat is not None else user.id in ADMIN_IDS
    if not allowed:
        await callback.answer("Faqat adminlar qabul qilishi yoki rad etishi mumkin.", show_alert=True)
        return

    decision = row["decision"]
    if decision == "accepted":
        await callback.answer("Bu rasm allaqachon qabul qilingan va hisobga olingan. Chiqarish uchun: /fake", show_alert=True)
        await _strip_keyboard(callback.message)
        return
    if action == "no" and decision == "rejected":
        await callback.answer("Bu rasm allaqachon rad etilgan.", show_alert=True)
        await _strip_keyboard(callback.message)
        return

    admin = escape(user.full_name, quote=False)
    if action == "ok":
        if not await db.accept_duplicate(dup_id, user.id):
            await callback.answer("Qabul qilib bo'lmadi: eski yozuv, fayl ma'lumoti saqlanmagan.", show_alert=True)
            await _strip_keyboard(callback.message)
            return
        note = f"✅ Qabul qilindi, hisobga olindi — {admin}"
        toast = "✅ Rasm hisobga olindi"
        reaction: Optional[List[ReactionTypeEmoji]] = [ReactionTypeEmoji(emoji=REACT_EMOJI)] if REACT_EMOJI else []
    elif action == "no":
        await db.reject_duplicate(dup_id, user.id)
        note = f"❌ Rad etildi — {admin}"
        toast = "❌ Rad etildi, hisobga olinmadi"
        reaction = None  # 👎 qoladi
    else:
        await callback.answer()
        return

    await _apply_decision(callback, row, note, reaction)
    await callback.answer(toast)
    log.info(
        "Takror %s: chat %s, msg %s, agent %s, admin %s",
        "qabul qilindi" if action == "ok" else "rad etildi", row["chat_id"], row["message_id"], row["user_id"], user.id,
    )
