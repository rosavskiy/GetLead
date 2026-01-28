"""Обработчики для работы с ключевыми словами"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.database import async_session_maker
from database.crud import ProjectCRUD, KeywordCRUD
from database.models import User, KeywordType
from bot.states import KeywordStates, ExcludeStates
from bot.texts import get_text
from bot.keyboards import keywords_menu_kb, exclude_menu_kb, cancel_kb, main_menu_kb, ai_keywords_selection_kb

logger = logging.getLogger(__name__)

router = Router()


# ============ КЛЮЧЕВЫЕ СЛОВА ============

@router.callback_query(F.data == 'menu:keywords')
async def show_keywords_menu(callback: CallbackQuery, user: User):
    """Показать меню ключевых слов"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Сначала создайте проект!', show_alert=True)
            return
        
        keywords = await KeywordCRUD.get_all(session, active_project.id, KeywordType.INCLUDE)
    
    text = get_text('keywords_menu', user.language)
    text += f'\n\n📁 Проект: <b>{active_project.name}</b>'
    
    if keywords:
        text += f'\n\n🔑 <b>Ключевые слова ({len(keywords)}):</b>\n'
        for kw in keywords[:10]:  # Показываем первые 10
            text += f'• {kw.text}\n'
        if len(keywords) > 10:
            text += f'\n... и еще {len(keywords) - 10}'
    
    await callback.message.edit_text(
        text,
        reply_markup=keywords_menu_kb(bool(keywords), user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'keywords:add')
async def start_add_keywords(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать добавление ключевых слов"""
    await state.set_state(KeywordStates.waiting_for_keywords)
    
    text = get_text('enter_keywords', user.language)
    await callback.message.answer(text, reply_markup=cancel_kb(user.language))
    await callback.answer()


@router.message(KeywordStates.waiting_for_keywords)
async def process_keywords(message: Message, user: User, state: FSMContext):
    """Обработка ключевых слов"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    keywords = [kw.strip() for kw in message.text.split('\n') if kw.strip()]
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await message.answer('❌ Проект не найден!')
            return
        
        for keyword in keywords:
            await KeywordCRUD.add(session, active_project.id, keyword, KeywordType.INCLUDE)
    
    await state.clear()
    
    text = f'✅ Добавлено ключевых слов: {len(keywords)}'
    await message.answer(text, reply_markup=main_menu_kb(user.language))


@router.callback_query(F.data == 'keywords:list')
async def list_keywords(callback: CallbackQuery, user: User):
    """Показать список ключевых слов с возможностью удаления"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
        
        keywords = await KeywordCRUD.get_all(session, active_project.id, KeywordType.INCLUDE)
    
    if not keywords:
        no_kw = 'У вас пока нет ключевых слов' if user.language == 'ru' else 'You have no keywords yet'
        await callback.answer(no_kw, show_alert=True)
        return
    
    # Создаём inline клавиатуру со списком слов
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for kw in keywords:
        builder.button(
            text=f'❌ {kw.text}',
            callback_data=f'kw:del:{kw.id}'
        )
    
    # По 2 кнопки в ряд
    builder.adjust(2)
    
    # Кнопка назад
    builder.row()
    builder.button(text=get_text('btn_back', user.language), callback_data='menu:keywords')
    
    header = '🔑 <b>Ваши ключевые слова:</b>' if user.language == 'ru' else '🔑 <b>Your keywords:</b>'
    hint = '\n\n<i>Нажмите на слово чтобы удалить</i>' if user.language == 'ru' else '\n\n<i>Click to delete</i>'
    
    await callback.message.edit_text(
        f'{header}{hint}',
        reply_markup=builder.as_markup(),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('kw:del:'))
async def delete_single_keyword(callback: CallbackQuery, user: User):
    """Удалить одно ключевое слово"""
    keyword_id = int(callback.data.split(':')[2])
    
    async with async_session_maker() as session:
        # Получаем слово для показа в уведомлении
        keyword = await KeywordCRUD.get_by_id(session, keyword_id)
        if keyword:
            keyword_text = keyword.text
            await KeywordCRUD.delete(session, keyword_id)
            
            deleted = f'Удалено: {keyword_text}' if user.language == 'ru' else f'Deleted: {keyword_text}'
            await callback.answer(deleted)
        else:
            await callback.answer('❌ Слово не найдено', show_alert=True)
            return
    
    # Обновляем список
    await list_keywords(callback, user)


@router.callback_query(F.data == 'keywords:clear')
async def clear_keywords(callback: CallbackQuery, user: User):
    """Удалить все ключевые слова"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
        
        await KeywordCRUD.delete_all(session, active_project.id, KeywordType.INCLUDE)
    
    text = get_text('keywords_cleared', user.language)
    await callback.answer(text)
    
    # Обновляем меню
    await show_keywords_menu(callback, user)


@router.callback_query(F.data == 'keywords:ai')
async def start_ai_keywords(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать AI подбор ключевых слов"""
    await state.set_state(KeywordStates.waiting_for_ai_niche)
    
    if user.language == 'ru':
        text = '''🤖 <b>AI-подбор ключевых слов</b>

Опишите своими словами <b>кого вы ищете</b> — вашего идеального клиента.

<b>Примеры описаний:</b>
• "Ищу людей, которым нужно оформить визы в любые страны"
• "Мне нужны клиенты на разработку сайтов и лендингов"
• "Ищу тех, кто хочет заказать SMM продвижение"

💡 Чем подробнее описание — тем точнее будут ключевые слова!'''
    else:
        text = '''🤖 <b>AI Keyword Suggestion</b>

Describe in your own words <b>who you are looking for</b> — your ideal client.

<b>Example descriptions:</b>
• "I'm looking for people who need visa services"
• "I need clients for website development"
• "Looking for those who want SMM promotion"

💡 The more detailed description — the more accurate keywords!'''
    
    await callback.message.answer(text, parse_mode='HTML', reply_markup=cancel_kb(user.language))
    await callback.answer()


@router.message(KeywordStates.waiting_for_ai_niche)
async def process_ai_keywords(message: Message, user: User, state: FSMContext):
    """Обработка AI подбора ключевых слов — показываем предложения"""
    if message.text == '❌ Отмена' or message.text == '❌ Cancel':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    description = message.text.strip()
    lang = user.language
    
    # Показываем сообщение о генерации
    gen_text = '🤖 Анализирую описание и генерирую ключевые слова...' if lang == 'ru' else '🤖 Analyzing and generating keywords...'
    status_msg = await message.answer(gen_text)
    
    try:
        from utils.ai_helpers import generate_keywords
        keywords = await generate_keywords(description)
        
        if not keywords:
            err = '❌ Не удалось сгенерировать ключевые слова. Попробуйте описать подробнее.' if lang == 'ru' else '❌ Could not generate keywords. Try a more detailed description.'
            await status_msg.edit_text(err)
            await state.clear()
            return
        
        # Сохраняем предложенные ключевые слова в состояние
        await state.update_data(suggested_keywords=keywords)
        await state.set_state(KeywordStates.selecting_ai_keywords)
        
        # Показываем предложения с кнопками
        if lang == 'ru':
            text = f'''🤖 <b>AI предлагает {len(keywords)} ключевых слов:</b>

Нажмите на слово чтобы <b>добавить</b> его.
Или используйте кнопки ниже.

'''
        else:
            text = f'''🤖 <b>AI suggests {len(keywords)} keywords:</b>

Click on a word to <b>add</b> it.
Or use the buttons below.

'''
        
        # Показываем превью
        for i, kw in enumerate(keywords[:20], 1):
            text += f'{i}. {kw}\n'
        
        if len(keywords) > 20:
            more = len(keywords) - 20
            text += f'\n... и ещё {more}' if lang == 'ru' else f'\n... and {more} more'
        
        # Создаём клавиатуру с кнопками
        keyboard = ai_keywords_selection_kb(keywords[:20], lang)
        
        await status_msg.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        
    except ValueError as e:
        logger.error(f"AI keywords ValueError: {e}")
        await status_msg.edit_text(f'❌ Ошибка: {str(e)}')
        await state.clear()
    except Exception as e:
        logger.error(f"AI keywords error: {e}", exc_info=True)
        err = '❌ Произошла ошибка. Попробуйте позже.' if lang == 'ru' else '❌ An error occurred. Try again later.'
        await status_msg.edit_text(err)
        await state.clear()


@router.callback_query(F.data.startswith('ai_kw:add:'))
async def add_ai_keyword(callback: CallbackQuery, user: User, state: FSMContext):
    """Добавить одно ключевое слово из AI предложений"""
    keyword_index = int(callback.data.split(':')[2])
    
    data = await state.get_data()
    keywords = data.get('suggested_keywords', [])
    
    if keyword_index >= len(keywords):
        await callback.answer('❌ Ключевое слово не найдено', show_alert=True)
        return
    
    keyword = keywords[keyword_index]
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
        
        await KeywordCRUD.add(session, active_project.id, keyword, KeywordType.INCLUDE)
    
    # Отмечаем как добавленное
    added = data.get('added_keywords', set())
    added.add(keyword_index)
    await state.update_data(added_keywords=added)
    
    await callback.answer(f'✅ Добавлено: {keyword}')


@router.callback_query(F.data == 'ai_kw:add_all')
async def add_all_ai_keywords(callback: CallbackQuery, user: User, state: FSMContext):
    """Добавить все AI ключевые слова"""
    data = await state.get_data()
    keywords = data.get('suggested_keywords', [])
    
    if not keywords:
        await callback.answer('❌ Нет ключевых слов', show_alert=True)
        return
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
        
        added_count = 0
        for keyword in keywords:
            await KeywordCRUD.add(session, active_project.id, keyword, KeywordType.INCLUDE)
            added_count += 1
        
        # Инвалидируем кэш
        try:
            from utils.cache import CacheService
            await CacheService.invalidate_project_keywords(active_project.id)
        except Exception:
            pass
    
    await state.clear()
    
    lang = user.language
    text = f'✅ Добавлено {added_count} ключевых слов!' if lang == 'ru' else f'✅ Added {added_count} keywords!'
    await callback.message.edit_text(text)
    await callback.message.answer(
        get_text('main_menu', lang),
        reply_markup=main_menu_kb(lang)
    )
    await callback.answer()


@router.callback_query(F.data == 'ai_kw:done')
async def finish_ai_keywords(callback: CallbackQuery, user: User, state: FSMContext):
    """Завершить выбор AI ключевых слов"""
    data = await state.get_data()
    added = data.get('added_keywords', set())
    
    await state.clear()
    
    lang = user.language
    count = len(added)
    
    if count > 0:
        text = f'✅ Добавлено {count} ключевых слов!' if lang == 'ru' else f'✅ Added {count} keywords!'
    else:
        text = '👌 Ключевые слова не добавлены' if lang == 'ru' else '👌 No keywords added'
    
    await callback.message.edit_text(text)
    await callback.message.answer(
        get_text('main_menu', lang),
        reply_markup=main_menu_kb(lang)
    )
    await callback.answer()


# ============ ИСКЛЮЧАЮЩИЕ СЛОВА ============

@router.callback_query(F.data == 'menu:exclude')
async def show_exclude_menu(callback: CallbackQuery, user: User):
    """Показать меню исключающих слов"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Сначала создайте проект!', show_alert=True)
            return
        
        keywords = await KeywordCRUD.get_all(session, active_project.id, KeywordType.EXCLUDE)
    
    text = get_text('exclude_menu', user.language)
    text += f'\n\n📁 Проект: <b>{active_project.name}</b>'
    
    if keywords:
        text += f'\n\n🚫 <b>Исключающие слова ({len(keywords)}):</b>\n'
        for kw in keywords[:10]:
            text += f'• {kw.text}\n'
        if len(keywords) > 10:
            text += f'\n... и еще {len(keywords) - 10}'
    
    await callback.message.edit_text(
        text,
        reply_markup=exclude_menu_kb(bool(keywords), user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'exclude:add')
async def start_add_exclude(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать добавление исключающих слов"""
    await state.set_state(ExcludeStates.waiting_for_keywords)
    
    text = 'Введите исключающие слова (каждое с новой строки):'
    await callback.message.answer(text, reply_markup=cancel_kb(user.language))
    await callback.answer()


@router.message(ExcludeStates.waiting_for_keywords)
async def process_exclude(message: Message, user: User, state: FSMContext):
    """Обработка исключающих слов"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    keywords = [kw.strip() for kw in message.text.split('\n') if kw.strip()]
    
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await message.answer('❌ Проект не найден!')
            return
        
        for keyword in keywords:
            await KeywordCRUD.add(session, active_project.id, keyword, KeywordType.EXCLUDE)
    
    await state.clear()
    
    text = f'✅ Добавлено исключающих слов: {len(keywords)}'
    await message.answer(text, reply_markup=main_menu_kb(user.language))


@router.callback_query(F.data == 'exclude:clear')
async def clear_exclude(callback: CallbackQuery, user: User):
    """Удалить все исключающие слова"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
        
        if not active_project:
            await callback.answer('❌ Проект не найден!', show_alert=True)
            return
        
        await KeywordCRUD.delete_all(session, active_project.id, KeywordType.EXCLUDE)
    
    text = '🗑 Исключающие слова удалены'
    await callback.answer(text)
    
    await show_exclude_menu(callback, user)
