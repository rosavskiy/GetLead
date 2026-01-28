"""Конфигурация приложения"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Основные настройки приложения"""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )
    
    # Bot
    BOT_TOKEN: str
    ADMIN_IDS: str = ""
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Telethon Userbots
    USERBOT_1_API_ID: int = 0
    USERBOT_1_API_HASH: str = ""
    USERBOT_1_PHONE: str = ""
    USERBOT_1_SESSION_NAME: str = "userbot_1"
    
    USERBOT_2_API_ID: int = 0
    USERBOT_2_API_HASH: str = ""
    USERBOT_2_PHONE: str = ""
    USERBOT_2_SESSION_NAME: str = "userbot_2"
    
    USERBOT_3_API_ID: int = 0
    USERBOT_3_API_HASH: str = ""
    USERBOT_3_PHONE: str = ""
    USERBOT_3_SESSION_NAME: str = "userbot_3"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # Payment Systems
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    CRYPTOBOT_TOKEN: str = ""
    
    # AmoCRM (для OAuth интеграции)
    AMOCRM_CLIENT_ID: str = ""
    AMOCRM_CLIENT_SECRET: str = ""
    AMOCRM_REDIRECT_URI: str = ""
    
    # App Settings
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    WEBHOOK_URL: str = ""
    WEBHOOK_PATH: str = "/webhook"
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Список ID администраторов"""
        if not self.ADMIN_IDS:
            return []
        return [int(admin_id.strip()) for admin_id in self.ADMIN_IDS.split(',')]
    
    def get_admin_ids(self) -> List[int]:
        """Получить список ID администраторов"""
        return self.admin_ids_list
    
    @property
    def userbots_config(self) -> List[dict]:
        """Конфигурация юзерботов"""
        bots = []
        
        if self.USERBOT_1_API_ID:
            bots.append({
                'api_id': self.USERBOT_1_API_ID,
                'api_hash': self.USERBOT_1_API_HASH,
                'phone': self.USERBOT_1_PHONE,
                'session_name': self.USERBOT_1_SESSION_NAME
            })
        
        if self.USERBOT_2_API_ID:
            bots.append({
                'api_id': self.USERBOT_2_API_ID,
                'api_hash': self.USERBOT_2_API_HASH,
                'phone': self.USERBOT_2_PHONE,
                'session_name': self.USERBOT_2_SESSION_NAME
            })
        
        if self.USERBOT_3_API_ID:
            bots.append({
                'api_id': self.USERBOT_3_API_ID,
                'api_hash': self.USERBOT_3_API_HASH,
                'phone': self.USERBOT_3_PHONE,
                'session_name': self.USERBOT_3_SESSION_NAME
            })
        
        return bots


settings = Settings()
