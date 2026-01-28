"""Утилиты для работы с AI и поиска чатов"""
import aiohttp
import re
import logging
import httpx
import asyncio
from openai import AsyncOpenAI
from typing import List, Optional, Dict, Any
from telethon import TelegramClient, functions
from telethon.tl.types import Channel, Chat as TelegramChat
from telethon.errors import FloodWaitError, ChannelPrivateError, UsernameNotOccupiedError, UsernameInvalidError
from config import settings

logger = logging.getLogger(__name__)

# Глобальный клиент для поиска чатов (создаётся один раз)
_search_client: Optional[TelegramClient] = None
_search_client_lock = asyncio.Lock()


async def get_search_client() -> Optional[TelegramClient]:
    """Получить Telethon клиент для поиска чатов"""
    global _search_client
    
    async with _search_client_lock:
        if _search_client is not None and _search_client.is_connected():
            return _search_client
        
        # Берём первый доступный юзербот из userbots_config
        userbots = settings.userbots_config
        if not userbots:
            logger.warning("No userbot sessions configured for chat search")
            return None
        
        session = userbots[0]
        try:
            client = TelegramClient(
                f"sessions/{session['session_name']}",
                session['api_id'],
                session['api_hash']
            )
            await client.connect()
            
            if not await client.is_user_authorized():
                logger.warning(f"Session {session['session_name']} not authorized")
                return None
            
            _search_client = client
            logger.info("Search client connected successfully")
            return _search_client
            
        except Exception as e:
            logger.error(f"Failed to create search client: {e}")
            return None


async def search_telegram_chats(query: str, limit: int = 30) -> List[Dict[str, Any]]:
    """
    УМНЫЙ поиск чатов через Telegram Global Search API
    
    Использует messages.SearchGlobal для поиска по содержимому сообщений,
    затем извлекает уникальные чаты и сортирует по количеству участников.
    
    Это находит чаты где ОБСУЖДАЮТ тему, даже если в названии нет ключевого слова!
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество сообщений для анализа
        
    Returns:
        Список словарей с информацией о РЕАЛЬНЫХ чатах, отсортированный по участникам
    """
    results = []
    seen_chat_ids = set()
    client = await get_search_client()
    
    if not client:
        logger.warning("No client available for Telegram search")
        return []
    
    try:
        from telethon.tl.types import InputMessagesFilterEmpty, InputPeerEmpty
        from telethon.tl.functions.messages import SearchGlobalRequest
        
        # Глобальный поиск по сообщениям - находит чаты где обсуждают тему
        search_result = await client(SearchGlobalRequest(
            q=query,
            filter=InputMessagesFilterEmpty(),
            min_date=None,
            max_date=None,
            offset_rate=0,
            offset_peer=InputPeerEmpty(),
            offset_id=0,
            limit=limit
        ))
        
        # Собираем все чаты из результатов
        chats_map = {c.id: c for c in search_result.chats}
        
        # Считаем сколько раз каждый чат встретился (релевантность)
        chat_relevance = {}
        for msg in search_result.messages:
            chat_id = getattr(msg, 'peer_id', None)
            if chat_id:
                # Извлекаем реальный ID
                real_id = getattr(chat_id, 'channel_id', None) or getattr(chat_id, 'chat_id', None)
                if real_id:
                    chat_relevance[real_id] = chat_relevance.get(real_id, 0) + 1
        
        # Обрабатываем найденные чаты
        for chat in search_result.chats:
            try:
                if chat.id in seen_chat_ids:
                    continue
                seen_chat_ids.add(chat.id)
                
                # Только чаты с username (публичные)
                if not hasattr(chat, 'username') or not chat.username:
                    continue
                
                # Получаем количество участников
                subscribers = getattr(chat, 'participants_count', None)
                
                # Определяем тип чата
                chat_type = 'unknown'
                if isinstance(chat, Channel):
                    if chat.megagroup:
                        chat_type = 'supergroup'
                    elif chat.broadcast:
                        chat_type = 'channel'
                    else:
                        chat_type = 'group'
                
                # Релевантность = сколько сообщений найдено в этом чате
                relevance = chat_relevance.get(chat.id, 0)
                
                results.append({
                    'username': f'@{chat.username}',
                    'title': getattr(chat, 'title', chat.username),
                    'link': f't.me/{chat.username}',
                    'subscribers': subscribers,
                    'type': chat_type,
                    'relevance': relevance,
                    'source': 'telegram_global_search',
                    'verified': True
                })
                    
            except Exception as e:
                logger.warning(f"Error processing chat: {e}")
                continue
        
        # Дополнительно ищем через contacts.Search (по названию)
        try:
            contacts_result = await client(functions.contacts.SearchRequest(
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
                        'relevance': 5,  # Бонус за совпадение по названию
                        'source': 'telegram_contacts_search',
                        'verified': True
                    })
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Contacts search failed: {e}")
        
        # Сортируем: сначала по релевантности, потом по подписчикам
        results.sort(key=lambda x: (
            -x.get('relevance', 0),
            -(x.get('subscribers') or 0)
        ))
        
        logger.info(f"Telegram smart search found {len(results)} unique chats for '{query}'")
        
    except FloodWaitError as e:
        logger.warning(f"Telegram flood wait: {e.seconds}s")
        await asyncio.sleep(min(e.seconds, 30))
    except Exception as e:
        logger.error(f"Telegram search error: {e}", exc_info=True)
    
    return results


