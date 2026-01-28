"""FSM состояния для бота"""
from aiogram.fsm.state import State, StatesGroup


class ProjectStates(StatesGroup):
    """Состояния для работы с проектами"""
    waiting_for_name = State()
    waiting_for_delete_confirm = State()


class KeywordStates(StatesGroup):
    """Состояния для работы с ключевыми словами"""
    waiting_for_keywords = State()
    waiting_for_ai_niche = State()
    selecting_ai_keywords = State()  # Выбор из AI предложений


class ExcludeStates(StatesGroup):
    """Состояния для работы с исключающими словами"""
    waiting_for_keywords = State()
    waiting_for_ai_niche = State()


class FilterStates(StatesGroup):
    """Состояния для работы с фильтрами"""
    waiting_for_filter = State()
    waiting_for_ai_niche = State()


class ChatStates(StatesGroup):
    """Состояния для работы с чатами"""
    waiting_for_link = State()
    waiting_for_ai_niche = State()
