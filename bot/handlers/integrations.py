"""Обработчики для интеграций (AmoCRM и др.)"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.database import async_session_maker
from database.models import User, AmoCRMIntegration
from database.crud import AmoCRMCRUD
from bot.keyboards import integrations_menu_kb, amocrm_menu_kb, back_to_main_kb, cancel_kb

logger = logging.getLogger(__name__)
router = Router()


class AmoCRMStates(StatesGroup):
    """Состояния для настройки AmoCRM"""
    waiting_for_subdomain = State()
    waiting_for_token = State()


@router.callback_query(F.data == 'menu:integrations')
async def show_integrations_menu(callback: CallbackQuery, user: User):
    """Показать меню интеграций"""
    async with async_session_maker() as session:
        amocrm = await AmoCRMCRUD.get_by_user(session, user.id)
    
    text = """🔗 <b>Интеграции</b>

Подключите внешние сервисы для автоматической обработки лидов:

<b>AmoCRM</b> — автоматическое создание сделок из найденных лидов
<b>Webhook API</b> — отправка лидов на ваш сервер

💡 Интеграции доступны на всех платных тарифах."""
    
    await callback.message.edit_text(
        text,
        reply_markup=integrations_menu_kb(has_amocrm=bool(amocrm and amocrm.is_active)),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'integrations:amocrm')
async def show_amocrm_menu(callback: CallbackQuery, user: User):
    """Показать меню AmoCRM"""
    async with async_session_maker() as session:
        amocrm = await AmoCRMCRUD.get_by_user(session, user.id)
    
    if amocrm and amocrm.is_active:
        text = f"""✅ <b>AmoCRM подключен</b>

🏢 <b>Аккаунт:</b> {amocrm.subdomain}.amocrm.ru
🔄 <b>Статус:</b> Активен

⚙️ <b>Настройки:</b>
• Воронка: {amocrm.pipeline_id or 'По умолчанию'}
• Ответственный: {amocrm.responsible_user_id or 'По умолчанию'}

Все найденные лиды будут автоматически создаваться как сделки в вашей CRM."""
    else:
        text = """❌ <b>AmoCRM не подключен</b>

Подключите AmoCRM для автоматического создания сделок из найденных лидов.

📋 <b>Что нужно:</b>
1. Войдите в AmoCRM
2. Создайте интеграцию (Настройки → API)
3. Скопируйте токен доступа

После подключения все лиды будут автоматически попадать в вашу CRM!"""
    
    await callback.message.edit_text(
        text,
        reply_markup=amocrm_menu_kb(is_connected=bool(amocrm and amocrm.is_active)),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'amocrm:connect')
async def start_amocrm_connection(callback: CallbackQuery, user: User, state: FSMContext):
    """Начать подключение AmoCRM"""
    await state.set_state(AmoCRMStates.waiting_for_subdomain)
    
    text = """🔗 <b>Подключение AmoCRM</b>

<b>Шаг 1/2:</b> Введите поддомен вашего AmoCRM

Например, если ваш AmoCRM находится по адресу:
<code>example.amocrm.ru</code>

Введите только: <code>example</code>"""
    
    await callback.message.answer(text, reply_markup=cancel_kb(), parse_mode='HTML')
    await callback.answer()


@router.message(AmoCRMStates.waiting_for_subdomain)
async def process_amocrm_subdomain(message: Message, user: User, state: FSMContext):
    """Обработка поддомена AmoCRM"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer('Отменено', reply_markup=back_to_main_kb())
        return
    
    subdomain = message.text.strip().lower()
    # Убираем .amocrm.ru если пользователь ввёл полный адрес
    subdomain = subdomain.replace('.amocrm.ru', '').replace('https://', '').replace('http://', '')
    
    await state.update_data(subdomain=subdomain)
    await state.set_state(AmoCRMStates.waiting_for_token)
    
    text = f"""✅ Поддомен: <code>{subdomain}</code>

<b>Шаг 2/2:</b> Введите Long-lived токен AmoCRM

Как получить токен:
1. Откройте {subdomain}.amocrm.ru
2. Перейдите в Настройки → API → Создать интеграцию
3. Создайте интеграцию и скопируйте токен

⚠️ Храните токен в безопасности!"""
    
    await message.answer(text, reply_markup=cancel_kb(), parse_mode='HTML')


