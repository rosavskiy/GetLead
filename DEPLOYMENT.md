# Инструкция по развертыванию GetLead

## 🎯 Рекомендуемое развертывание (Debian 12 | 1 CPU / 4 GB RAM)

> **Для серверов с ограниченными ресурсами (1 core, 4 GB RAM, 10 GB disk) рекомендуется развертывание БЕЗ Docker**

### Почему без Docker?

- ✅ Экономия 300-500 MB RAM (без Docker оверхеда)
- ✅ Быстрее работает на 1 CPU core
- ✅ Меньше занимает места на диске (~2 GB вместо ~3.5 GB)
- ✅ Проще управление через systemd
- ✅ Прямой доступ к логам и процессам

### Пошаговая инструкция

#### Шаг 1: Подключитесь к серверу

```bash
ssh root@138.124.29.247
```

#### Шаг 2: Создайте пользователя для приложения

```bash
# Создать пользователя
useradd -m -s /bin/bash getlead
usermod -aG sudo getlead

# Переключиться на нового пользователя
su - getlead
cd ~
```

#### Шаг 3: Установите зависимости

```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить необходимые пакеты и зависимости для сборки
sudo apt install -y software-properties-common build-essential libssl-dev libffi-dev

# Установить Python 3.11 (Debian 12 поставляется с Python 3.11 по умолчанию)
sudo apt install -y python3 python3-venv python3-pip git

# Установить PostgreSQL 15
sudo apt install -y postgresql postgresql-contrib

# Установить Redis
sudo apt install -y redis-server
```

#### Шаг 4: Оптимизация PostgreSQL для 4 GB RAM

```bash
# Найти версию PostgreSQL
PG_VERSION=$(ls /etc/postgresql/ | head -n1)

# Редактировать конфигурацию PostgreSQL (обычно версия 15 в Debian 12)
sudo nano /etc/postgresql/$PG_VERSION/main/postgresql.conf
# Или напрямую:
sudo nano /etc/postgresql/15/main/postgresql.conf
```

Измените следующие параметры:

```ini
# Оптимизация для 4 GB RAM
shared_buffers = 512MB              # было 128MB
effective_cache_size = 2GB          # было 4GB
maintenance_work_mem = 128MB        # было 64MB
work_mem = 16MB                     # было 4MB
max_connections = 50                # было 100

# Производительность
random_page_cost = 1.1              # для SSD
effective_io_concurrency = 200      # для SSD
```

Сохраните (Ctrl+O, Enter, Ctrl+X) и перезапустите PostgreSQL:

```bash
sudo systemctl restart postgresql
```

#### Шаг 5: Оптимизация Redis для ограниченной памяти

```bash
sudo nano /etc/redis/redis.conf
```

Добавьте/измените:

```ini
maxmemory 256mb
maxmemory-policy allkeys-lru
save ""  # отключить сохранение на диск (FSM данные можно восстановить)
```

Перезапустите Redis:

```bash
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

#### Шаг 6: Создайте базу данных

```bash
sudo -u postgres psql
```

В консоли PostgreSQL:

```sql
CREATE DATABASE getlead_db;
CREATE USER getlead_user WITH PASSWORD 'ВАШ_НАДЕЖНЫЙ_ПАРОЛЬ';
GRANT ALL PRIVILEGES ON DATABASE getlead_db TO getlead_user;
\q
```

#### Шаг 7: Клонируйте проект

```bash
cd /home/getlead
git clone https://github.com/ВАШ_USERNAME/getlead.git
cd getlead
```

#### Шаг 8: Настройте виртуальное окружение

```bash
# В Debian 12 Python 3.11 доступен как python3
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Шаг 9: Настройте .env файл

```bash
cp .env.example .env
nano .env
```

Заполните все необходимые переменные:

```env
# Bot
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_IDS=ваш_telegram_id

# Database (замените пароль)
DATABASE_URL=postgresql+asyncpg://getlead_user:ВАШ_ПАРОЛЬ@localhost:5432/getlead_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Userbot 1 (получите на my.telegram.org)
USERBOT_1_API_ID=12345678
USERBOT_1_API_HASH=abcdef1234567890
USERBOT_1_PHONE=+79001234567
USERBOT_1_SESSION_NAME=userbot_1

# OpenAI (опционально)
OPENAI_API_KEY=sk-...

# Production settings
DEBUG=false
LOG_LEVEL=INFO
```

Сохраните и защитите файл:

```bash
chmod 600 .env
```

#### Шаг 10: Инициализируйте базу данных

```bash
source venv/bin/activate
python main.py
# Нажмите Ctrl+C после инициализации таблиц
```

#### Шаг 11: Авторизуйте userbot (первый раз)

```bash
python run_userbot.py
# Введите код из SMS
# После успешной авторизации нажмите Ctrl+C
```

#### Шаг 12: Создайте systemd сервисы

##### Control Bot сервис

```bash
sudo nano /etc/systemd/system/getlead-bot.service
```

```ini
[Unit]
Description=GetLead Telegram Bot
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=getlead
WorkingDirectory=/home/getlead/getlead
Environment="PATH=/home/getlead/getlead/venv/bin"
ExecStart=/home/getlead/getlead/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Ограничения ресурсов
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

##### Userbot сервис

```bash
sudo nano /etc/systemd/system/getlead-userbot.service
```

```ini
[Unit]
Description=GetLead Userbot Worker
After=network.target postgresql.service redis.service getlead-bot.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=getlead
WorkingDirectory=/home/getlead/getlead
Environment="PATH=/home/getlead/getlead/venv/bin"
ExecStart=/home/getlead/getlead/venv/bin/python run_userbot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Ограничения ресурсов
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

