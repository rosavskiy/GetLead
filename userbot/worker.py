"""Юзербот для мониторинга чатов"""
import asyncio
import json
import logging
from typing import Optional
from telethon import TelegramClient, events, functions
from telethon.tl.types import Channel, Chat as TelegramChat
from telethon.errors import FloodWaitError, ChannelPrivateError
from aiogram import Bot

from config import settings
from database.database import async_session_maker
from database.models import Chat, Project, KeywordType
from database.crud import ChatCRUD, ProjectCRUD, KeywordCRUD, LeadMatchCRUD
from userbot.matching import MatchingEngine
from utils.cache import CacheService

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
        
        # Запускаем фоновую задачу проверки новых чатов
        asyncio.create_task(self.check_new_chats_periodically())
        
        # Запускаем обработчик запросов на поиск чатов через Redis
        asyncio.create_task(self.process_search_requests())
        
        # Запускаем клиента
        await self.client.run_until_disconnected()
    
    async def process_search_requests(self):
        """Обработка запросов на поиск чатов через Redis"""
        import redis.asyncio as redis
        
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            logger.info(f"🔍 {self.session_name}: Слушаю запросы на поиск чатов...")
            
            while True:
                try:
                    # Ждём запрос из очереди (блокирующий вызов с таймаутом)
                    result = await redis_client.blpop('chat_search_requests', timeout=5)
                    
                    if result:
                        _, request_data = result
                        request = json.loads(request_data)
                        
                        query = request.get('query', '')
                        request_id = request.get('request_id', '')
                        
                        logger.info(f"🔍 Поиск чатов по запросу: '{query}'")
                        
                        # Выполняем поиск
                        results = await self.search_chats(query)
                        
                        # Сохраняем результат в Redis
                        response_key = f'chat_search_response:{request_id}'
                        await redis_client.setex(
                            response_key, 
                            60,  # TTL 60 секунд
                            json.dumps(results)
                        )
                        
                        logger.info(f"✅ Найдено {len(results)} чатов для '{query}'")
                        
                except Exception as e:
                    logger.error(f"Ошибка обработки поискового запроса: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis для поиска: {e}")
    
    async def search_chats(self, query: str) -> list:
        """Поиск чатов через Telegram API"""
        results = []
        seen_chat_ids = set()
        
        try:
            from telethon.tl.types import InputMessagesFilterEmpty, InputPeerEmpty
            from telethon.tl.functions.messages import SearchGlobalRequest
            
            # 1. Глобальный поиск по сообщениям
            search_result = await self.client(SearchGlobalRequest(
                q=query,
                filter=InputMessagesFilterEmpty(),
                min_date=None,
                max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=30
            ))
            
            # Считаем релевантность
            chat_relevance = {}
            for msg in search_result.messages:
                chat_id = getattr(msg, 'peer_id', None)
                if chat_id:
                    real_id = getattr(chat_id, 'channel_id', None) or getattr(chat_id, 'chat_id', None)
                    if real_id:
                        chat_relevance[real_id] = chat_relevance.get(real_id, 0) + 1
            
            # Обрабатываем чаты
            for chat in search_result.chats:
                try:
                    if chat.id in seen_chat_ids:
                        continue
                    seen_chat_ids.add(chat.id)
                    
                    if not hasattr(chat, 'username') or not chat.username:
                        continue
                    
                    subscribers = getattr(chat, 'participants_count', None)
                    
                    chat_type = 'unknown'
                    if isinstance(chat, Channel):
                        if chat.megagroup:
                            chat_type = 'supergroup'
                        elif chat.broadcast:
                            chat_type = 'channel'
                        else:
                            chat_type = 'group'
                    
                    relevance = chat_relevance.get(chat.id, 0)
                    
                    results.append({
                        'username': f'@{chat.username}',
                        'title': getattr(chat, 'title', chat.username),
                        'link': f't.me/{chat.username}',
                        'subscribers': subscribers,
                        'type': chat_type,
                        'relevance': relevance,
                        'verified': True
                    })
                except Exception:
                    continue
            
            # 2. Дополнительный поиск по названию
            try:
                contacts_result = await self.client(functions.contacts.SearchRequest(
                    q=query,
                    limit=20
                ))
                
                for chat in contacts_result.chats:
                    try:
                        if chat.id in seen_chat_ids:
                            continue
                        seen_chat_ids.add(chat.id)
                        
                        if not hasattr(chat, 'username') or not chat.username:
                            continue
                        
                        subscribers = getattr(chat, 'participants_count', None)
                        
                        chat_type = 'unknown'
                        if isinstance(chat, Channel):
                            if chat.megagroup:
                                chat_type = 'supergroup'
                            elif chat.broadcast:
                                chat_type = 'channel'
                            else:
                                chat_type = 'group'
                        
                        results.append({
                            'username': f'@{chat.username}',
                            'title': getattr(chat, 'title', chat.username),
                            'link': f't.me/{chat.username}',
                            'subscribers': subscribers,
                            'type': chat_type,
                            'relevance': 5,
                            'verified': True
                        })
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Contacts search failed: {e}")
            
            # Сортируем
            results.sort(key=lambda x: (-x.get('relevance', 0), -(x.get('subscribers') or 0)))
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait: {e.seconds}s")
            await asyncio.sleep(min(e.seconds, 30))
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        return results[:20]
    
    async def check_new_chats_periodically(self):
        """Периодическая проверка новых чатов (каждые 60 секунд)"""
        while True:
            try:
                await asyncio.sleep(60)  # Проверяем раз в минуту
                await self.load_chats()
            except Exception as e:
                logger.error(f"❌ Ошибка периодической проверки чатов: {e}")
    
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
                        # Добавляем в список мониторинга после успешного вступления
                        if chat.telegram_id:
                            self.monitored_chats.add(chat.telegram_id)
                    elif chat.telegram_id and chat.telegram_id not in self.monitored_chats:
                        # Чат уже подключен, но не в списке мониторинга
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
            chat_id = event.chat_id
            logger.info(f"🔔 Событие NewMessage: chat_id={chat_id}, monitored={chat_id in self.monitored_chats}")
            
            # Проверяем, что сообщение из мониторируемого чата
            if chat_id not in self.monitored_chats:
                logger.debug(f"❌ Чат {chat_id} не мониторится. Список: {self.monitored_chats}")
                return
            
            # Получаем текст сообщения
            text = event.message.message
            if not text:
                logger.debug(f"⚠️ Сообщение без текста в чате {chat_id}")
                return
            
            # Игнорируем свои сообщения
            is_outgoing = event.message.out
            logger.info(f"📨 Сообщение в чате {chat_id}: '{text[:50]}...', out={is_outgoing}")
            
            if is_outgoing:
                logger.info(f"⏭️ Пропускаем свое сообщение")
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
                # Пробуем взять из кэша
                cached_keywords = await CacheService.get_project_keywords(project.id)
                
                if cached_keywords:
                    # Восстанавливаем объекты из кэша
                    from database.models import Keyword
                    include_keywords = [
                        type('Keyword', (), kw) for kw in cached_keywords.get('include', [])
                    ]
                    exclude_keywords = [
                        type('Keyword', (), kw) for kw in cached_keywords.get('exclude', [])
                    ]
                else:
                    # Загружаем из БД
                    include_keywords = await KeywordCRUD.get_all(
                        session, project.id, KeywordType.INCLUDE
                    )
                    exclude_keywords = await KeywordCRUD.get_all(
                        session, project.id, KeywordType.EXCLUDE
                    )
                    
                    # Кэшируем
                    await CacheService.set_project_keywords(project.id, {
                        'include': [{'text': k.text, 'type': k.type.value} for k in include_keywords],
                        'exclude': [{'text': k.text, 'type': k.type.value} for k in exclude_keywords]
                    })
                
                # Проверяем совпадение
                result = MatchingEngine.process_message(
                    text=text,
                    include_keywords=include_keywords,
                    exclude_keywords=exclude_keywords,
                    filters=[]  # TODO: Добавить поддержку фильтров
                )
                
                if result['matched']:
                    message_link = self.get_message_link(event)
                    
                    # Получаем информацию об отправителе
                    sender = await event.get_sender()
                    sender_username = getattr(sender, 'username', None)
                    sender_id = getattr(sender, 'id', None)
                    
                    # Сохраняем лид в БД
                    keywords_json = json.dumps([kw.text for kw in result['keywords'][:10]])
                    
                    lead_match = await LeadMatchCRUD.create(
                        session=session,
                        user_id=project.user_id,
                        project_id=project.id,
                        chat_id=chat.id,
                        message_text=text[:2000],  # Ограничиваем длину
                        message_link=message_link,
                        matched_keywords=keywords_json,
                        telegram_message_id=event.message.id,
                        sender_username=sender_username,
                        sender_id=sender_id
                    )
                    
                    # Отправляем в AmoCRM если настроено
                    try:
                        from utils.amocrm import send_lead_to_amocrm
                        await send_lead_to_amocrm(session, project.user_id, lead_match)
                    except Exception as e:
                        logger.error(f"Ошибка отправки в AmoCRM: {e}")
                    
                    # Отправляем уведомление пользователю
                    await self.send_notification(
                        user_telegram_id=project.user.telegram_id,
                        message_text=text,
                        keywords=result['keywords'],
                        chat=chat,
                        message_link=message_link,
                        sender_username=sender_username
                    )
        
        except Exception as e:
            logger.error(f"❌ Ошибка проверки проекта: {e}")
    
    async def send_notification(
        self,
        user_telegram_id: int,
        message_text: str,
        keywords: list,
        chat: Chat,
        message_link: str,
        sender_username: str = None
    ):
        """Отправка уведомления пользователю"""
        try:
            # Обрезаем текст если он слишком длинный
            if len(message_text) > 500:
                message_text = message_text[:500] + '...'
            
            # Форматируем ключевые слова
            keywords_text = ', '.join([kw.text for kw in keywords[:5]])
            
            # Информация об отправителе
            sender_info = f"👤 <b>Отправитель:</b> @{sender_username}\n" if sender_username else ""
            
            # Формируем сообщение
            notification = f"""🔔 <b>Найдено совпадение!</b>

💬 <b>Чат:</b> {chat.title or chat.telegram_link}
🔑 <b>Ключевые слова:</b> {keywords_text}
{sender_info}
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
