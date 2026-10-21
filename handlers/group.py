"""Bot guruhga qo'shilganda / chiqarilganda. Guruhga hech narsa yozmaydi, qo'shgan odamga shaxsiy xabar beradi."""
import logging
from html import escape

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
    adder = event.from_user
    if adder is not None and not adder.is_bot:
        existing = await db.get_chat(chat.id)
        if existing is None or not existing["owner_id"]:
            await db.set_chat_owner(chat.id, adder.id)
    log.info("Guruhga qo'shildi: %s (%s), qo'shgan: %s", chat.title, chat.id, adder.id if adder else None)

    is_admin = event.new_chat_member.status == "administrator"
    if adder is None:
        return
    text = (
        f"✅ Bot <b>{escape(chat.title or str(chat.id), quote=False)}</b> guruhiga qo'shildi.\n\n"
        + ("" if is_admin else "❗️ Botni guruhda <b>admin</b> qiling, aks holda rasmlarni ko'ra olmaydi.\n\n")
        + "Guruhda bot jim turadi. Hisobotlar shu yerda, shaxsiy chatda:\n"
        "/bugun, /kecha, /hafta, /oy, /hisobot. Barcha buyruqlar: /help"
    )
    try:
        await event.bot.send_message(adder.id, text)
    except Exception as e:  # noqa: BLE001
        log.warning("Qo'shgan odamga (%s) yozib bo'lmadi, u botga /start bosmagan: %s", adder.id, e)


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def bot_removed(event: ChatMemberUpdated) -> None:
    await db.remove_chat(event.chat.id)
    log.info("Guruhdan chiqarildi: %s (%s)", event.chat.title, event.chat.id)
