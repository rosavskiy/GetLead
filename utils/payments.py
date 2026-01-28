"""Утилиты для работы с платёжными системами"""
import uuid
import logging
import aiohttp
from typing import Optional, Dict
from datetime import datetime, timedelta
from base64 import b64encode

from config import settings

logger = logging.getLogger(__name__)


class YooKassaClient:
    """Клиент для работы с ЮKassa API"""
    
    BASE_URL = "https://api.yookassa.ru/v3"
    
    def __init__(self):
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY
        
        if not self.shop_id or not self.secret_key:
            logger.warning("YooKassa credentials not configured")
    
    def _get_auth_header(self) -> str:
        """Получить заголовок авторизации"""
        credentials = f"{self.shop_id}:{self.secret_key}"
        encoded = b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def create_payment(
        self,
        amount: float,
        currency: str = "RUB",
        description: str = "",
        return_url: str = None,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """
        Создать платёж
        
        Args:
            amount: Сумма платежа
            currency: Валюта
            description: Описание платежа
            return_url: URL для возврата после оплаты
            metadata: Дополнительные данные (user_id, plan и т.д.)
        
        Returns:
            Данные платежа с confirmation_url
        """
        if not self.shop_id or not self.secret_key:
            logger.error("YooKassa not configured")
            return None
        
        idempotence_key = str(uuid.uuid4())
        
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": currency
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or settings.WEBHOOK_URL
            },
            "capture": True,
            "description": description,
            "metadata": metadata or {}
        }
        
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
            "Idempotence-Key": idempotence_key
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.BASE_URL}/payments",
                    json=payment_data,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        logger.error(f"YooKassa error: {error}")
                        return None
                    
                    result = await response.json()
                    return {
                        "payment_id": result["id"],
                        "status": result["status"],
                        "confirmation_url": result["confirmation"]["confirmation_url"],
                        "amount": float(result["amount"]["value"]),
                        "created_at": result["created_at"]
                    }
            except Exception as e:
                logger.error(f"YooKassa request error: {e}")
                return None
    
    async def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Получить информацию о платеже"""
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.BASE_URL}/payments/{payment_id}",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        return None
                    
                    result = await response.json()
                    return {
                        "payment_id": result["id"],
                        "status": result["status"],
                        "amount": float(result["amount"]["value"]),
                        "metadata": result.get("metadata", {}),
                        "paid": result["paid"]
                    }
            except Exception as e:
                logger.error(f"YooKassa get payment error: {e}")
                return None


class CryptoBotClient:
    """Клиент для работы с CryptoBot API"""
    
    BASE_URL = "https://pay.crypt.bot/api"
    
    def __init__(self):
        self.token = settings.CRYPTOBOT_TOKEN
        
        if not self.token:
            logger.warning("CryptoBot token not configured")
    
    async def create_invoice(
        self,
        amount: float,
        currency: str = "USDT",
        description: str = "",
        payload: str = ""
    ) -> Optional[Dict]:
        """
        Создать счёт на оплату
        
        Args:
            amount: Сумма
            currency: Криптовалюта (USDT, TON, BTC, ETH)
            description: Описание
            payload: Дополнительные данные (JSON строка)
        
        Returns:
            Данные счёта с pay_url
        """
        if not self.token:
            logger.error("CryptoBot not configured")
            return None
        
        params = {
            "asset": currency,
            "amount": str(amount),
            "description": description,
            "payload": payload,
            "expires_in": 3600  # 1 час
        }
        
        headers = {
            "Crypto-Pay-API-Token": self.token
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.BASE_URL}/createInvoice",
                    data=params,
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if not result.get("ok"):
                        logger.error(f"CryptoBot error: {result}")
                        return None
                    
                    invoice = result["result"]
                    return {
                        "invoice_id": invoice["invoice_id"],
                        "status": invoice["status"],
                        "pay_url": invoice["pay_url"],
                        "amount": float(invoice["amount"]),
                        "asset": invoice["asset"]
                    }
            except Exception as e:
                logger.error(f"CryptoBot request error: {e}")
                return None
    
    async def get_invoice(self, invoice_id: int) -> Optional[Dict]:
        """Получить информацию о счёте"""
        if not self.token:
            return None
        
        params = {
            "invoice_ids": str(invoice_id)
        }
        
        headers = {
            "Crypto-Pay-API-Token": self.token
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.BASE_URL}/getInvoices",
                    params=params,
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if not result.get("ok") or not result["result"]["items"]:
                        return None
                    
                    invoice = result["result"]["items"][0]
                    return {
                        "invoice_id": invoice["invoice_id"],
                        "status": invoice["status"],
                        "amount": float(invoice["amount"]),
                        "asset": invoice["asset"],
                        "paid": invoice["status"] == "paid"
                    }
            except Exception as e:
                logger.error(f"CryptoBot get invoice error: {e}")
                return None


# Цены тарифов
PLAN_PRICES = {
    "freelancer": {"rub": 500, "usdt": 5},
    "standard": {"rub": 1500, "usdt": 15},
    "startup": {"rub": 1000, "usdt": 10},
    "company": {"rub": 3000, "usdt": 30}
}


def get_plan_price(plan: str, currency: str = "rub") -> float:
    """Получить цену тарифа"""
    return PLAN_PRICES.get(plan, {}).get(currency, 0)
