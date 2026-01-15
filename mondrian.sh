#!/bin/bash
# Mondrian Services Launcher
# Supports: base mode, RAG, LoRA adapters, model selection, all services
# Examples:
#   ./mondrian.sh --restart                                          (all services, default model: Qwen2-VL-7B)
#   ./mondrian.sh --restart --mode=lora --lora-path=adapters/ansel/epoch_10
#   ./mondrian.sh --restart --model="Qwen/Qwen2-VL-4B-Instruct"     (use lighter 4B model)
#   ./mondrian.sh --restart --all-services                            (ensure all services running)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Try both locations: root venv first, then mondrian/venv
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    VENV_DIR="$SCRIPT_DIR/mondrian/venv"
fi
VENV_PYTHON="$VENV_DIR/bin/python3"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
SYSTEM_PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
SERVICES_SCRIPT="$SCRIPT_DIR/scripts/start_services.py"

# Parse model argument
MODEL_ARG=""
ALL_SERVICES=false
for arg in "$@"; do
    if [[ $arg == --model=* ]]; then
        MODEL_ARG="${arg#--model=}"
        # Remove this from arguments passed to start_services
        set -- "${@/$arg}"
    elif [[ $arg == "--all-services" ]] || [[ $arg == "--full" ]]; then
        ALL_SERVICES=true
        # Remove this from arguments passed to start_services
        set -- "${@/$arg}"
    fi
done

# Set default model if not specified (Qwen2-VL-7B for best quality)
if [ -z "$MODEL_ARG" ]; then
    MODEL_ARG="Qwen/Qwen2-VL-7B-Instruct"
    echo "Using default model: $MODEL_ARG"
fi

# Check if running with --system-python flag
USE_SYSTEM_PYTHON=false
if [[ "$1" == "--system-python" ]]; then
    USE_SYSTEM_PYTHON=true
    shift  # Remove this argument before passing to start_services.py
fi

# Select Python: prefer venv unless system explicitly requested
if [ "$USE_SYSTEM_PYTHON" = true ]; then
    echo "Using system Python (requested via --system-python)"
    PYTHON="$SYSTEM_PYTHON"
elif [ -f "$VENV_PYTHON" ]; then
    # Use venv Python
    echo "Using venv Python: $VENV_PYTHON"
    PYTHON="$VENV_PYTHON"
    # Export VIRTUAL_ENV so start_services.py can detect it
    export VIRTUAL_ENV="$VENV_DIR"
    export PATH="$VENV_DIR/bin:$PATH"
    echo "Virtual environment configured (VIRTUAL_ENV=$VIRTUAL_ENV)"
else
    echo "WARNING: venv Python not found at $VENV_PYTHON"
    # Try to find system python3
    if command -v python3 &> /dev/null; then
        PYTHON=$(command -v python3)
        echo "Falling back to system Python: $PYTHON"
    else
        echo "ERROR: No suitable Python found"
        echo "Please create venv: python3 -m venv venv"
        exit 1
    fi
fi

# Detect platform and use appropriate services script
OS_NAME=$(uname -s)
if [[ "$OS_NAME" == "Linux" ]]; then
    SERVICES_SCRIPT="$SCRIPT_DIR/scripts/start_services.py"
    echo "Detected Linux - using PyTorch/CUDA services"
elif [[ "$OS_NAME" == "Darwin" ]]; then
    SERVICES_SCRIPT="$SCRIPT_DIR/scripts/start_services.py"
    echo "Detected macOS - using MLX services"
else
    echo "WARNING: Unknown OS ($OS_NAME), defaulting to standard services"
    SERVICES_SCRIPT="$SCRIPT_DIR/scripts/start_services.py"
fi

# Check if start_services script exists
if [ ! -f "$SERVICES_SCRIPT" ]; then
    echo "ERROR: Services script not found at $SERVICES_SCRIPT"
    exit 1
fi

# Build arguments for start_services
SERVICE_ARGS=("$@")

# Add model argument (always include, using default or specified value)
SERVICE_ARGS+=(--model="$MODEL_ARG")

# Add all-services flag if requested
if [ "$ALL_SERVICES" = true ]; then
    SERVICE_ARGS+=(--all-services)
fi

# Forward all arguments to the appropriate start_services script
exec "$PYTHON" "$SERVICES_SCRIPT" "${SERVICE_ARGS[@]}"
