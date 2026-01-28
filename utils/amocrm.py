"""Утилиты для интеграции с AmoCRM"""
import logging
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from config import settings

logger = logging.getLogger(__name__)


class AmoCRMClient:
    """Клиент для работы с AmoCRM API"""
    
    BASE_URL = "https://{subdomain}.amocrm.ru/api/v4"
    
    def __init__(self, subdomain: str, access_token: str, refresh_token: str = None):
        self.subdomain = subdomain
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.base_url = self.BASE_URL.format(subdomain=subdomain)
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None
    ) -> Optional[Dict]:
        """Выполнение запроса к API"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(
                    method,
                    url,
                    json=data,
                    params=params,
                    headers=headers
                ) as response:
                    if response.status == 401:
                        logger.error("AmoCRM: Токен истёк или недействителен")
                        return None
                    
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(f"AmoCRM API error: {response.status} - {error_text}")
                        return None
                    
                    if response.status == 204:
                        return {}
                    
                    return await response.json()
            except Exception as e:
                logger.error(f"AmoCRM request error: {e}")
                return None
    
    async def get_account_info(self) -> Optional[Dict]:
        """Получить информацию об аккаунте"""
        return await self._request("GET", "/account")
    
    async def get_pipelines(self) -> Optional[List[Dict]]:
        """Получить список воронок"""
        result = await self._request("GET", "/leads/pipelines")
        if result and "_embedded" in result:
            return result["_embedded"]["pipelines"]
        return None
    
    async def get_users(self) -> Optional[List[Dict]]:
        """Получить список пользователей"""
        result = await self._request("GET", "/users")
        if result and "_embedded" in result:
            return result["_embedded"]["users"]
        return None
    
    async def create_lead(
        self,
        name: str,
        price: int = 0,
        pipeline_id: int = None,
        status_id: int = None,
        responsible_user_id: int = None,
        custom_fields: List[Dict] = None,
        tags: List[str] = None,
        contacts: List[Dict] = None
    ) -> Optional[Dict]:
        """
        Создать сделку в AmoCRM
        
        Args:
            name: Название сделки
            price: Бюджет
            pipeline_id: ID воронки
            status_id: ID статуса
            responsible_user_id: ID ответственного
            custom_fields: Кастомные поля
            tags: Теги
            contacts: Связанные контакты
        """
        lead_data = {
            "name": name,
            "price": price
        }
        
        if pipeline_id:
            lead_data["pipeline_id"] = pipeline_id
        if status_id:
            lead_data["status_id"] = status_id
        if responsible_user_id:
            lead_data["responsible_user_id"] = responsible_user_id
        if custom_fields:
            lead_data["custom_fields_values"] = custom_fields
        if tags:
            lead_data["_embedded"] = {"tags": [{"name": tag} for tag in tags]}
        
        result = await self._request("POST", "/leads", data=[lead_data])
        
        if result and "_embedded" in result:
            lead = result["_embedded"]["leads"][0]
            
            # Если есть контакты, привязываем их
            if contacts:
                await self.link_contacts_to_lead(lead["id"], contacts)
            
            return lead
        
        return None
    
    async def create_contact(
        self,
        name: str,
        phone: str = None,
        telegram: str = None,
        responsible_user_id: int = None
    ) -> Optional[Dict]:
        """Создать контакт"""
        contact_data = {
            "name": name
        }
        
        if responsible_user_id:
            contact_data["responsible_user_id"] = responsible_user_id
        
        # Добавляем поля с телефоном и Telegram
        custom_fields = []
        if phone:
            custom_fields.append({
                "field_code": "PHONE",
                "values": [{"value": phone, "enum_code": "WORK"}]
            })
        if telegram:
            custom_fields.append({
                "field_code": "IM",  # Мессенджеры
                "values": [{"value": telegram, "enum_code": "TELEGRAM"}]
            })
        
        if custom_fields:
            contact_data["custom_fields_values"] = custom_fields
        
        result = await self._request("POST", "/contacts", data=[contact_data])
        
        if result and "_embedded" in result:
            return result["_embedded"]["contacts"][0]
        
        return None
    
    async def link_contacts_to_lead(self, lead_id: int, contacts: List[Dict]) -> bool:
        """Привязать контакты к сделке"""
        links = [{"to_entity_id": c["id"], "to_entity_type": "contacts"} for c in contacts]
        
        result = await self._request(
            "POST",
            f"/leads/{lead_id}/link",
            data=links
        )
        
        return result is not None
    
    async def add_note_to_lead(self, lead_id: int, text: str) -> Optional[Dict]:
        """Добавить примечание к сделке"""
        note_data = [{
            "entity_id": lead_id,
            "note_type": "common",
            "params": {
                "text": text
            }
        }]
        
        result = await self._request("POST", "/leads/notes", data=note_data)
        
        if result and "_embedded" in result:
            return result["_embedded"]["notes"][0]
        
        return None


async def send_lead_to_amocrm(
    session: AsyncSession,
    user_id: int,
    lead_match
) -> bool:
    """
    Отправить найденный лид в AmoCRM пользователя
    
    Args:
        session: Сессия БД
        user_id: ID пользователя
        lead_match: Объект LeadMatch
        
    Returns:
        True если успешно отправлено
    """
    from database.models import AmoCRMIntegration, User
    
    # Получаем интеграцию пользователя
    result = await session.execute(
        select(AmoCRMIntegration)
        .where(AmoCRMIntegration.user_id == user_id, AmoCRMIntegration.is_active == True)
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        logger.debug(f"AmoCRM не настроен для пользователя {user_id}")
        return False
    
    # Проверяем срок действия токена
    if integration.token_expires_at < datetime.utcnow():
        logger.warning(f"Токен AmoCRM истёк для пользователя {user_id}")
        # TODO: Обновление токена через refresh_token
        return False
    
    # Создаём клиента
    client = AmoCRMClient(
        subdomain=integration.subdomain,
        access_token=integration.access_token,
        refresh_token=integration.refresh_token
    )
    
    try:
        # Формируем название сделки
        lead_name = f"Лид из Telegram: {lead_match.chat.title or 'Чат'}"
        
        # Создаём контакт если есть username
        contact = None
        if lead_match.sender_username:
            contact = await client.create_contact(
                name=f"@{lead_match.sender_username}",
                telegram=f"@{lead_match.sender_username}",
                responsible_user_id=integration.responsible_user_id
            )
        
        # Создаём сделку
        lead = await client.create_lead(
            name=lead_name,
            pipeline_id=integration.pipeline_id,
            status_id=integration.status_id,
            responsible_user_id=integration.responsible_user_id,
            tags=["GetLead", "Telegram"],
            contacts=[contact] if contact else None
        )
        
        if not lead:
            logger.error(f"Не удалось создать сделку в AmoCRM для пользователя {user_id}")
            return False
        
        # Добавляем примечание с текстом сообщения
        note_text = f"""📱 Лид из GetLead Bot

