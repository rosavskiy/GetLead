"""Обработчики для личного кабинета и статистики пользователя"""
import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func

from database.database import async_session_maker
from database.models import User, Project, LeadMatch, Chat, SubscriptionPlan
from database.crud import ProjectCRUD
from bot.keyboards import profile_menu_kb, stats_period_kb, back_to_main_kb
from utils.subscription_helpers import get_subscription_limits

router = Router()


@router.callback_query(F.data == 'menu:profile')
async def show_profile(callback: CallbackQuery, user: User):
    """Показать личный кабинет пользователя"""
    async with async_session_maker() as session:
        # Получаем статистику
        projects_count = await session.execute(
            select(func.count(Project.id)).where(Project.user_id == user.id)
        )
        projects_count = projects_count.scalar() or 0
        
        # Количество лидов за всё время
        total_leads = await session.execute(
            select(func.count(LeadMatch.id)).where(LeadMatch.user_id == user.id)
        )
        total_leads = total_leads.scalar() or 0
        
        # Лиды за сегодня
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_leads = await session.execute(
            select(func.count(LeadMatch.id))
            .where(LeadMatch.user_id == user.id, LeadMatch.created_at >= today)
        )
        today_leads = today_leads.scalar() or 0
        
        # Лиды за неделю
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_leads = await session.execute(
            select(func.count(LeadMatch.id))
            .where(LeadMatch.user_id == user.id, LeadMatch.created_at >= week_ago)
        )
        week_leads = week_leads.scalar() or 0
        
        # Количество чатов
        chats_count = await session.execute(
            select(func.count(func.distinct(Chat.id)))
            .select_from(Project)
            .join(Project.chats)
            .where(Project.user_id == user.id)
        )
        chats_count = chats_count.scalar() or 0
    
    # Лимиты тарифа
    limits = get_subscription_limits(user.subscription_plan)
    
    # Формируем текст профиля
    plan_names = {
        SubscriptionPlan.FREE: '🆓 Бесплатный',
        SubscriptionPlan.FREELANCER: '💼 Фрилансер',
        SubscriptionPlan.STANDARD: '📊 Стандарт',
        SubscriptionPlan.STARTUP: '🚀 Стартап',
        SubscriptionPlan.COMPANY: '🏢 Компания'
    }
    
    plan_name = plan_names.get(user.subscription_plan, 'Неизвестный')
    
    text = f"""👤 <b>Личный кабинет</b>

📱 <b>ID:</b> <code>{user.telegram_id}</code>
👤 <b>Username:</b> @{user.username or 'не указан'}
📅 <b>Регистрация:</b> {user.created_at.strftime('%d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━

💳 <b>Тариф:</b> {plan_name}"""
    
    if user.subscription_plan != SubscriptionPlan.FREE:
        if user.subscription_end_date:
            days_left = (user.subscription_end_date - datetime.utcnow()).days
            text += f"\n⏳ <b>До окончания:</b> {days_left} дней"
            text += f"\n📆 <b>Истекает:</b> {user.subscription_end_date.strftime('%d.%m.%Y')}"
    
    text += f"""

━━━━━━━━━━━━━━━━━━━━

📊 <b>Статистика</b>

📁 <b>Проектов:</b> {projects_count}
💬 <b>Чатов:</b> {chats_count}/{limits['max_chats'] if limits['max_chats'] > 0 else '∞'}

🎯 <b>Найдено лидов:</b>
   • Сегодня: <b>{today_leads}</b>
   • За неделю: <b>{week_leads}</b>
   • Всего: <b>{total_leads}</b>
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=profile_menu_kb(user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'profile:stats')
async def show_detailed_stats(callback: CallbackQuery, user: User):
    """Показать детальную статистику"""
    text = """📊 <b>Детальная статистика</b>

