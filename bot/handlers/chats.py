"""Обработчики для работы с чатами"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import re

from database.database import async_session_maker
from database.crud import ProjectCRUD, ChatCRUD
from database.models import User
from bot.states import ChatStates
from bot.texts import get_text
from bot.keyboards import chats_menu_kb, cancel_kb, main_menu_kb

router = Router()


@router.callback_query(F.data == 'menu:chats')
async def show_chats_menu(callback: CallbackQuery, user: User):
    """Показать меню чатов"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Сначала создайте проект!', show_alert=True)
            return
    
    text = get_text('chats_menu', user.language)
    text += f'\n\n📁 Проект: <b>{active_project.name}</b>'
    
    if active_project.chats:
        text += f'\n\n💬 <b>Ваши чаты ({len(active_project.chats)}):</b>\n'
        for chat in active_project.chats[:10]:
            status = '✅' if chat.is_joined else '⏳'
            title = chat.title or chat.telegram_link
            text += f'{status} {title}\n'
        if len(active_project.chats) > 10:
            text += f'\n... и еще {len(active_project.chats) - 10}'
    
    await callback.message.edit_text(
        text,
        reply_markup=chats_menu_kb(user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'chats:add')
async def start_add_chat(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать добавление чата"""
    await state.set_state(ChatStates.waiting_for_link)
    
    text = get_text('enter_chat_link', user.language)
    text += '\n\nПример: https://t.me/example_chat'
    await callback.message.answer(text, reply_markup=cancel_kb(user.language))
    await callback.answer()


@router.message(ChatStates.waiting_for_link)
async def process_chat_link(message: Message, user: User, state: FSMContext):
    """Обработка ссылки на чат"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    # Валидация ссылки
    link = message.text.strip()
    
    # Проверяем формат ссылки
    if not re.match(r'https?://t\.me/[\w\d_]+', link):
        await message.answer('❌ Неверный формат ссылки. Пример: https://t.me/example_chat')
        return
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await message.answer('❌ Проект не найден!')
            return
        
        # Проверяем, есть ли уже такой чат
        existing_chat = await ChatCRUD.get_by_link(session, link)
        
        if existing_chat:
            # Чат уже существует, просто привязываем к проекту
            await ChatCRUD.assign_to_project(session, existing_chat.id, active_project.id)
            text = get_text('chat_exists', user.language)
        else:
            # Создаем новый чат
            chat = await ChatCRUD.add(session, link)
            await ChatCRUD.assign_to_project(session, chat.id, active_project.id)
            text = get_text('chat_added', user.language, chat_link=link)
            
            # TODO: Отправить задачу в юзербот на проверку и вступление в чат
    
    await state.clear()
    await message.answer(text, reply_markup=main_menu_kb(user.language))


@router.callback_query(F.data == 'chats:list')
async def list_chats(callback: CallbackQuery, user: User):
    """Показать список всех чатов"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
    
    if not active_project.chats:
        await callback.answer('У вас пока нет добавленных чатов', show_alert=True)
        return
    
    text = f'📁 Проект: <b>{active_project.name}</b>\n\n💬 <b>Все чаты:</b>\n\n'
    
    for i, chat in enumerate(active_project.chats, 1):
        status = '✅ Подключен' if chat.is_joined else '⏳ Ожидание'
        title = chat.title or 'Без названия'
        text += f'{i}. <b>{title}</b>\n'
        text += f'   {status}\n'
        text += f'   {chat.telegram_link}\n\n'
    
    await callback.message.answer(text, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'chats:packs')
async def show_packed_chats(callback: CallbackQuery, user: User):
    """Показать пакетные чаты"""
    text = """📦 <b>Пакетные подборки чатов</b>

🚀 <b>Фриланс РФ</b> (10 чатов)
Чаты для поиска заказов на фрилансе

💼 <b>IT Вакансии</b> (15 чатов)
Вакансии в IT-сфере

🏢 <b>Бизнес и стартапы</b> (12 чатов)
Чаты для предпринимателей

📢 Чтобы добавить пакет, напишите в поддержку: /support"""
    
    await callback.message.answer(text, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'chats:ai')
async def start_ai_chats(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать AI подбор чатов"""
    await state.set_state(ChatStates.waiting_for_ai_niche)
    
    text = '🤖 Введите вашу нишу для AI-подбора чатов:\n\nНапример: "Веб-разработка", "Маркетинг", "Дизайн"'
    await callback.message.answer(text, reply_markup=cancel_kb(user.language))
    await callback.answer()


@router.message(ChatStates.waiting_for_ai_niche)
async def process_ai_chats(message: Message, user: User, state: FSMContext):
    """Обработка AI подбора чатов (заглушка)"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    await state.clear()
    
    # TODO: Интеграция с OpenAI и поиском чатов
    text = '🤖 AI-подбор чатов будет доступен после интеграции с OpenAI'
    await message.answer(text, reply_markup=main_menu_kb(user.language))
