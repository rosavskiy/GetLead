"""Основные обработчики команд"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import update

from database.database import async_session_maker
from database.models import User
from bot.texts import get_text
from bot.keyboards import main_menu_kb, back_to_main_kb, language_selection_kb

router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message, user: User, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    # Если пользователь новый (язык по умолчанию), показываем выбор языка
    # Проверяем, был ли пользователь создан только что (нет проектов и язык ru)
    async with async_session_maker() as session:
        from database.models import Project
        from sqlalchemy import select, func
        
        projects_count = await session.execute(
            select(func.count(Project.id)).where(Project.user_id == user.id)
        )
        projects_count = projects_count.scalar() or 0
    
    # Если новый пользователь - спрашиваем язык
    if projects_count == 0 and user.language == 'ru':
        text = get_text('choose_language', 'ru')
        await message.answer(text, reply_markup=language_selection_kb(), parse_mode='HTML')
        return
    
    text = get_text('start', user.language)
    await message.answer(text, reply_markup=main_menu_kb(user.language), parse_mode='HTML')


@router.callback_query(F.data.startswith('set_lang:'))
async def set_initial_language(callback: CallbackQuery, user: User):
    """Установить язык при первом запуске"""
    new_lang = callback.data.split(':')[1]
    
    async with async_session_maker() as session:
        await session.execute(
            update(User)
            .where(User.id == user.id)
            .values(language=new_lang)
        )
        await session.commit()
    
    # Обновляем язык
    user.language = new_lang
    
    lang_name = get_text('lang_russian', new_lang) if new_lang == 'ru' else get_text('lang_english', new_lang)
    await callback.answer(get_text('language_changed', new_lang).format(lang_name))
    
    # Показываем приветственное сообщение
    text = get_text('start', new_lang)
    await callback.message.edit_text(text, reply_markup=main_menu_kb(new_lang), parse_mode='HTML')


@router.callback_query(F.data == 'menu:main')
async def show_main_menu(callback: CallbackQuery, user: User, state: FSMContext):
    """Показать главное меню"""
    await state.clear()
    
    text = get_text('main_menu', user.language)
    await callback.message.edit_text(text, reply_markup=main_menu_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.message(Command('menu'))
async def cmd_menu(message: Message, user: User, state: FSMContext):
    """Обработчик команды /menu"""
    await state.clear()
    text = get_text('main_menu', user.language)
    await message.answer(text, reply_markup=main_menu_kb(user.language), parse_mode='HTML')


@router.message(Command('profile'))
async def cmd_profile(message: Message, user: User, state: FSMContext):
    """Обработчик команды /profile"""
    await state.clear()
    # Импортируем здесь чтобы избежать циклических импортов
    from bot.handlers.profile import show_profile_menu_msg
    await show_profile_menu_msg(message, user)


@router.message(Command('projects'))
async def cmd_projects(message: Message, user: User, state: FSMContext):
    """Обработчик команды /projects"""
    await state.clear()
    from bot.handlers.projects import show_projects_menu_msg
    await show_projects_menu_msg(message, user)


@router.message(Command('stats'))
async def cmd_stats(message: Message, user: User, state: FSMContext):
    """Обработчик команды /stats"""
    await state.clear()
    from bot.handlers.profile import show_stats_msg
    await show_stats_msg(message, user)


@router.message(Command('help'))
async def cmd_help(message: Message, user: User):
    """Обработчик команды /help"""
    text = get_text('help_title', user.language) + get_text('help_text', user.language)
    await message.answer(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')


@router.message(Command('language'))
async def cmd_language(message: Message, user: User):
    """Обработчик команды /language"""
    text = get_text('choose_language', user.language)
    await message.answer(text, reply_markup=language_selection_kb(), parse_mode='HTML')


@router.callback_query(F.data == 'menu:help')
async def show_help(callback: CallbackQuery, user: User):
    """Показать помощь"""
    text = get_text('help_title', user.language) + get_text('help_text', user.language)
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'menu:support')
async def show_support(callback: CallbackQuery, user: User):
    """Показать контакты поддержки"""
    text = get_text('support_title', user.language) + '\n\n' + get_text('support_text', user.language)
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()
