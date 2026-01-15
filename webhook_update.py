#!/usr/bin/env python3
"""
Webhook сервер для автоматического обновления при push в GitHub

Установка:
1. pip install flask
2. Настройте GitHub Webhook:
   - Payload URL: http://your-server-ip:5000/webhook
   - Content type: application/json
   - Secret: установите в WEBHOOK_SECRET
   - Events: Just the push event

3. Запустите: python webhook_update.py
   Или создайте systemd service для автозапуска

Безопасность:
- Используйте секретный ключ
- Запускайте за nginx/reverse proxy
- Используйте HTTPS в продакшене
"""

import os
import hmac
import hashlib
import subprocess
import logging
from flask import Flask, request, jsonify

# Конфигурация
WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET', 'your-secret-key-here')
UPDATE_SCRIPT = '/home/getlead/getlead/update.sh'
ALLOWED_BRANCH = 'main'  # Обновляться только при push в main

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/getlead/webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def verify_signature(payload_body, signature_header):
    """Проверка подписи GitHub webhook"""
    if not signature_header:
        return False
    
    hash_algorithm, github_signature = signature_header.split('=')
    
    if hash_algorithm != 'sha256':
        return False
    
    mac = hmac.new(
        WEBHOOK_SECRET.encode(),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    
    return hmac.compare_digest(mac.hexdigest(), github_signature)


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик GitHub webhook"""
    
    # Проверка подписи
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        logger.warning('❌ Неверная подпись webhook')
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Получаем данные
    event = request.headers.get('X-GitHub-Event')
    payload = request.json
    
    logger.info(f'📥 Получен webhook event: {event}')
    
    # Обрабатываем только push события
    if event != 'push':
        logger.info(f'ℹ️  Игнорируем event: {event}')
        return jsonify({'message': 'Event ignored'}), 200
    
    # Проверяем ветку
    ref = payload.get('ref', '')
    branch = ref.replace('refs/heads/', '')
    
    if branch != ALLOWED_BRANCH:
        logger.info(f'ℹ️  Игнорируем push в ветку: {branch}')
        return jsonify({'message': f'Branch {branch} ignored'}), 200
    
    # Получаем информацию о коммите
    commits = payload.get('commits', [])
    if commits:
        last_commit = commits[-1]
        commit_msg = last_commit.get('message', 'No message')
        author = last_commit.get('author', {}).get('name', 'Unknown')
        logger.info(f'📝 Последний коммит: "{commit_msg}" от {author}')
    
    # Запускаем скрипт обновления
    logger.info(f'🚀 Запуск скрипта обновления: {UPDATE_SCRIPT}')
    
    try:
        result = subprocess.run(
            ['bash', UPDATE_SCRIPT],
            capture_output=True,
            text=True,
            timeout=300  # 5 минут максимум
        )
        
        if result.returncode == 0:
            logger.info('✅ Обновление завершено успешно')
            return jsonify({
                'message': 'Update successful',
                'output': result.stdout
            }), 200
        else:
            logger.error(f'❌ Ошибка обновления: {result.stderr}')
            return jsonify({
                'error': 'Update failed',
                'output': result.stderr
            }), 500
            
    except subprocess.TimeoutExpired:
        logger.error('❌ Превышено время ожидания обновления')
        return jsonify({'error': 'Update timeout'}), 500
    except Exception as e:
        logger.error(f'❌ Ошибка при запуске обновления: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/', methods=['GET'])
def index():
    """Главная страница"""
    return jsonify({
        'service': 'GetLead Auto-Update Webhook',
        'status': 'running',
        'endpoints': {
            '/webhook': 'POST - GitHub webhook endpoint',
            '/health': 'GET - Health check'
        }
    }), 200


if __name__ == '__main__':
    # В продакшене используйте gunicorn:
    # gunicorn -w 2 -b 0.0.0.0:5000 webhook_update:app
    
    logger.info('🚀 Запуск webhook сервера...')
    logger.info(f'📂 Update script: {UPDATE_SCRIPT}')
    logger.info(f'🌿 Allowed branch: {ALLOWED_BRANCH}')
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
