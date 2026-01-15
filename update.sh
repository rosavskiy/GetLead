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
BACKUP_DIR="/home/getlead/backups"
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

# 1. Создание бэкапа (опционально)
log "Создание бэкапа текущей версии..."
BACKUP_NAME="backup_$(date '+%Y%m%d_%H%M%S')"
mkdir -p "$BACKUP_DIR"

# Копируем только важные файлы (не node_modules, venv и т.д.)
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.session' \
    --exclude='.git' \
    . 2>/dev/null || warning "Бэкап создан с предупреждениями"

log "Бэкап создан: $BACKUP_DIR/$BACKUP_NAME.tar.gz"

# Удаляем старые бэкапы (храним только последние 5)
cd "$BACKUP_DIR"
ls -t | tail -n +6 | xargs -r rm --
cd "$PROJECT_DIR"

# 2. Проверка обновлений
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

# 3. Получение обновлений
log "Скачивание обновлений..."
git pull origin main || {
    error "Ошибка при git pull. Откат к бэкапу..."
    tar -xzf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$PROJECT_DIR"
    exit 1
}

# 4. Проверка изменений в requirements.txt
if git diff HEAD@{1} HEAD --name-only | grep -q "requirements.txt"; then
    log "Обнаружены изменения в requirements.txt"
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

# 5. Проверка изменений в моделях БД
if git diff HEAD@{1} HEAD --name-only | grep -q "database/models.py"; then
    warning "⚠️  Обнаружены изменения в моделях БД!"
    warning "⚠️  Возможно, требуется миграция базы данных"
    warning "⚠️  Проверьте вручную: alembic upgrade head"
fi

# 6. Перезапуск сервисов
log "Перезапуск сервисов..."

# Останавливаем сервисы
sudo systemctl stop getlead-userbot
sudo systemctl stop getlead-bot

# Ждём завершения процессов
sleep 3

# Запускаем сервисы
sudo systemctl start getlead-bot
sudo systemctl start getlead-userbot

# Проверяем статус
sleep 2

if sudo systemctl is-active --quiet getlead-bot; then
    log "✅ getlead-bot успешно запущен"
else
    error "❌ getlead-bot не запустился! Проверьте логи: journalctl -u getlead-bot -n 50"
    exit 1
fi

if sudo systemctl is-active --quiet getlead-userbot; then
    log "✅ getlead-userbot успешно запущен"
else
    error "❌ getlead-userbot не запустился! Проверьте логи: journalctl -u getlead-userbot -n 50"
    exit 1
fi

# 7. Проверка здоровья приложения
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

# 8. Очистка
log "Очистка временных файлов..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

log "=========================================="
log "✅ Обновление успешно завершено!"
log "=========================================="
log "Версия: $(git log -1 --pretty=format:'%h - %s (%ar)')"
log ""
log "Для просмотра логов:"
log "  Bot: sudo journalctl -u getlead-bot -f"
log "  Userbot: sudo journalctl -u getlead-userbot -f"
