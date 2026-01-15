"""Запуск юзерботов для мониторинга чатов"""
import asyncio
import logging
from config import settings
from userbot.worker import UserbotWorker

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Запуск всех юзерботов из конфигурации"""
    
    workers = []
    
    for bot_config in settings.userbots_config:
        worker = UserbotWorker(
            api_id=bot_config['api_id'],
            api_hash=bot_config['api_hash'],
            session_name=bot_config['session_name'],
            phone=bot_config['phone']
        )
        workers.append(worker)
    
    if not workers:
        logger.error("Нет настроенных юзерботов! Проверьте .env файл")
        return
    
    logger.info(f"Запуск {len(workers)} юзерботов...")
    
    # Запускаем всех воркеров параллельно
    # Используем gather с return_exceptions=True для обработки ошибок
    tasks = [worker.start() for worker in workers]
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == '__main__':
    asyncio.run(main())
