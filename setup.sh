#!/bin/bash

echo "========================================"
echo "GetLead - Quick Start Script"
echo "========================================"
echo ""

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 не установлен! Установите Python 3.10+"
    exit 1
fi

echo "[1/5] Проверка Python... OK"
echo ""

# Проверка наличия venv
if [ ! -d "venv" ]; then
    echo "[2/5] Создание виртуального окружения..."
    python3 -m venv venv
    echo "Виртуальное окружение создано!"
else
    echo "[2/5] Виртуальное окружение уже существует"
fi
echo ""

# Активация venv
echo "[3/5] Активация виртуального окружения..."
source venv/bin/activate
echo ""

# Установка зависимостей
echo "[4/5] Установка зависимостей..."
pip install -r requirements.txt
echo ""

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "[5/5] Создание .env файла из шаблона..."
    cp .env.example .env
    echo ""
    echo "[WARNING] Файл .env создан! НЕОБХОДИМО заполнить его перед запуском!"
    echo ""
    echo "Откройте .env в текстовом редакторе и заполните:"
    echo "- BOT_TOKEN"
    echo "- DATABASE_URL"
    echo "- USERBOT_1_API_ID, USERBOT_1_API_HASH, USERBOT_1_PHONE"
    echo ""
else
    echo "[5/5] Файл .env найден"
fi
echo ""

echo "========================================"
echo "Установка завершена!"
echo "========================================"
echo ""
echo "Для запуска бота:"
echo "1. Убедитесь, что PostgreSQL и Redis запущены"
echo "2. Заполните .env файл"
echo "3. Запустите: python main.py"
echo "4. В другом терминале: python run_userbot.py"
echo ""
echo "Подробная инструкция: DEPLOYMENT.md"
echo "========================================"
