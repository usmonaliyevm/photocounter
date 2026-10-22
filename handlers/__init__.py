"""Barcha routerlarni bitta joyga yig'ish."""
from aiogram import Router

from . import admin, fake, group, names, photos, start, stats

router = Router()
router.include_router(start.router)
router.include_router(admin.router)
router.include_router(names.router)
router.include_router(fake.router)
router.include_router(stats.router)
router.include_router(group.router)
router.include_router(photos.router)
