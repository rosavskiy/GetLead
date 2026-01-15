"""Обработчики для работы с оплатой"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.models import User, SubscriptionPlan
from bot.keyboards import payment_menu_kb, payment_method_kb, back_to_main_kb

router = Router()


@router.callback_query(F.data == 'menu:payment')
async def show_payment_menu(callback: CallbackQuery, user: User):
    """Показать меню тарифов"""
    text = """💳 <b>Тарифы GetLead</b>

Выберите подходящий тариф:

💼 <b>Фрилансер</b> — 500₽/мес
   • До 5 чатов
   • Безлимит ключевых слов
   • AI-подбор

📊 <b>Стандарт</b> — 1500₽/мес
   • До 20 чатов
   • Безлимит ключевых слов
   • AI-подбор
   • Приоритетная поддержка

🚀 <b>Стартап</b> — 1000₽/мес
   • До 10 чатов
   • Безлимит ключевых слов
   • AI-подбор

🏢 <b>Компания</b> — 3000₽/мес
   • До 50 чатов
   • Безлимит ключевых слов
   • AI-подбор
   • VIP поддержка
   • Персональный менеджер

"""
    
    if user.subscription_plan != SubscriptionPlan.FREE:
        text += f'\n✅ Ваш текущий тариф: <b>{user.subscription_plan.value.upper()}</b>'
        if user.subscription_end_date:
            text += f'\nДействителен до: {user.subscription_end_date.strftime("%d.%m.%Y")}'
    
    await callback.message.edit_text(
        text,
        reply_markup=payment_menu_kb(user.subscription_plan, user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('payment:'))
async def select_payment_plan(callback: CallbackQuery, user: User):
    """Выбор тарифного плана"""
    plan = callback.data.split(':')[1]
    
    prices = {
        'freelancer': '500₽',
        'standard': '1500₽',
        'startup': '1000₽',
        'company': '3000₽'
    }
    
    text = f'Вы выбрали тариф: <b>{plan.upper()}</b>\nСтоимость: {prices[plan]}\n\nВыберите способ оплаты:'
    
    await callback.message.edit_text(
        text,
        reply_markup=payment_method_kb(plan, user.language),
        parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data.startswith('pay:card:'))
async def process_card_payment(callback: CallbackQuery, user: User):
    """Обработка оплаты картой через ЮKassa"""
    plan = callback.data.split(':')[2]
    
    # TODO: Интеграция с ЮKassa
    text = """💳 <b>Оплата банковской картой</b>

Интеграция с ЮKassa будет доступна после настройки платежного шлюза.

Для оплаты свяжитесь с поддержкой: @getlead_support"""
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith('pay:crypto:'))
async def process_crypto_payment(callback: CallbackQuery, user: User):
    """Обработка оплаты криптовалютой"""
    plan = callback.data.split(':')[2]
    
    # TODO: Интеграция с CryptoBot
    text = """₿ <b>Оплата криптовалютой</b>

Интеграция с CryptoBot будет доступна после настройки.

Для оплаты свяжитесь с поддержкой: @getlead_support"""
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()
