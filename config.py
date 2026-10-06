"""Конфигурация бота"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ID администратора
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Путь к базе данных
DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/tasks.db")

# Часовой пояс
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

# Уровень логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Google Calendar (один календарь владельца бота)
GOOGLE_CALENDAR_ENABLED = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN", "")
GOOGLE_CALENDAR_EVENT_DURATION_MINUTES = int(
    os.getenv("GOOGLE_CALENDAR_EVENT_DURATION_MINUTES", "60")
)

# Создаем директорию для базы данных, если её нет
db_dir = Path(DATABASE_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения!")










