"""Утилиты для работы с AI"""
import aiohttp
import re
import logging
from openai import AsyncOpenAI
from typing import List, Optional
from config import settings

logger = logging.getLogger(__name__)


def get_openai_client() -> Optional[AsyncOpenAI]:
    """Создаёт OpenAI клиент по требованию (избегаем проблем с глобальным клиентом)"""
    if settings.OPENAI_API_KEY:
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return None

# Встроенная база популярных чатов по категориям (бесплатно!)
CHAT_DATABASE = {
    'it': [
        '@ru_python', '@pro_python_code', '@python_scripts',
        '@javascript_ru', '@react_js', '@vuejs_club',
        '@devops_ru', '@docker_ru', '@kubernetes_ru',
        '@frontend_ru', '@webdev_ru', '@css_ru',
        '@nodejs_ru', '@golang_ru', '@rust_ru',
        '@linux_ru', '@sysadminka', '@linux_beginners',
        '@mobile_dev', '@android_dev', '@ios_dev',
        '@it_freelance', '@freelance_orders_ru', '@itchats',
    ],
    'design': [
        '@designchat', '@design_ru', '@uxuidesign',
        '@figma_rus', '@photoshop_ru', '@illustrator_chat',
        '@webdesign_ru', '@tgdesigners', '@design_jobs',
        '@logodesigners', '@motion_design', '@3d_chat_ru',
        '@branding_ru', '@freelance_design', '@graphic_design_ru',
    ],
    'marketing': [
        '@smm_chat', '@marketing_ru', '@digital_marketing_ru',
        '@targetolog_chat', '@context_ads', '@seo_chat_ru',
        '@smm_jobs', '@copywriting_ru', '@content_marketing',
        '@email_marketing', '@growth_hacking_ru', '@marketers_chat',
        '@reklama_chat', '@influencer_marketing', '@brand_marketing',
    ],
    'business': [
        '@bizforum', '@startupru', '@business_ru',
        '@entrepreneur_chat', '@investory_ru', '@finance_chat',
        '@startup_ideas', '@business_jobs', '@b2b_chat',
        '@sales_chat_ru', '@ecommerce_ru', '@dropshipping_ru',
        '@franchise_chat', '@business_networking',
    ],
    'real_estate': [
        '@realty_chat', '@nedvizhimost_ru', '@arenda_chat',
        '@ipoteka_chat', '@kvartira_chat', '@novostroyki_chat',
        '@rieltor_chat', '@zagorodnaya_nedvizhimost',
        '@kommercheska_nedvizhimost', '@investicii_nedvizhimost',
    ],
    'education': [
        '@education_chat', '@courses_ru', '@online_education',
        '@repetitory_chat', '@english_chat_ru', '@languages_ru',
        '@teachers_chat', '@school_chat', '@university_chat',
    ],
    'crypto': [
        '@crypto_chat_ru', '@bitcoin_ru', '@ethereum_ru',
        '@trading_crypto', '@nft_chat_ru', '@defi_ru',
        '@crypto_signals_ru', '@blockchain_dev',
    ],
    'freelance': [
        '@freelance_orders_ru', '@fl_orders', '@freelancejob',
        '@udalenka_chat', '@remote_work_ru', '@freelance_ru',
        '@kwork_orders', '@work_orders_ru', '@freelance_exchange',
    ],
    'legal': [
        '@lawyers_chat', '@yurist_chat', '@legal_ru',
        '@accounting_chat', '@buhgalter_chat', '@nalog_chat',
    ],
    'hr': [
        '@hr_chat_ru', '@rabota_chat', '@vacancy_chat',
        '@headhunter_chat', '@recruiting_ru', '@hh_chat',
    ],
    'travel': [
        '@travel_chat_ru', '@visa_help', '@immigranty_chat',
        '@relocation_chat', '@expats_ru', '@tourism_chat',
        '@emigration_ru', '@work_abroad', '@europe_visa',
        '@usa_visa_chat', '@canada_immigration',
    ],
    'services': [
        '@uslugi_chat', '@master_chat', '@repair_chat',
        '@cleaning_chat', '@beauty_masters', '@photo_video_chat',
        '@event_chat', '@wedding_chat', '@catering_chat',
    ],
}

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