async def verify_chat_exists(username: str) -> Optional[Dict[str, Any]]:
    """
    Проверить существование чата и получить информацию о нём
    
    Args:
        username: Username чата (с @ или без)
        
    Returns:
        Информация о чате или None если не существует
    """
    client = await get_search_client()
    
    if not client:
        return None
    
    # Убираем @ если есть
    username = username.lstrip('@')
    
    try:
        entity = await client.get_entity(username)
        
        subscribers = None
        chat_type = 'unknown'
        
        if isinstance(entity, Channel):
            # Получаем полную информацию о канале
            full = await client(functions.channels.GetFullChannelRequest(entity))
            subscribers = full.full_chat.participants_count
            
            if entity.megagroup:
                chat_type = 'supergroup'
            elif entity.broadcast:
                chat_type = 'channel'
            else:
                chat_type = 'group'
        elif isinstance(entity, TelegramChat):
            subscribers = entity.participants_count
            chat_type = 'group'
        
        return {
            'username': f'@{username}',
            'title': getattr(entity, 'title', username),
            'link': f't.me/{username}',
            'subscribers': subscribers,
            'type': chat_type,
            'source': 'telegram_verified',
            'verified': True
        }
        
    except (UsernameNotOccupiedError, UsernameInvalidError):
        logger.info(f"Chat @{username} does not exist")
        return None
    except ChannelPrivateError:
        logger.info(f"Chat @{username} is private")
        return None
    except FloodWaitError as e:
        logger.warning(f"Flood wait: {e.seconds}s")
        await asyncio.sleep(min(e.seconds, 30))
        return None
    except Exception as e:
        logger.warning(f"Error verifying @{username}: {e}")
        return None


def get_openai_client() -> Optional[AsyncOpenAI]:
    """Создаёт OpenAI клиент по требованию (избегаем проблем с глобальным клиентом)"""
    if settings.OPENAI_API_KEY:
        # Создаём httpx клиент без proxies для избежания конфликта версий
        http_client = httpx.AsyncClient()
        return AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=http_client
        )
    return None

# База данных пуста - все чаты ищутся через Telegram API
CHAT_DATABASE = {}

