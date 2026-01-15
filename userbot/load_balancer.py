"""Балансировщик нагрузки между юзерботами"""
import logging
from typing import Optional, List, Dict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Chat, User, Project
from config import settings

logger = logging.getLogger(__name__)


class UserbotLoadBalancer:
    """Распределение нагрузки между юзерботами"""
    
    # Максимальное количество чатов на один юзербот
    MAX_CHATS_PER_USERBOT = 30
    
    # Максимальное количество пользователей на один юзербот
    MAX_USERS_PER_USERBOT = 20
    
    @staticmethod
    def get_available_userbots() -> List[Dict]:
        """Получить список доступных юзерботов из конфига"""
        return settings.userbots_config
    
    @staticmethod
    async def get_userbot_stats(session: AsyncSession) -> List[Dict]:
        """
        Получить статистику по каждому юзерботу
        
        Returns:
            [
                {
                    'session_name': 'userbot_1',
                    'total_chats': 15,
                    'active_users': 8,
                    'load_percent': 50.0
                },
                ...
            ]
        """
        userbots = UserbotLoadBalancer.get_available_userbots()
        stats = []
        
        for bot in userbots:
            session_name = bot['session_name']
            
            # Количество чатов, закрепленных за юзерботом
            result = await session.execute(
                select(func.count(Chat.id))
                .where(Chat.assigned_userbot == session_name)
            )
            total_chats = result.scalar() or 0
            
            # Количество уникальных пользователей, чьи чаты мониторит этот юзербот
            # (подсчет через проекты)
            from database.models import chat_project_association
            result = await session.execute(
                select(func.count(func.distinct(Project.user_id)))
                .select_from(Chat)
                .join(chat_project_association, Chat.id == chat_project_association.c.chat_id)
                .join(Project, chat_project_association.c.project_id == Project.id)
                .where(Chat.assigned_userbot == session_name)
            )
            active_users = result.scalar() or 0
            
            # Процент загрузки (по чатам)
            load_percent = (total_chats / UserbotLoadBalancer.MAX_CHATS_PER_USERBOT) * 100
            
            stats.append({
                'session_name': session_name,
                'phone': bot['phone'],
                'total_chats': total_chats,
                'active_users': active_users,
                'load_percent': load_percent,
                'is_overloaded': total_chats >= UserbotLoadBalancer.MAX_CHATS_PER_USERBOT
            })
        
        return stats
    
    @staticmethod
    async def assign_userbot_for_chat(session: AsyncSession, chat_id: int) -> Optional[str]:
        """
        Назначить оптимальный юзербот для чата
        
        Args:
            session: Сессия БД
            chat_id: ID чата
            
        Returns:
            session_name назначенного юзербота или None если все перегружены
        """
        stats = await UserbotLoadBalancer.get_userbot_stats(session)
        
        if not stats:
            logger.error("❌ Нет доступных юзерботов в конфигурации!")
            return None
        
        # Сортируем по загруженности (от меньшей к большей)
        stats.sort(key=lambda x: x['total_chats'])
        
        # Выбираем наименее загруженный
        best_bot = stats[0]
        
        if best_bot['is_overloaded']:
            logger.warning(
                f"⚠️ Все юзерботы перегружены! "
                f"Назначаем {best_bot['session_name']} (чатов: {best_bot['total_chats']})"
            )
        
        # Обновляем чат
        from sqlalchemy import update
        await session.execute(
            update(Chat)
            .where(Chat.id == chat_id)
            .values(assigned_userbot=best_bot['session_name'])
        )
        await session.commit()
        
        logger.info(
            f"✅ Чат #{chat_id} назначен юзерботу {best_bot['session_name']} "
            f"(загрузка: {best_bot['total_chats']}/{UserbotLoadBalancer.MAX_CHATS_PER_USERBOT})"
        )
        
        return best_bot['session_name']
    
    @staticmethod
    async def rebalance_chats(session: AsyncSession):
        """
        Перебалансировать чаты между юзерботами
        Используется когда добавляется новый юзербот или нужно оптимизировать распределение
        """
        logger.info("🔄 Запуск ребалансировки чатов...")
        
        userbots = UserbotLoadBalancer.get_available_userbots()
        if not userbots:
            logger.error("❌ Нет доступных юзерботов!")
            return
        
        # Получаем все активные чаты
        result = await session.execute(
            select(Chat).where(Chat.is_active == True)
        )
        chats = list(result.scalars().all())
        
        total_chats = len(chats)
        chats_per_bot = total_chats // len(userbots)
        
        logger.info(
            f"📊 Всего чатов: {total_chats}, "
            f"Юзерботов: {len(userbots)}, "
            f"Чатов на бота: ~{chats_per_bot}"
        )
        
        # Распределяем чаты равномерно
        for idx, chat in enumerate(chats):
            userbot_idx = idx % len(userbots)
            assigned_bot = userbots[userbot_idx]['session_name']
            
            if chat.assigned_userbot != assigned_bot:
                from sqlalchemy import update
                await session.execute(
                    update(Chat)
                    .where(Chat.id == chat.id)
                    .values(assigned_userbot=assigned_bot)
                )
        
        await session.commit()
        logger.info("✅ Ребалансировка завершена!")
    
    @staticmethod
    async def get_user_userbot(session: AsyncSession, user_id: int) -> Optional[str]:
        """
        Получить юзербот, который обслуживает пользователя
        (по активному проекту)
        
        Returns:
            session_name юзербота или None
        """
        # Получаем активный проект пользователя
        result = await session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.is_active == True)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return None
        
        # Получаем чаты проекта
        from database.models import chat_project_association
        result = await session.execute(
            select(Chat.assigned_userbot)
            .select_from(Chat)
            .join(chat_project_association, Chat.id == chat_project_association.c.chat_id)
            .where(chat_project_association.c.project_id == project.id)
            .limit(1)
        )
        
        return result.scalar_one_or_none()
