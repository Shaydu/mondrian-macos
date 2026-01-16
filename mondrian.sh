#!/bin/bash
# Mondrian Services Launcher
# Supports: base mode, RAG, LoRA adapters, model selection, all services
# Examples:
#   ./mondrian.sh --restart                                          (all services, default: Qwen3-VL-4B + LoRA ansel_qwen3_4b_10ep)
#   ./mondrian.sh --restart --mode=base                              (use base model without LoRA)
#   ./mondrian.sh --restart --mode=lora --lora-path=adapters/ansel_qwen3_4b_10ep
#   ./mondrian.sh --restart --model="Qwen/Qwen2-VL-7B-Instruct"     (use different base model)
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

# Parse model and db arguments
MODEL_ARG=""
DB_ARG=""
ALL_SERVICES=false
for arg in "$@"; do
    if [[ $arg == --model=* ]]; then
        MODEL_ARG="${arg#--model=}"
        # Remove this from arguments passed to start_services
        set -- "${@/$arg}"
    elif [[ $arg == --db=* ]]; then
        DB_ARG="${arg#--db=}"
        # Remove this from arguments passed to start_services
        set -- "${@/$arg}"
    elif [[ $arg == "--all-services" ]] || [[ $arg == "--full" ]]; then
        ALL_SERVICES=true
        # Remove this from arguments passed to start_services
        set -- "${@/$arg}"
    fi
done

# Set default model if not specified (Qwen3-VL-4B for best compatibility)
if [ -z "$MODEL_ARG" ]; then
    MODEL_ARG="Qwen/Qwen3-VL-4B-Instruct"
fi

# Set default mode and LoRA adapter
DEFAULT_MODE="lora"
DEFAULT_LORA_PATH="./adapters/ansel_qwen3_4b_10ep"

# Check if mode was explicitly specified
MODE_SPECIFIED=false
for arg in "$@"; do
    if [[ $arg == --mode=* ]]; then
        MODE_SPECIFIED=true
        break
    fi
done

# Add default mode if not specified
if [ "$MODE_SPECIFIED" = false ]; then
    set -- "$@" "--mode=$DEFAULT_MODE"
    echo "Using default mode: $DEFAULT_MODE"
fi

# Check if lora-path was explicitly specified
LORA_PATH_SPECIFIED=false
for arg in "$@"; do
    if [[ $arg == --lora-path=* ]]; then
        LORA_PATH_SPECIFIED=true
        break
    fi
done

# Add default LoRA path if not specified and mode includes lora
if [ "$LORA_PATH_SPECIFIED" = false ]; then
    for arg in "$@"; do
        if [[ $arg == --mode=lora* ]]; then
            set -- "$@" "--lora-path=$DEFAULT_LORA_PATH"
            echo "Using default LoRA adapter: $DEFAULT_LORA_PATH"
            break
        fi
    done
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

# Add database argument if specified
if [ -n "$DB_ARG" ]; then
    SERVICE_ARGS+=(--db="$DB_ARG")
fi

# Add all-services flag if requested
if [ "$ALL_SERVICES" = true ]; then
    SERVICE_ARGS+=(--all-services)
fi

# Forward all arguments to the appropriate start_services script
exec "$PYTHON" "$SERVICES_SCRIPT" "${SERVICE_ARGS[@]}"
