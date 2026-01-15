"""Скрипт для авторизации юзерботов (запускается ОДИН РАЗ)"""
import asyncio
import logging
from config import settings
from userbot.worker import UserbotWorker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def authorize_userbot(bot_config):
    """Авторизация одного юзербота"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Авторизация юзербота: {bot_config['session_name']}")
    logger.info(f"Номер телефона: {bot_config['phone']}")
    logger.info(f"{'='*60}\n")
    
    worker = UserbotWorker(
        api_id=bot_config['api_id'],
        api_hash=bot_config['api_hash'],
        session_name=bot_config['session_name'],
        phone=bot_config['phone']
    )
    
    try:
        # Авторизуем юзербота
        await worker.client.start(phone=bot_config['phone'])
        logger.info(f"✅ Юзербот {bot_config['session_name']} успешно авторизован!")
        
        # Отключаемся
        await worker.client.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Ошибка авторизации {bot_config['session_name']}: {e}")
        raise


async def main():
    """Поэтапная авторизация всех юзерботов"""
    
    if not settings.userbots_config:
        logger.error("❌ Нет настроенных юзерботов! Проверьте .env файл")
        return
    
    logger.info(f"Найдено {len(settings.userbots_config)} юзерботов для авторизации")
    logger.info("Юзерботы будут авторизованы ПОЭТАПНО (один за другим)\n")
    
    # Авторизуем каждый юзербот последовательно
    for i, bot_config in enumerate(settings.userbots_config, 1):
        logger.info(f"\n📱 Авторизация {i}/{len(settings.userbots_config)}")
        
        # Создаем клиента
        from telethon import TelegramClient
        client = TelegramClient(
            bot_config['session_name'],
            bot_config['api_id'],
            bot_config['api_hash']
        )
        
        try:
            # Запускаем авторизацию
            await client.start(phone=bot_config['phone'])
            logger.info(f"✅ {bot_config['session_name']} успешно авторизован!\n")
            
            # Отключаемся
            await client.disconnect()
            
        except Exception as e:
            logger.error(f"❌ Ошибка при авторизации {bot_config['session_name']}: {e}")
            logger.info("Пропускаем этот юзербот и продолжаем...\n")
            continue
    
    logger.info("\n" + "="*60)
    logger.info("🎉 Авторизация завершена!")
    logger.info("="*60)
    logger.info("\nТеперь можно запускать юзерботы через:")
    logger.info("  python run_userbot.py")
    logger.info("\nИли через systemd:")
    logger.info("  sudo systemctl start getlead-userbot")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Авторизация прервана пользователем")
    except Exception as e:
        logger.error(f"\n\n❌ Критическая ошибка: {e}")
