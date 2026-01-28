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


async def search_telemetr_chats(query: str) -> List[dict]:
    """
    Поиск чатов на Telemetr.me (бесплатный скрапинг)
    
    Args:
        query: Поисковый запрос
        
    Returns:
        Список словарей с информацией о чатах
    """
    try:
        url = f"https://telemetr.me/channels/?q={query}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return []
                
                html = await response.text()
                
                # Извлекаем username'ы чатов
                pattern = r'@([a-zA-Z0-9_]{5,})'
                usernames = re.findall(pattern, html)
                
                # Убираем дубликаты и системные
                seen = set()
                result = []
                for username in usernames:
                    if username not in seen and not username.startswith('telemetr'):
                        seen.add(username)
                        result.append({'username': f'@{username}', 'link': f't.me/{username}'})
                        if len(result) >= 15:
                            break
                
                return result
    except Exception:
        return []


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
        
        return keywords
    finally:
        await client.close()


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
        
        return words
    finally:
        await client.close()


async def suggest_chats(niche: str) -> List[dict]:
    """
    Предложение чатов для мониторинга (гибридный подход)
    
    1. Определяем категорию по нише
    2. Берём чаты из встроенной базы
    3. Дополняем поиском на Telemetr.me
    
    Args:
        niche: Описание ниши
        
    Returns:
        Список словарей с информацией о чатах
    """
    results = []
    
    try:
        # 1. Определяем категорию
        category = detect_category(niche)
        logger.info(f"Detected category '{category}' for niche '{niche}'")
        
        # 2. Берём из встроенной базы
        db_chats = CHAT_DATABASE.get(category, [])
        for chat in db_chats[:10]:
            results.append({
                'username': chat,
                'link': f't.me/{chat.replace("@", "")}',
                'source': 'database'
            })
        
        logger.info(f"Found {len(results)} chats from database")
        
        # 3. Пробуем найти на Telemetr.me (опционально)
        try:
            telemetr_chats = await search_telemetr_chats(niche)
            for chat in telemetr_chats[:5]:
                if chat['username'] not in [r['username'] for r in results]:
                    chat['source'] = 'telemetr'
                    results.append(chat)
            logger.info(f"Found {len(telemetr_chats)} chats from Telemetr")
        except Exception as e:
            logger.warning(f"Telemetr search failed: {e}")
        
        # 4. Если есть OpenAI и мало результатов, дополняем AI-предложениями
        if settings.OPENAI_API_KEY and len(results) < 10:
            try:
                ai_suggestions = await suggest_chat_names_ai(niche)
                for name in ai_suggestions[:5]:
                    results.append({
                        'username': name,
                        'link': None,
                        'source': 'ai_suggestion'
                    })
                logger.info(f"Added {len(ai_suggestions)} AI suggestions")
            except Exception as e:
                logger.warning(f"AI suggestions failed: {e}")
        
        logger.info(f"Total chats found: {len(results)}")
        
    except Exception as e:
        logger.error(f"Error in suggest_chats: {e}")
        # Возвращаем хотя бы что-то из общей базы фриланса
        for chat in CHAT_DATABASE.get('freelance', [])[:5]:
            results.append({
                'username': chat,
                'link': f't.me/{chat.replace("@", "")}',
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
    finally:
        await client.close()


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
        
        return filters
    finally:
        await client.close()
