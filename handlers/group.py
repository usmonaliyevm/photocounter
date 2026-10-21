"""Bot guruhga qo'shilganda / chiqarilganda."""
import logging

from aiogram import Router
from aiogram.filters import JOIN_TRANSITION, LEAVE_TRANSITION, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

from db import db

log = logging.getLogger(__name__)
router = Router()


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def bot_added(event: ChatMemberUpdated) -> None:
    chat = event.chat
    if chat.type not in ("group", "supergroup"):
        return
    await db.upsert_chat(chat.id, chat.title or "")
    log.info("Guruhga qo'shildi: %s (%s)", chat.title, chat.id)
    await event.bot.send_message(
        chat.id,
        "Salom! 👋 Men guruhga tashlangan rasmlarni foto otchyot sifatida sanayman.\n\n"
        "Meni <b>admin</b> qilishni unutmang, aks holda rasmlarni ko'ra olmayman.\n"
        "Hisobot: /bugun, /hafta, /oy. Barcha buyruqlar: /help",
    )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def bot_removed(event: ChatMemberUpdated) -> None:
    await db.remove_chat(event.chat.id)
    log.info("Guruhdan chiqarildi: %s (%s)", event.chat.title, event.chat.id)
