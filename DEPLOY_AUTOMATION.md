# 🚀 Автоматизация развертывания и обновлений

## Варианты обновления

### 1. Ручное обновление (простой способ)

Запустите скрипт на сервере:

```bash
cd /home/getlead/getlead
./update.sh
```

**Что делает скрипт:**
- ✅ Создает бэкап текущей версии
- ✅ Скачивает обновления с GitHub
- ✅ Обновляет зависимости (если изменился requirements.txt)
- ✅ Перезапускает сервисы
- ✅ Проверяет работоспособность
- ✅ Логирует все действия

### 2. Автоматическое обновление через GitHub Webhook (продвинутый)

При каждом `git push` в `main` ветку бот автоматически обновится на сервере.

## 📋 Установка автоматического обновления

### Шаг 1: Подготовка на сервере

```bash
# Подключитесь к серверу
ssh getlead@your-server-ip

# Перейдите в директорию проекта
cd /home/getlead/getlead

# Сделайте скрипты исполняемыми
chmod +x update.sh
chmod +x deploy/setup_webhook.sh

# Запустите установку webhook
./deploy/setup_webhook.sh
```

Скрипт выдаст секретный ключ:
```
Ваш секретный ключ: a1b2c3d4e5f6...
Сохраните его! Понадобится для настройки GitHub
```

### Шаг 2: Настройка GitHub Webhook

1. Откройте ваш репозиторий на GitHub
2. Перейдите в **Settings** → **Webhooks** → **Add webhook**
3. Заполните форму:

```
Payload URL: http://YOUR_SERVER_IP:5000/webhook
Content type: application/json
Secret: (вставьте секретный ключ из шага 1)
```

4. В разделе **Which events would you like to trigger this webhook?**:
   - Выберите **Just the push event**

5. Нажмите **Add webhook**

### Шаг 3: Проверка работы

```bash
# На вашем локальном компьютере
cd /path/to/getlead
echo "test" >> README.md
git add README.md
git commit -m "Test auto-update"
git push origin main

# На сервере проверьте логи
ssh getlead@your-server-ip
sudo journalctl -u getlead-webhook -f
```

Вы должны увидеть:
```
📥 Получен webhook event: push
📝 Последний коммит: "Test auto-update" от YourName
🚀 Запуск скрипта обновления...
✅ Обновление завершено успешно
```

## 🔒 Безопасность (для продакшена)

### Настройка Nginx Reverse Proxy

```bash
sudo apt install nginx

# Создайте конфиг
sudo nano /etc/nginx/sites-available/webhook
```

```nginx
server {
    listen 80;
    server_name webhook.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активируйте конфиг
sudo ln -s /etc/nginx/sites-available/webhook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Установите SSL сертификат
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d webhook.yourdomain.com
```

Теперь webhook URL будет:
```
https://webhook.yourdomain.com/webhook
```

## 📊 Мониторинг

### Просмотр логов обновлений

```bash
# Логи webhook сервиса
sudo journalctl -u getlead-webhook -f

# Логи скрипта обновления
tail -f /home/getlead/update.log

# Логи бота после обновления
sudo journalctl -u getlead-bot -n 50
sudo journalctl -u getlead-userbot -n 50
```

### Статус сервисов

```bash
# Проверить все сервисы GetLead
sudo systemctl status getlead-bot
sudo systemctl status getlead-userbot
sudo systemctl status getlead-webhook

# Или одной командой
sudo systemctl status 'getlead-*'
```

## 🛠 Управление обновлениями

### Откат к предыдущей версии

Если обновление прошло неудачно:

```bash
cd /home/getlead/getlead

# Посмотреть доступные бэкапы
ls -lh /home/getlead/backups/

# Восстановить из бэкапа
tar -xzf /home/getlead/backups/backup_20260115_143022.tar.gz -C /home/getlead/getlead

# Перезапустить сервисы
sudo systemctl restart getlead-bot
sudo systemctl restart getlead-userbot
```

### Ручной перезапуск без обновления

```bash
# Перезапустить только бота
sudo systemctl restart getlead-bot

# Перезапустить только юзербота
sudo systemctl restart getlead-userbot

# Перезапустить всё
sudo systemctl restart getlead-bot getlead-userbot
```

### Временное отключение автообновлений

```bash
# Остановить webhook сервис
sudo systemctl stop getlead-webhook

# Отключить автозапуск
sudo systemctl disable getlead-webhook

# Включить обратно
sudo systemctl enable getlead-webhook
sudo systemctl start getlead-webhook
```

## 🎯 Best Practices

### 1. Тестирование перед деплоем

Создайте тестовую ветку:

```bash
git checkout -b test-feature
# Делайте изменения
git push origin test-feature
```

Webhook **не сработает** (только для main ветки), можно тестировать локально.

После тестирования:
```bash
git checkout main
git merge test-feature
git push origin main  # Теперь сработает автообновление
```

### 2. Миграции базы данных

Если вы изменили `database/models.py`:

```bash
# На локальной машине
alembic revision --autogenerate -m "Add new field"
git add alembic/versions/*
git commit -m "DB migration: add new field"
git push origin main
```

На сервере автоматически запустится скрипт, но нужно **вручную** применить миграцию:

```bash
ssh getlead@server
cd /home/getlead/getlead
source venv/bin/activate
alembic upgrade head
```

### 3. Критичные обновления

Для критичных изменений (изменения структуры БД, breaking changes):

1. Временно отключите webhook:
```bash
sudo systemctl stop getlead-webhook
```

2. Обновите вручную с контролем:
```bash
./update.sh
```

3. Проверьте работоспособность

4. Включите webhook обратно:
```bash
sudo systemctl start getlead-webhook
```

## 📞 Уведомления об обновлениях

Можно добавить уведомления в Telegram при успешном обновлении.

Отредактируйте `update.sh`, добавьте в конец:

```bash
# Отправка уведомления в Telegram
TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_admin_chat_id"
MESSAGE="✅ GetLead обновлён до версии: $(git log -1 --pretty=format:'%h - %s')"

curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
     -d chat_id="${TELEGRAM_CHAT_ID}" \
     -d text="${MESSAGE}" > /dev/null
```

## 🔧 Troubleshooting

### Webhook не срабатывает

```bash
# Проверьте, запущен ли сервис
sudo systemctl status getlead-webhook

# Проверьте логи
sudo journalctl -u getlead-webhook -n 50

# Проверьте доступность порта
curl http://localhost:5000/health

# Проверьте firewall
sudo ufw status
```

### Обновление зависло

```bash
# Проверьте процессы
ps aux | grep python

# Убейте зависший процесс
sudo systemctl stop getlead-webhook
sudo systemctl restart getlead-bot getlead-userbot
```

### Git конфликты

```bash
cd /home/getlead/getlead

# Сбросить локальные изменения
git reset --hard HEAD

# Снова попробовать обновиться
./update.sh
```

---

**Готово!** Теперь ваш бот будет автоматически обновляться при каждом `git push` в main ветку.
