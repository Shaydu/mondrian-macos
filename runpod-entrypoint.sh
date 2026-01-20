#!/bin/bash
# RunPod entrypoint script - handles initialization and service startup

set -e

echo "==================================="
echo "Mondrian RunPod Initialization"
echo "==================================="

# Display GPU information
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Information:"
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
    echo ""
fi

# Check if database exists, if not initialize it
if [ ! -f /app/mondrian.db ]; then
    echo "Database not found. Initializing..."
    python3 init_database.py
    echo "Database initialized successfully"
else
    echo "Database found: /app/mondrian.db"
fi

# Create necessary directories
mkdir -p /app/logs /app/uploads /app/temp /app/models

# Display environment info
echo ""
echo "Environment:"
echo "  Python: $(python3 --version)"
echo "  PyTorch: $(python3 -c 'import torch; print(torch.__version__)' 2>/dev/null || echo 'Not installed')"
echo "  CUDA Available: $(python3 -c 'import torch; print(torch.cuda.is_available())' 2>/dev/null || echo 'N/A')"
echo "  CUDA Version: $(python3 -c 'import torch; print(torch.version.cuda if torch.cuda.is_available() else \"N/A\")' 2>/dev/null || echo 'N/A')"
echo ""

# Parse command line arguments
MODE="${MODE:-base}"
BACKEND="${BACKEND:-bnb}"
LORA_PATH="${LORA_PATH:-}"

# Export service URLs for internal communication
export AI_ADVISOR_URL="${AI_ADVISOR_URL:-http://localhost:5100}"
export JOB_SERVICE_URL="${JOB_SERVICE_URL:-http://localhost:5005}"
export SUMMARY_SERVICE_URL="${SUMMARY_SERVICE_URL:-http://localhost:5006}"

# CRITICAL: Override database path in config to use container path
# This ensures services connect to /app/mondrian.db, not the host path
DB_PATH="/app/mondrian.db"
sqlite3 $DB_PATH "INSERT OR REPLACE INTO config (key, value) VALUES ('db_path', '$DB_PATH');" 2>/dev/null || true

echo "Configuration:"
echo "  Mode: $MODE"
echo "  Backend: $BACKEND"
echo "  LoRA Path: ${LORA_PATH:-none}"
echo "  Database: $DB_PATH"
echo ""

# Start services based on configuration
CMD_ARGS=("start-comprehensive")

# CRITICAL: Pass explicit database path as argument
CMD_ARGS+=("--db-path" "/app/mondrian.db")

if [ "$MODE" != "base" ]; then
    CMD_ARGS+=("--mode" "$MODE")
fi

if [ -n "$BACKEND" ]; then
    CMD_ARGS+=("--backend" "$BACKEND")
fi

if [ -n "$LORA_PATH" ]; then
    CMD_ARGS+=("--lora-path" "$LORA_PATH")
fi

echo "Starting Mondrian services..."
echo "Command: python3 scripts/start_services.py ${CMD_ARGS[*]}"
echo ""
echo "==================================="
echo ""

# Execute the main command
exec python3 scripts/start_services.py "${CMD_ARGS[@]}"
