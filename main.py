"""Главная точка входа приложения"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from redis.asyncio import Redis

from config import settings
from bot.handlers import register_all_handlers
from bot.middlewares import SubscriptionMiddleware
from database.database import init_db

# Настройка логирования
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Установка команд бота для меню"""
    
    # Команды для обычных пользователей
    user_commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="profile", description="👤 Личный кабинет"),
        BotCommand(command="projects", description="📁 Мои проекты"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="language", description="🌐 Сменить язык"),
    ]
    
    # Команды для админов (расширенные)
    admin_commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="profile", description="👤 Личный кабинет"),
        BotCommand(command="projects", description="📁 Мои проекты"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="admin_stats", description="📊 Статистика юзерботов"),
        BotCommand(command="admin_rebalance", description="🔄 Ребалансировка чатов"),
        BotCommand(command="admin_limits", description="⚙️ Лимиты системы"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="language", description="🌐 Сменить язык"),
    ]
    
    # Устанавливаем команды по умолчанию для всех пользователей
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    
    # Устанавливаем расширенные команды для админов
    admin_ids = settings.get_admin_ids()
    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(
                admin_commands, 
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
            logger.info(f"Установлены админ-команды для {admin_id}")
        except Exception as e:
            logger.warning(f"Не удалось установить команды для админа {admin_id}: {e}")
    
    logger.info("Команды бота установлены")


async def main():
    """Основная функция запуска бота"""
    
    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    await init_db()
    
    # Инициализация Redis для хранения состояний
    redis = Redis.from_url(settings.REDIS_URL)
    storage = RedisStorage(redis=redis)
    
    # Создание бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # Установка команд меню
    await set_bot_commands(bot)
    
    # Регистрация middleware
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    
    # Регистрация обработчиков
    register_all_handlers(dp)
    
    logger.info("Бот запущен!")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await redis.close()


if __name__ == '__main__':
    asyncio.run(main())