async def suggest_chats(niche: str, min_subscribers: int = 1000) -> List[dict]:
    """
    Предложение ЖИВЫХ чатов для мониторинга
    
    Стратегия:
    1. Парсим Telemetr.me и TGStat.ru с фильтром по подписчикам
    2. Дополняем из встроенной базы
    3. Сортируем по количеству подписчиков
    4. Возвращаем только активные чаты (1000+ участников)
    
    Args:
        niche: Описание ниши
        min_subscribers: Минимум подписчиков (по умолчанию 1000)
        
    Returns:
        Список словарей с информацией о чатах, отсортированный по популярности
    """
    results = []
    seen_usernames = set()
    
    try:
        logger.info(f"Starting chat search for niche: '{niche}'")
        
        # 1. Определяем категорию и ключевые слова для поиска
        category = detect_category(niche)
        logger.info(f"Detected category: '{category}'")
        
        # Формируем поисковые запросы
        search_queries = [niche]
        
        # Добавляем ключевые слова категории
        category_keywords = NICHE_KEYWORDS.get(category, [])[:3]
        search_queries.extend(category_keywords)
        
        # 2. Параллельно ищем на Telemetr и TGStat
        import asyncio
        
        search_tasks = []
        for query in search_queries[:2]:  # Первые 2 запроса
            search_tasks.append(search_telemetr_chats(query, min_subscribers))
            search_tasks.append(search_tgstat_chats(query, min_subscribers))
        
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Собираем результаты
        for result in search_results:
            if isinstance(result, Exception):
                logger.warning(f"Search task failed: {result}")
                continue
            if isinstance(result, list):
                for chat in result:
                    username_lower = chat['username'].lower()
                    if username_lower not in seen_usernames:
                        seen_usernames.add(username_lower)
                        results.append(chat)
        
        logger.info(f"Found {len(results)} chats from web search")
        
        # 3. Дополняем из встроенной базы (с оценкой подписчиков)
        db_chats = CHAT_DATABASE.get(category, [])
        for chat in db_chats:
            username_lower = chat.lower()
            if username_lower not in seen_usernames:
                seen_usernames.add(username_lower)
                results.append({
                    'username': chat,
                    'link': f't.me/{chat.replace("@", "")}',
                    'subscribers': 5000,  # Оценка для чатов из базы
                    'source': 'database'
                })
        
        # 4. Сортируем по количеству подписчиков
        results.sort(key=lambda x: x.get('subscribers', 0), reverse=True)
        
        # 5. Фильтруем только с достаточным количеством подписчиков
        results = [r for r in results if r.get('subscribers', 5000) >= min_subscribers]
        
        logger.info(f"After filtering: {len(results)} chats with {min_subscribers}+ subscribers")
        
        # 6. Если мало результатов и есть OpenAI - добавляем AI предложения
        if settings.OPENAI_API_KEY and len(results) < 5:
            try:
                ai_suggestions = await suggest_chat_names_ai(niche)
                for name in ai_suggestions[:5]:
                    if name.lower() not in seen_usernames:
                        results.append({
                            'username': name,
                            'link': None,
                            'subscribers': None,
                            'source': 'ai_suggestion'
                        })
                logger.info(f"Added {len(ai_suggestions)} AI suggestions")
            except Exception as e:
                logger.warning(f"AI suggestions failed: {e}")
        
        logger.info(f"Total results: {len(results)}")
        
    except Exception as e:
        logger.error(f"Error in suggest_chats: {e}", exc_info=True)
        # Fallback - возвращаем из базы
        for chat in CHAT_DATABASE.get(category if 'category' in dir() else 'freelance', [])[:5]:
            results.append({
                'username': chat,
                'link': f't.me/{chat.replace("@", "")}',
                'subscribers': 5000,
                'source': 'database'
            })
    
    return results[:15]


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
