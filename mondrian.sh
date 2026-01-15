#!/bin/bash
# Mondrian Services Launcher
# Can use either system Python or venv

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/mondrian/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
SYSTEM_PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
SERVICES_SCRIPT="$SCRIPT_DIR/scripts/start_services.py"

# Check if running with --system-python flag
USE_SYSTEM_PYTHON=false
if [[ "$1" == "--system-python" ]]; then
    USE_SYSTEM_PYTHON=true
    shift  # Remove this argument before passing to start_services.py
fi

# Select Python: prefer system if requested or venv has issues
if [ "$USE_SYSTEM_PYTHON" = true ]; then
    echo "Using system Python (requested via --system-python)"
    PYTHON="$SYSTEM_PYTHON"
elif [ -f "$VENV_PYTHON" ]; then
    # Try venv first
    echo "Using venv Python: $VENV_PYTHON"
    # Activate venv if it exists
    if [ -f "$VENV_ACTIVATE" ]; then
        source "$VENV_ACTIVATE"
        echo "Virtual environment activated"
    fi
    PYTHON="$VENV_PYTHON"
else
    echo "WARNING: venv Python not found at $VENV_PYTHON"
    if [ -f "$SYSTEM_PYTHON" ]; then
        echo "Falling back to system Python: $SYSTEM_PYTHON"
        PYTHON="$SYSTEM_PYTHON"
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
