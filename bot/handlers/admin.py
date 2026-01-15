"""Административные команды для управления юзерботами"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config import settings
from database.database import async_session_maker
from userbot.load_balancer import UserbotLoadBalancer

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("admin_stats"))
async def admin_stats(message: Message):
    """Статистика по юзерботам (только для админов)"""
    
    if message.from_user.id not in settings.admin_ids_list:
        await message.answer("❌ Доступ запрещен")
        return
    
    async with async_session_maker() as session:
        stats = await UserbotLoadBalancer.get_userbot_stats(session)
        
        if not stats:
            await message.answer("⚠️ Нет настроенных юзерботов")
            return
        
        text = "📊 **Статистика юзерботов:**\n\n"
        
        for bot in stats:
            status_emoji = "🟢" if not bot['is_overloaded'] else "🔴"
            text += f"{status_emoji} **{bot['session_name']}**\n"
            text += f"   📱 Телефон: `{bot['phone']}`\n"
            text += f"   💬 Чатов: {bot['total_chats']}/{UserbotLoadBalancer.MAX_CHATS_PER_USERBOT}\n"
            text += f"   👥 Пользователей: {bot['active_users']}\n"
            text += f"   📈 Загрузка: {bot['load_percent']:.1f}%\n\n"
        
        # Общая статистика
        total_chats = sum(b['total_chats'] for b in stats)
        total_users = sum(b['active_users'] for b in stats)
        avg_load = sum(b['load_percent'] for b in stats) / len(stats)
        
        text += "📈 **Общая статистика:**\n"
        text += f"   Всего юзерботов: {len(stats)}\n"
        text += f"   Всего чатов: {total_chats}\n"
        text += f"   Всего пользователей: {total_users}\n"
        text += f"   Средняя загрузка: {avg_load:.1f}%\n"
        
        await message.answer(text, parse_mode="Markdown")


@router.message(Command("admin_rebalance"))
async def admin_rebalance(message: Message):
    """Перебалансировать чаты между юзерботами"""
    
    if message.from_user.id not in settings.admin_ids_list:
        await message.answer("❌ Доступ запрещен")
        return
    
    await message.answer("🔄 Запуск перебалансировки...")
    
    async with async_session_maker() as session:
        await UserbotLoadBalancer.rebalance_chats(session)
    
    await message.answer("✅ Перебалансировка завершена! Используйте /admin_stats для просмотра результата")


@router.message(Command("admin_limits"))
async def admin_limits(message: Message):
    """Показать текущие лимиты системы"""
    
    if message.from_user.id not in settings.admin_ids_list:
        await message.answer("❌ Доступ запрещен")
        return
    
    text = "⚙️ **Текущие лимиты системы:**\n\n"
    text += f"📊 **Юзерботы:**\n"
    text += f"   Макс. чатов на юзербот: {UserbotLoadBalancer.MAX_CHATS_PER_USERBOT}\n"
    text += f"   Макс. пользователей на юзербот: {UserbotLoadBalancer.MAX_USERS_PER_USERBOT}\n\n"
    
    userbots = UserbotLoadBalancer.get_available_userbots()
    text += f"   Настроено юзерботов: {len(userbots)}\n"
    text += f"   Теоретическая емкость: {len(userbots) * UserbotLoadBalancer.MAX_CHATS_PER_USERBOT} чатов\n"
    text += f"   Теоретически клиентов: ~{len(userbots) * UserbotLoadBalancer.MAX_USERS_PER_USERBOT}\n\n"
    
    text += "💡 **Рекомендации:**\n"
    text += "   • 1 юзербот = до 20 клиентов\n"
    text += "   • При загрузке >80% добавьте юзерботов\n"
    text += "   • Используйте /admin_rebalance для оптимизации\n"
    
    await message.answer(text, parse_mode="Markdown")
