"""Обработчики для работы с оплатой"""
import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.database import async_session_maker
from database.models import User, SubscriptionPlan
from database.crud import UserCRUD
from bot.keyboards import payment_menu_kb, payment_method_kb, back_to_main_kb
from utils.payments import YooKassaClient, CryptoBotClient, get_plan_price, PLAN_PRICES
from config import settings

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
   • Интеграция с CRM

"""
    
    if user.subscription_plan != SubscriptionPlan.FREE:
        text += f'\n✅ Ваш текущий тариф: <b>{user.subscription_plan.value.upper()}</b>'
        if user.subscription_end_date:
            days_left = (user.subscription_end_date - datetime.utcnow()).days
            text += f'\n⏳ Осталось дней: {days_left}'
            text += f'\n📆 Действителен до: {user.subscription_end_date.strftime("%d.%m.%Y")}'
    
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
    
    price_rub = get_plan_price(plan, 'rub')
    price_usdt = get_plan_price(plan, 'usdt')
    
    text = f"""💳 <b>Оплата тарифа</b>

📦 Тариф: <b>{plan.upper()}</b>
💰 Стоимость: <b>{price_rub}₽</b> или <b>${price_usdt}</b>
⏱ Период: 1 месяц

Выберите способ оплаты:"""
    
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
    price = get_plan_price(plan, 'rub')
    
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        text = """💳 <b>Оплата банковской картой</b>

⚠️ Платёжная система временно недоступна.
Для оплаты свяжитесь с поддержкой: @getlead_support"""
        await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
        await callback.answer()
        return
    
    # Создаём платёж
    yookassa = YooKassaClient()
    
    payment = await yookassa.create_payment(
        amount=price,
        currency="RUB",
        description=f"GetLead - тариф {plan.upper()} (1 месяц)",
        return_url=f"https://t.me/{(await callback.bot.get_me()).username}",
        metadata={
            "user_id": str(user.id),
            "telegram_id": str(user.telegram_id),
            "plan": plan
        }
    )
    
    if not payment:
        await callback.answer('❌ Ошибка создания платежа', show_alert=True)
        return
    
    text = f"""💳 <b>Оплата банковской картой</b>

📦 Тариф: <b>{plan.upper()}</b>
💰 Сумма: <b>{price}₽</b>

🔗 <a href="{payment['confirmation_url']}">Перейти к оплате</a>

⏱ Ссылка действительна 1 час.
После оплаты подписка активируется автоматически."""
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith('pay:crypto:'))
async def process_crypto_payment(callback: CallbackQuery, user: User):
    """Обработка оплаты криптовалютой"""
    plan = callback.data.split(':')[2]
    price = get_plan_price(plan, 'usdt')
    
    if not settings.CRYPTOBOT_TOKEN:
        text = """₿ <b>Оплата криптовалютой</b>

⚠️ Платёжная система временно недоступна.
Для оплаты свяжитесь с поддержкой: @getlead_support"""
        await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
        await callback.answer()
        return
    
    # Создаём счёт
    cryptobot = CryptoBotClient()
    
    payload = json.dumps({
        "user_id": user.id,
        "telegram_id": user.telegram_id,
        "plan": plan
    })
    
    invoice = await cryptobot.create_invoice(
        amount=price,
        currency="USDT",
        description=f"GetLead - тариф {plan.upper()} (1 месяц)",
        payload=payload
    )
    
    if not invoice:
        await callback.answer('❌ Ошибка создания счёта', show_alert=True)
        return
    
    text = f"""₿ <b>Оплата криптовалютой</b>

📦 Тариф: <b>{plan.upper()}</b>
💰 Сумма: <b>${price} USDT</b>

🔗 <a href="{invoice['pay_url']}">Перейти к оплате</a>

⏱ Ссылка действительна 1 час.
После оплаты подписка активируется автоматически."""
    
    await callback.message.edit_text(text, reply_markup=back_to_main_kb(user.language), parse_mode='HTML')
    await callback.answer()
