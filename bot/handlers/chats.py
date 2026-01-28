"""Обработчики для работы с чатами"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import re

from database.database import async_session_maker
from database.crud import ProjectCRUD, ChatCRUD
from database.models import User
from bot.states import ChatStates
from bot.texts import get_text
from bot.keyboards import chats_menu_kb, cancel_kb, main_menu_kb, chats_list_kb, confirm_delete_chat_kb

logger = logging.getLogger(__name__)
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
    logger.info(f"📩 Добавление чата: {link} от пользователя {user.id}")
    
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
        logger.info(f"📋 existing_chat: {existing_chat}, assigned_userbot: {existing_chat.assigned_userbot if existing_chat else 'N/A'}, is_joined: {existing_chat.is_joined if existing_chat else 'N/A'}")
        
        if existing_chat:
            # Чат уже существует, привязываем к проекту
            await ChatCRUD.assign_to_project(session, existing_chat.id, active_project.id)
            
            # Сбрасываем is_joined если чат не вступлен
            if not existing_chat.is_joined:
                from sqlalchemy import update
                await session.execute(
                    update(Chat).where(Chat.id == existing_chat.id).values(is_joined=False)
                )
                await session.commit()
                logger.info(f"🔄 Сброшен is_joined для чата {link}")
            
            # Проверяем назначен ли юзербот - если нет, назначаем
            if not existing_chat.assigned_userbot:
                from userbot.load_balancer import UserbotLoadBalancer
                await UserbotLoadBalancer.assign_userbot_for_chat(session, existing_chat.id)
                logger.info(f"✅ Назначен юзербот для существующего чата {link}")
            else:
                logger.info(f"ℹ️ Юзербот уже назначен: {existing_chat.assigned_userbot}")
            
            text = get_text('chat_exists', user.language)
        else:
            # Создаем новый чат
            logger.info(f"🆕 Создаём новый чат: {link}")
            chat = await ChatCRUD.add(session, link)
            await ChatCRUD.assign_to_project(session, chat.id, active_project.id)
            text = get_text('chat_added', user.language, chat_link=link)
        
        # Всегда уведомляем юзербота о новом/обновленном чате через Redis
        try:
            import redis.asyncio as redis
            from config import settings
            redis_client = redis.from_url(settings.REDIS_URL)
            await redis_client.publish('userbot:reload_chats', 'reload')
            await redis_client.close()
            logger.info(f"📡 Отправлен сигнал reload_chats в Redis")
        except Exception as e:
            logger.warning(f"❌ Не удалось уведомить юзербота: {e}")
    
    await state.clear()
    await message.answer(text, reply_markup=main_menu_kb(user.language))


@router.callback_query(F.data == 'chats:list')
async def list_chats(callback: CallbackQuery, user: User):
    """Показать список всех чатов с кнопками удаления"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
    
    if not active_project.chats:
        no_chats = 'У вас пока нет добавленных чатов' if user.language == 'ru' else 'You have no chats yet'
        await callback.answer(no_chats, show_alert=True)
        return
    
    if user.language == 'ru':
        text = f'📁 Проект: <b>{active_project.name}</b>\n\n'
        text += f'💬 <b>Ваши чаты ({len(active_project.chats)}):</b>\n\n'
        text += '🗑 Нажмите на чат чтобы удалить его:'
    else:
        text = f'📁 Project: <b>{active_project.name}</b>\n\n'
        text += f'💬 <b>Your chats ({len(active_project.chats)}):</b>\n\n'
        text += '🗑 Click on a chat to delete it:'
    
    await callback.message.edit_text(
        text, 
        parse_mode='HTML',
        reply_markup=chats_list_kb(active_project.chats, user.language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('chats:delete:'))
async def ask_delete_chat(callback: CallbackQuery, user: User):
    """Запросить подтверждение удаления чата"""
    chat_id = int(callback.data.split(':')[2])
    
    async with async_session_maker() as session:
        chat = await ChatCRUD.get_by_id(session, chat_id)
        
        if not chat:
            await callback.answer('❌ Чат не найден!', show_alert=True)
            return
    
    title = chat.title or chat.telegram_link
    
    if user.language == 'ru':
        text = f'🗑 <b>Удалить чат?</b>\n\n{title}\n\nЭто действие нельзя отменить.'
    else:
        text = f'🗑 <b>Delete chat?</b>\n\n{title}\n\nThis action cannot be undone.'
    
    await callback.message.edit_text(
        text,
        parse_mode='HTML',
        reply_markup=confirm_delete_chat_kb(chat_id, user.language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith('chats:confirm_delete:'))
async def confirm_delete_chat(callback: CallbackQuery, user: User):
    """Подтвердить удаление чата"""
    chat_id = int(callback.data.split(':')[2])
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
        
        # Удаляем связь чата с проектом
        success = await ChatCRUD.remove_from_project(session, chat_id, active_project.id)
        
        if success:
            if user.language == 'ru':
                await callback.answer('✅ Чат удалён из мониторинга!', show_alert=True)
            else:
                await callback.answer('✅ Chat removed from monitoring!', show_alert=True)
        else:
            await callback.answer('❌ Ошибка при удалении', show_alert=True)
    
    # Возвращаемся к списку чатов
    await list_chats(callback, user)


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
    """Обработка AI подбора чатов"""
    if message.text == '❌ Отмена' or message.text == '❌ Cancel':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    niche = message.text.strip()
    lang = user.language
    
    # Показываем сообщение о генерации
    searching_text = '🔍 Ищу реальные чаты через Telegram...' if lang == 'ru' else '🔍 Searching real chats via Telegram...'
    status_msg = await message.answer(searching_text)
    
    try:
        from utils.ai_helpers import suggest_chats, format_subscribers
        chat_suggestions = await suggest_chats(niche)
        
        if not chat_suggestions:
            if lang == 'ru':
                err_text = ('❌ Не удалось найти чаты по запросу.\n\n'
                           '💡 <b>Попробуйте:</b>\n'
                           '• Использовать более общие слова\n'
                           '• Ввести тему на русском и английском\n'
                           '• Поискать чаты вручную в Telegram')
            else:
                err_text = ('❌ Could not find chats for this query.\n\n'
                           '💡 <b>Try:</b>\n'
                           '• Use more general keywords\n'
                           '• Search in both Russian and English\n'
                           '• Search manually in Telegram')
            await status_msg.edit_text(err_text, parse_mode='HTML')
            await state.clear()
            return
        
        await state.clear()
        
        # Показываем результат
        if lang == 'ru':
            text = f'💬 <b>Чаты по запросу "{niche}"</b>\n\n'
        else:
            text = f'💬 <b>Chats for "{niche}"</b>\n\n'
        
        # Все результаты - это чаты (каналы отфильтрованы)
        for chat in chat_suggestions[:15]:
            title = chat.get('title', chat['username'])
            subs = chat.get('subscribers')
            if subs:
                subs_str = f" • <b>{format_subscribers(subs)}</b>"
            else:
                subs_str = ""
            
            # Все результаты - чаты
            type_emoji = '👥 '
            
            text += f"• {type_emoji}<a href=\"https://{chat['link']}\">{title}</a>{subs_str}\n"
        
        text += '\n'
        
        # Инструкция
        if lang == 'ru':
            text += '━━━━━━━━━━━━━━━━━━━━━\n'
            text += '💡 <b>Как добавить чат:</b>\n'
            text += '1. Нажмите на ссылку чата\n'
            text += '2. Убедитесь что чат активный\n'
            text += '3. Скопируйте username или ссылку\n'
            text += '4. Добавьте через "➕ Добавить чат"'
        else:
            text += '━━━━━━━━━━━━━━━━━━━━━\n'
            text += '💡 <b>How to add a chat:</b>\n'
            text += '1. Click on the chat link\n'
            text += '2. Make sure the chat is active\n'
            text += '3. Copy the link\n'
            text += '4. Add via "➕ Add Chat"'
        
        await status_msg.edit_text(text, parse_mode='HTML', disable_web_page_preview=True)
        await message.answer(
            'Вернуться в меню:' if lang == 'ru' else 'Return to menu:', 
            reply_markup=main_menu_kb(lang)
        )
        
    except ValueError as e:
        await status_msg.edit_text(f'❌ Ошибка: {str(e)}')
        await state.clear()
    except Exception as e:
        import logging
        logging.error(f"AI chats error: {e}", exc_info=True)
        err_text = '❌ Произошла ошибка при поиске чатов' if lang == 'ru' else '❌ Error while searching for chats'
        await status_msg.edit_text(err_text)
        await state.clear()