# Маппинг ниш на категории
NICHE_KEYWORDS = {
    'it': ['программирование', 'разработка', 'python', 'javascript', 'web', 'веб', 'frontend', 'backend', 
           'devops', 'мобильная', 'ios', 'android', 'it', 'software', 'код', 'developer'],
    'design': ['дизайн', 'ui', 'ux', 'графика', 'figma', 'photoshop', 'иллюстрация', 'лого', 
               'брендинг', '3d', 'motion', 'анимация', 'верстка'],
    'marketing': ['маркетинг', 'smm', 'seo', 'таргет', 'реклама', 'продвижение', 'контент', 
                  'копирайтинг', 'email', 'digital', 'трафик', 'лиды'],
    'business': ['бизнес', 'стартап', 'предприниматель', 'инвестиции', 'финансы', 'продажи', 
                 'b2b', 'ecommerce', 'франшиза', 'партнерство'],
    'real_estate': ['недвижимость', 'квартира', 'аренда', 'ипотека', 'риелтор', 'новостройка', 
                    'дом', 'коммерческая', 'загородная'],
    'education': ['образование', 'курсы', 'обучение', 'репетитор', 'английский', 'язык', 
                  'школа', 'университет', 'тренинг'],
    'crypto': ['крипто', 'bitcoin', 'биткоин', 'ethereum', 'nft', 'блокчейн', 'трейдинг', 
               'defi', 'токен'],
    'freelance': ['фриланс', 'заказы', 'удаленка', 'удалённая', 'проекты', 'подработка'],
    'legal': ['юрист', 'право', 'бухгалтер', 'налог', 'юридический', 'accounting'],
    'hr': ['hr', 'кадры', 'вакансии', 'работа', 'рекрутинг', 'найм', 'резюме'],
    'travel': ['виза', 'визы', 'путешествие', 'туризм', 'эмиграция', 'иммиграция', 'релокация',
               'переезд', 'abroad', 'заграница', 'expat'],
    'services': ['услуги', 'ремонт', 'уборка', 'мастер', 'красота', 'фото', 'видео',
                 'свадьба', 'event', 'кейтеринг'],
}


def detect_category(niche: str) -> str:
    """Определить категорию по нише"""
    niche_lower = niche.lower()
    
    max_score = 0
    best_category = 'freelance'  # По умолчанию
    
    for category, keywords in NICHE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in niche_lower)
        if score > max_score:
            max_score = score
            best_category = category
    
    return best_category


async def search_telemetr_chats(query: str, min_subscribers: int = 1000) -> List[dict]:
    """
    Поиск чатов на Telemetr.me с извлечением статистики
    
    Args:
        query: Поисковый запрос
        min_subscribers: Минимальное количество подписчиков
        
    Returns:
        Список словарей с информацией о чатах, отсортированный по подписчикам
    """
    results = []
    
    try:
        # Поиск по запросу
        url = f"https://telemetr.me/channels/?q={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.warning(f"Telemetr returned status {response.status}")
                    return []
                
                html = await response.text()
                
                # Ищем карточки каналов с подписчиками
                # Формат: @username и рядом число подписчиков (например "12.5K" или "1.2M")
                # Паттерн для извлечения username и subscribers
                
                # Сначала найдём все ссылки на каналы
                channel_pattern = r'href="[^"]*(/channels/([a-zA-Z0-9_]+))"[^>]*>.*?(\d+(?:\.\d+)?[KkMmКкМм]?)\s*(?:подписчик|subscriber|участник|member)'
                matches = re.findall(channel_pattern, html, re.IGNORECASE | re.DOTALL)
                
                # Альтернативный паттерн - просто ищем @username и числа рядом
                if not matches:
                    # Извлекаем username'ы
                    username_pattern = r'@([a-zA-Z0-9_]{5,32})'
                    usernames = re.findall(username_pattern, html)
                    
                    # Извлекаем числа (подписчики)
                    numbers_pattern = r'(\d+(?:\.\d+)?)\s*([KkMmКкМм])?(?:\s*(?:подписчик|subscriber|участник|member|чел))?'
                    numbers = re.findall(numbers_pattern, html)
                    
                    seen = set()
                    for username in usernames:
                        if username.lower() in seen or username.lower().startswith('telemetr'):
                            continue
                        seen.add(username.lower())
                        
                        # Пытаемся найти число подписчиков для этого канала
                        subscribers = 5000  # Дефолт если не нашли
                        
                        # Ищем число рядом с username в HTML
                        idx = html.find(f'@{username}')
                        if idx != -1:
                            context = html[max(0, idx-200):idx+200]
                            for num, suffix in numbers:
                                num_float = float(num)
                                if suffix and suffix.upper() in ['K', 'К']:
                                    num_float *= 1000
                                elif suffix and suffix.upper() in ['M', 'М']:
                                    num_float *= 1000000
                                if num_float >= 100:  # Похоже на подписчиков
                                    subscribers = int(num_float)
                                    break
                        
                        if subscribers >= min_subscribers:
                            results.append({
                                'username': f'@{username}',
                                'link': f't.me/{username}',
                                'subscribers': subscribers,
                                'source': 'telemetr'
                            })
                        
                        if len(results) >= 20:
                            break
                else:
                    for match in matches:
                        username = match[1]
                        sub_str = match[2]
                        
                        # Парсим число подписчиков
                        subscribers = parse_subscriber_count(sub_str)
                        
                        if subscribers >= min_subscribers:
                            results.append({
                                'username': f'@{username}',
                                'link': f't.me/{username}',
                                'subscribers': subscribers,
                                'source': 'telemetr'
                            })
        
        # Сортируем по подписчикам (больше = лучше)
        results.sort(key=lambda x: x['subscribers'], reverse=True)
        
        logger.info(f"Telemetr found {len(results)} chats for '{query}'")
        return results[:15]
        
    except Exception as e:
        logger.error(f"Telemetr search error: {e}")
        return []