@router.message(AmoCRMStates.waiting_for_token)
async def process_amocrm_token(message: Message, user: User, state: FSMContext):
    """Обработка токена AmoCRM"""
    if message.text == '❌ Отмена':
        await state.clear()
        await message.answer('Отменено', reply_markup=back_to_main_kb())
        return
    
    data = await state.get_data()
    subdomain = data['subdomain']
    token = message.text.strip()
    
    # Удаляем сообщение с токеном из безопасности
    try:
        await message.delete()
    except:
        pass
    
    # Проверяем токен
    from utils.amocrm import AmoCRMClient
    client = AmoCRMClient(subdomain=subdomain, access_token=token)
    account = await client.get_account_info()
    
    if not account:
        await message.answer(
            '❌ Не удалось подключиться к AmoCRM. Проверьте поддомен и токен.',
            reply_markup=back_to_main_kb()
        )
        await state.clear()
        return
    
    # Сохраняем интеграцию
    from datetime import datetime, timedelta
    
    async with async_session_maker() as session:
        await AmoCRMCRUD.create_or_update(
            session=session,
            user_id=user.id,
            subdomain=subdomain,
            access_token=token,
            refresh_token='',  # Long-lived токен не требует refresh
            expires_at=datetime.utcnow() + timedelta(days=365)  # Условно на год
        )
    
    await state.clear()
    
    text = f"""✅ <b>AmoCRM успешно подключен!</b>

🏢 Аккаунт: {subdomain}.amocrm.ru

Теперь все найденные лиды будут автоматически создаваться как сделки в вашей CRM.

💡 Вы можете настроить воронку и ответственного в настройках интеграции."""
    
    await message.answer(text, reply_markup=back_to_main_kb(), parse_mode='HTML')


@router.callback_query(F.data == 'amocrm:disconnect')
async def disconnect_amocrm(callback: CallbackQuery, user: User):
    """Отключить AmoCRM"""
    async with async_session_maker() as session:
        await AmoCRMCRUD.delete(session, user.id)
    
    await callback.answer('AmoCRM отключен', show_alert=True)
    await show_amocrm_menu(callback, user)


@router.callback_query(F.data == 'amocrm:pipeline')
async def show_pipeline_settings(callback: CallbackQuery, user: User):
    """Показать настройки воронки"""
    async with async_session_maker() as session:
        amocrm = await AmoCRMCRUD.get_by_user(session, user.id)
    
    if not amocrm:
        await callback.answer('AmoCRM не подключен', show_alert=True)
        return
    
    # Получаем список воронок
    from utils.amocrm import AmoCRMClient
    client = AmoCRMClient(subdomain=amocrm.subdomain, access_token=amocrm.access_token)
    pipelines = await client.get_pipelines()
    
    if not pipelines:
        await callback.answer('Не удалось получить воронки', show_alert=True)
        return
    
    text = "⚙️ <b>Настройка воронки</b>\n\nВыберите воронку для создания сделок:\n\n"
    
    for pipeline in pipelines:
        is_selected = '✅' if pipeline['id'] == amocrm.pipeline_id else '⚪️'
        text += f"{is_selected} {pipeline['name']}\n"
    
    text += "\n💡 Напишите ID воронки для выбора (число)"
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'integrations:webhook')
async def show_webhook_info(callback: CallbackQuery, user: User):
    """Показать информацию о Webhook API"""
    text = f"""🔗 <b>Webhook API</b>

Отправляйте найденные лиды на свой сервер в реальном времени.

<b>Ваш Webhook URL:</b>
<code>Не настроен</code>

<b>Формат данных:</b>
<code>{{
  "lead_id": 123,
  "message_text": "...",
  "keywords": ["keyword1", "keyword2"],
  "chat": {{"title": "...", "link": "..."}},
  "sender": {{"username": "..."}},
  "timestamp": "2025-01-28T12:00:00Z"
}}</code>

🔜 <b>Скоро!</b> Эта функция в разработке."""
    
    await callback.message.edit_text(
        text,
        reply_markup=back_to_main_kb(),
        parse_mode='HTML'
    )
    await callback.answer()