#### Шаг 13: Запустите сервисы

```bash
# Перезагрузить конфигурацию systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable getlead-bot
sudo systemctl enable getlead-userbot

# Запустить сервисы
sudo systemctl start getlead-bot
sudo systemctl start getlead-userbot

# Проверить статус
sudo systemctl status getlead-bot
sudo systemctl status getlead-userbot
```

#### Шаг 14: Настройте firewall

```bash
# Установить и настроить UFW
sudo apt install ufw
sudo ufw allow 22/tcp
sudo ufw enable
```

#### Шаг 15: Настройте ротацию логов

```bash
sudo nano /etc/logrotate.d/getlead
```

```text
/var/log/getlead/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 getlead getlead
}
```

### 📊 Мониторинг и управление

#### Просмотр логов

```bash
# Логи бота
sudo journalctl -u getlead-bot -f

# Логи юзербота
sudo journalctl -u getlead-userbot -f

# Последние 100 строк
sudo journalctl -u getlead-bot -n 100

# Логи за сегодня
sudo journalctl -u getlead-bot --since today
```

#### Перезапуск сервисов

```bash
sudo systemctl restart getlead-bot
sudo systemctl restart getlead-userbot
```

#### Остановка сервисов:

```bash
sudo systemctl stop getlead-bot
sudo systemctl stop getlead-userbot
```

#### Проверка ресурсов:

```bash
# Использование памяти
free -h

# Процессы Python
ps aux | grep python

# Использование диска
df -h

# Статистика PostgreSQL
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('getlead_db'));"

# Статистика Redis
redis-cli INFO memory
```

### 🔄 Обновление проекта

```bash
cd /home/getlead/getlead
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart getlead-bot
sudo systemctl restart getlead-userbot
```

### 🛠 Troubleshooting

#### Бот не запускается:

```bash
# Проверить логи на ошибки
sudo journalctl -u getlead-bot -n 50

# Проверить файл .env
cat .env | grep -v "PASSWORD\|SECRET\|TOKEN" # безопасный просмотр

# Проверить подключение к БД
sudo -u getlead psql -U getlead_user -d getlead_db -h localhost
```

#### Userbot теряет соединение:

```bash
# Пересоздать сессию
cd /home/getlead/getlead
rm *.session
python run_userbot.py  # Авторизоваться заново
```

#### Нехватка памяти:

```bash
# Проверить, что не запущены лишние процессы
systemctl list-units --type=service --state=running

# Добавить swap (если нет)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 📈 Оптимизация производительности

1. **Отключите лишние сервисы:**
```bash
sudo systemctl disable snapd
sudo systemctl stop snapd
```

2. **Настройте лимиты для Python процессов** (уже в systemd сервисах):
   - MemoryMax=512M (максимум памяти)
   - CPUQuota=50% (50% от 1 core)

3. **Мониторинг памяти:**
```bash
# Создать скрипт мониторинга
cat > /home/getlead/monitor.sh << 'EOF'
#!/bin/bash
echo "=== Memory Usage ==="
free -h
echo ""
echo "=== GetLead Processes ==="
ps aux | grep -E "getlead|python" | grep -v grep
echo ""
echo "=== PostgreSQL ==="
systemctl status postgresql | grep -E "Active|Memory"
echo ""
echo "=== Redis ==="
systemctl status redis-server | grep -E "Active|Memory"
EOF

chmod +x /home/getlead/monitor.sh

# Запускать при необходимости
/home/getlead/monitor.sh
```

### ✅ Контрольный список готовности

- [ ] PostgreSQL установлен и оптимизирован
- [ ] Redis установлен с ограничением памяти
- [ ] База данных создана
- [ ] Проект склонирован и зависимости установлены
- [ ] Файл .env заполнен и защищен (chmod 600)
- [ ] Userbot авторизован (есть .session файл)
- [ ] Systemd сервисы созданы и включены
- [ ] Firewall настроен
- [ ] Логи доступны через journalctl
- [ ] Бот отвечает в Telegram

### 💰 Использование ресурсов (ожидаемое)

| Компонент | RAM | CPU | Disk |
|-----------|-----|-----|------|
| PostgreSQL | ~250 MB | 5-10% | ~200 MB |
| Redis | ~100 MB | 1-2% | ~50 MB |
| Bot | ~150 MB | 5-15% | ~100 MB |
| Userbot | ~200 MB | 10-20% | ~100 MB |
| System | ~300 MB | 5% | ~2 GB |
| **Итого** | **~1 GB** | **25-50%** | **~2.5 GB** |

**Резерв:** 3 GB RAM свободно для пиковых нагрузок

---

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

### 1. Подготовка сервера (Debian 12)

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых зависимостей
sudo apt install -y software-properties-common build-essential

# Установка Python (в Debian 12 уже есть Python 3.11)
sudo apt install -y python3 python3-venv python3-pip

# Установка PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Установка Redis
sudo apt install -y redis-server

# Установка Git
sudo apt install -y git
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
python3 -m venv venv
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

# Проверьте права доступа в pg_hba.conf (версия может отличаться)
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
3. Обратитесь в поддержку: <support@getlead.bot>