async def search_tgstat_chats(query: str, min_subscribers: int = 1000) -> List[dict]:
    """
    Поиск чатов на TGStat.ru с извлечением статистики
    
    Args:
        query: Поисковый запрос
        min_subscribers: Минимальное количество подписчиков
        
    Returns:
        Список словарей с информацией о чатах
    """
    results = []
    
    try:
        # TGStat поиск
        url = f"https://tgstat.ru/channels/search?q={query}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.warning(f"TGStat returned status {response.status}")
                    return []
                
                html = await response.text()
                
                # Ищем карточки каналов
                # TGStat обычно имеет формат: /channel/@username и число подписчиков
                card_pattern = r'/channel/@([a-zA-Z0-9_]+).*?(\d+(?:\.\d+)?[KkMmКкМм]?)\s*(?:подписчик|участник)'
                matches = re.findall(card_pattern, html, re.IGNORECASE | re.DOTALL)
                
                seen = set()
                for username, sub_str in matches:
                    if username.lower() in seen:
                        continue
                    seen.add(username.lower())
                    
                    subscribers = parse_subscriber_count(sub_str)
                    
                    if subscribers >= min_subscribers:
                        results.append({
                            'username': f'@{username}',
                            'link': f't.me/{username}',
                            'subscribers': subscribers,
                            'source': 'tgstat'
                        })
                
                # Если паттерн не сработал, ищем альтернативно
                if not results:
                    username_pattern = r'@([a-zA-Z0-9_]{5,32})'
                    usernames = re.findall(username_pattern, html)
                    
                    for username in usernames[:15]:
                        if username.lower() not in seen and not username.lower().startswith('tgstat'):
                            seen.add(username.lower())
                            results.append({
                                'username': f'@{username}',
                                'link': f't.me/{username}',
                                'subscribers': 5000,  # Оценка
                                'source': 'tgstat'
                            })
        
        results.sort(key=lambda x: x['subscribers'], reverse=True)
        logger.info(f"TGStat found {len(results)} chats for '{query}'")
        return results[:10]
        
    except Exception as e:
        logger.error(f"TGStat search error: {e}")
        return []


def parse_subscriber_count(sub_str: str) -> int:
    """Парсит строку подписчиков в число (12.5K -> 12500)"""
    try:
        sub_str = sub_str.strip().upper().replace(',', '.').replace(' ', '')
        
        multiplier = 1
        if 'K' in sub_str or 'К' in sub_str:
            multiplier = 1000
            sub_str = sub_str.replace('K', '').replace('К', '')
        elif 'M' in sub_str or 'М' in sub_str:
            multiplier = 1000000
            sub_str = sub_str.replace('M', '').replace('М', '')
        
        return int(float(sub_str) * multiplier)
    except:
        return 0


