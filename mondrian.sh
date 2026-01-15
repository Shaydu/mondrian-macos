#!/bin/bash
# Mondrian Services Launcher
# Uses project venv for consistency with tests

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/mondrian/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
SYSTEM_PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
SERVICES_SCRIPT="$SCRIPT_DIR/scripts/start_services.py"

# Activate venv if it exists
if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
    echo "Virtual environment activated"
else
    echo "WARNING: venv not found at $VENV_DIR"
fi

# Prefer venv Python, fallback to system Python 3.12
if [ -f "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
    echo "Using venv Python: $PYTHON"
else
    echo "WARNING: venv Python not found at $VENV_PYTHON"
    if [ -f "$SYSTEM_PYTHON" ]; then
        PYTHON="$SYSTEM_PYTHON"
        echo "Falling back to system Python: $PYTHON"
    else
        echo "ERROR: No suitable Python found"
        echo "Please create venv: python3 -m venv mondrian/venv"
        exit 1
    fi
fi

# Check if start_services.py exists
if [ ! -f "$SERVICES_SCRIPT" ]; then
    echo "ERROR: start_services.py not found at $SERVICES_SCRIPT"
    exit 1
fi

# Forward all arguments to start_services.py
exec "$PYTHON" "$SERVICES_SCRIPT" "$@"
