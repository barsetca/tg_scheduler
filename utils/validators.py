"""Валидация данных"""
import re
from datetime import date, time, datetime
from typing import Optional, Tuple


def validate_time(time_str: str) -> Tuple[bool, Optional[time]]:
    """Валидация времени в формате HH:MM"""
    pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
    if re.match(pattern, time_str):
        try:
            hours, minutes = map(int, time_str.split(':'))
            return True, time(hours, minutes)
        except ValueError:
            return False, None
    return False, None


def validate_date(date_str: str) -> Tuple[bool, Optional[date]]:
    """Валидация даты в формате YYYY-MM-DD или DD.MM.YYYY"""
    # Формат YYYY-MM-DD
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        return True, date_obj
    except ValueError:
        pass
    
    # Формат DD.MM.YYYY
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y").date()
        return True, date_obj
    except ValueError:
        pass
    
    # Формат DD.MM (текущий год)
    try:
        date_obj = datetime.strptime(date_str, "%d.%m").date()
        date_obj = date_obj.replace(year=date.today().year)
        return True, date_obj
    except ValueError:
        pass
    
    return False, None


def validate_minutes(minutes_str: str) -> Tuple[bool, Optional[int]]:
    """Валидация количества минут (для откладывания)"""
    try:
        minutes = int(minutes_str)
        if minutes > 0 and minutes <= 1440:  # Максимум 24 часа
            return True, minutes
        return False, None
    except ValueError:
        return False, None


def is_date_in_past(date_obj: date) -> bool:
    """Проверка, что дата не в прошлом"""
    return date_obj < date.today()


def parse_date(date_value: str | date) -> date:
    """Парсинг даты из строки или объекта date"""
    if isinstance(date_value, date):
        return date_value
    if isinstance(date_value, str):
        return date.fromisoformat(date_value)
    raise ValueError(f"Невозможно распарсить дату: {date_value}")


def parse_time(time_value: str | time | None) -> time | None:
    """Парсинг времени из строки или объекта time"""
    if time_value is None:
        return None
    if isinstance(time_value, time):
        return time_value
    if isinstance(time_value, str):
        # Парсим время из строки (формат HH:MM или HH:MM:SS)
        time_str = time_value[:5]  # Берем только HH:MM
        try:
            return time.fromisoformat(time_str)
        except ValueError:
            return time(0, 0)  # Возвращаем время по умолчанию при ошибке
    raise ValueError(f"Невозможно распарсить время: {time_value}")

