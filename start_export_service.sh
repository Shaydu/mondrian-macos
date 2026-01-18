#!/bin/bash
# Start Export Service for Mondrian
# Handles PDF/image export of analysis results

cd "$(dirname "$0")" || exit 1

# Default port
PORT=${1:-5007}

echo "Starting Mondrian Export Service on port $PORT..."
echo "Export endpoint: http://localhost:$PORT/export/<job_id>"
echo ""

python3 mondrian/export_service_linux.py \
    --port "$PORT" \
    --host 0.0.0.0 \
    --job-service-url "http://127.0.0.1:5005" \
    --advisor-service-url "http://127.0.0.1:5100"
