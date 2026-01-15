"""Middleware для проверки подписки"""
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from config import settings
from database.database import async_session_maker
from database.crud import UserCRUD
from database.models import SubscriptionPlan
from bot.texts import get_text


class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки активной подписки пользователя"""
    
    # Команды, доступные без подписки
    FREE_COMMANDS = ['/start', 'menu:main', 'menu:payment', 'payment:', 'pay:']
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Проверка подписки"""
        
        # Проверяем, является ли пользователь администратором
        if event.from_user.id in settings.admin_ids_list:
            # Админы имеют полный доступ без проверки подписки
            return await handler(event, data)
        
        # Получаем пользователя
        async with async_session_maker() as session:
            user = await UserCRUD.get_or_create(
                session,
                telegram_id=event.from_user.id,
                username=event.from_user.username
            )
            
            # Сохраняем пользователя в данных для использования в хендлерах
            data['user'] = user
            
            # Проверяем, является ли это бесплатной командой
            command_text = ''
            if isinstance(event, Message):
                command_text = event.text or ''
            elif isinstance(event, CallbackQuery):
                command_text = event.data or ''
            
            is_free_command = any(
                cmd in command_text for cmd in self.FREE_COMMANDS
            )
            
            # Если бесплатная команда, пропускаем проверку
            if is_free_command:
                return await handler(event, data)
            
            # Проверяем подписку
            if user.subscription_plan == SubscriptionPlan.FREE:
                # Нет подписки
                text = get_text('no_subscription', user.language)
                
                if isinstance(event, Message):
                    await event.answer(text)
                elif isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                
                return
            
            # Проверяем срок действия подписки
            if user.subscription_end_date and user.subscription_end_date < datetime.utcnow():
                # Подписка истекла
                text = get_text('subscription_expired', user.language)
                
                if isinstance(event, Message):
                    await event.answer(text)
                elif isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                
                return
            
            # Подписка активна, продолжаем обработку
            return await handler(event, data)
