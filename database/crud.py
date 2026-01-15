"""CRUD операции для работы с базой данных"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, Project, Keyword, Filter, Chat, KeywordType, SubscriptionPlan


class UserCRUD:
    """CRUD операции для пользователей"""
    
    @staticmethod
    async def get_or_create(session: AsyncSession, telegram_id: int, username: Optional[str] = None) -> User:
        """Получить или создать пользователя"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user
    
    @staticmethod
    async def update_subscription(
        session: AsyncSession,
        user_id: int,
        plan: SubscriptionPlan,
        end_date: Optional[datetime] = None
    ) -> User:
        """Обновить подписку пользователя"""
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(subscription_plan=plan, subscription_end_date=end_date)
        )
        await session.commit()
        
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one()


class ProjectCRUD:
    """CRUD операции для проектов"""
    
    @staticmethod
    async def create(session: AsyncSession, user_id: int, name: str) -> Project:
        """Создать проект"""
        project = Project(user_id=user_id, name=name)
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project
    
    @staticmethod
    async def get_active(session: AsyncSession, user_id: int) -> Optional[Project]:
        """Получить активный проект пользователя"""
        result = await session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.is_active == True)
            .options(selectinload(Project.keywords), selectinload(Project.chats))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(session: AsyncSession, user_id: int) -> List[Project]:
        """Получить все проекты пользователя"""
        result = await session.execute(
            select(Project).where(Project.user_id == user_id)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def set_active(session: AsyncSession, project_id: int, user_id: int):
        """Сделать проект активным"""
        # Деактивировать все проекты пользователя
        await session.execute(
            update(Project)
            .where(Project.user_id == user_id)
            .values(is_active=False)
        )
        # Активировать выбранный
        await session.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(is_active=True)
        )
        await session.commit()
    
    @staticmethod
    async def delete(session: AsyncSession, project_id: int):
        """Удалить проект"""
        await session.execute(delete(Project).where(Project.id == project_id))
        await session.commit()


class KeywordCRUD:
    """CRUD операции для ключевых слов"""
    
    @staticmethod
    async def add(session: AsyncSession, project_id: int, text: str, keyword_type: KeywordType) -> Keyword:
        """Добавить ключевое слово"""
        keyword = Keyword(project_id=project_id, text=text.lower(), type=keyword_type)
        session.add(keyword)
        await session.commit()
        await session.refresh(keyword)
        return keyword
    
    @staticmethod
    async def get_all(session: AsyncSession, project_id: int, keyword_type: KeywordType) -> List[Keyword]:
        """Получить все ключевые слова проекта определенного типа"""
        result = await session.execute(
            select(Keyword)
            .where(Keyword.project_id == project_id, Keyword.type == keyword_type)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def delete_all(session: AsyncSession, project_id: int, keyword_type: KeywordType):
        """Удалить все ключевые слова проекта"""
        await session.execute(
            delete(Keyword)
            .where(Keyword.project_id == project_id, Keyword.type == keyword_type)
        )
        await session.commit()


class ChatCRUD:
    """CRUD операции для чатов"""
    
    @staticmethod
    async def add(
        session: AsyncSession,
        telegram_link: str,
        telegram_id: Optional[int] = None,
        title: Optional[str] = None
    ) -> Chat:
        """Добавить чат"""
        # Проверяем, есть ли уже такой чат
        result = await session.execute(
            select(Chat).where(Chat.telegram_link == telegram_link)
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            chat = Chat(telegram_link=telegram_link, telegram_id=telegram_id, title=title)
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
            
            # Автоматически назначаем юзербот для нового чата
            # Импорт здесь чтобы избежать циклической зависимости
            from userbot.load_balancer import UserbotLoadBalancer
            await UserbotLoadBalancer.assign_userbot_for_chat(session, chat.id)
        
        return chat
    
    @staticmethod
    async def get_by_link(session: AsyncSession, telegram_link: str) -> Optional[Chat]:
        """Получить чат по ссылке"""
        result = await session.execute(
            select(Chat).where(Chat.telegram_link == telegram_link)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def assign_to_project(session: AsyncSession, chat_id: int, project_id: int):
        """Привязать чат к проекту"""
        result = await session.execute(
            select(Project).where(Project.id == project_id).options(selectinload(Project.chats))
        )
        project = result.scalar_one()
        
        result = await session.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one()
        
        if chat not in project.chats:
            project.chats.append(chat)
            await session.commit()
