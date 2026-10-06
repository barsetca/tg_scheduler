#!/bin/bash
# Скрипт для остановки бота

echo "🛑 Остановка бота..."

# Поиск процессов бота
PIDS=$(ps aux | grep -E "[p]ython.*main\.py" | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "ℹ️  Бот не запущен"
    exit 0
fi

echo "Найдены процессы бота (PID: $PIDS)"

# Остановка процессов
for PID in $PIDS; do
    echo "Остановка процесса $PID..."
    kill "$PID" 2>/dev/null
    
    # Ждем 2 секунды
    sleep 2
    
    # Проверяем, завершился ли процесс
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Процесс $PID не завершился, принудительная остановка..."
        kill -9 "$PID" 2>/dev/null
    fi
done

# Проверка результата
REMAINING=$(ps aux | grep -E "[p]ython.*main\.py" | awk '{print $2}')
if [ -z "$REMAINING" ]; then
    echo "✅ Бот успешно остановлен"
else
    echo "⚠️  Некоторые процессы все еще запущены (PID: $REMAINING)"
    echo "Попробуйте принудительную остановку: kill -9 $REMAINING"
    exit 1
fi







