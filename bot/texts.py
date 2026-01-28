"""Тексты сообщений для бота"""

TEXTS = {
    'ru': {
        # Приветствие и выбор языка
        'choose_language': """🌍 <b>Выберите язык / Choose language</b>

Выберите язык, на котором хотите продолжить:
Choose the language you want to continue with:""",
        
        'start': """👋 Добро пожаловать в <b>GetLead</b>!

Я помогу вам находить целевых клиентов в Telegram-чатах по ключевым словам.

🔍 Вы настраиваете ключевые слова и чаты для мониторинга
📩 Я присылаю уведомления, когда нахожу совпадения
⚡ Можете быстро ответить потенциальному клиенту

Начните с создания проекта и настройки ключевых слов!""",
        
        # Меню
        'main_menu': '🏠 Главное меню',
        'projects_menu': '📁 Ваши проекты',
        'keywords_menu': '🔑 Ключевые слова',
        'exclude_menu': '🚫 Исключающие слова',
        'filters_menu': '🔧 Фильтры',
        'chats_menu': '💬 Чаты для мониторинга',
        'payment_menu': '💳 Тарифы и оплата',
        
        # Кнопки главного меню
        'btn_profile': '👤 Профиль',
        'btn_stats': '📊 Статистика',
        'btn_projects': '📁 Проекты',
        'btn_keywords': '🔑 Ключевые слова',
        'btn_exclude': '🚫 Исключающие слова',
        'btn_filters': '🔧 Фильтры',
        'btn_chats': '💬 Чаты',
        'btn_payment': '💳 Тарифы',
        'btn_integrations': '🔗 Интеграции',
        'btn_help': '❓ Помощь',
        'btn_back': '🔙 Назад',
        'btn_back_main': '🔙 Главное меню',
        'btn_cancel': '❌ Отмена',
        
        # Проекты
        'project_created': '✅ Проект "{}" создан!',
        'project_activated': '✅ Проект "{}" активирован!',
        'project_deleted': '🗑 Проект удален',
        'btn_create_project': '➕ Создать проект',
        'btn_delete_project': '🗑 Удалить проект',
        'enter_project_name': 'Введите название проекта:',
        'no_projects': '📁 У вас пока нет проектов.\n\nСоздайте первый проект, чтобы начать мониторинг!',
        
        # Ключевые слова
        'keyword_added': '✅ Ключевое слово "{}" добавлено!',
        'keywords_cleared': '🗑 Все ключевые слова удалены',
        'btn_add_keywords': '➕ Добавить слова',
        'btn_ai_suggest': '🤖 AI подбор',
        'btn_show_list': '📋 Показать список',
        'btn_clear_all': '🗑 Удалить все',
        'enter_keywords': 'Введите ключевые слова (каждое с новой строки):',
        'no_keywords': '🔑 У вас пока нет ключевых слов.\n\nДобавьте слова для поиска лидов!',
        'keywords_list': '🔑 <b>Ваши ключевые слова:</b>\n\n',
        
        # Чаты
        'chat_added': '✅ Чат добавлен: {}',
        'chat_exists': 'ℹ️ Этот чат уже добавлен',
        'btn_my_chats': '📋 Мои чаты',
        'btn_chat_packs': '📦 Пакетные чаты',
        'btn_add_chat': '➕ Добавить чат',
        'enter_chat_link': 'Отправьте ссылку на чат (t.me/...):',
        'no_chats': '💬 У вас пока нет чатов для мониторинга.\n\nДобавьте чаты, в которых нужно искать лидов!',
        
        # Подписка
        'no_subscription': '⚠️ У вас нет активной подписки. Оформите тариф для работы с ботом.',
        'btn_card_payment': '💳 Банковская карта',
        'btn_crypto_payment': '₿ Криптовалюта',
        
        # Профиль
        'profile_title': '👤 <b>Личный кабинет</b>',
        'profile_id': '📱 <b>ID:</b>',
        'profile_username': '👤 <b>Username:</b>',
        'profile_registered': '📅 <b>Регистрация:</b>',
        'profile_plan': '💳 <b>Тариф:</b>',
        'profile_expires': '⏳ <b>До окончания:</b>',
        'profile_expires_date': '📆 <b>Истекает:</b>',
        'profile_stats': '📊 <b>Статистика</b>',
        'profile_projects': '📁 <b>Проектов:</b>',
        'profile_chats': '💬 <b>Чатов:</b>',
        'profile_leads': '🎯 <b>Найдено лидов:</b>',
        'profile_today': 'Сегодня',
        'profile_week': 'За неделю',
        'profile_total': 'Всего',
        'btn_detailed_stats': '📊 Детальная статистика',
        'btn_recent_leads': '🎯 Последние лиды',
        'btn_settings': '⚙️ Настройки',
        
        # Настройки
        'settings_title': '⚙️ <b>Настройки</b>',
        'settings_language': '🌐 <b>Язык:</b>',
        'settings_notifications': '🔔 <b>Уведомления:</b>',
        'settings_integrations': '🔗 <b>Интеграции:</b>',
        'settings_tip': '💡 Для настройки интеграций используйте меню ниже.',
        'btn_change_language': '🌐 Сменить язык',
        'btn_notifications': '🔔 Уведомления',
        'notifications_enabled': 'Включены',
        'notifications_disabled': 'Отключены',
        'lang_russian': 'Русский 🇷🇺',
        'lang_english': 'English 🇬🇧',
        'language_changed': '✅ Язык изменён на {}',
        'choose_language_title': '🌐 <b>Выбор языка</b>\n\nВыберите язык интерфейса:',
        
        # Уведомления
        'notifications_title': '🔔 <b>Настройки уведомлений</b>',
        'notifications_current': 'Текущий статус:',
        'notifications_all': 'Все уведомления включены',
        'notifications_important': 'Только важные',
        'notifications_off': 'Отключены',
        'notifications_desc': """Выберите режим уведомлений:

• <b>Все уведомления</b> — получать уведомления о каждом найденном лиде
• <b>Только важные</b> — уведомления раз в час со сводкой
• <b>Отключить</b> — не получать уведомления (лиды сохраняются)""",
        'btn_notif_all': '✅ Все уведомления',
        'btn_notif_important': '🔕 Только важные',
        'btn_notif_off': '❌ Отключить',
        'notif_mode_set': '✅ Режим: {}',
        
        # Статистика
        'stats_title': '📊 <b>Детальная статистика</b>',
        'stats_choose_period': 'Выберите период для просмотра:',
        'stats_today': '📅 Сегодня',
        'stats_week': '📆 Неделя',
        'stats_month': '🗓 Месяц',
        'stats_all_time': '📊 Всё время',
        'stats_total_leads': '🎯 <b>Всего лидов:</b>',
        'stats_processed': '📞 <b>Обработано:</b>',
        'stats_converted': '✅ <b>Конвертировано:</b>',
        'stats_by_projects': '📁 <b>По проектам:</b>',
        'stats_top_chats': '💬 <b>Топ-5 чатов:</b>',
        'stats_no_data': 'Нет данных',
        'stats_leads_suffix': 'лидов',
        
        # Лиды
        'leads_title': '🎯 <b>Последние лиды</b>',
        'leads_none': 'У вас пока нет найденных лидов',
        'leads_go_to': 'Перейти',
        
        # Интеграции
        'integrations_title': '🔗 <b>Интеграции</b>',
        'amocrm_connected': '✅ Подключен',
        'amocrm_disconnected': '❌ Не подключен',
        
        # Фильтры
        'filters_title': '🔧 <b>Логические фильтры</b>',
        'filters_desc': """Используйте операторы для точного поиска:

<b>+ (И)</b> — оба слова должны быть в сообщении
Пример: <code>купить + квартиру</code>

<b>| (ИЛИ)</b> — хотя бы одно слово
Пример: <code>аренда | съём</code>

Комбинируйте: <code>купить + квартиру | дом</code>""",
        'btn_add_filter': '➕ Добавить фильтр',
        'btn_show_filters': '📋 Показать все',
        'btn_clear_filters': '🗑 Удалить все',
        
        # Помощь
        'help_title': '📖 <b>Как пользоваться ботом:</b>',
        'help_text': """
1️⃣ <b>Создайте проект</b>
   Проект — это набор настроек для одной ниши (например, "Недвижимость")

2️⃣ <b>Добавьте ключевые слова</b>
   Укажите слова, по которым нужно искать сообщения

3️⃣ <b>Добавьте чаты для мониторинга</b>
   Укажите ссылки на группы, которые нужно отслеживать

4️⃣ <b>Получайте уведомления</b>
   Бот будет присылать сообщения, в которых нашел ваши ключевые слова

🤖 <b>AI-функции:</b>
Используйте кнопку "AI подбор" для автоматического подбора:
- Ключевых слов по нише
- Исключающих слов
- Релевантных чатов

🎯 <b>Фильтры:</b>
+ (И) — оба слова должны быть в тексте
| (ИЛИ) — хотя бы одно слово

📹 Видео-инструкция: /video""",
        
        # Поддержка
        'support_title': '💬 <b>Служба поддержки</b>',
        'support_text': """По всем вопросам обращайтесь:
📧 Email: support@getlead.bot
💬 Telegram: @getlead_support

Мы ответим в течение 24 часов!""",
        
        # Тарифы
        'plan_free': '🆓 Бесплатный',
        'plan_freelancer': '💼 Фрилансер',
        'plan_standard': '📊 Стандарт',
        'plan_startup': '🚀 Стартап',
        'plan_company': '🏢 Компания',
        'days_left': '{} дней',
    },
    'en': {
        # Welcome and language selection
        'choose_language': """🌍 <b>Выберите язык / Choose language</b>

Выберите язык, на котором хотите продолжить:
Choose the language you want to continue with:""",
        
        'start': """👋 Welcome to <b>GetLead</b>!

I'll help you find target clients in Telegram chats by keywords.

🔍 You set up keywords and chats to monitor
📩 I send notifications when I find matches
⚡ You can quickly respond to potential clients

Start by creating a project and setting up keywords!""",
        
        # Menu
        'main_menu': '🏠 Main Menu',
        'projects_menu': '📁 Your Projects',
        'keywords_menu': '🔑 Keywords',
        'exclude_menu': '🚫 Exclude Words',
        'filters_menu': '🔧 Filters',
        'chats_menu': '💬 Chats to Monitor',
        'payment_menu': '💳 Plans & Payment',
        
        # Main menu buttons
        'btn_profile': '👤 Profile',
        'btn_stats': '📊 Statistics',
        'btn_projects': '📁 Projects',
        'btn_keywords': '🔑 Keywords',
        'btn_exclude': '🚫 Exclude Words',
        'btn_filters': '🔧 Filters',
        'btn_chats': '💬 Chats',
        'btn_payment': '💳 Plans',
        'btn_integrations': '🔗 Integrations',
        'btn_help': '❓ Help',
        'btn_back': '🔙 Back',
        'btn_back_main': '🔙 Main Menu',
        'btn_cancel': '❌ Cancel',
        
        # Projects
        'project_created': '✅ Project "{}" created!',
        'project_activated': '✅ Project "{}" activated!',
        'project_deleted': '🗑 Project deleted',
        'btn_create_project': '➕ Create Project',
        'btn_delete_project': '🗑 Delete Project',
        'enter_project_name': 'Enter project name:',
        'no_projects': '📁 You don\'t have any projects yet.\n\nCreate your first project to start monitoring!',
        
        # Keywords
        'keyword_added': '✅ Keyword "{}" added!',
        'keywords_cleared': '🗑 All keywords cleared',
        'btn_add_keywords': '➕ Add Keywords',
        'btn_ai_suggest': '🤖 AI Suggest',
        'btn_show_list': '📋 Show List',
        'btn_clear_all': '🗑 Clear All',
        'enter_keywords': 'Enter keywords (one per line):',
        'no_keywords': '🔑 You don\'t have any keywords yet.\n\nAdd keywords to find leads!',
        'keywords_list': '🔑 <b>Your keywords:</b>\n\n',
        
        # Chats
        'chat_added': '✅ Chat added: {}',
        'chat_exists': 'ℹ️ This chat is already added',
        'btn_my_chats': '📋 My Chats',
        'btn_chat_packs': '📦 Chat Packs',
        'btn_add_chat': '➕ Add Chat',
        'enter_chat_link': 'Send chat link (t.me/...):',
        'no_chats': '💬 You don\'t have any chats yet.\n\nAdd chats to monitor for leads!',
        
        # Subscription
        'no_subscription': '⚠️ You don\'t have an active subscription. Please subscribe to use the bot.',
        'btn_card_payment': '💳 Bank Card',
        'btn_crypto_payment': '₿ Cryptocurrency',
        
        # Profile
        'profile_title': '👤 <b>Profile</b>',
        'profile_id': '📱 <b>ID:</b>',
        'profile_username': '👤 <b>Username:</b>',
        'profile_registered': '📅 <b>Registered:</b>',
        'profile_plan': '💳 <b>Plan:</b>',
        'profile_expires': '⏳ <b>Expires in:</b>',
        'profile_expires_date': '📆 <b>Expires:</b>',
        'profile_stats': '📊 <b>Statistics</b>',
        'profile_projects': '📁 <b>Projects:</b>',
        'profile_chats': '💬 <b>Chats:</b>',
        'profile_leads': '🎯 <b>Leads found:</b>',
        'profile_today': 'Today',
        'profile_week': 'This week',
        'profile_total': 'Total',
        'btn_detailed_stats': '📊 Detailed Stats',
        'btn_recent_leads': '🎯 Recent Leads',
        'btn_settings': '⚙️ Settings',
        
        # Settings
        'settings_title': '⚙️ <b>Settings</b>',
        'settings_language': '🌐 <b>Language:</b>',
        'settings_notifications': '🔔 <b>Notifications:</b>',
        'settings_integrations': '🔗 <b>Integrations:</b>',
        'settings_tip': '💡 Use the menu below to configure integrations.',
        'btn_change_language': '🌐 Change Language',
        'btn_notifications': '🔔 Notifications',
        'notifications_enabled': 'Enabled',
        'notifications_disabled': 'Disabled',
        'lang_russian': 'Русский 🇷🇺',
        'lang_english': 'English 🇬🇧',
        'language_changed': '✅ Language changed to {}',
        'choose_language_title': '🌐 <b>Choose Language</b>\n\nSelect interface language:',
        
        # Notifications
        'notifications_title': '🔔 <b>Notification Settings</b>',
        'notifications_current': 'Current status:',
        'notifications_all': 'All notifications enabled',
        'notifications_important': 'Important only',
        'notifications_off': 'Disabled',
        'notifications_desc': """Choose notification mode:

• <b>All notifications</b> — receive notification for every lead found
• <b>Important only</b> — hourly summary notifications
• <b>Disable</b> — no notifications (leads are still saved)""",
        'btn_notif_all': '✅ All Notifications',
        'btn_notif_important': '🔕 Important Only',
        'btn_notif_off': '❌ Disable',
        'notif_mode_set': '✅ Mode: {}',
        
        # Statistics
        'stats_title': '📊 <b>Detailed Statistics</b>',
        'stats_choose_period': 'Choose period to view:',
        'stats_today': '📅 Today',
        'stats_week': '📆 Week',
        'stats_month': '🗓 Month',
        'stats_all_time': '📊 All Time',
        'stats_total_leads': '🎯 <b>Total leads:</b>',
        'stats_processed': '📞 <b>Processed:</b>',
        'stats_converted': '✅ <b>Converted:</b>',
        'stats_by_projects': '📁 <b>By projects:</b>',
        'stats_top_chats': '💬 <b>Top 5 chats:</b>',
        'stats_no_data': 'No data',
        'stats_leads_suffix': 'leads',
        
        # Leads
        'leads_title': '🎯 <b>Recent Leads</b>',
        'leads_none': 'You don\'t have any leads yet',
        'leads_go_to': 'View',
        
        # Integrations
        'integrations_title': '🔗 <b>Integrations</b>',
        'amocrm_connected': '✅ Connected',
        'amocrm_disconnected': '❌ Not connected',
        
        # Filters
        'filters_title': '🔧 <b>Logical Filters</b>',
        'filters_desc': """Use operators for precise search:

<b>+ (AND)</b> — both words must be in the message
Example: <code>buy + apartment</code>

<b>| (OR)</b> — at least one word
Example: <code>rent | lease</code>

Combine: <code>buy + apartment | house</code>""",
        'btn_add_filter': '➕ Add Filter',
        'btn_show_filters': '📋 Show All',
        'btn_clear_filters': '🗑 Clear All',
        
        # Help
        'help_title': '📖 <b>How to use the bot:</b>',
        'help_text': """
1️⃣ <b>Create a project</b>
   A project is a set of settings for one niche (e.g., "Real Estate")

2️⃣ <b>Add keywords</b>
   Specify words to search for in messages

3️⃣ <b>Add chats to monitor</b>
   Provide links to groups you want to track

4️⃣ <b>Receive notifications</b>
   The bot will send messages where it found your keywords

🤖 <b>AI features:</b>
Use the "AI Suggest" button to automatically find:
- Keywords for your niche
- Exclude words
- Relevant chats

🎯 <b>Filters:</b>
+ (AND) — both words must be in text
| (OR) — at least one word

📹 Video tutorial: /video""",
        
        # Support
        'support_title': '💬 <b>Support</b>',
        'support_text': """For any questions contact us:
📧 Email: support@getlead.bot
💬 Telegram: @getlead_support

We'll respond within 24 hours!""",
        
        # Plans
        'plan_free': '🆓 Free',
        'plan_freelancer': '💼 Freelancer',
        'plan_standard': '📊 Standard',
        'plan_startup': '🚀 Startup',
        'plan_company': '🏢 Company',
        'days_left': '{} days',
    }
}


def get_text(key: str, lang: str = 'ru', **kwargs) -> str:
    """Получить текст сообщения на нужном языке"""
    text = TEXTS.get(lang, TEXTS['ru']).get(key, TEXTS['ru'].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text
