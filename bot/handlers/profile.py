"""Обработчики для личного кабинета и статистики пользователя"""
import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, update

from database.database import async_session_maker
from database.models import User, Project, LeadMatch, Chat, SubscriptionPlan
from database.crud import ProjectCRUD
from bot.keyboards import profile_menu_kb, stats_period_kb, back_to_main_kb, settings_menu_kb
from bot.texts import get_text
from utils.subscription_helpers import get_subscription_limits

router = Router()


@router.callback_query(F.data == 'menu:profile')
async def show_profile(callback: CallbackQuery, user: User):
    """Показать личный кабинет пользователя"""
    lang = user.language
    
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
    
    # Названия тарифов
    plan_name = get_text(f'plan_{user.subscription_plan.name.lower()}', lang)
    
    text = f"""{get_text('profile_title', lang)}

{get_text('profile_id', lang)} <code>{user.telegram_id}</code>
{get_text('profile_username', lang)} @{user.username or ('не указан' if lang == 'ru' else 'not set')}
{get_text('profile_registered', lang)} {user.created_at.strftime('%d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━

{get_text('profile_plan', lang)} {plan_name}"""
    
    if user.subscription_plan != SubscriptionPlan.FREE:
        if user.subscription_end_date:
            days_left = (user.subscription_end_date - datetime.utcnow()).days
            text += f"\n{get_text('profile_expires', lang)} {get_text('days_left', lang).format(days_left)}"
            text += f"\n{get_text('profile_expires_date', lang)} {user.subscription_end_date.strftime('%d.%m.%Y')}"
    
    text += f"""

━━━━━━━━━━━━━━━━━━━━

{get_text('profile_stats', lang)}

{get_text('profile_projects', lang)} {projects_count}
{get_text('profile_chats', lang)} {chats_count}/{limits['max_chats'] if limits['max_chats'] > 0 else '∞'}

{get_text('profile_leads', lang)}
   • {get_text('profile_today', lang)}: <b>{today_leads}</b>
   • {get_text('profile_week', lang)}: <b>{week_leads}</b>
   • {get_text('profile_total', lang)}: <b>{total_leads}</b>
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=profile_menu_kb(lang),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'profile:stats')
async def show_detailed_stats(callback: CallbackQuery, user: User):
    """Показать детальную статистику"""
    lang = user.language
    text = f"""{get_text('stats_title', lang)}

{get_text('stats_choose_period', lang)}"""
    
    await callback.message.edit_text(
        text,
        reply_markup=stats_period_kb(lang),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('stats:period:'))
async def show_stats_by_period(callback: CallbackQuery, user: User):
    """Показать статистику за период"""
    lang = user.language
    period = callback.data.split(':')[2]
    
    # Определяем даты периода
    now = datetime.utcnow()
    period_names = {
        'today': get_text('profile_today', lang).lower(),
        'week': get_text('profile_week', lang).lower(),
        'month': get_text('stats_month', lang).lower().replace('🗓 ', ''),
        'all': get_text('stats_all_time', lang).lower().replace('📊 ', '')
    }
    
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
    else:  # all
        start_date = datetime(2020, 1, 1)
    
    period_name = period_names.get(period, '')
    
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
    
    text = f"""📊 <b>{get_text('stats_title', lang).replace('📊 <b>', '').replace('</b>', '')} {period_name}</b>

{get_text('stats_total_leads', lang)} {total_leads}
{get_text('stats_processed', lang)} {contacted_leads} ({conversion_rate:.1f}%)
{get_text('stats_converted', lang)} {converted_leads}

━━━━━━━━━━━━━━━━━━━━

{get_text('stats_by_projects', lang)}
"""
    
    if projects_stats:
        for name, count in projects_stats[:5]:
            text += f"• {name}: <b>{count}</b> {get_text('stats_leads_suffix', lang)}\n"
    else:
        text += get_text('stats_no_data', lang) + "\n"
    
    text += f"\n{get_text('stats_top_chats', lang)}\n"
    
    if chats_stats:
        for title, count in chats_stats:
            title = title or ('Без названия' if lang == 'ru' else 'Untitled')
            if len(title) > 25:
                title = title[:22] + '...'
            text += f"• {title}: <b>{count}</b>\n"
    else:
        text += get_text('stats_no_data', lang) + "\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_kb(lang),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'profile:leads')
async def show_recent_leads(callback: CallbackQuery, user: User):
    """Показать последние найденные лиды"""
    lang = user.language
    
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
        await callback.answer(get_text('leads_none', lang), show_alert=True)
        return
    
    text = f"{get_text('leads_title', lang)}\n\n"
    
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
🔗 <a href="{lead.message_link}">{get_text('leads_go_to', lang)}</a>

"""
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_kb(lang),
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    await callback.answer()