def format_subscribers(count: int) -> str:
    """Форматирует число подписчиков (12500 -> 12.5K)"""
    if count >= 1000000:
        return f"{count/1000000:.1f}M"
    elif count >= 1000:
        return f"{count/1000:.1f}K"
    return str(count)


async def generate_keywords(niche: str) -> List[str]:
    """
    Генерация ключевых слов для ниши с помощью GPT
    
    Args:
        niche: Описание ниши (например, "Веб-разработка")
        
    Returns:
        Список ключевых слов
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI API key не настроен")
    
    try:
        prompt = f"""Ты - эксперт по лидогенерации в Telegram.

Дана ниша: "{niche}"

Сгенерируй список из 15-20 ключевых слов и фраз, по которым можно искать потенциальных клиентов в русскоязычных Telegram-чатах.

Ключевые слова должны быть:
- Конкретными (ищу, нужен, требуется)
- Релевантными нише
- На русском языке
- Разнообразными (от общих до специфичных)

Верни ТОЛЬКО список слов/фраз, каждое с новой строки, без нумерации и пояснений."""

        logger.info(f"Generating keywords for niche: '{niche}'")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты - помощник для генерации ключевых слов для поиска лидов."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        keywords_text = response.choices[0].message.content.strip()
        keywords = [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]
        
        logger.info(f"Generated {len(keywords)} keywords")
        return keywords
        
    except Exception as e:
        logger.error(f"Error generating keywords: {e}", exc_info=True)
        raise
    finally:
        try:
            await client.close()
        except Exception:
            pass  # Игнорируем ошибки закрытия


async def generate_exclude_words(niche: str) -> List[str]:
    """
    Генерация исключающих слов для фильтрации спама
    
    Args:
        niche: Описание ниши
        
    Returns:
        Список исключающих слов
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI API key не настроен")
    
    try:
        prompt = f"""Ты - эксперт по фильтрации спама в Telegram.

Дана ниша: "{niche}"

Сгенерируй список из 10-15 исключающих слов, которые помогут отфильтровать нерелевантные сообщения и спам.

Исключающие слова должны быть:
- Типичными для спама (казино, ставки, займы и т.д.)
- Не относящимися к нише
- На русском языке

Верни ТОЛЬКО список слов, каждое с новой строки, без нумерации и пояснений."""

        logger.info(f"Generating exclude words for niche: '{niche}'")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты - помощник для генерации исключающих слов."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        words_text = response.choices[0].message.content.strip()
        words = [w.strip() for w in words_text.split('\n') if w.strip()]
        
        logger.info(f"Generated {len(words)} exclude words")
        return words
        
    except Exception as e:
        logger.error(f"Error generating exclude words: {e}", exc_info=True)
        raise
    finally:
        try:
            await client.close()
        except Exception:
            pass  # Игнорируем ошибки закрытия


