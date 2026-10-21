"""Barcha routerlarni bitta joyga yig'ish."""
from aiogram import Router

from . import start, menu, echo

router = Router()
router.include_router(start.router)
router.include_router(menu.router)
router.include_router(echo.router)  # echo har doim oxirida bo'lishi kerak
