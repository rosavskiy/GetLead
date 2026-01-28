"""Модели базы данных"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, BigInteger, Boolean, DateTime, ForeignKey, Text, Table, Column, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from database.database import Base


class SubscriptionPlan(str, enum.Enum):
    """Тарифные планы"""
    FREE = "free"
    FREELANCER = "freelancer"  # 5 чатов
    STANDARD = "standard"      # 20 чатов
    STARTUP = "startup"        # 10 чатов
    COMPANY = "company"        # 50 чатов


class KeywordType(str, enum.Enum):
    """Тип ключевого слова"""
    INCLUDE = "include"  # Ключевые слова
    EXCLUDE = "exclude"  # Исключающие слова


# Many-to-Many таблица для связи проектов и чатов
chat_project_association = Table(
    'chat_project',
    Base.metadata,
    Column('chat_id', ForeignKey('chats.id', ondelete='CASCADE'), primary_key=True),
    Column('project_id', ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    """Пользователь бота"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default='ru')
    
    # Подписка
    subscription_plan: Mapped[SubscriptionPlan] = mapped_column(
        SQLEnum(SubscriptionPlan),
        default=SubscriptionPlan.FREE
    )
    subscription_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    projects: Mapped[List["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    lead_matches: Mapped[List["LeadMatch"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    amocrm_integration: Mapped[Optional["AmoCRMIntegration"]] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    
    def __repr__(self):
        return f"<User {self.telegram_id}>"


class Project(Base):
    """Проект пользователя"""
    __tablename__ = 'projects'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="projects")
    keywords: Mapped[List["Keyword"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    filters: Mapped[List["Filter"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    lead_matches: Mapped[List["LeadMatch"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    chats: Mapped[List["Chat"]] = relationship(
        secondary=chat_project_association,
        back_populates="projects"
    )
    
    def __repr__(self):
        return f"<Project {self.name}>"


class Keyword(Base):
    """Ключевое или исключающее слово"""
    __tablename__ = 'keywords'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'))
    text: Mapped[str] = mapped_column(String(500))
    type: Mapped[KeywordType] = mapped_column(SQLEnum(KeywordType), default=KeywordType.INCLUDE)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    project: Mapped["Project"] = relationship(back_populates="keywords")
    
    def __repr__(self):
        return f"<Keyword {self.text} ({self.type})>"


class Filter(Base):
    """Логические фильтры (AND/OR)"""
    __tablename__ = 'filters'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'))
    logic_string: Mapped[str] = mapped_column(Text)  # Например: "квартиру + сниму | комнату"
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    project: Mapped["Project"] = relationship(back_populates="filters")
    
    def __repr__(self):
        return f"<Filter {self.logic_string}>"


class Chat(Base):
    """Чат для мониторинга"""
    __tablename__ = 'chats'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_link: Mapped[str] = mapped_column(String(500), unique=True)  # t.me/...
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_joined: Mapped[bool] = mapped_column(Boolean, default=False)  # Вступил ли юзербот
    
    # Какой юзербот отвечает за этот чат
    assigned_userbot: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    projects: Mapped[List["Project"]] = relationship(
        secondary=chat_project_association,
        back_populates="chats"
    )


class LeadMatch(Base):
    """Найденные совпадения (лиды) для статистики"""
    __tablename__ = 'lead_matches'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.id', ondelete='CASCADE'), index=True)
    
    # Информация о сообщении
    message_text: Mapped[str] = mapped_column(Text)
    message_link: Mapped[str] = mapped_column(String(500))
    telegram_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sender_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Ключевые слова, которые сработали
    matched_keywords: Mapped[str] = mapped_column(Text)  # JSON список
    
    # Статус обработки
    is_sent_to_crm: Mapped[bool] = mapped_column(Boolean, default=False)
    is_contacted: Mapped[bool] = mapped_column(Boolean, default=False)  # Связались с лидом
    is_converted: Mapped[bool] = mapped_column(Boolean, default=False)  # Конвертирован в клиента
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="lead_matches")
    project: Mapped["Project"] = relationship(back_populates="lead_matches")
    chat: Mapped["Chat"] = relationship()
    
    def __repr__(self):
        return f"<LeadMatch {self.id} user={self.user_id}>"


class AmoCRMIntegration(Base):
    """Интеграция с AmoCRM для пользователя"""
    __tablename__ = 'amocrm_integrations'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    
    # AmoCRM credentials
    subdomain: Mapped[str] = mapped_column(String(255))  # example.amocrm.ru
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime)
    
    # Настройки
    pipeline_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # Воронка
    status_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # Статус в воронке
    responsible_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # Ответственный
    
    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="amocrm_integration")
    
    def __repr__(self):
        return f"<AmoCRMIntegration {self.subdomain}>"
    
    def __repr__(self):
        return f"<Chat {self.telegram_link}>"


class PackedChatGroup(Base):
    """Пакетные подборки чатов от администратора"""
    __tablename__ = 'packed_chat_groups'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))  # "Фриланс РФ", "IT вакансии"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chat_links: Mapped[str] = mapped_column(Text)  # JSON массив ссылок
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PackedChatGroup {self.name}>"
