"""Движок для мониторинга сообщений (матчинг)"""
import re
from typing import List, Dict, Set
from database.models import Keyword, KeywordType


class MatchingEngine:
    """Движок для проверки совпадений в тексте"""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Нормализация текста"""
        # Приводим к нижнему регистру
        text = text.lower()
        # Удаляем эмодзи (опционально)
        # text = re.sub(r'[^\w\s]', '', text)
        return text
    
    @staticmethod
    def check_keywords(text: str, keywords: List[Keyword]) -> List[Keyword]:
        """
        Проверка наличия ключевых слов в тексте
        
        Args:
            text: Текст сообщения
            keywords: Список ключевых слов для проверки
            
        Returns:
            Список найденных ключевых слов
        """
        normalized_text = MatchingEngine.normalize_text(text)
        found_keywords = []
        
        for keyword in keywords:
            normalized_keyword = keyword.text.lower()
            
            # Проверяем наличие слова в тексте
            # Используем word boundaries для точного поиска слов
            pattern = r'\b' + re.escape(normalized_keyword) + r'\b'
            if re.search(pattern, normalized_text):
                found_keywords.append(keyword)
        
        return found_keywords
    
    @staticmethod
    def check_exclude_words(text: str, exclude_words: List[Keyword]) -> bool:
        """
        Проверка наличия исключающих слов
        
        Args:
            text: Текст сообщения
            exclude_words: Список исключающих слов
            
        Returns:
            True если найдено исключающее слово (нужно отбросить сообщение)
        """
        normalized_text = MatchingEngine.normalize_text(text)
        
        for word in exclude_words:
            normalized_word = word.text.lower()
            pattern = r'\b' + re.escape(normalized_word) + r'\b'
            
            if re.search(pattern, normalized_text):
                return True  # Найдено исключающее слово
        
        return False
    
    @staticmethod
    def parse_filter(filter_string: str) -> Dict:
        """
        Парсинг логического фильтра
        
        Примеры:
        - "квартиру + сниму" -> AND
        - "квартиру | комнату" -> OR
        - "сниму + квартиру | комнату" -> комбинация
        
        Args:
            filter_string: Строка фильтра
            
        Returns:
            Словарь с распарсенным фильтром
        """
        # TODO: Реализация парсинга сложных фильтров
        # Пока упрощенная версия
        
        if '+' in filter_string and '|' in filter_string:
            # Комбинированный фильтр
            return {'type': 'complex', 'filter': filter_string}
        elif '+' in filter_string:
            # AND фильтр
            words = [w.strip() for w in filter_string.split('+')]
            return {'type': 'and', 'words': words}
        elif '|' in filter_string:
            # OR фильтр
            words = [w.strip() for w in filter_string.split('|')]
            return {'type': 'or', 'words': words}
        else:
            # Простое слово
            return {'type': 'simple', 'word': filter_string.strip()}
    
    @staticmethod
    def check_filter(text: str, filter_dict: Dict) -> bool:
        """
        Проверка текста по фильтру
        
        Args:
            text: Текст сообщения
            filter_dict: Распарсенный фильтр
            
        Returns:
            True если текст проходит фильтр
        """
        normalized_text = MatchingEngine.normalize_text(text)
        filter_type = filter_dict.get('type')
        
        if filter_type == 'simple':
            word = filter_dict['word'].lower()
            pattern = r'\b' + re.escape(word) + r'\b'
            return bool(re.search(pattern, normalized_text))
        
        elif filter_type == 'and':
            # Все слова должны присутствовать
            for word in filter_dict['words']:
                pattern = r'\b' + re.escape(word.lower()) + r'\b'
                if not re.search(pattern, normalized_text):
                    return False
            return True
        
        elif filter_type == 'or':
            # Хотя бы одно слово должно присутствовать
            for word in filter_dict['words']:
                pattern = r'\b' + re.escape(word.lower()) + r'\b'
                if re.search(pattern, normalized_text):
                    return True
            return False
        
        elif filter_type == 'complex':
            # TODO: Реализация сложных фильтров
            return True
        
        return False
    
    @staticmethod
    def process_message(
        text: str,
        include_keywords: List[Keyword],
        exclude_keywords: List[Keyword],
        filters: List = None
    ) -> Dict:
        """
        Полная обработка сообщения
        
        Args:
            text: Текст сообщения
            include_keywords: Ключевые слова для поиска
            exclude_keywords: Исключающие слова
            filters: Логические фильтры
            
        Returns:
            Словарь с результатом: {'matched': bool, 'keywords': List, 'reason': str}
        """
        # 1. Проверка исключающих слов
        if exclude_keywords and MatchingEngine.check_exclude_words(text, exclude_keywords):
            return {
                'matched': False,
                'keywords': [],
                'reason': 'Найдено исключающее слово'
            }
        
        # 2. Проверка ключевых слов
        found_keywords = MatchingEngine.check_keywords(text, include_keywords)
        
        if not found_keywords:
            return {
                'matched': False,
                'keywords': [],
                'reason': 'Ключевые слова не найдены'
            }
        
        # 3. Проверка фильтров (если есть)
        if filters:
            for filter_obj in filters:
                filter_dict = MatchingEngine.parse_filter(filter_obj.logic_string)
                if not MatchingEngine.check_filter(text, filter_dict):
                    return {
                        'matched': False,
                        'keywords': found_keywords,
                        'reason': 'Не прошло фильтр'
                    }
        
        # 4. Все проверки пройдены!
        return {
            'matched': True,
            'keywords': found_keywords,
            'reason': 'Совпадение найдено'
        }
