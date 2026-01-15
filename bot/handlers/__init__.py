"""Регистрация всех обработчиков"""
from aiogram import Dispatcher
from bot.handlers import common, projects, keywords, chats, payment, admin


def register_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    
    # Порядок важен! Более специфичные обработчики должны быть раньше
    dp.include_router(admin.router)  # Админ команды первыми
    dp.include_router(common.router)
    dp.include_router(projects.router)
    dp.include_router(keywords.router)
    dp.include_router(chats.router)
    dp.include_router(payment.router)
