#!/bin/bash
# Скрипт для запуска бота

set -e  # Остановка при ошибке

# Проверка наличия виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Запустите сначала: ./setup.sh"
    exit 1
fi

# Используем Python из venv напрямую (не зависит от активации)
VENV_PYTHON="venv/bin/python3"

# Проверка наличия Python в venv
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Python не найден в виртуальном окружении!"
    echo "Запустите сначала: ./setup.sh"
    exit 1
fi

# Проверка наличия необходимых модулей
echo "🔍 Проверка зависимостей..."
if ! "$VENV_PYTHON" -c "import apscheduler" 2>/dev/null; then
    echo "❌ Модуль apscheduler не найден!"
    echo "Запустите установку зависимостей: ./setup.sh"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте файл .env с настройками бота (см. README.md)"
    exit 1
fi

# Проверка на запущенные экземпляры бота
RUNNING_PIDS=$(ps aux | grep -E "[p]ython.*main\.py" | awk '{print $2}')
if [ -n "$RUNNING_PIDS" ]; then
    echo "⚠️  Обнаружены запущенные экземпляры бота (PID: $RUNNING_PIDS)"
    echo "Остановите их перед запуском нового экземпляра:"
    echo "  ./stop.sh"
    echo "Или вручную:"
    echo "  kill $RUNNING_PIDS"
    exit 1
fi

# Запуск бота
echo "🚀 Запуск бота..."
"$VENV_PYTHON" main.py

