#!/bin/bash
# Mondrian Services Launcher
# Supports: model presets, base mode, RAG, LoRA adapters, all services
# Examples:
#   ./mondrian.sh --restart                                          (default: qwen3-4b-instruct)
#   ./mondrian.sh --restart --model-preset=qwen3-4b-thinking        (switch to thinking model)
#   ./mondrian.sh --restart --model-preset=qwen3-8b-instruct        (switch to 8B model)
#   ./mondrian.sh --restart --generation-profile=beam_search        (switch to beam search)
#   ./mondrian.sh --restart --generation-profile=sampling           (switch to sampling)
#   ./mondrian.sh --help                                             (show available model presets)
#   ./mondrian.sh --restart --mode=base                              (use base model without LoRA)
#   ./mondrian.sh --restart --model="Qwen/Custom-Model"             (override with custom model)

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
GENERATION_PROFILE=""
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
    elif [[ $arg == --generation-profile=* ]]; then
        GENERATION_PROFILE="${arg#--generation-profile=}"
        # Remove this from arguments passed to start_services
        set -- "${@/$arg}"
    elif [[ $arg == "--all-services" ]] || [[ $arg == "--full" ]]; then
        ALL_SERVICES=true
        # Remove this from arguments passed to start_services
        set -- "${@/$arg}"
    fi
done

# Load model configuration from model_config.json
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_CONFIG_FILE="$SCRIPT_DIR/model_config.json"

# Function to extract value from JSON using Python (fallback if jq not available)
extract_json_value() {
    local json_file=$1
    local key_path=$2
    python3 -c "import json, sys; f=open('$json_file'); d=json.load(f); keys='$key_path'.strip('.').split('.'); result=d; [result:=result[k] for k in keys]; print(result)" 2>/dev/null
}

# Parse model preset from --model-preset argument
MODEL_PRESET=""
for arg in "$@"; do
    if [[ $arg == --model-preset=* ]]; then
        MODEL_PRESET="${arg#--model-preset=}"
        # Remove this from arguments passed to start_services
        set -- "${@/$arg}"
        break
    fi
done

# Set default model preset if not specified
if [ -z "$MODEL_PRESET" ]; then
    MODEL_PRESET=$(extract_json_value "$MODEL_CONFIG_FILE" ".defaults.model_preset")
fi

# Extract model info from config
MODEL_ARG=$(extract_json_value "$MODEL_CONFIG_FILE" ".models.$MODEL_PRESET.model_id")
DEFAULT_LORA_PATH=$(extract_json_value "$MODEL_CONFIG_FILE" ".models.$MODEL_PRESET.adapter")
DEFAULT_MODE="lora"

if [ -z "$MODEL_ARG" ]; then
    echo "ERROR: Unknown model preset: $MODEL_PRESET"
    echo "Available presets:"
    python3 -c "import json; f=open('$MODEL_CONFIG_FILE'); d=json.load(f); [print(f'  - {k}: {v.get(\"name\")} ({v.get(\"description\")})') for k,v in d.get('models', {}).items()]"
    exit 1
fi

echo "Using model preset: $MODEL_PRESET"
echo "  Model: $MODEL_ARG"
echo "  Adapter: $DEFAULT_LORA_PATH"

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

# Add generation profile if specified
if [ -n "$GENERATION_PROFILE" ]; then
    SERVICE_ARGS+=(--generation-profile="$GENERATION_PROFILE")
fi

# Add all-services flag if requested
if [ "$ALL_SERVICES" = true ]; then
    SERVICE_ARGS+=(--all-services)
fi

# Forward all arguments to the appropriate start_services script
exec "$PYTHON" "$SERVICES_SCRIPT" "${SERVICE_ARGS[@]}"