async def suggest_chats(niche: str, min_subscribers: int = 100) -> List[dict]:
    """
    Предложение РЕАЛЬНЫХ чатов для мониторинга
    
    Стратегия:
    1. Ищем через Telegram Global Search API (100% существующие чаты)
    2. Если Telegram недоступен - сообщаем пользователю
    
    ВАЖНО: Веб-парсинг Telemetr/TGStat отключён - они возвращают мусор!
    
    Args:
        niche: Описание ниши
        min_subscribers: Минимум подписчиков
        
    Returns:
        Список словарей с информацией о РЕАЛЬНЫХ чатах
    """
    results = []
    seen_usernames = set()
    
    try:
        logger.info(f"Starting REAL chat search for niche: '{niche}'")
        
        # 1. Определяем категорию
        category = detect_category(niche)
        logger.info(f"Detected category: '{category}'")
        
        # Формируем поисковые запросы
        search_queries = [niche]
        category_keywords = NICHE_KEYWORDS.get(category, [])[:5]
        search_queries.extend(category_keywords)
        
        # Убираем дубликаты
        search_queries = list(dict.fromkeys(search_queries))
        
        # 2. Поиск через Telegram API (ЕДИНСТВЕННЫЙ надёжный источник!)
        for query in search_queries[:4]:
            try:
                telegram_results = await search_telegram_chats(query, limit=15)
                for chat in telegram_results:
                    username_lower = chat['username'].lower()
                    if username_lower not in seen_usernames:
                        seen_usernames.add(username_lower)
                        results.append(chat)
                
                # Небольшая пауза между запросами для избежания flood
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Telegram search for '{query}' failed: {e}")
                continue
        
        logger.info(f"Found {len(results)} VERIFIED chats from Telegram search")
        
        # ВАЖНО: Веб-парсинг (Telemetr/TGStat) ОТКЛЮЧЁН!
        # Они возвращают мусорные данные - топ каналов без фильтрации по запросу
        
        # 3. Сортируем по подписчикам
        results.sort(key=lambda x: -(x.get('subscribers') or 0))
        
        # 4. Фильтруем по минимальному количеству подписчиков
        final_results = []
        for r in results:
            subs = r.get('subscribers')
            if subs is None or subs >= min_subscribers:
                final_results.append(r)
        
        logger.info(f"Total results: {len(final_results)} chats")
        
        # Ограничиваем количество
        return final_results[:20]
        
    except Exception as e:
        logger.error(f"Error in suggest_chats: {e}", exc_info=True)
        return []


async def suggest_chat_names_ai(niche: str) -> List[str]:
    """
    AI предложение названий чатов для ручного поиска
    
    Args:
        niche: Описание ниши
        
    Returns:
        Список предполагаемых названий чатов
    """
    client = get_openai_client()
    if not client:
        return []
    
    try:
        prompt = f"""Дана ниша: "{niche}"

Предложи 5-7 типичных названий Telegram-чатов и каналов, где могут обсуждаться заказы/вакансии/сделки в этой нише.

Названия должны быть:
- Реалистичными
- На русском языке
- Релевантными нише

Верни ТОЛЬКО список названий, каждое с новой строки, без @, без пояснений."""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты - помощник для поиска Telegram-чатов."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        chats_text = response.choices[0].message.content.strip()
        chats = [c.strip() for c in chats_text.split('\n') if c.strip()]
        
        return chats
    except Exception as e:
        logger.error(f"Error in suggest_chat_names_ai: {e}")
        return []
    finally:
        try:
            await client.close()
        except Exception:
            pass


async def generate_filters(niche: str, keywords: List[str]) -> List[str]:
    """
    Генерация логических фильтров на основе ключевых слов
    
    Args:
        niche: Описание ниши
        keywords: Список ключевых слов
        
    Returns:
        Список логических фильтров
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OpenAI API key не настроен")
    
    try:
        keywords_str = ', '.join(keywords[:10])  # Берем первые 10
        
        prompt = f"""Ты - эксперт по созданию поисковых фильтров.

Дана ниша: "{niche}"
Ключевые слова: {keywords_str}

Создай 5-7 логических фильтров для более точного поиска лидов.

Используй операторы:
+ (И) - оба слова должны быть в тексте
| (ИЛИ) - хотя бы одно слово

Примеры:
сниму + квартиру
разработка | программирование
ищу + дизайнер | дизайнера

Верни ТОЛЬКО список фильтров, каждый с новой строки, без пояснений."""

        logger.info(f"Generating filters for niche: '{niche}'")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты - помощник для создания поисковых фильтров."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        filters_text = response.choices[0].message.content.strip()
        filters = [f.strip() for f in filters_text.split('\n') if f.strip()]
        
        logger.info(f"Generated {len(filters)} filters")
        return filters
        
    except Exception as e:
        logger.error(f"Error generating filters: {e}", exc_info=True)
        raise
    finally:
        try:
            await client.close()
        except Exception:
            pass
