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

# Создаем директорию для базы данных, если её нет
db_dir = Path(DATABASE_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения!")











