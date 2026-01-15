# Инструкция по развертыванию GetLead

## 🚀 Быстрый старт (для разработки)

### 1. Получение учетных данных

#### Telegram Bot Token
1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям и получите токен
4. Добавьте токен в `.env` как `BOT_TOKEN`

#### Telegram API Credentials (для юзербота)
1. Перейдите на [my.telegram.org](https://my.telegram.org)
2. Войдите с номером телефона
3. Перейдите в "API Development Tools"
4. Создайте новое приложение
5. Получите `api_id` и `api_hash`
6. Добавьте в `.env` как `USERBOT_1_API_ID` и `USERBOT_1_API_HASH`

⚠️ **Важно:** Для юзербота используйте отдельный Telegram-аккаунт, не ваш основной!

#### OpenAI API Key (опционально)
1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com)
2. Создайте API ключ
3. Добавьте в `.env` как `OPENAI_API_KEY`

### 2. Настройка базы данных

#### Вариант 1: PostgreSQL локально

**Windows:**
```powershell
# Установите PostgreSQL
# Скачайте с https://www.postgresql.org/download/windows/

# Создайте базу данных
psql -U postgres
CREATE DATABASE getlead_db;
CREATE USER getlead_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE getlead_db TO getlead_user;
\q
```

**Linux:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib

sudo -u postgres psql
CREATE DATABASE getlead_db;
CREATE USER getlead_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE getlead_db TO getlead_user;
\q
```

**Строка подключения:**
```
DATABASE_URL=postgresql+asyncpg://getlead_user:your_password@localhost:5432/getlead_db
```

#### Вариант 2: PostgreSQL в Docker

```bash
docker run -d \
  --name getlead-postgres \
  -e POSTGRES_DB=getlead_db \
  -e POSTGRES_USER=getlead_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  postgres:15
```

### 3. Настройка Redis

#### Вариант 1: Redis локально

**Windows:**
```powershell
# Скачайте Redis с https://github.com/microsoftarchive/redis/releases
# Запустите redis-server.exe
```

**Linux:**
```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

#### Вариант 2: Redis в Docker

```bash
docker run -d \
  --name getlead-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 4. Заполнение .env файла

```bash
# Скопируйте пример
cp .env.example .env

# Отредактируйте .env
nano .env  # или используйте любой редактор
```

Пример заполненного `.env`:

```env
# Bot
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789
ADMIN_IDS=123456789

# Database
DATABASE_URL=postgresql+asyncpg://getlead_user:password@localhost:5432/getlead_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Userbot 1
USERBOT_1_API_ID=12345678
USERBOT_1_API_HASH=abcdef1234567890abcdef1234567890
USERBOT_1_PHONE=+79001234567
USERBOT_1_SESSION_NAME=userbot_1

# OpenAI (опционально)
OPENAI_API_KEY=sk-...

# Payment (опционально)
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
CRYPTOBOT_TOKEN=...
```

### 5. Первый запуск

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите Control Bot
python main.py
```

При первом запуске создастся структура БД.

### 6. Запуск Userbot

```bash
# В отдельном терминале
python run_userbot.py
```

При первом запуске вам придет SMS с кодом подтверждения:
```
Please enter the code you received: 12345
```

После этого создастся `.session` файл, и в следующий раз код не понадобится.

## 🐳 Развертывание с Docker

### Создайте docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: getlead_db
      POSTGRES_USER: getlead_user
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  bot:
    build: .
    command: python main.py
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  userbot:
    build: .
    command: python run_userbot.py
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./sessions:/app/sessions
    restart: unless-stopped

volumes:
  postgres_data:
```

### Создайте Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### Запуск

```bash
docker-compose up -d
```

## 🌐 Развертывание на сервере

### 1. Подготовка сервера (Ubuntu 22.04)

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python
sudo apt install python3.11 python3.11-venv python3-pip -y

# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Установка Redis
sudo apt install redis-server -y

# Установка Git
sudo apt install git -y
```

### 2. Клонирование проекта

```bash
cd /opt
sudo git clone https://github.com/yourusername/getlead.git
cd getlead
sudo chown -R $USER:$USER /opt/getlead
```

### 3. Настройка виртуального окружения

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Настройка systemd сервисов

#### Control Bot: `/etc/systemd/system/getlead-bot.service`

```ini
[Unit]
Description=GetLead Telegram Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/getlead
Environment="PATH=/opt/getlead/venv/bin"
ExecStart=/opt/getlead/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Userbot: `/etc/systemd/system/getlead-userbot.service`

```ini
[Unit]
Description=GetLead Userbot Worker
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/getlead
Environment="PATH=/opt/getlead/venv/bin"
ExecStart=/opt/getlead/venv/bin/python run_userbot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 5. Запуск сервисов

```bash
sudo systemctl daemon-reload
sudo systemctl enable getlead-bot
sudo systemctl enable getlead-userbot
sudo systemctl start getlead-bot
sudo systemctl start getlead-userbot

# Проверка статуса
sudo systemctl status getlead-bot
sudo systemctl status getlead-userbot

# Просмотр логов
sudo journalctl -u getlead-bot -f
sudo journalctl -u getlead-userbot -f
```

## 🔒 Безопасность

### 1. Настройка firewall

```bash
sudo ufw allow 22/tcp
sudo ufw enable
```

### 2. Создание отдельного пользователя

```bash
sudo useradd -m -s /bin/bash getlead
sudo usermod -aG sudo getlead
```

### 3. Настройка прав на файлы

```bash
chmod 600 .env
chmod 600 *.session
```

## 📊 Мониторинг

### Настройка логирования

Логи сохраняются в:
- `/var/log/syslog` (через systemd)
- Или в файл, если настроить в коде

### Проверка работоспособности

```bash
# Проверка БД
psql -U getlead_user -d getlead_db -c "SELECT COUNT(*) FROM users;"

# Проверка Redis
redis-cli ping

# Проверка сервисов
systemctl status getlead-bot
systemctl status getlead-userbot
```

## 🔄 Обновление

```bash
cd /opt/getlead
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart getlead-bot
sudo systemctl restart getlead-userbot
```

## 🐛 Troubleshooting

### Проблема: База данных не подключается

**Решение:**
```bash
# Проверьте, запущен ли PostgreSQL
sudo systemctl status postgresql

# Проверьте права доступа в pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

### Проблема: Userbot не может войти

**Решение:**
- Убедитесь, что номер телефона указан в международном формате: `+79001234567`
- Проверьте, что API_ID и API_HASH корректные
- Удалите `.session` файлы и попробуйте снова

### Проблема: FloodWaitError

**Решение:**
- Это ограничение Telegram, нужно подождать указанное время
- Используйте несколько юзерботов для распределения нагрузки

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `sudo journalctl -u getlead-bot -f`
2. Убедитесь, что все переменные окружения заполнены
3. Обратитесь в поддержку: support@getlead.bot
