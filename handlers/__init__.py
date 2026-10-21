"""Barcha routerlarni bitta joyga yig'ish."""
from aiogram import Router

from . import admin, group, photos, start, stats

router = Router()
router.include_router(start.router)
router.include_router(admin.router)
router.include_router(stats.router)
router.include_router(group.router)
router.include_router(photos.router)
