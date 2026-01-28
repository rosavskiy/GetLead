"""Обработчики для работы с фильтрами (логические операторы AND/OR)"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.database import async_session_maker
from database.crud import ProjectCRUD
from database.models import User, Filter
from bot.states import FilterStates
from bot.texts import get_text
from bot.keyboards import filters_menu_kb, cancel_kb, main_menu_kb
from sqlalchemy import select, delete

router = Router()


@router.callback_query(F.data == 'menu:filters')
async def show_filters_menu(callback: CallbackQuery, user: User):
    """Показать меню фильтров"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Сначала создайте проект!', show_alert=True)
            return
        
        # Получаем фильтры проекта
        result = await session.execute(
            select(Filter).where(Filter.project_id == active_project.id)
        )
        filters = list(result.scalars().all())
    
    text = f"""🔧 <b>Логические фильтры</b>

📁 Проект: <b>{active_project.name}</b>

Фильтры позволяют создавать сложные условия поиска:
• <code>+</code> (И) — оба слова должны быть в тексте
• <code>|</code> (ИЛИ) — хотя бы одно слово

<b>Примеры:</b>
• <code>ищу + разработчика</code> — оба слова
• <code>python | javascript</code> — любое из слов
• <code>срочно + дизайн | верстка</code> — комбинация
"""
    
    if filters:
        text += f"\n\n🔧 <b>Ваши фильтры ({len(filters)}):</b>\n"
        for f in filters[:10]:
            text += f"• <code>{f.logic_string}</code>\n"
        if len(filters) > 10:
            text += f"\n... и ещё {len(filters) - 10}"
    else:
        text += "\n\n📭 У вас пока нет фильтров"
    
    await callback.message.edit_text(
        text,
        reply_markup=filters_menu_kb(bool(filters), user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'filters:add')
async def start_add_filter(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать добавление фильтра"""
    await state.set_state(FilterStates.waiting_for_filter)
    
    text = """🔧 <b>Добавление фильтра</b>

Введите логический фильтр:

<b>Операторы:</b>
• <code>+</code> — И (оба слова обязательны)
• <code>|</code> — ИЛИ (любое из слов)

<b>Примеры:</b>
• <code>ищу + программиста</code>
• <code>react | vue | angular</code>
• <code>срочно + backend | frontend</code>"""
    
    await callback.message.answer(text, reply_markup=cancel_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.message(FilterStates.waiting_for_filter)
async def process_filter(message: Message, user: User, state: FSMContext):
    """Обработка добавления фильтра"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    filter_string = message.text.strip()
    
    # Проверяем что фильтр содержит операторы
    if '+' not in filter_string and '|' not in filter_string:
        await message.answer(
            '❌ Фильтр должен содержать операторы + или |\n\n'
            'Пример: <code>ищу + разработчика</code>',
            parse_mode='HTML'
        )
        return
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await message.answer('❌ Проект не найден!')
            await state.clear()
            return
        
        # Создаём фильтр
        new_filter = Filter(project_id=active_project.id, logic_string=filter_string)
        session.add(new_filter)
        await session.commit()
    
    await state.clear()
    
    text = f'✅ Фильтр добавлен: <code>{filter_string}</code>'
    await message.answer(text, reply_markup=main_menu_kb(user.language), parse_mode='HTML')


@router.callback_query(F.data == 'filters:list')
async def list_filters(callback: CallbackQuery, user: User):
    """Показать все фильтры"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
        
        result = await session.execute(
            select(Filter).where(Filter.project_id == active_project.id)
        )
        filters = list(result.scalars().all())
    
    if not filters:
        await callback.answer('У вас пока нет фильтров', show_alert=True)
        return
    
    text = f'📁 Проект: <b>{active_project.name}</b>\n\n🔧 <b>Все фильтры:</b>\n\n'
    
    for i, f in enumerate(filters, 1):
        text += f'{i}. <code>{f.logic_string}</code>\n'
    
    from bot.keyboards import back_to_main_kb
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'filters:clear')
async def clear_filters(callback: CallbackQuery, user: User):
    """Удалить все фильтры"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
        
        await session.execute(
            delete(Filter).where(Filter.project_id == active_project.id)
        )
        await session.commit()
    
    await callback.answer('🗑 Все фильтры удалены')
    
    # Обновляем меню
    await show_filters_menu(callback, user)
