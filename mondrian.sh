#!/bin/bash
# Mondrian Services Launcher
# Automatically uses Python 3.12 for MLX compatibility

PYTHON312="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_SCRIPT="$SCRIPT_DIR/scripts/start_services.py"

# Check if Python 3.12 is installed
if [ ! -f "$PYTHON312" ]; then
    echo "ERROR: Python 3.12 not found at $PYTHON312"
    echo "MLX backend requires Python 3.12+"
    echo "Please install Python 3.12 from python.org"
    exit 1
fi

# Check if start_services.py exists
if [ ! -f "$SERVICES_SCRIPT" ]; then
    echo "ERROR: start_services.py not found at $SERVICES_SCRIPT"
    exit 1
fi

# Forward all arguments to start_services.py using Python 3.12
exec "$PYTHON312" "$SERVICES_SCRIPT" "$@"
