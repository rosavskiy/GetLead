"""Обработчики для работы с проектами"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.database import async_session_maker
from database.crud import ProjectCRUD
from database.models import User
from bot.states import ProjectStates
from bot.texts import get_text
from bot.keyboards import projects_menu_kb, cancel_kb, main_menu_kb

router = Router()


async def get_projects_text(user: User) -> tuple:
    """Получить текст и клавиатуру для меню проектов"""
    async with async_session_maker() as session:
        projects = await ProjectCRUD.get_all(session, user.id)
    
    text = get_text('projects_menu', user.language)
    
    if not projects:
        text += '\n\nУ вас пока нет проектов. Создайте первый проект!'
    else:
        text += '\n\n📁 <b>Ваши проекты:</b>\n'
        for project in projects:
            status = '✅ Активен' if project.is_active else '⚪ Неактивен'
            text += f'\n• {project.name} — {status}'
    
    return text, projects


async def show_projects_menu_msg(message: Message, user: User):
    """Показать меню проектов как сообщение (для команды)"""
    text, projects = await get_projects_text(user)
    await message.answer(text, reply_markup=projects_menu_kb(projects, user.language), parse_mode='HTML')


@router.callback_query(F.data == 'menu:projects')
async def show_projects_menu(callback: CallbackQuery, user: User):
    """Показать меню проектов"""
    text, projects = await get_projects_text(user)
    
    await callback.message.edit_text(
        text,
        reply_markup=projects_menu_kb(projects, user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'project:create')
async def start_create_project(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать создание проекта"""
    await state.set_state(ProjectStates.waiting_for_name)
    
    text = get_text('enter_project_name', user.language)
    await callback.message.answer(text, reply_markup=cancel_kb(user.language))
    await callback.answer()


@router.message(ProjectStates.waiting_for_name)
async def process_project_name(message: Message, user: User, state: FSMContext):
    """Обработка названия проекта"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    project_name = message.text.strip()
    
    async with async_session_maker() as session:
        # Создаем проект
        project = await ProjectCRUD.create(session, user.id, project_name)
        # Делаем его активным
        await ProjectCRUD.set_active(session, project.id, user.id)
    
    await state.clear()
    
    text = get_text('project_created', user.language, project_name=project_name)
    await message.answer(text, reply_markup=main_menu_kb(user.language))


@router.callback_query(F.data.startswith('project:activate:'))
async def activate_project(callback: CallbackQuery, user: User):
    """Активировать проект"""
    project_id = int(callback.data.split(':')[2])
    
    async with async_session_maker() as session:
        await ProjectCRUD.set_active(session, project_id, user.id)
        projects = await ProjectCRUD.get_all(session, user.id)
        
        # Находим активированный проект
        project = next(p for p in projects if p.id == project_id)
    
    text = get_text('project_activated', user.language, project_name=project.name)
    await callback.answer(text)
    
    # Обновляем меню
    await callback.message.edit_reply_markup(
        reply_markup=projects_menu_kb(projects, user.language)
    )


@router.callback_query(F.data == 'project:delete')
async def start_delete_project(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать удаление проекта"""
    async with async_session_maker() as session:
        active_project = await ProjectCRUD.get_active(session, user.id)
    
    if not active_project:
        await callback.answer('❌ Сначала выберите проект для удаления', show_alert=True)
        return
    
    await state.set_state(ProjectStates.waiting_for_delete_confirm)
    await state.update_data(project_id=active_project.id)
    
    text = f'⚠️ Вы уверены, что хотите удалить проект "<b>{active_project.name}</b>"?\n\nНапишите "Да" для подтверждения'
    await callback.message.answer(text, reply_markup=cancel_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.message(ProjectStates.waiting_for_delete_confirm)
async def confirm_delete_project(message: Message, user: User, state: FSMContext):
    """Подтверждение удаления проекта"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer(
            get_text('main_menu', user.language),
            reply_markup=main_menu_kb(user.language)
        )
        return
    
    if message.text.lower() != 'да':
        await message.answer('❌ Удаление отменено')
        await state.clear()
        return
    
    data = await state.get_data()
    project_id = data['project_id']
    
    async with async_session_maker() as session:
        await ProjectCRUD.delete(session, project_id)
    
    await state.clear()
    
    text = get_text('project_deleted', user.language)
    await message.answer(text, reply_markup=main_menu_kb(user.language))
