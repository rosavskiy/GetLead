# Структура проекта GetLead

```
GetLead/
│
├── 📁 bot/                          # Control Bot (Aiogram 3.x)
│   ├── handlers/                   # Обработчики команд
│   │   ├── __init__.py            # Регистрация всех handlers
│   │   ├── common.py              # /start, помощь, главное меню
│   │   ├── projects.py            # Управление проектами
│   │   ├── keywords.py            # Ключевые и исключающие слова
│   │   ├── chats.py               # Управление чатами
│   │   └── payment.py             # Тарифы и оплата
│   │
│   ├── __init__.py
│   ├── keyboards.py               # Inline и Reply клавиатуры
│   ├── middlewares.py             # Middleware (проверка подписки)
│   ├── states.py                  # FSM состояния
│   └── texts.py                   # Тексты сообщений (мультиязычность)
│
├── 📁 database/                     # База данных (PostgreSQL + SQLAlchemy)
│   ├── __init__.py
│   ├── database.py                # Настройка подключения, engine, sessions
│   ├── models.py                  # SQLAlchemy модели (User, Project, Keyword, Chat)
│   └── crud.py                    # CRUD операции (UserCRUD, ProjectCRUD, etc.)
│
├── 📁 userbot/                      # Userbot Workers (Telethon)
│   ├── __init__.py
│   ├── worker.py                  # Воркер для мониторинга чатов
│   └── matching.py                # Движок матчинга (проверка ключевых слов)
│
├── 📁 utils/                        # Вспомогательные утилиты
│   ├── __init__.py
│   ├── ai_helpers.py              # OpenAI интеграция (генерация ключевых слов)
│   └── subscription_helpers.py    # Проверка подписок и лимитов
│
├── 📄 config.py                     # Конфигурация (Pydantic Settings)
├── 📄 main.py                       # Точка входа Control Bot
├── 📄 run_userbot.py                # Точка входа Userbot Workers
│
├── 📄 .env.example                  # Шаблон переменных окружения
├── 📄 .gitignore                    # Git ignore (sessions, .env, __pycache__)
├── 📄 requirements.txt              # Python зависимости
│
├── 📄 README.md                     # Главная документация
├── 📄 DEPLOYMENT.md                 # Инструкция по развертыванию
├── 📄 QUICKSTART.md                 # Краткая справка
├── 📄 LICENSE                       # MIT License
│
├── 📄 setup.bat                     # Установочный скрипт (Windows)
└── 📄 setup.sh                      # Установочный скрипт (Linux/Mac)
```

## Описание ключевых модулей

### Control Bot (bot/)

**handlers/common.py**
- Команда `/start`
- Главное меню
- Помощь и поддержка

**handlers/projects.py**
- Создание проектов
- Переключение активного проекта
- Удаление проектов

**handlers/keywords.py**
- Добавление ключевых слов
- Добавление исключающих слов
- AI-подбор слов
- Удаление слов

**handlers/chats.py**
- Добавление чатов по ссылке
- Просмотр списка чатов
- Пакетные чаты
- AI-подбор чатов

**handlers/payment.py**
- Выбор тарифа
- Оплата через ЮKassa
- Оплата через CryptoBot

### Database (database/)

**models.py - Основные модели:**

```python
User                    # Пользователь бота
├── telegram_id        # ID в Telegram
├── subscription_plan  # Тарифный план
├── subscription_end_date
└── projects[]         # Список проектов

Project                # Проект пользователя
├── name              # Название проекта
├── is_active         # Активен ли
├── keywords[]        # Ключевые слова
├── filters[]         # Логические фильтры
└── chats[]           # Чаты для мониторинга

Keyword               # Ключевое слово
├── text             # Текст слова
├── type             # INCLUDE или EXCLUDE
└── project_id

Chat                  # Чат для мониторинга
├── telegram_link    # Ссылка t.me/...
├── telegram_id      # ID чата
├── is_joined        # Вступил ли бот
├── assigned_userbot # Какой юзербот отвечает
└── projects[]       # Проекты, которые мониторят
```

**crud.py - CRUD операции:**
- `UserCRUD` - работа с пользователями
- `ProjectCRUD` - работа с проектами
- `KeywordCRUD` - работа с ключевыми словами
- `ChatCRUD` - работа с чатами

### Userbot Engine (userbot/)

**worker.py - Основной воркер:**

```python
UserbotWorker
├── start()                  # Запуск юзербота
├── load_chats()            # Загрузка чатов для мониторинга
├── join_chat()             # Вступление в чат
├── process_message()       # Обработка нового сообщения
├── check_project_match()   # Проверка совпадения
└── send_notification()     # Отправка уведомления
```

**matching.py - Движок матчинга:**

```python
MatchingEngine
├── normalize_text()        # Нормализация текста
├── check_keywords()        # Проверка ключевых слов
├── check_exclude_words()   # Проверка исключающих слов
├── parse_filter()          # Парсинг логических фильтров
├── check_filter()          # Проверка фильтров
└── process_message()       # Полная обработка сообщения
```

## Поток данных

```
1. Пользователь → Control Bot → БД
   - Создает проект
   - Добавляет ключевые слова
   - Добавляет чаты

2. БД → Userbot Worker
   - Загружает настройки
   - Вступает в чаты
   - Начинает мониторинг

3. Telegram → Userbot → Matching Engine
   - Получает новое сообщение
   - Проверяет по ключевым словам
   - Проверяет исключающие слова
   - Применяет фильтры

4. Matching Engine → Control Bot → Пользователь
   - Если найдено совпадение
   - Отправляет уведомление
   - С ссылкой на сообщение
```

## База данных

### Таблицы

```sql
users                      # Пользователи
projects                   # Проекты
keywords                   # Ключевые слова
filters                    # Логические фильтры
chats                      # Чаты
chat_project              # Many-to-Many связь
packed_chat_groups        # Пакетные чаты от админа
```

### Связи

```
User (1) ←→ (∞) Project
Project (1) ←→ (∞) Keyword
Project (1) ←→ (∞) Filter
Project (∞) ←→ (∞) Chat
```

## Технологии

- **Python 3.10+** - язык программирования
- **aiogram 3.x** - Bot API framework
- **Telethon** - MTProto framework для юзербота
- **SQLAlchemy** - ORM для работы с БД
- **PostgreSQL** - реляционная база данных
- **Redis** - кэш и очереди
- **OpenAI API** - AI-функции
- **Pydantic** - валидация настроек

## Следующие шаги

- [ ] Добавить миграции Alembic
- [ ] Настроить Celery для фоновых задач
- [ ] Интегрировать ЮKassa
- [ ] Интегрировать CryptoBot
- [ ] Добавить статистику
- [ ] Добавить экспорт лидов
- [ ] Docker контейнеризация
- [ ] CI/CD pipeline
