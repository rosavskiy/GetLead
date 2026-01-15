"""Тексты сообщений для бота"""

TEXTS = {
    'ru': {
        'start': """👋 Добро пожаловать в <b>GetLead</b>!

Я помогу вам находить целевых клиентов в Telegram-чатах по ключевым словам.

🔍 Вы настраиваете ключевые слова и чаты для мониторинга
📩 Я присылаю уведомления, когда нахожу совпадения
⚡ Можете быстро ответить потенциальному клиенту

Начните с создания проекта и настройки ключевых слов!""",
        
        'main_menu': '🏠 Главное меню',
        'projects_menu': '📁 Ваши проекты',
        'keywords_menu': '🔑 Ключевые слова',
        'exclude_menu': '🚫 Исключающие слова',
        'filters_menu': '🔧 Фильтры',
        'chats_menu': '💬 Чаты для мониторинга',
        'payment_menu': '💳 Тарифы и оплата',
        
        'project_created': '✅ Проект "{}" создан!',
        'project_activated': '✅ Проект "{}" активирован!',
        'project_deleted': '🗑 Проект удален',
        
        'keyword_added': '✅ Ключевое слово "{}" добавлено!',
        'keywords_cleared': '🗑 Все ключевые слова удалены',
        
        'chat_added': '✅ Чат добавлен: {}',
        'chat_exists': 'ℹ️ Этот чат уже добавлен',
        
        'no_subscription': '⚠️ У вас нет активной подписки. Оформите тариф для работы с ботом.',
        
        'enter_project_name': 'Введите название проекта:',
        'enter_keywords': 'Введите ключевые слова (каждое с новой строки):',
        'enter_chat_link': 'Отправьте ссылку на чат (t.me/...):',
    },
    'en': {
        'start': """👋 Welcome to <b>GetLead</b>!

I'll help you find target clients in Telegram chats by keywords.

🔍 You set up keywords and chats to monitor
📩 I send notifications when I find matches
⚡ You can quickly respond to potential clients

Start by creating a project and setting up keywords!""",
        
        'main_menu': '🏠 Main Menu',
        'projects_menu': '📁 Your Projects',
        'keywords_menu': '🔑 Keywords',
        'exclude_menu': '🚫 Exclude Words',
        'filters_menu': '🔧 Filters',
        'chats_menu': '💬 Chats to Monitor',
        'payment_menu': '💳 Plans & Payment',
        
        'project_created': '✅ Project "{}" created!',
        'project_activated': '✅ Project "{}" activated!',
        'project_deleted': '🗑 Project deleted',
        
        'keyword_added': '✅ Keyword "{}" added!',
        'keywords_cleared': '🗑 All keywords cleared',
        
        'chat_added': '✅ Chat added: {}',
        'chat_exists': 'ℹ️ This chat is already added',
        
        'no_subscription': '⚠️ You don\'t have an active subscription. Please subscribe to use the bot.',
        
        'enter_project_name': 'Enter project name:',
        'enter_keywords': 'Enter keywords (one per line):',
        'enter_chat_link': 'Send chat link (t.me/...):',
    }
}


def get_text(key: str, lang: str = 'ru', **kwargs) -> str:
    """Получить текст сообщения на нужном языке"""
    text = TEXTS.get(lang, TEXTS['ru']).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
