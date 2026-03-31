#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "[INFO] Creating an environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "[INFO] Installing dependencies..."
pip install --upgrade pip
pip install tinytuya psutil

echo "[INFO] Setting up autorun..."
# Call __main__.py, which will create a .service file
./.venv/bin/python3 "__main__.py" --autostart

echo "[SUCCESS] Done!"
