"""Soxta rasm: admin guruhda rasmga reply qilib /fake yozadi — rasm hisobdan chiqadi. /unfake — qaytarish."""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, ReactionTypeEmoji

from access import is_admin_user
from config import DUP_REACT_EMOJI
from db import db
from reports import agent_label

log = logging.getLogger(__name__)
router = Router()
IN_GROUP = F.chat.type.in_({"group", "supergroup"})


async def _handle(message: Message, rejected: bool) -> None:
    user = message.from_user
    if user is None or not await is_admin_user(message.bot, user.id):
        return  # adminlardan boshqa uchun jim
    target = message.reply_to_message
    cmd = "fake" if rejected else "unfake"
    if target is None:
        await message.reply(f"Rasmga reply qilib <code>/{cmd}</code> yozing.")
        return

    row = await db.set_rejected(message.chat.id, target.message_id, rejected, user.id)
    if row is None:
        await message.reply("Bu xabar hisobda yo'q: rasm emas yoki takror sifatida allaqachon sanalmagan.")
        return

    who = agent_label(row["full_name"] or "noma'lum", row["username"], int(row["user_id"]))
    if rejected:
        await message.reply(f"❌ Rasm soxta deb belgilandi, hisobga olinmadi.\n{who}")
        if DUP_REACT_EMOJI:
            try:
                await target.react([ReactionTypeEmoji(emoji=DUP_REACT_EMOJI)])
            except Exception as e:  # noqa: BLE001
                log.debug("Reaksiya qo'yilmadi: %s", e)
    else:
        await message.reply(f"✅ Rasm hisobga qaytarildi.\n{who}")
        try:
            await target.react([])
        except Exception as e:  # noqa: BLE001
            log.debug("Reaksiya olinmadi: %s", e)
    log.info("/%s: chat %s, msg %s, agent %s, admin %s", cmd, message.chat.id, target.message_id, row["user_id"], user.id)


@router.message(Command("fake"), IN_GROUP)
async def cmd_fake(message: Message) -> None:
    await _handle(message, rejected=True)


@router.message(Command("unfake"), IN_GROUP)
async def cmd_unfake(message: Message) -> None:
    await _handle(message, rejected=False)
