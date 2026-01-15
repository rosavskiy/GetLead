"""Утилиты для работы с AI"""
from openai import AsyncOpenAI
from typing import List
from config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


async def generate_keywords(niche: str) -> List[str]:
    """
    Генерация ключевых слов для ниши с помощью GPT
    
    Args:
        niche: Описание ниши (например, "Веб-разработка")
        
    Returns:
        Список ключевых слов
    """
    if not client:
        raise ValueError("OpenAI API key не настроен")
    
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


async def generate_exclude_words(niche: str) -> List[str]:
    """
    Генерация исключающих слов для фильтрации спама
    
    Args:
        niche: Описание ниши
        
    Returns:
        Список исключающих слов
    """
    if not client:
        raise ValueError("OpenAI API key не настроен")
    
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


async def suggest_chats(niche: str) -> List[str]:
    """
    Предложение названий чатов для мониторинга
    
    Args:
        niche: Описание ниши
        
    Returns:
        Список предполагаемых названий чатов
    """
    if not client:
        raise ValueError("OpenAI API key не настроен")
    
    prompt = f"""Ты - эксперт по Telegram-сообществам.

Дана ниша: "{niche}"

Предложи 10-15 типичных названий Telegram-чатов и каналов, где могут обсуждаться заказы/вакансии/сделки в этой нише.

Названия должны быть:
- Реалистичными (как реальные чаты)
- На русском языке
- Релевантными нише
- Разнообразными (биржи, вакансии, фриланс и т.д.)

Верни ТОЛЬКО список названий, каждое с новой строки, без @, без пояснений.

Пример формата:
Фриланс Заказы
IT Вакансии
Работа для дизайнеров"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты - помощник для поиска Telegram-чатов."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=400
    )
    
    chats_text = response.choices[0].message.content.strip()
    chats = [c.strip() for c in chats_text.split('\n') if c.strip()]
    
    return chats


async def generate_filters(niche: str, keywords: List[str]) -> List[str]:
    """
    Генерация логических фильтров на основе ключевых слов
    
    Args:
        niche: Описание ниши
        keywords: Список ключевых слов
        
    Returns:
        Список логических фильтров
    """
    if not client:
        raise ValueError("OpenAI API key не настроен")
    
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
