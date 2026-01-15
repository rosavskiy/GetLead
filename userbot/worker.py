"""Юзербот для мониторинга чатов"""
import asyncio
import logging
from typing import Optional
from telethon import TelegramClient, events, functions
from telethon.tl.types import Channel, Chat as TelegramChat
from telethon.errors import FloodWaitError, ChannelPrivateError
from aiogram import Bot

from config import settings
from database.database import async_session_maker
from database.models import Chat, Project, KeywordType
from database.crud import ChatCRUD, ProjectCRUD, KeywordCRUD
from userbot.matching import MatchingEngine

logger = logging.getLogger(__name__)


class UserbotWorker:
    """Воркер юзербота для мониторинга"""
    
    def __init__(self, api_id: int, api_hash: str, session_name: str, phone: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.phone = phone
        
        self.client: Optional[TelegramClient] = None
        self.bot: Optional[Bot] = None
        self.monitored_chats = set()  # Множество chat_id для мониторинга
        
    async def start(self):
        """Запуск юзербота"""
        logger.info(f"Запуск юзербота {self.session_name}...")
        
        # Создаем клиента Telethon
        self.client = TelegramClient(
            self.session_name,
            self.api_id,
            self.api_hash
        )
        
        # Создаем Bot API клиента для отправки уведомлений
        self.bot = Bot(token=settings.BOT_TOKEN)
        
        await self.client.start(phone=self.phone)
        logger.info(f"✅ Юзербот {self.session_name} запущен!")
        
        # Загружаем список чатов для мониторинга
        await self.load_chats()
        
        # Регистрируем обработчик новых сообщений
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            await self.process_message(event)
        
        # Запускаем клиента
        await self.client.run_until_disconnected()
    
    async def load_chats(self):
        """Загрузка чатов для мониторинга"""
        logger.info("Загрузка чатов для мониторинга...")
        
        async with async_session_maker() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Chat).where(Chat.assigned_userbot == self.session_name)
            )
            chats = result.scalars().all()
            
            for chat in chats:
                try:
                    # Пытаемся вступить в чат (если еще не вступили)
                    if not chat.is_joined:
                        await self.join_chat(chat)
                    
                    self.monitored_chats.add(chat.telegram_id)
                    logger.info(f"✅ Мониторинг чата: {chat.telegram_link}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка загрузки чата {chat.telegram_link}: {e}")
    
    async def join_chat(self, chat: Chat):
        """Вступление в чат"""
        try:
            logger.info(f"Вступление в чат: {chat.telegram_link}")
            
            # Получаем сущность чата
            entity = await self.client.get_entity(chat.telegram_link)
            
            # Если это канал, вступаем
            if isinstance(entity, Channel):
                await self.client(functions.channels.JoinChannelRequest(entity))
                
                # Обновляем статус в БД
                async with async_session_maker() as session:
                    from sqlalchemy import update
                    await session.execute(
                        update(Chat)
                        .where(Chat.id == chat.id)
                        .values(
                            is_joined=True,
                            telegram_id=entity.id,
                            title=entity.title
                        )
                    )
                    await session.commit()
                
                logger.info(f"✅ Вступили в чат: {chat.telegram_link}")
            
        except FloodWaitError as e:
            logger.warning(f"⏳ FloodWait: нужно подождать {e.seconds} секунд")
            await asyncio.sleep(e.seconds)
            
        except ChannelPrivateError:
            logger.error(f"❌ Чат приватный или недоступен: {chat.telegram_link}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка вступления в чат: {e}")
    
    async def process_message(self, event):
        """Обработка нового сообщения"""
        try:
            # Проверяем, что сообщение из мониторируемого чата
            chat_id = event.chat_id
            if chat_id not in self.monitored_chats:
                return
            
            # Получаем текст сообщения
            text = event.message.message
            if not text:
                return
            
            # Игнорируем свои сообщения
            if event.message.out:
                return
            
            # Получаем все проекты, которые мониторят этот чат
            async with async_session_maker() as session:
                from sqlalchemy import select
                from database.models import chat_project_association
                
                # Находим чат
                result = await session.execute(
                    select(Chat).where(Chat.telegram_id == chat_id)
                )
                chat = result.scalar_one_or_none()
                
                if not chat:
                    return
                
                # Получаем все проекты этого чата
                for project in chat.projects:
                    await self.check_project_match(event, text, project, chat)
        
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    async def check_project_match(self, event, text: str, project: Project, chat: Chat):
        """Проверка совпадения для конкретного проекта"""
        try:
            async with async_session_maker() as session:
                # Загружаем ключевые слова
                include_keywords = await KeywordCRUD.get_all(
                    session, project.id, KeywordType.INCLUDE
                )
                exclude_keywords = await KeywordCRUD.get_all(
                    session, project.id, KeywordType.EXCLUDE
                )
                
                # Проверяем совпадение
                result = MatchingEngine.process_message(
                    text=text,
                    include_keywords=include_keywords,
                    exclude_keywords=exclude_keywords,
                    filters=[]  # TODO: Добавить поддержку фильтров
                )
                
                if result['matched']:
                    # Отправляем уведомление пользователю
                    await self.send_notification(
                        user_telegram_id=project.user.telegram_id,
                        message_text=text,
                        keywords=result['keywords'],
                        chat=chat,
                        message_link=self.get_message_link(event)
                    )
        
        except Exception as e:
            logger.error(f"❌ Ошибка проверки проекта: {e}")
    
    async def send_notification(
        self,
        user_telegram_id: int,
        message_text: str,
        keywords: list,
        chat: Chat,
        message_link: str
    ):
        """Отправка уведомления пользователю"""
        try:
            # Обрезаем текст если он слишком длинный
            if len(message_text) > 500:
                message_text = message_text[:500] + '...'
            
            # Форматируем ключевые слова
            keywords_text = ', '.join([kw.text for kw in keywords[:5]])
            
            # Формируем сообщение
            notification = f"""🔔 <b>Найдено совпадение!</b>

💬 <b>Чат:</b> {chat.title or chat.telegram_link}
🔑 <b>Ключевые слова:</b> {keywords_text}

📝 <b>Текст сообщения:</b>
{message_text}

🔗 <a href="{message_link}">Перейти к сообщению</a>
"""
            
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=notification,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            logger.info(f"✅ Уведомление отправлено пользователю {user_telegram_id}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")
    
    def get_message_link(self, event) -> str:
        """Получение ссылки на сообщение"""
        try:
            chat = event.chat
            message_id = event.message.id
            
            if hasattr(chat, 'username') and chat.username:
                return f"https://t.me/{chat.username}/{message_id}"
            else:
                # Приватный чат
                return f"https://t.me/c/{chat.id}/{message_id}"
        except:
            return "#"
