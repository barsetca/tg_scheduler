"""Единая работа с локальным временем, заданным в конфигурации бота."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from config import TIMEZONE


_timezone = ZoneInfo(TIMEZONE)


def local_now() -> datetime:
    """Текущее время часового пояса бота без tzinfo для SQLite."""
    return datetime.now(_timezone).replace(tzinfo=None)


def local_today() -> date:
    """Текущая календарная дата часового пояса бота."""
    return local_now().date()
