"""Дополнительные утилиты для работы с датами и подписками"""
from datetime import datetime, timedelta
from database.models import SubscriptionPlan


def get_subscription_limits(plan: SubscriptionPlan) -> dict:
    """Получить лимиты для тарифного плана"""
    limits = {
        SubscriptionPlan.FREE: {
            'max_chats': 0,
            'max_keywords': 0,
            'ai_enabled': False,
            'support_priority': 'low'
        },
        SubscriptionPlan.FREELANCER: {
            'max_chats': 5,
            'max_keywords': -1,  # Безлимит
            'ai_enabled': True,
            'support_priority': 'normal'
        },
        SubscriptionPlan.STANDARD: {
            'max_chats': 20,
            'max_keywords': -1,
            'ai_enabled': True,
            'support_priority': 'high'
        },
        SubscriptionPlan.STARTUP: {
            'max_chats': 10,
            'max_keywords': -1,
            'ai_enabled': True,
            'support_priority': 'normal'
        },
        SubscriptionPlan.COMPANY: {
            'max_chats': 50,
            'max_keywords': -1,
            'ai_enabled': True,
            'support_priority': 'vip'
        }
    }
    
    return limits.get(plan, limits[SubscriptionPlan.FREE])


def calculate_subscription_end_date(plan: SubscriptionPlan, months: int = 1) -> datetime:
    """Рассчитать дату окончания подписки"""
    return datetime.utcnow() + timedelta(days=30 * months)


def is_subscription_active(subscription_plan: SubscriptionPlan, end_date: datetime) -> bool:
    """Проверить, активна ли подписка"""
    if subscription_plan == SubscriptionPlan.FREE:
        return False
    
    if not end_date:
        return False
    
    return end_date > datetime.utcnow()
