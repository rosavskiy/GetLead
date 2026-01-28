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
from bot.keyboards import keywords_menu_kb, exclude_menu_kb, cancel_kb, main_menu_kb

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
    
    text = '🤖 Введите вашу нишу для AI-подбора ключевых слов:\n\nНапример: "Дизайн сайтов", "SMM", "Копирайтинг"'
    await callback.message.answer(text, reply_markup=cancel_kb(user.language))
    await callback.answer()


@router.message(KeywordStates.waiting_for_ai_niche)
async def process_ai_keywords(message: Message, user: User, state: FSMContext):
    """Обработка AI подбора ключевых слов"""
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
    gen_text = '🤖 Генерирую ключевые слова...' if lang == 'ru' else '🤖 Generating keywords...'
    status_msg = await message.answer(gen_text)
    
    try:
        from utils.ai_helpers import generate_keywords
        keywords = await generate_keywords(niche)
        
        if not keywords:
            err = '❌ Не удалось сгенерировать ключевые слова' if lang == 'ru' else '❌ Could not generate keywords'
            await status_msg.edit_text(err)
            await state.clear()
            return
        
        # Сохраняем ключевые слова
        async with async_session_maker() as session:
            active_project = await ProjectCRUD.get_active(session, user.id)
            
            if not active_project:
                err = '❌ Проект не найден!' if lang == 'ru' else '❌ Project not found!'
                await status_msg.edit_text(err)
                await state.clear()
                return
            
            added_count = 0
            for keyword in keywords:
                if keyword.strip():
                    await KeywordCRUD.add(session, active_project.id, keyword.strip(), KeywordType.INCLUDE)
                    added_count += 1
            
            # Инвалидируем кэш (опционально, не падаем если Redis недоступен)
            try:
                from utils.cache import CacheService
                await CacheService.invalidate_project_keywords(active_project.id)
            except Exception as cache_err:
                logger.warning(f"Cache invalidation failed: {cache_err}")
        
        await state.clear()
        
        # Показываем результат
        keywords_preview = '\n'.join([f'• {kw}' for kw in keywords[:10]])
        if lang == 'ru':
            text = f'✅ <b>Добавлено {added_count} ключевых слов!</b>\n\n{keywords_preview}'
        else:
            text = f'✅ <b>Added {added_count} keywords!</b>\n\n{keywords_preview}'
        
        if len(keywords) > 10:
            more = f'и ещё {len(keywords) - 10}' if lang == 'ru' else f'and {len(keywords) - 10} more'
            text += f'\n\n... {more}'
        
        await status_msg.edit_text(text, parse_mode='HTML')
        menu_text = 'Вернуться в меню:' if lang == 'ru' else 'Return to menu:'
        await message.answer(menu_text, reply_markup=main_menu_kb(lang))
        
    except ValueError as e:
        logger.error(f"AI keywords ValueError: {e}")
        await status_msg.edit_text(f'❌ Ошибка: {str(e)}')
        await state.clear()
    except Exception as e:
        logger.error(f"AI keywords error: {e}", exc_info=True)
        err = '❌ Произошла ошибка при генерации' if lang == 'ru' else '❌ Error during generation'
        await status_msg.edit_text(err)
        await state.clear()
        
    except ValueError as e:
        await status_msg.edit_text(f'❌ Ошибка: {str(e)}')
        await state.clear()
    except Exception as e:
        err = '❌ Произошла ошибка при генерации' if lang == 'ru' else '❌ Error during generation'
        await status_msg.edit_text(err)
        await state.clear()


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
