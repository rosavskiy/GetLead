"""Обработчики для работы с фильтрами (логические операторы AND/OR)"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.database import async_session_maker
from database.crud import ProjectCRUD
from database.models import User, Filter
from bot.states import FilterStates
from bot.texts import get_text
from bot.keyboards import filters_menu_kb, cancel_kb, main_menu_kb, back_to_main_kb
from sqlalchemy import select, delete

router = Router()


@router.callback_query(F.data == 'menu:filters')
async def show_filters_menu(callback: CallbackQuery, user: User):
    """Показать меню фильтров"""
    lang = user.language
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            msg = '❌ Сначала создайте проект!' if lang == 'ru' else '❌ Create a project first!'
            await callback.answer(msg, show_alert=True)
            return
        
        # Получаем фильтры проекта
        result = await session.execute(
            select(Filter).where(Filter.project_id == active_project.id)
        )
        filters = list(result.scalars().all())
    
    project_label = 'Проект' if lang == 'ru' else 'Project'
    your_filters = 'Ваши фильтры' if lang == 'ru' else 'Your filters'
    no_filters = '📭 У вас пока нет фильтров' if lang == 'ru' else '📭 You don\'t have any filters yet'
    more_text = 'и ещё' if lang == 'ru' else 'and more'
    
    text = f"""{get_text('filters_title', lang)}

📁 {project_label}: <b>{active_project.name}</b>

{get_text('filters_desc', lang)}
"""
    
    if filters:
        text += f"\n\n🔧 <b>{your_filters} ({len(filters)}):</b>\n"
        for f in filters[:10]:
            text += f"• <code>{f.logic_string}</code>\n"
        if len(filters) > 10:
            text += f"\n... {more_text} {len(filters) - 10}"
    else:
        text += f"\n\n{no_filters}"
    
    await callback.message.edit_text(
        text,
        reply_markup=filters_menu_kb(bool(filters), lang),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'filters:add')
async def start_add_filter(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать добавление фильтра"""
    lang = user.language
    await state.set_state(FilterStates.waiting_for_filter)
    
    if lang == 'ru':
        text = """🔧 <b>Добавление фильтра</b>

Введите логический фильтр:

<b>Операторы:</b>
• <code>+</code> — И (оба слова обязательны)
• <code>|</code> — ИЛИ (любое из слов)

<b>Примеры:</b>
• <code>ищу + программиста</code>
• <code>react | vue | angular</code>
• <code>срочно + backend | frontend</code>"""
    else:
        text = """🔧 <b>Add Filter</b>

Enter a logical filter:

<b>Operators:</b>
• <code>+</code> — AND (both words required)
• <code>|</code> — OR (any of the words)

<b>Examples:</b>
• <code>looking + developer</code>
• <code>react | vue | angular</code>
• <code>urgent + backend | frontend</code>"""
    
    await callback.message.answer(text, reply_markup=cancel_kb(lang), parse_mode='HTML')
    await callback.answer()


@router.message(FilterStates.waiting_for_filter)
async def process_filter(message: Message, user: User, state: FSMContext):
    """Обработка добавления фильтра"""
    lang = user.language
    cancel_text = get_text('btn_cancel', lang)
    
    if message.text == cancel_text or message.text == '❌ Отмена' or message.text == '❌ Cancel':
        await state.clear()
        await message.answer(
            get_text('main_menu', lang),
            reply_markup=main_menu_kb(lang)
        )
        return
    
    filter_string = message.text.strip()
    
    # Проверяем что фильтр содержит операторы
    if '+' not in filter_string and '|' not in filter_string:
        if lang == 'ru':
            err_msg = '❌ Фильтр должен содержать операторы + или |\n\nПример: <code>ищу + разработчика</code>'
        else:
            err_msg = '❌ Filter must contain + or | operators\n\nExample: <code>looking + developer</code>'
        await message.answer(err_msg, parse_mode='HTML')
        return
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            err = '❌ Проект не найден!' if lang == 'ru' else '❌ Project not found!'
            await message.answer(err)
            await state.clear()
            return
        
        # Создаём фильтр
        new_filter = Filter(project_id=active_project.id, logic_string=filter_string)
        session.add(new_filter)
        await session.commit()
    
    await state.clear()
    
    added_text = 'Фильтр добавлен' if lang == 'ru' else 'Filter added'
    text = f'✅ {added_text}: <code>{filter_string}</code>'
    await message.answer(text, reply_markup=main_menu_kb(lang), parse_mode='HTML')


@router.callback_query(F.data == 'filters:list')
async def list_filters(callback: CallbackQuery, user: User):
    """Показать все фильтры"""
    lang = user.language
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            err = '❌ Проект не найден!' if lang == 'ru' else '❌ Project not found!'
            await callback.answer(err, show_alert=True)
            return
        
        result = await session.execute(
            select(Filter).where(Filter.project_id == active_project.id)
        )
        filters = list(result.scalars().all())
    
    if not filters:
        msg = 'У вас пока нет фильтров' if lang == 'ru' else 'You don\'t have any filters yet'
        await callback.answer(msg, show_alert=True)
        return
    
    project_label = 'Проект' if lang == 'ru' else 'Project'
    all_filters = 'Все фильтры' if lang == 'ru' else 'All filters'
    
    text = f'📁 {project_label}: <b>{active_project.name}</b>\n\n🔧 <b>{all_filters}:</b>\n\n'
    
    for i, f in enumerate(filters, 1):
        text += f'{i}. <code>{f.logic_string}</code>\n'
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(lang), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'filters:clear')
async def clear_filters(callback: CallbackQuery, user: User):
    """Удалить все фильтры"""
    lang = user.language
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            err = '❌ Проект не найден!' if lang == 'ru' else '❌ Project not found!'
            await callback.answer(err, show_alert=True)
            return
        
        await session.execute(
            delete(Filter).where(Filter.project_id == active_project.id)
        )
        await session.commit()
    
    msg = '🗑 Все фильтры удалены' if lang == 'ru' else '🗑 All filters cleared'
    await callback.answer(msg)
    
    # Обновляем меню
    await show_filters_menu(callback, user)
