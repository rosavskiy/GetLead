"""Клавиатуры для бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List
from database.models import Project, SubscriptionPlan


def main_menu_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        ('� Профиль', 'menu:profile'),
        ('📊 Статистика', 'profile:stats'),
        ('📁 Проекты', 'menu:projects'),
        ('🔑 Ключевые слова', 'menu:keywords'),
        ('🚫 Исключающие слова', 'menu:exclude'),
        ('🔧 Фильтры', 'menu:filters'),
        ('💬 Чаты', 'menu:chats'),
        ('💳 Тарифы', 'menu:payment'),
        ('🔗 Интеграции', 'menu:integrations'),
        ('❓ Помощь', 'menu:help'),
    ]
    
    for text, callback in buttons:
        builder.button(text=text, callback_data=callback)
    
    builder.adjust(2)
    return builder.as_markup()


def projects_menu_kb(projects: List[Project], lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню проектов"""
    builder = InlineKeyboardBuilder()
    
    for project in projects:
        status = '✅' if project.is_active else '⚪'
        builder.button(
            text=f"{status} {project.name}",
            callback_data=f"project:activate:{project.id}"
        )
    
    builder.button(text='➕ Создать проект', callback_data='project:create')
    builder.button(text='🗑 Удалить проект', callback_data='project:delete')
    builder.button(text='🔙 Назад', callback_data='menu:main')
    
    builder.adjust(1)
    return builder.as_markup()


def keywords_menu_kb(has_keywords: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню ключевых слов"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text='➕ Добавить слова', callback_data='keywords:add')
    builder.button(text='🤖 AI подбор', callback_data='keywords:ai')
    
    if has_keywords:
        builder.button(text='📋 Показать список', callback_data='keywords:list')
        builder.button(text='🗑 Удалить все', callback_data='keywords:clear')
    
    builder.button(text='🔙 Назад', callback_data='menu:main')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def exclude_menu_kb(has_keywords: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню исключающих слов"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text='➕ Добавить слова', callback_data='exclude:add')
    builder.button(text='🤖 AI подбор', callback_data='exclude:ai')
    
    if has_keywords:
        builder.button(text='📋 Показать список', callback_data='exclude:list')
        builder.button(text='🗑 Удалить все', callback_data='exclude:clear')
    
    builder.button(text='🔙 Назад', callback_data='menu:main')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def chats_menu_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню чатов"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text='📋 Мои чаты', callback_data='chats:list')
    builder.button(text='📦 Пакетные чаты', callback_data='chats:packs')
    builder.button(text='➕ Добавить чат', callback_data='chats:add')
    builder.button(text='🤖 AI подбор', callback_data='chats:ai')
    builder.button(text='🔙 Назад', callback_data='menu:main')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def payment_menu_kb(current_plan: SubscriptionPlan, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню тарифов"""
    builder = InlineKeyboardBuilder()
    
    plans = [
        ('💼 Фрилансер (5 чатов) - 500₽', 'payment:freelancer', SubscriptionPlan.FREELANCER),
        ('📊 Стандарт (20 чатов) - 1500₽', 'payment:standard', SubscriptionPlan.STANDARD),
        ('🚀 Стартап (10 чатов) - 1000₽', 'payment:startup', SubscriptionPlan.STARTUP),
        ('🏢 Компания (50 чатов) - 3000₽', 'payment:company', SubscriptionPlan.COMPANY),
    ]
    
    for text, callback, plan in plans:
        if plan == current_plan:
            text = f'✅ {text}'
        builder.button(text=text, callback_data=callback)
    
    builder.button(text='🔙 Назад', callback_data='menu:main')
    
    builder.adjust(1)
    return builder.as_markup()


def payment_method_kb(plan: str, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Выбор способа оплаты"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text='💳 Банковская карта', callback_data=f'pay:card:{plan}')
    builder.button(text='₿ Криптовалюта', callback_data=f'pay:crypto:{plan}')
    builder.button(text='🔙 Назад', callback_data='menu:payment')
    
    builder.adjust(1)
    return builder.as_markup()


def back_to_main_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 Главное меню', callback_data='menu:main')
    return builder.as_markup()


def cancel_kb(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Кнопка отмены"""
    builder = ReplyKeyboardBuilder()
    builder.button(text='❌ Отмена')
    return builder.as_markup(resize_keyboard=True)


def profile_menu_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню личного кабинета"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text='📊 Детальная статистика', callback_data='profile:stats')
    builder.button(text='🎯 Последние лиды', callback_data='profile:leads')
    builder.button(text='⚙️ Настройки', callback_data='profile:settings')
    builder.button(text='🔗 Интеграции', callback_data='menu:integrations')
    builder.button(text='🔙 Главное меню', callback_data='menu:main')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def stats_period_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Выбор периода статистики"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text='📅 Сегодня', callback_data='stats:period:today')
    builder.button(text='📆 Неделя', callback_data='stats:period:week')
    builder.button(text='🗓 Месяц', callback_data='stats:period:month')
    builder.button(text='📊 Всё время', callback_data='stats:period:all')
    builder.button(text='🔙 Назад', callback_data='menu:profile')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def settings_menu_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню настроек"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text='🌐 Сменить язык', callback_data='settings:language')
    builder.button(text='🔔 Уведомления', callback_data='settings:notifications')
    builder.button(text='🔗 AmoCRM', callback_data='integrations:amocrm')
    builder.button(text='🔙 Назад', callback_data='menu:profile')
    
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def integrations_menu_kb(has_amocrm: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню интеграций"""
    builder = InlineKeyboardBuilder()
    
    amocrm_status = '✅' if has_amocrm else '❌'
    builder.button(text=f'{amocrm_status} AmoCRM', callback_data='integrations:amocrm')
    builder.button(text='📋 Webhook API', callback_data='integrations:webhook')
    builder.button(text='🔙 Главное меню', callback_data='menu:main')
    
    builder.adjust(2, 1)
    return builder.as_markup()


def amocrm_menu_kb(is_connected: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню настройки AmoCRM"""
    builder = InlineKeyboardBuilder()
    
    if is_connected:
        builder.button(text='⚙️ Настройки воронки', callback_data='amocrm:pipeline')
        builder.button(text='🔄 Переподключить', callback_data='amocrm:reconnect')
        builder.button(text='❌ Отключить', callback_data='amocrm:disconnect')
    else:
        builder.button(text='🔗 Подключить AmoCRM', callback_data='amocrm:connect')
    
    builder.button(text='🔙 Назад', callback_data='menu:integrations')
    
    builder.adjust(1)
    return builder.as_markup()


def filters_menu_kb(has_filters: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню фильтров"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text='➕ Добавить фильтр', callback_data='filters:add')
    
    if has_filters:
        builder.button(text='📋 Показать все', callback_data='filters:list')
        builder.button(text='🗑 Удалить все', callback_data='filters:clear')
    
    builder.button(text='🔙 Главное меню', callback_data='menu:main')
    
    builder.adjust(1)
    return builder.as_markup()
