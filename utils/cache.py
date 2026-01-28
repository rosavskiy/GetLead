"""Утилиты для кэширования данных в Redis"""
import json
import logging
from typing import Optional, List, Dict, Any
from redis.asyncio import Redis
from datetime import timedelta

from config import settings

logger = logging.getLogger(__name__)

# Глобальный клиент Redis
_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Получить клиент Redis"""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


class CacheKeys:
    """Ключи для кэширования"""
    
    @staticmethod
    def user_keywords(user_id: int, project_id: int) -> str:
        """Ключ для ключевых слов пользователя"""
        return f"keywords:user:{user_id}:project:{project_id}"
    
    @staticmethod
    def user_exclude_words(user_id: int, project_id: int) -> str:
        """Ключ для исключающих слов"""
        return f"exclude:user:{user_id}:project:{project_id}"
    
    @staticmethod
    def chat_projects(chat_id: int) -> str:
        """Ключ для проектов чата"""
        return f"chat:projects:{chat_id}"
    
    @staticmethod
    def user_stats(user_id: int) -> str:
        """Ключ для статистики пользователя"""
        return f"stats:user:{user_id}"
    
    @staticmethod
    def project_keywords_pattern(project_id: int) -> str:
        """Ключ для всех ключевых слов проекта (для юзербота)"""
        return f"project:keywords:{project_id}"
    
    @staticmethod
    def monitored_chats() -> str:
        """Ключ для списка мониторируемых чатов"""
        return "monitored:chats"


class CacheService:
    """Сервис кэширования"""
    
    # Время жизни кэша (в секундах)
    TTL_KEYWORDS = 300  # 5 минут
    TTL_CHATS = 60  # 1 минута
    TTL_STATS = 120  # 2 минуты
    
    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        try:
            redis = await get_redis()
            value = await redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    @staticmethod
    async def set(key: str, value: Any, ttl: int = 300) -> bool:
        """Установить значение в кэш"""
        try:
            redis = await get_redis()
            await redis.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    @staticmethod
    async def delete(key: str) -> bool:
        """Удалить значение из кэша"""
        try:
            redis = await get_redis()
            await redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        """Удалить все ключи по паттерну"""
        try:
            redis = await get_redis()
            keys = await redis.keys(pattern)
            if keys:
                return await redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    # === Специализированные методы ===
    
    @staticmethod
    async def get_project_keywords(project_id: int) -> Optional[List[Dict]]:
        """Получить ключевые слова проекта из кэша"""
        key = CacheKeys.project_keywords_pattern(project_id)
        return await CacheService.get(key)
    
    @staticmethod
    async def set_project_keywords(project_id: int, keywords: List[Dict]) -> bool:
        """Сохранить ключевые слова проекта в кэш"""
        key = CacheKeys.project_keywords_pattern(project_id)
        return await CacheService.set(key, keywords, CacheService.TTL_KEYWORDS)
    
    @staticmethod
    async def invalidate_project_keywords(project_id: int) -> bool:
        """Инвалидировать кэш ключевых слов проекта"""
        key = CacheKeys.project_keywords_pattern(project_id)
        return await CacheService.delete(key)
    
    @staticmethod
    async def get_chat_projects(chat_telegram_id: int) -> Optional[List[Dict]]:
        """Получить проекты чата из кэша"""
        key = CacheKeys.chat_projects(chat_telegram_id)
        return await CacheService.get(key)
    
    @staticmethod
    async def set_chat_projects(chat_telegram_id: int, projects: List[Dict]) -> bool:
        """Сохранить проекты чата в кэш"""
        key = CacheKeys.chat_projects(chat_telegram_id)
        return await CacheService.set(key, projects, CacheService.TTL_CHATS)
    
    @staticmethod
    async def invalidate_chat_projects(chat_telegram_id: int) -> bool:
        """Инвалидировать кэш проектов чата"""
        key = CacheKeys.chat_projects(chat_telegram_id)
        return await CacheService.delete(key)
    
    @staticmethod
    async def get_monitored_chats() -> Optional[List[int]]:
        """Получить список мониторируемых чатов"""
        key = CacheKeys.monitored_chats()
        return await CacheService.get(key)
    
    @staticmethod
    async def set_monitored_chats(chat_ids: List[int]) -> bool:
        """Сохранить список мониторируемых чатов"""
        key = CacheKeys.monitored_chats()
        return await CacheService.set(key, chat_ids, CacheService.TTL_CHATS)
    
    @staticmethod
    async def add_monitored_chat(chat_id: int) -> bool:
        """Добавить чат в список мониторируемых"""
        try:
            redis = await get_redis()
            await redis.sadd("monitored:chats:set", chat_id)
            return True
        except Exception as e:
            logger.error(f"Error adding monitored chat: {e}")
            return False
    
    @staticmethod
    async def is_chat_monitored(chat_id: int) -> bool:
        """Проверить, мониторится ли чат"""
        try:
            redis = await get_redis()
            return await redis.sismember("monitored:chats:set", chat_id)
        except Exception as e:
            logger.error(f"Error checking monitored chat: {e}")
            return False


class RateLimiter:
    """Ограничитель частоты запросов"""
    
    @staticmethod
    async def is_allowed(key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Проверить, разрешён ли запрос
        
        Args:
            key: Уникальный ключ (например, user_id)
            max_requests: Максимум запросов
            window_seconds: Временное окно в секундах
            
        Returns:
            True если запрос разрешён
        """
        try:
            redis = await get_redis()
            rate_key = f"rate:{key}"
            
            current = await redis.get(rate_key)
            
            if current is None:
                await redis.setex(rate_key, window_seconds, 1)
                return True
            
            if int(current) >= max_requests:
                return False
            
            await redis.incr(rate_key)
            return True
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return True  # При ошибке пропускаем
    
    @staticmethod
    async def get_remaining(key: str, max_requests: int) -> int:
        """Получить оставшееся количество запросов"""
        try:
            redis = await get_redis()
            rate_key = f"rate:{key}"
            current = await redis.get(rate_key)
            
            if current is None:
                return max_requests
            
            return max(0, max_requests - int(current))
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return max_requests
