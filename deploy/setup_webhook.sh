#!/bin/bash

###############################################################################
# Скрипт настройки автоматического обновления через GitHub Webhook
###############################################################################

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=========================================="
echo "Настройка GitHub Webhook"
echo -e "==========================================${NC}"

# 1. Установка зависимостей
echo -e "${GREEN}1. Установка зависимостей...${NC}"
source /home/getlead/getlead/venv/bin/activate
pip install flask gunicorn
deactivate

# 2. Создание секретного ключа
echo -e "${GREEN}2. Генерация секретного ключа...${NC}"
SECRET=$(openssl rand -hex 32)
echo -e "${YELLOW}Ваш секретный ключ:${NC} $SECRET"
echo -e "${YELLOW}Сохраните его! Понадобится для настройки GitHub${NC}"

# 3. Создание systemd service
echo -e "${GREEN}3. Установка systemd service...${NC}"
sudo sed "s/your-secret-key-change-this/$SECRET/" /home/getlead/getlead/deploy/webhook.service > /tmp/webhook.service
sudo mv /tmp/webhook.service /etc/systemd/system/getlead-webhook.service

# 4. Сделать update.sh исполняемым
echo -e "${GREEN}4. Настройка прав доступа...${NC}"
chmod +x /home/getlead/getlead/update.sh
chmod +x /home/getlead/getlead/webhook_update.py

# 5. Настройка sudo без пароля для перезапуска сервисов
echo -e "${GREEN}5. Настройка sudo...${NC}"
echo "getlead ALL=(ALL) NOPASSWD: /bin/systemctl start getlead-bot" | sudo tee /etc/sudoers.d/getlead-update
echo "getlead ALL=(ALL) NOPASSWD: /bin/systemctl stop getlead-bot" | sudo tee -a /etc/sudoers.d/getlead-update
echo "getlead ALL=(ALL) NOPASSWD: /bin/systemctl start getlead-userbot" | sudo tee -a /etc/sudoers.d/getlead-update
echo "getlead ALL=(ALL) NOPASSWD: /bin/systemctl stop getlead-userbot" | sudo tee -a /etc/sudoers.d/getlead-update
echo "getlead ALL=(ALL) NOPASSWD: /bin/systemctl restart getlead-bot" | sudo tee -a /etc/sudoers.d/getlead-update
echo "getlead ALL=(ALL) NOPASSWD: /bin/systemctl restart getlead-userbot" | sudo tee -a /etc/sudoers.d/getlead-update
echo "getlead ALL=(ALL) NOPASSWD: /bin/systemctl is-active getlead-bot" | sudo tee -a /etc/sudoers.d/getlead-update
echo "getlead ALL=(ALL) NOPASSWD: /bin/systemctl is-active getlead-userbot" | sudo tee -a /etc/sudoers.d/getlead-update
sudo chmod 0440 /etc/sudoers.d/getlead-update

# 6. Настройка firewall
echo -e "${GREEN}6. Настройка firewall...${NC}"
sudo ufw allow 5000/tcp comment 'GetLead Webhook'

# 7. Запуск сервиса
echo -e "${GREEN}7. Запуск webhook сервиса...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable getlead-webhook
sudo systemctl start getlead-webhook

# Проверка статуса
sleep 2
if sudo systemctl is-active --quiet getlead-webhook; then
    echo -e "${GREEN}✅ Webhook сервис успешно запущен!${NC}"
else
    echo -e "${YELLOW}⚠️  Webhook сервис не запустился. Проверьте: journalctl -u getlead-webhook${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "✅ Настройка завершена!"
echo -e "==========================================${NC}"
echo ""
echo -e "${YELLOW}📝 Следующие шаги:${NC}"
echo ""
echo "1. Перейдите в настройки вашего GitHub репозитория:"
echo "   Settings → Webhooks → Add webhook"
echo ""
echo "2. Заполните форму:"
echo "   Payload URL: http://$(curl -s ifconfig.me):5000/webhook"
echo "   Content type: application/json"
echo "   Secret: $SECRET"
echo "   Events: Just the push event"
echo ""
echo "3. Сохраните webhook"
echo ""
echo "4. Протестируйте:"
echo "   - Сделайте коммит в main ветку"
echo "   - Проверьте логи: sudo journalctl -u getlead-webhook -f"
echo ""
echo -e "${YELLOW}🔒 Для продакшена настройте nginx reverse proxy с HTTPS!${NC}"
