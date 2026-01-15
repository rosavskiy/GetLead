"""Основные обработчики команд"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.models import User
from bot.texts import get_text
from bot.keyboards import main_menu_kb, back_to_main_kb

router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message, user: User, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    text = get_text('start', user.language)
    await message.answer(text, reply_markup=main_menu_kb(user.language), parse_mode='HTML')


@router.callback_query(F.data == 'menu:main')
async def show_main_menu(callback: CallbackQuery, user: User, state: FSMContext):
    """Показать главное меню"""
    await state.clear()
    
    text = get_text('main_menu', user.language)
    await callback.message.edit_text(text, reply_markup=main_menu_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'menu:help')
async def show_help(callback: CallbackQuery, user: User):
    """Показать помощь"""
    text = """📖 <b>Как пользоваться ботом:</b>

1️⃣ <b>Создайте проект</b>
   Проект — это набор настроек для одной ниши (например, "Недвижимость")

2️⃣ <b>Добавьте ключевые слова</b>
   Укажите слова, по которым нужно искать сообщения

3️⃣ <b>Добавьте чаты для мониторинга</b>
   Укажите ссылки на группы, которые нужно отслеживать

4️⃣ <b>Получайте уведомления</b>
   Бот будет присылать сообщения, в которых нашел ваши ключевые слова

🤖 <b>AI-функции:</b>
Используйте кнопку "AI подбор" для автоматического подбора:
- Ключевых слов по нише
- Исключающих слов
- Релевантных чатов

🎯 <b>Фильтры:</b>
+ (И) — оба слова должны быть в тексте
| (ИЛИ) — хотя бы одно слово

📹 Видео-инструкция: /video"""
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'menu:support')
async def show_support(callback: CallbackQuery, user: User):
    """Показать контакты поддержки"""
    text = """💬 <b>Служба поддержки</b>

По всем вопросам обращайтесь:
📧 Email: support@getlead.bot
💬 Telegram: @getlead_support

Мы ответим в течение 24 часов!"""
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()
