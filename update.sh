#!/bin/bash

###############################################################################
# Скрипт автоматического обновления GetLead с GitHub
# Использование: ./update.sh
###############################################################################

set -e  # Останавливаться при ошибках

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Конфигурация
PROJECT_DIR="/home/getlead"
LOG_FILE="/home/getlead/update.log"

# Функции для логирования
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Проверка, что скрипт запущен из правильной директории
if [ ! -d "$PROJECT_DIR" ]; then
    error "Директория проекта не найдена: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

log "=========================================="
log "Начало обновления GetLead"
log "=========================================="

# 1. Проверка обновлений
log "Проверка обновлений из GitHub..."
git fetch origin

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})
BASE=$(git merge-base @ @{u})

if [ $LOCAL = $REMOTE ]; then
    log "Проект уже обновлён до последней версии"
    exit 0
elif [ $LOCAL = $BASE ]; then
    log "Найдены новые обновления"
elif [ $REMOTE = $BASE ]; then
    warning "Локальная версия новее удалённой"
    exit 0
else
    error "Ветки разошлись. Требуется ручное разрешение конфликтов"
    exit 1
fi

# 2. Получение обновлений
log "Скачивание обновлений..."
git pull origin main || {
    error "Ошибка при git pull"
    exit 1
}

# 3. Проверка изменений в requirements.txt или новых Python файлов
NEED_DEPS_UPDATE=false

if git diff HEAD@{1} HEAD --name-only | grep -q "requirements.txt"; then
    NEED_DEPS_UPDATE=true
    log "Обнаружены изменения в requirements.txt"
fi

# Также обновляем зависимости если добавлены новые .py файлы в utils/
if git diff HEAD@{1} HEAD --name-only | grep -q "utils/.*\.py"; then
    NEED_DEPS_UPDATE=true
    log "Обнаружены новые утилиты, проверяем зависимости..."
fi

if [ "$NEED_DEPS_UPDATE" = true ]; then
    log "Обновление зависимостей Python..."
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt || {
        error "Ошибка при установке зависимостей"
        exit 1
    }
    deactivate
else
    log "Зависимости не изменились, пропускаем обновление"
fi

# 4. Проверка изменений в моделях БД и применение миграций
if git diff HEAD@{1} HEAD --name-only | grep -q "database/models.py"; then
    warning "⚠️  Обнаружены изменения в моделях БД!"
    log "Применение миграций..."
    
    source venv/bin/activate
    
    # Проверяем наличие alembic.ini
    if [ -f "alembic.ini" ]; then
        log "Использование Alembic для миграции..."
        alembic upgrade head || {
            error "Ошибка миграции Alembic"
            warning "Попытка создать таблицы через SQLAlchemy..."
            python -c "import asyncio; from database.database import init_db; asyncio.run(init_db())" || {
                error "Ошибка создания таблиц"
            }
        }
    else
        log "Alembic не настроен. Создание таблиц через SQLAlchemy..."
        python -c "import asyncio; from database.database import init_db; asyncio.run(init_db())" || {
            error "Ошибка создания таблиц БД"
        }
    fi
    
    deactivate
    log "✅ Миграция БД завершена"
fi

# 5. Перезапуск сервисов
log "Перезапуск сервисов..."

# Останавливаем сервисы
systemctl stop getlead-userbot
systemctl stop getlead-bot

# Ждём завершения процессов
sleep 3

# Запускаем сервисы
systemctl start getlead-bot
systemctl start getlead-userbot

# Проверяем статус
sleep 2

if systemctl is-active --quiet getlead-bot; then
    log "✅ getlead-bot успешно запущен"
else
    error "❌ getlead-bot не запустился! Проверьте логи: journalctl -u getlead-bot -n 50"
    exit 1
fi

if systemctl is-active --quiet getlead-userbot; then
    log "✅ getlead-userbot успешно запущен"
else
    error "❌ getlead-userbot не запустился! Проверьте логи: journalctl -u getlead-userbot -n 50"
    exit 1
fi

# 6. Проверка здоровья приложения
log "Проверка работоспособности..."
sleep 5

# Проверяем, что процессы действительно работают
if pgrep -f "python.*main.py" > /dev/null; then
    log "✅ Bot процесс работает"
else
    error "❌ Bot процесс не найден"
fi

if pgrep -f "python.*run_userbot.py" > /dev/null; then
    log "✅ Userbot процесс работает"
else
    error "❌ Userbot процесс не найден"
fi

# 7. Очистка
log "Очистка временных файлов..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

log "=========================================="
log "✅ Обновление успешно завершено!"
log "=========================================="
log "Версия: $(git log -1 --pretty=format:'%h - %s (%ar)')"
log ""
log "Для просмотра логов:"
log "  Bot: journalctl -u getlead-bot -f"
log "  Userbot: journalctl -u getlead-userbot -f"
