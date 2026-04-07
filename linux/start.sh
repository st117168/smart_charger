#!/bin/bash

echo "========================================"
echo "  Smart Charger - Ручной запуск"
echo "========================================"
echo ""

# Получаем директорию, где находится скрипт (папка linux)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Поднимаемся на уровень выше (в корневую папку проекта)
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
echo "[INFO] Директория проекта: $PROJECT_DIR"

# Проверяем наличие виртуального окружения
if [ -f ".venv_linux/bin/python" ]; then
    echo "[INFO] Запуск из виртуального окружения..."
    .venv_linux/bin/python "__main__.py"
else
    echo "[INFO] Виртуальное окружение не найдено, запуск из системного Python..."
    echo "[INFO] Рекомендуется сначала установить автозапуск: ./install.sh"
    echo ""
    python3 "smart_charger/__main__.py"
fi

echo ""
echo "[INFO] Программа остановлена."