Выберите период для просмотра:"""
    
    await callback.message.edit_text(
        text,
        reply_markup=stats_period_kb(user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('stats:period:'))
async def show_stats_by_period(callback: CallbackQuery, user: User):
    """Показать статистику за период"""
    period = callback.data.split(':')[2]
    
    # Определяем даты периода
    now = datetime.utcnow()
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_name = 'сегодня'
    elif period == 'week':
        start_date = now - timedelta(days=7)
        period_name = 'за неделю'
    elif period == 'month':
        start_date = now - timedelta(days=30)
        period_name = 'за месяц'
    else:  # all
        start_date = datetime(2020, 1, 1)
        period_name = 'за всё время'
    
    async with async_session_maker() as session:
        # Общее количество лидов
        total_leads = await session.execute(
            select(func.count(LeadMatch.id))
            .where(LeadMatch.user_id == user.id, LeadMatch.created_at >= start_date)
        )
        total_leads = total_leads.scalar() or 0
        
        # Лиды по проектам
        projects_stats = await session.execute(
            select(
                Project.name,
                func.count(LeadMatch.id).label('leads_count')
            )
            .outerjoin(LeadMatch, 
                (LeadMatch.project_id == Project.id) & 
                (LeadMatch.created_at >= start_date))
            .where(Project.user_id == user.id)
            .group_by(Project.id)
            .order_by(func.count(LeadMatch.id).desc())
        )
        projects_stats = projects_stats.all()
        
        # Лиды по чатам (топ-5)
        chats_stats = await session.execute(
            select(
                Chat.title,
                func.count(LeadMatch.id).label('leads_count')
            )
            .join(LeadMatch, LeadMatch.chat_id == Chat.id)
            .where(LeadMatch.user_id == user.id, LeadMatch.created_at >= start_date)
            .group_by(Chat.id)
            .order_by(func.count(LeadMatch.id).desc())
            .limit(5)
        )
        chats_stats = chats_stats.all()
        
        # Конверсия (отвеченные / всего)
        contacted_leads = await session.execute(
            select(func.count(LeadMatch.id))
            .where(
                LeadMatch.user_id == user.id,
                LeadMatch.created_at >= start_date,
                LeadMatch.is_contacted == True
            )
        )
        contacted_leads = contacted_leads.scalar() or 0
        
        converted_leads = await session.execute(
            select(func.count(LeadMatch.id))
            .where(
                LeadMatch.user_id == user.id,
                LeadMatch.created_at >= start_date,
                LeadMatch.is_converted == True
            )
        )
        converted_leads = converted_leads.scalar() or 0
    
    # Формируем текст
    conversion_rate = (contacted_leads/total_leads*100) if total_leads > 0 else 0
    
    text = f"""📊 <b>Статистика {period_name}</b>

🎯 <b>Всего лидов:</b> {total_leads}
📞 <b>Обработано:</b> {contacted_leads} ({conversion_rate:.1f}%)
✅ <b>Конвертировано:</b> {converted_leads}

━━━━━━━━━━━━━━━━━━━━

📁 <b>По проектам:</b>
"""
    
    if projects_stats:
        for name, count in projects_stats[:5]:
            text += f"• {name}: <b>{count}</b> лидов\n"
    else:
        text += "Нет данных\n"
    
    text += "\n💬 <b>Топ-5 чатов:</b>\n"
    
    if chats_stats:
        for title, count in chats_stats:
            title = title or 'Без названия'
            if len(title) > 25:
                title = title[:22] + '...'
            text += f"• {title}: <b>{count}</b>\n"
    else:
        text += "Нет данных\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_kb(user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'profile:leads')
async def show_recent_leads(callback: CallbackQuery, user: User):
    """Показать последние найденные лиды"""
    async with async_session_maker() as session:
        # Получаем последние 10 лидов
        result = await session.execute(
            select(LeadMatch)
            .where(LeadMatch.user_id == user.id)
            .order_by(LeadMatch.created_at.desc())
            .limit(10)
        )
        leads = result.scalars().all()
    
    if not leads:
        await callback.answer('У вас пока нет найденных лидов', show_alert=True)
        return
    
    text = "🎯 <b>Последние лиды</b>\n\n"
    
    for lead in leads:
        # Обрезаем текст сообщения
        msg_text = lead.message_text[:100] + '...' if len(lead.message_text) > 100 else lead.message_text
        
        # Парсим ключевые слова
        try:
            keywords = json.loads(lead.matched_keywords)
            keywords_str = ', '.join(keywords[:3])
        except:
            keywords_str = 'N/A'
        
        status = '✅' if lead.is_contacted else '⏳'
        
        text += f"""{status} <b>{lead.created_at.strftime('%d.%m %H:%M')}</b>
🔑 {keywords_str}
💬 {msg_text}
🔗 <a href="{lead.message_link}">Перейти</a>

"""
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_kb(user.language),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data == 'profile:settings')
async def show_settings(callback: CallbackQuery, user: User):
    """Показать настройки пользователя"""
    text = f"""⚙️ <b>Настройки</b>

🌐 <b>Язык:</b> {'Русский 🇷🇺' if user.language == 'ru' else 'English 🇬🇧'}

🔔 <b>Уведомления:</b> Включены

🔗 <b>Интеграции:</b>
• AmoCRM: {'✅ Подключен' if hasattr(user, 'amocrm_integration') and user.amocrm_integration else '❌ Не подключен'}

💡 Для настройки интеграций используйте меню ниже."""
    
    from bot.keyboards import settings_menu_kb
    
    await callback.message.edit_text(
        text,
        reply_markup=settings_menu_kb(user.language),
        parse_mode='HTML'
    )
    await callback.answer()