@router.callback_query(F.data == 'profile:settings')
async def show_settings(callback: CallbackQuery, user: User):
    """Показать настройки пользователя"""
    lang = user.language
    
    # Проверяем интеграцию AmoCRM
    async with async_session_maker() as session:
        from database.crud import AmoCRMCRUD
        amocrm = await AmoCRMCRUD.get_by_user(session, user.id)
    
    amocrm_status = get_text('amocrm_connected', lang) if amocrm and amocrm.is_active else get_text('amocrm_disconnected', lang)
    lang_display = get_text('lang_russian', lang) if user.language == 'ru' else get_text('lang_english', lang)
    
    text = f"""{get_text('settings_title', lang)}

{get_text('settings_language', lang)} {lang_display}

{get_text('settings_notifications', lang)} {get_text('notifications_enabled', lang)}

{get_text('settings_integrations', lang)}
• AmoCRM: {amocrm_status}

{get_text('settings_tip', lang)}"""
    
    await callback.message.edit_text(
        text,
        reply_markup=settings_menu_kb(lang),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'settings:language')
async def show_language_settings(callback: CallbackQuery, user: User):
    """Показать выбор языка"""
    lang = user.language
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    
    ru_check = '✅' if user.language == 'ru' else ''
    en_check = '✅' if user.language == 'en' else ''
    
    builder.button(text=f'{ru_check} 🇷🇺 Русский', callback_data='lang:ru')
    builder.button(text=f'{en_check} 🇬🇧 English', callback_data='lang:en')
    builder.button(text=get_text('btn_back', lang), callback_data='profile:settings')
    builder.adjust(2, 1)
    
    text = get_text('choose_language_title', lang)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('lang:'))
async def change_language(callback: CallbackQuery, user: User):
    """Сменить язык"""
    new_lang = callback.data.split(':')[1]
    
    async with async_session_maker() as session:
        from database.models import User as UserModel
        
        await session.execute(
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(language=new_lang)
        )
        await session.commit()
    
    # Обновляем язык в объекте user для текущего запроса
    user.language = new_lang
    
    lang_name = get_text('lang_russian', new_lang) if new_lang == 'ru' else get_text('lang_english', new_lang)
    await callback.answer(get_text('language_changed', new_lang).format(lang_name))
    
    # Возвращаемся в настройки
    await show_settings(callback, user)


@router.callback_query(F.data == 'settings:notifications')
async def show_notifications_settings(callback: CallbackQuery, user: User):
    """Показать настройки уведомлений"""
    lang = user.language
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text('btn_notif_all', lang), callback_data='notif:all')
    builder.button(text=get_text('btn_notif_important', lang), callback_data='notif:important')
    builder.button(text=get_text('btn_notif_off', lang), callback_data='notif:off')
    builder.button(text=get_text('btn_back', lang), callback_data='profile:settings')
    builder.adjust(1)
    
    text = f"""{get_text('notifications_title', lang)}

{get_text('notifications_current', lang)} <b>{get_text('notifications_all', lang)}</b>

{get_text('notifications_desc', lang)}

⚠️ {'Функция в разработке' if lang == 'ru' else 'Feature in development'}"""
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('notif:'))
async def change_notifications(callback: CallbackQuery, user: User):
    """Сменить режим уведомлений (заглушка)"""
    lang = user.language
    mode = callback.data.split(':')[1]
    
    modes = {
        'all': get_text('notifications_all', lang),
        'important': get_text('notifications_important', lang),
        'off': get_text('notifications_off', lang)
    }
    
    # TODO: Сохранить настройку в БД (нужно добавить поле в модель User)
    msg = get_text('notif_mode_set', lang).format(modes.get(mode, '')) + (' Функция в разработке.' if lang == 'ru' else ' Feature in development.')
    await callback.answer(msg, show_alert=True)

