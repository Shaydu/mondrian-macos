#!/bin/bash

# Mondrian Services Manager - MLX/qwen3-vlm Version
# This is the updated script for starting all services with MLX/qwen3-vlm backend.

set -e

SCRIPT_VERSION="v2.0-MLX"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PORT_JOB=5005
PORT_AI=5100
MODEL="Qwen3-VL-4B-Instruct-MLX-4bit"
DB_PATH="mondrian.db"

# Get local IP (for reference)
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
fi

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Mondrian Services Manager ${SCRIPT_VERSION}${NC}"
echo -e "${CYAN}║  macOS Local Development Environment (MLX/qwen3-vlm)${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    if check_port $port; then
        echo -e "${YELLOW}  Killing process on port $port...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Function to test service endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local timeout=${3:-5}
    
    echo -n "  Testing $name... "
    if curl -s --max-time $timeout "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ DOWN${NC}"
        return 1
    fi
}

# Function to get Python from virtual environment
get_python() {
    if [ -f "../bin/python" ]; then
        echo "../bin/python"
    elif [ -f "../bin/python3" ]; then
        echo "../bin/python3"
    elif command -v python3 &> /dev/null; then
        echo "python3"
    else
        echo "python"
    fi
}

# Cleanup phase
print_section "Cleanup: Stopping Old Services"

echo "Clearing Python bytecode cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo -e "${GREEN}  ✓ Cache cleared${NC}"

echo ""
echo "Stopping existing services..."
kill_port $PORT_JOB
kill_port $PORT_AI
echo -e "${GREEN}  ✓ Old services stopped${NC}"

# Setup phase
print_section "Setup: Configuration & Verification"

PYTHON=$(get_python)
echo "Python: $PYTHON"
$PYTHON --version

echo ""
echo "Environment:"
echo "  Local IP: $LOCAL_IP"
echo "  Job Service Port: $PORT_JOB"
echo "  AI Advisor Port: $PORT_AI"
echo "  Model: $MODEL"
echo "  Database: $DB_PATH"

echo ""
echo "Creating directories..."
mkdir -p logs source edges analysis analysis_md prompts
echo -e "${GREEN}  ✓ Directories created${NC}"

# Database phase
print_section "Database: Initialization"

if [ -f "$DB_PATH" ]; then
    echo "Database exists: $DB_PATH"
    if $PYTHON -c "import sqlite3; conn = sqlite3.connect('$DB_PATH'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM advisors'); count = cursor.fetchone()[0]; conn.close(); exit(0 if count > 0 else 1)" 2>/dev/null; then
        echo -e "${GREEN}  ✓ Database already initialized${NC}"
    else
        echo "  Initializing database..."
        $PYTHON "mondrian/init_database.py"
    fi
else
    echo "Creating new database..."
    $PYTHON init_database.py
fi

# Services phase
print_section "Services: Starting AI Advisor & Job Service"

echo "Starting AI Advisor Service on port $PORT_AI..."
nohup $PYTHON ai_advisor_service_v1.13.py \
    --port $PORT_AI \
    --db "$DB_PATH" \
    --model "$MODEL" \
    --job_service_url "http://127.0.0.1:$PORT_JOB" \
    > logs/ai_advisor_out.log 2> logs/ai_advisor_err.log &
AI_PID=$!
sleep 2

echo "Starting Job Service on port $PORT_JOB..."
nohup $PYTHON job_service_v2.3.py \
    --port $PORT_JOB \
    --db "$DB_PATH" \
    --ai_service_url "http://127.0.0.1:$PORT_AI/analyze" \
    > logs/job_service_out.log 2> logs/job_service_err.log &
JOB_PID=$!
sleep 2

# Health check phase
print_section "Health Check: Verifying Services"

echo ""
echo "Checking service endpoints..."
echo ""

if test_endpoint "AI Advisor Service" "http://127.0.0.1:$PORT_AI/health"; then
    AI_HEALTH=$(curl -s "http://127.0.0.1:$PORT_AI/health")
    echo "  Response: $AI_HEALTH" | head -c 100
    echo ""
else
    echo -e "${RED}  ✗ AI Advisor Service failed to start${NC}"
    echo "  Check logs/ai_advisor_err.log for details"
    exit 1
fi

echo ""
if test_endpoint "Job Service" "http://127.0.0.1:$PORT_JOB/health"; then
    JOB_HEALTH=$(curl -s "http://127.0.0.1:$PORT_JOB/health")
    echo "  Response: $JOB_HEALTH" | head -c 100
    echo ""
else
    echo -e "${RED}  ✗ Job Service failed to start${NC}"
    echo "  Check logs/job_service_err.log for details"
    exit 1
fi

# Startup complete
print_section "Startup Complete"

echo ""
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo ""
echo "Service Endpoints:"
echo "  Job Service:     http://127.0.0.1:$PORT_JOB"
echo "  AI Advisor:      http://127.0.0.1:$PORT_AI"
echo ""
echo "Logs:"
echo "  logs/job_service_out.log"
echo "  logs/ai_advisor_out.log"
echo ""
echo "Database:"
echo "  $DB_PATH"
echo ""
echo "Next steps:"
echo "  1. Upload an image: curl -F 'image=@source/test.jpg' http://127.0.0.1:$PORT_JOB/upload"
echo "  2. Check status: curl http://127.0.0.1:$PORT_JOB/status/<job_id>"
echo "  3. Get analysis: curl http://127.0.0.1:$PORT_JOB/analysis/<job_id>"
echo ""
echo "Press Ctrl+C to stop services"
echo ""

# Monitoring loop
trap 'echo ""; echo "Shutting down services..."; kill $AI_PID $JOB_PID 2>/dev/null; exit 0' INT TERM

while true; do
    sleep 30
    if ! kill -0 $AI_PID 2>/dev/null; then
        echo -e "${RED}✗ AI Advisor Service crashed!${NC}"
        echo "  Restarting..."
        nohup $PYTHON ai_advisor_service_v1.13.py \
            --port $PORT_AI \
            --db "$DB_PATH" \
            --model "$MODEL" \
            --job_service_url "http://127.0.0.1:$PORT_JOB" \
            > logs/ai_advisor_out.log 2> logs/ai_advisor_err.log &
        AI_PID=$!
    fi
    if ! kill -0 $JOB_PID 2>/dev/null; then
        echo -e "${RED}✗ Job Service crashed!${NC}"
        echo "  Restarting..."
        nohup $PYTHON job_service_v2.3.py \
            --port $PORT_JOB \
            --db "$DB_PATH" \
            --ai_service_url "http://127.0.0.1:$PORT_AI/analyze" \
            > logs/job_service_out.log 2> logs/job_service_err.log &
        JOB_PID=$!
    fi
done
