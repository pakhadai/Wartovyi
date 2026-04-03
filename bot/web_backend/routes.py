"""
Точка входу API: підключає доменні роутери.
Для моків у тестах патчіть bot.infrastructure.database.*, а не цей модуль.
"""

from fastapi import APIRouter

from bot.web_backend.routers import chats, meta, punishments, settings, spam, statistics

router = APIRouter()
for sub in (meta, chats, settings, spam, statistics, punishments):
    router.include_router(sub.router)
