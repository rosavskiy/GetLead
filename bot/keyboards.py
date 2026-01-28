"""Клавиатуры для бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List
from database.models import Project, SubscriptionPlan
from bot.texts import get_text


def language_selection_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора языка при первом запуске"""
    builder = InlineKeyboardBuilder()
    builder.button(text='🇷🇺 Русский', callback_data='set_lang:ru')
    builder.button(text='🇬🇧 English', callback_data='set_lang:en')
    builder.adjust(2)
    return builder.as_markup()


def main_menu_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        (get_text('btn_profile', lang), 'menu:profile'),
        (get_text('btn_stats', lang), 'profile:stats'),
        (get_text('btn_projects', lang), 'menu:projects'),
        (get_text('btn_keywords', lang), 'menu:keywords'),
        (get_text('btn_exclude', lang), 'menu:exclude'),
        (get_text('btn_filters', lang), 'menu:filters'),
        (get_text('btn_chats', lang), 'menu:chats'),
        (get_text('btn_payment', lang), 'menu:payment'),
        (get_text('btn_integrations', lang), 'menu:integrations'),
        (get_text('btn_help', lang), 'menu:help'),
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
    
    builder.button(text=get_text('btn_create_project', lang), callback_data='project:create')
    builder.button(text=get_text('btn_delete_project', lang), callback_data='project:delete')
    builder.button(text=get_text('btn_back', lang), callback_data='menu:main')
    
    builder.adjust(1)
    return builder.as_markup()