🔑 Ключевые слова: {lead_match.matched_keywords}

💬 Текст сообщения:
{lead_match.message_text}

🔗 Ссылка: {lead_match.message_link}
"""
        
        await client.add_note_to_lead(lead["id"], note_text)
        
        # Обновляем статус отправки в БД
        from database.models import LeadMatch
        await session.execute(
            update(LeadMatch)
            .where(LeadMatch.id == lead_match.id)
            .values(is_sent_to_crm=True)
        )
        await session.commit()
        
        logger.info(f"✅ Лид {lead_match.id} отправлен в AmoCRM пользователя {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки в AmoCRM: {e}")
        return False


def get_amocrm_oauth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Получить URL для OAuth авторизации AmoCRM"""
    return (
        f"https://www.amocrm.ru/oauth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"state={state}&"
        f"response_type=code&"
        f"mode=popup"
    )


async def exchange_code_for_tokens(
    subdomain: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str
) -> Optional[Dict]:
    """Обменять код авторизации на токены"""
    url = f"https://{subdomain}.amocrm.ru/oauth2/access_token"
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"AmoCRM token exchange error: {error_text}")
                    return None
                
                tokens = await response.json()
                return {
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "expires_in": tokens["expires_in"]
                }
        except Exception as e:
            logger.error(f"AmoCRM token exchange error: {e}")
            return None
