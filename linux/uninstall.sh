#!/bin/bash

echo "========================================"
echo "  Smart Charger - Uninstalling"
echo "========================================"
echo ""

# Get the directory of the script (linux folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Move one level up (root project folder)
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
echo "[INFO] Project directory: $PROJECT_DIR"

echo "[INFO] Stopping and disabling service..."
# Stop service and handle autostart logic via Python
# We use python from venv if it exists, otherwise system python
if [ -f ".venv_linux/bin/python3" ]; then
    ./.venv_linux/bin/python3 "__main__.py" --no-autostart
else
    python3 "__main__.py" --no-autostart
fi

# Double check: stop and remove systemd service file if it exists
systemctl --user stop smart-charger.service 2>/dev/null
systemctl --user disable smart-charger.service 2>/dev/null
rm -f ~/.config/systemd/user/smart-charger.service 2>/dev/null
systemctl --user daemon-reload

echo "[INFO] Removing virtual environment..."
if [ -d ".venv_linux" ]; then
    rm -rf .venv_linux
    echo "[INFO] .venv_linux folder deleted."
fi

echo "[INFO] Cleaning up data and logs..."
if [ -d "data" ]; then
    rm -rf data
    echo "[INFO] 'data' folder deleted."
fi

echo ""
echo "[SUCCESS] Uninstall complete!"
