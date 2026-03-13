#!/usr/bin/env bash
# Bootstrap the converter virtual environment
# Usage: bash converter/setup.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "Creating virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q

echo "Done. To use: source converter/.venv/bin/activate"