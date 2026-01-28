"""CRUD операции для работы с базой данных"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, Project, Keyword, Filter, Chat, KeywordType, SubscriptionPlan, LeadMatch, AmoCRMIntegration


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
    async def get_by_id(session: AsyncSession, keyword_id: int) -> Optional[Keyword]:
        """Получить ключевое слово по ID"""
        result = await session.execute(
            select(Keyword).where(Keyword.id == keyword_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(session: AsyncSession, project_id: int, keyword_type: KeywordType) -> List[Keyword]:
        """Получить все ключевые слова проекта определенного типа"""
        result = await session.execute(
            select(Keyword)
            .where(Keyword.project_id == project_id, Keyword.type == keyword_type)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def delete(session: AsyncSession, keyword_id: int):
        """Удалить ключевое слово по ID"""
        await session.execute(
            delete(Keyword).where(Keyword.id == keyword_id)
        )
        await session.commit()
    
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
    
    @staticmethod
    async def get_by_id(session: AsyncSession, chat_id: int) -> Optional[Chat]:
        """Получить чат по ID"""
        result = await session.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def remove_from_project(session: AsyncSession, chat_id: int, project_id: int) -> bool:
        """Удалить чат из проекта. Если чат больше не привязан ни к одному проекту - удаляем из БД"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            result = await session.execute(
                select(Project).where(Project.id == project_id).options(selectinload(Project.chats))
            )
            project = result.scalar_one_or_none()
            
            if not project:
                logger.warning(f"Проект {project_id} не найден")
                return False
            
            result = await session.execute(
                select(Chat).where(Chat.id == chat_id).options(selectinload(Chat.projects))
            )
            chat = result.scalar_one_or_none()
            
            if not chat:
                logger.warning(f"Чат {chat_id} не найден")
                return False
            
            logger.info(f"Удаление чата {chat.telegram_link} из проекта {project.name}")
            
            if chat in project.chats:
                project.chats.remove(chat)
                await session.commit()
                
                # Перезагружаем чат с projects чтобы проверить есть ли ещё связи
                result = await session.execute(
                    select(Chat).where(Chat.id == chat_id).options(selectinload(Chat.projects))
                )
                chat = result.scalar_one_or_none()
                
                # Если чат больше не привязан ни к одному проекту - удаляем из БД
                if chat and not chat.projects:
                    logger.info(f"Чат {chat.telegram_link} больше не привязан к проектам, удаляем из БД")
                    await session.delete(chat)
                    await session.commit()
                    logger.info(f"Чат удалён из БД")
                
                return True
            
            logger.warning(f"Чат {chat_id} не привязан к проекту {project_id}")
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления чата: {e}", exc_info=True)
            await session.rollback()
            return False


class LeadMatchCRUD:
    """CRUD операции для найденных лидов"""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: int,
        project_id: int,
        chat_id: int,
        message_text: str,
        message_link: str,
        matched_keywords: str,
        telegram_message_id: int = None,
        sender_username: str = None,
        sender_id: int = None
    ) -> LeadMatch:
        """Создать запись о найденном лиде"""
        lead_match = LeadMatch(
            user_id=user_id,
            project_id=project_id,
            chat_id=chat_id,
            message_text=message_text,
            message_link=message_link,
            matched_keywords=matched_keywords,
            telegram_message_id=telegram_message_id,
            sender_username=sender_username,
            sender_id=sender_id
        )
        session.add(lead_match)
        await session.commit()
        await session.refresh(lead_match)
        return lead_match
    
    @staticmethod
    async def get_user_leads(
        session: AsyncSession,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[LeadMatch]:
        """Получить лиды пользователя"""
        result = await session.execute(
            select(LeadMatch)
            .where(LeadMatch.user_id == user_id)
            .order_by(LeadMatch.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_user_stats(
        session: AsyncSession,
        user_id: int,
        start_date: datetime = None
    ) -> dict:
        """Получить статистику пользователя"""
        query = select(func.count(LeadMatch.id)).where(LeadMatch.user_id == user_id)
        
        if start_date:
            query = query.where(LeadMatch.created_at >= start_date)
        
        total = await session.execute(query)
        total = total.scalar() or 0
        
        contacted = await session.execute(
            query.where(LeadMatch.is_contacted == True)
        )
        contacted = contacted.scalar() or 0
        
        converted = await session.execute(
            query.where(LeadMatch.is_converted == True)
        )
        converted = converted.scalar() or 0
        
        return {
            'total': total,
            'contacted': contacted,
            'converted': converted,
            'conversion_rate': (converted / total * 100) if total > 0 else 0
        }
    
    @staticmethod
    async def mark_contacted(session: AsyncSession, lead_id: int) -> bool:
        """Отметить лид как обработанный"""
        await session.execute(
            update(LeadMatch)
            .where(LeadMatch.id == lead_id)
            .values(is_contacted=True)
        )
        await session.commit()
        return True
    
    @staticmethod
    async def mark_converted(session: AsyncSession, lead_id: int) -> bool:
        """Отметить лид как конвертированный"""
        await session.execute(
            update(LeadMatch)
            .where(LeadMatch.id == lead_id)
            .values(is_converted=True)
        )
        await session.commit()
        return True


class AmoCRMCRUD:
    """CRUD операции для интеграции AmoCRM"""
    
    @staticmethod
    async def get_by_user(session: AsyncSession, user_id: int) -> Optional[AmoCRMIntegration]:
        """Получить интеграцию пользователя"""
        result = await session.execute(
            select(AmoCRMIntegration).where(AmoCRMIntegration.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_or_update(
        session: AsyncSession,
        user_id: int,
        subdomain: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        pipeline_id: int = None,
        status_id: int = None,
        responsible_user_id: int = None
    ) -> AmoCRMIntegration:
        """Создать или обновить интеграцию"""
        existing = await AmoCRMCRUD.get_by_user(session, user_id)
        
        if existing:
            await session.execute(
                update(AmoCRMIntegration)
                .where(AmoCRMIntegration.user_id == user_id)
                .values(
                    subdomain=subdomain,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=expires_at,
                    pipeline_id=pipeline_id,
                    status_id=status_id,
                    responsible_user_id=responsible_user_id,
                    is_active=True
                )
            )
            await session.commit()
            await session.refresh(existing)
            return existing
        
        integration = AmoCRMIntegration(
            user_id=user_id,
            subdomain=subdomain,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_at,
            pipeline_id=pipeline_id,
            status_id=status_id,
            responsible_user_id=responsible_user_id
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)
        return integration
    
    @staticmethod
    async def delete(session: AsyncSession, user_id: int) -> bool:
        """Удалить интеграцию"""
        await session.execute(
            delete(AmoCRMIntegration).where(AmoCRMIntegration.user_id == user_id)
        )
        await session.commit()
        return True
