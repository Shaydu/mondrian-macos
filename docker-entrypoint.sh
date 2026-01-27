#!/bin/bash
# Docker entrypoint - start services with embedded database

cd /app

# Database is embedded in the image at /app/mondrian.db
DB_PATH="/app/mondrian.db"

echo "========================================"
echo "Mondrian Docker Startup"
echo "========================================"
echo "Database: $DB_PATH"
echo ""

# Verify database exists
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at $DB_PATH"
    exit 1
fi

echo "Database size: $(du -h $DB_PATH | cut -f1)"
echo "Starting services..."
echo ""

# Create log directories
mkdir -p /app/logs

# Support LoRA+RAG mode and custom adapter paths via environment variables
SERVICE_ARGS="--db=$DB_PATH"

if [ -n "$MONDRIAN_MODE" ]; then
    SERVICE_ARGS="$SERVICE_ARGS --mode=$MONDRIAN_MODE"
    echo "Mode: $MONDRIAN_MODE"
fi

if [ -n "$MONDRIAN_LORA_PATH" ]; then
    SERVICE_ARGS="$SERVICE_ARGS --lora-path=$MONDRIAN_LORA_PATH"
    echo "LoRA Adapter: $MONDRIAN_LORA_PATH"
fi

if [ -n "$MONDRIAN_GENERATION_PROFILE" ]; then
    SERVICE_ARGS="$SERVICE_ARGS --generation-profile=$MONDRIAN_GENERATION_PROFILE"
    echo "Generation Profile: $MONDRIAN_GENERATION_PROFILE"
fi

echo ""

# Start services with explicit database path using --db= format
# The start_services.py script parses --db=<path>
exec python3 scripts/start_services.py start-comprehensive $SERVICE_ARGS
