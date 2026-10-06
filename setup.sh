#!/bin/bash
# Скрипт для установки зависимостей проекта

set -e  # Остановка при ошибке

echo "🔧 Настройка виртуального окружения для Telegram Task Manager Bot"
echo ""

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.10 или выше."
    exit 1
fi

# Проверка версии Python
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Требуется Python 3.10 или выше. Найдена версия: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python версии $PYTHON_VERSION найден"
echo ""

# Создание виртуального окружения, если его нет
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
    echo "✅ Виртуальное окружение создано"
else
    echo "ℹ️  Виртуальное окружение уже существует"
fi

echo ""

# Активация виртуального окружения
echo "🔌 Активация виртуального окружения..."
source venv/bin/activate

echo ""

# Обновление pip
echo "⬆️  Обновление pip..."
pip install --upgrade pip --quiet

echo ""

# Установка зависимостей
echo "📥 Установка зависимостей из requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo ""
    echo "✅ Все зависимости установлены успешно!"
else
    echo "❌ Файл requirements.txt не найден!"
    exit 1
fi

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "Для запуска бота используйте:"
echo "  ./run.sh"
echo ""
echo "Для остановки бота используйте:"
echo "  ./stop.sh"
echo ""
echo "Или вручную:"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo ""
echo "⚠️  ВАЖНО: После создания нового venv всегда запускайте ./setup.sh"
echo "   или устанавливайте зависимости вручную: pip install -r requirements.txt"