def keywords_menu_kb(has_keywords: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню ключевых слов"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('btn_add_keywords', lang), callback_data='keywords:add')
    builder.button(text=get_text('btn_ai_suggest', lang), callback_data='keywords:ai')
    
    if has_keywords:
        builder.button(text=get_text('btn_show_list', lang), callback_data='keywords:list')
        builder.button(text=get_text('btn_clear_all', lang), callback_data='keywords:clear')
    
    builder.button(text=get_text('btn_back', lang), callback_data='menu:main')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def exclude_menu_kb(has_keywords: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню исключающих слов"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('btn_add_keywords', lang), callback_data='exclude:add')
    builder.button(text=get_text('btn_ai_suggest', lang), callback_data='exclude:ai')
    
    if has_keywords:
        builder.button(text=get_text('btn_show_list', lang), callback_data='exclude:list')
        builder.button(text=get_text('btn_clear_all', lang), callback_data='exclude:clear')
    
    builder.button(text=get_text('btn_back', lang), callback_data='menu:main')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def chats_menu_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню чатов"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('btn_my_chats', lang), callback_data='chats:list')
    builder.button(text=get_text('btn_chat_packs', lang), callback_data='chats:packs')
    builder.button(text=get_text('btn_add_chat', lang), callback_data='chats:add')
    builder.button(text=get_text('btn_ai_suggest', lang), callback_data='chats:ai')
    builder.button(text=get_text('btn_back', lang), callback_data='menu:main')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def chats_list_kb(chats: list, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Список чатов с кнопками удаления"""
    builder = InlineKeyboardBuilder()
    
    for chat in chats[:20]:  # Максимум 20 чатов
        title = chat.title or chat.telegram_link
        if len(title) > 25:
            title = title[:22] + '...'
        status = '✅' if chat.is_joined else '⏳'
        builder.button(
            text=f'🗑 {status} {title}',
            callback_data=f'chats:delete:{chat.id}'
        )
    
    # Кнопка назад
    builder.button(text=get_text('btn_back', lang), callback_data='menu:chats')
    
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete_chat_kb(chat_id: int, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Подтверждение удаления чата"""
    builder = InlineKeyboardBuilder()
    
    if lang == 'ru':
        builder.button(text='✅ Да, удалить', callback_data=f'chats:confirm_delete:{chat_id}')
        builder.button(text='❌ Отмена', callback_data='chats:list')
    else:
        builder.button(text='✅ Yes, delete', callback_data=f'chats:confirm_delete:{chat_id}')
        builder.button(text='❌ Cancel', callback_data='chats:list')
    
    builder.adjust(2)
    return builder.as_markup()


def payment_menu_kb(current_plan: SubscriptionPlan, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню тарифов"""
    builder = InlineKeyboardBuilder()
    
    if lang == 'ru':
        plans = [
            ('💼 Фрилансер (5 чатов) - 500₽', 'payment:freelancer', SubscriptionPlan.FREELANCER),
            ('📊 Стандарт (20 чатов) - 1500₽', 'payment:standard', SubscriptionPlan.STANDARD),
            ('🚀 Стартап (10 чатов) - 1000₽', 'payment:startup', SubscriptionPlan.STARTUP),
            ('🏢 Компания (50 чатов) - 3000₽', 'payment:company', SubscriptionPlan.COMPANY),
        ]
    else:
        plans = [
            ('💼 Freelancer (5 chats) - $5', 'payment:freelancer', SubscriptionPlan.FREELANCER),
            ('📊 Standard (20 chats) - $15', 'payment:standard', SubscriptionPlan.STANDARD),
            ('🚀 Startup (10 chats) - $10', 'payment:startup', SubscriptionPlan.STARTUP),
            ('🏢 Company (50 chats) - $30', 'payment:company', SubscriptionPlan.COMPANY),
        ]
    
    for text, callback, plan in plans:
        if plan == current_plan:
            text = f'✅ {text}'
        builder.button(text=text, callback_data=callback)
    
    builder.button(text=get_text('btn_back', lang), callback_data='menu:main')
    
    builder.adjust(1)
    return builder.as_markup()


def payment_method_kb(plan: str, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Выбор способа оплаты"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('btn_card_payment', lang), callback_data=f'pay:card:{plan}')
    builder.button(text=get_text('btn_crypto_payment', lang), callback_data=f'pay:crypto:{plan}')
    builder.button(text=get_text('btn_back', lang), callback_data='menu:payment')
    
    builder.adjust(1)
    return builder.as_markup()


def back_to_main_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_back_main', lang), callback_data='menu:main')
    return builder.as_markup()


def cancel_kb(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Кнопка отмены"""
    builder = ReplyKeyboardBuilder()
    builder.button(text=get_text('btn_cancel', lang))
    return builder.as_markup(resize_keyboard=True)


def profile_menu_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню личного кабинета"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('btn_detailed_stats', lang), callback_data='profile:stats')
    builder.button(text=get_text('btn_recent_leads', lang), callback_data='profile:leads')
    builder.button(text=get_text('btn_settings', lang), callback_data='profile:settings')
    builder.button(text=get_text('btn_integrations', lang), callback_data='menu:integrations')
    builder.button(text=get_text('btn_back_main', lang), callback_data='menu:main')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def stats_period_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Выбор периода статистики"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('stats_today', lang), callback_data='stats:period:today')
    builder.button(text=get_text('stats_week', lang), callback_data='stats:period:week')
    builder.button(text=get_text('stats_month', lang), callback_data='stats:period:month')
    builder.button(text=get_text('stats_all_time', lang), callback_data='stats:period:all')
    builder.button(text=get_text('btn_back', lang), callback_data='menu:profile')
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def settings_menu_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню настроек"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('btn_change_language', lang), callback_data='settings:language')
    builder.button(text=get_text('btn_notifications', lang), callback_data='settings:notifications')
    builder.button(text='🔗 AmoCRM', callback_data='integrations:amocrm')
    builder.button(text=get_text('btn_back', lang), callback_data='menu:profile')
    
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def integrations_menu_kb(has_amocrm: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню интеграций"""
    builder = InlineKeyboardBuilder()
    
    amocrm_status = '✅' if has_amocrm else '❌'
    builder.button(text=f'{amocrm_status} AmoCRM', callback_data='integrations:amocrm')
    builder.button(text='📋 Webhook API', callback_data='integrations:webhook')
    builder.button(text=get_text('btn_back_main', lang), callback_data='menu:main')
    
    builder.adjust(2, 1)
    return builder.as_markup()


def amocrm_menu_kb(is_connected: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню настройки AmoCRM"""
    builder = InlineKeyboardBuilder()
    
    if lang == 'ru':
        if is_connected:
            builder.button(text='⚙️ Настройки воронки', callback_data='amocrm:pipeline')
            builder.button(text='🔄 Переподключить', callback_data='amocrm:reconnect')
            builder.button(text='❌ Отключить', callback_data='amocrm:disconnect')
        else:
            builder.button(text='🔗 Подключить AmoCRM', callback_data='amocrm:connect')
    else:
        if is_connected:
            builder.button(text='⚙️ Pipeline Settings', callback_data='amocrm:pipeline')
            builder.button(text='🔄 Reconnect', callback_data='amocrm:reconnect')
            builder.button(text='❌ Disconnect', callback_data='amocrm:disconnect')
        else:
            builder.button(text='🔗 Connect AmoCRM', callback_data='amocrm:connect')
    
    builder.button(text=get_text('btn_back', lang), callback_data='menu:integrations')
    
    builder.adjust(1)
    return builder.as_markup()


def filters_menu_kb(has_filters: bool = False, lang: str = 'ru') -> InlineKeyboardMarkup:
    """Меню фильтров"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=get_text('btn_add_filter', lang), callback_data='filters:add')
    
    if has_filters:
        builder.button(text=get_text('btn_show_filters', lang), callback_data='filters:list')
        builder.button(text=get_text('btn_clear_filters', lang), callback_data='filters:clear')
    
    builder.button(text=get_text('btn_back_main', lang), callback_data='menu:main')
    
    builder.adjust(1)
    return builder.as_markup()


def ai_keywords_selection_kb(keywords: List[str], lang: str = 'ru') -> InlineKeyboardMarkup:
    """Клавиатура для выбора AI ключевых слов"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки для каждого ключевого слова (укороченные)
    for i, kw in enumerate(keywords):
        # Обрезаем длинные ключевые слова
        display_text = kw[:25] + '...' if len(kw) > 25 else kw
        builder.button(text=f'➕ {display_text}', callback_data=f'ai_kw:add:{i}')
    
    # Кнопки действий
    add_all = '✅ Добавить все' if lang == 'ru' else '✅ Add all'
    done = '✔️ Готово' if lang == 'ru' else '✔️ Done'
    
    builder.button(text=add_all, callback_data='ai_kw:add_all')
    builder.button(text=done, callback_data='ai_kw:done')
    
    # Размещаем: ключевые слова по 2 в ряд, кнопки действий по 1
    rows = []
    for i in range(0, len(keywords), 2):
        if i + 1 < len(keywords):
            rows.append(2)
        else:
            rows.append(1)
    rows.append(1)  # Добавить все
    rows.append(1)  # Готово
    
    builder.adjust(*rows)
    return builder.as_markup()
