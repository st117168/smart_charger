#!/bin/bash

echo "========================================"
echo "  Smart Charger - Статус"
echo "========================================"
echo ""

# Получаем директорию, где находится скрипт (папка linux)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Поднимаемся на уровень выше (в корневую папку проекта)
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[INFO] Директория проекта: $PROJECT_DIR"
echo ""

# Проверяем статус сервиса
echo "[INFO] Статус сервиса:"
systemctl --user status smart-charger.service --no-pager

#echo ""
#echo "========================================"
#echo "[INFO] Последние логи:"
#journalctl --user -u smart-charger.service -n 10 --no-pager

echo ""
echo "========================================"
echo "[INFO] Процессы:"
ps aux | grep -E "smart_charger|smart-charger" | grep -v grep

echo ""
echo "========================================"
echo "[INFO] Файл лога:"
if [ -f "$PROJECT_DIR/data/smart-charger.log" ]; then
    tail -n 10 "$PROJECT_DIR/data/smart-charger.log"
else
    echo "Файл лога не найден: $PROJECT_DIR/data/smart-charger.log"
fi
