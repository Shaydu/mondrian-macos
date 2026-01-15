#!/bin/bash
# RAG+LoRA E2E Test Runner
# Uses Python 3.12 (same as services) for compatibility
# Automatically detects and uses the correct Python version

set -e

PYTHON312="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_SCRIPT="$SCRIPT_DIR/test_rag_lora_e2e.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}RAG+LoRA E2E Test Runner${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if test script exists
if [ ! -f "$TEST_SCRIPT" ]; then
    echo -e "${RED}ERROR: Test script not found at $TEST_SCRIPT${NC}"
    exit 1
fi

# Check if Python 3.12 is installed
if [ ! -f "$PYTHON312" ]; then
    echo -e "${YELLOW}WARNING: Python 3.12 not found at $PYTHON312${NC}"
    echo "Falling back to system python3..."
    PYTHON_BIN="python3"
else
    echo -e "${GREEN}✓ Using Python 3.12 (same as services)${NC}"
    PYTHON_BIN="$PYTHON312"
fi

# Verify Python version
PYTHON_VERSION=$($PYTHON_BIN --version 2>&1)
echo "Python: $PYTHON_VERSION"

# Check if test image exists
TEST_IMAGE="$PROJECT_ROOT/source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg"
if [ ! -f "$TEST_IMAGE" ]; then
    echo -e "${YELLOW}WARNING: Test image not found at $TEST_IMAGE${NC}"
else
    echo -e "${GREEN}✓ Test image found${NC}"
fi

# Check if services are running
echo -e "\n${BLUE}Checking services...${NC}"
AI_SERVICE_UP=false
JOB_SERVICE_UP=false

# Check AI Advisor Service
if curl -s http://localhost:5100/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ AI Advisor Service (5100) is running${NC}"
    AI_SERVICE_UP=true
else
    echo -e "${RED}✗ AI Advisor Service (5100) is NOT running${NC}"
fi

# Check Job Service
if curl -s http://localhost:5005/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Job Service (5005) is running${NC}"
    JOB_SERVICE_UP=true
else
    echo -e "${YELLOW}⊘ Job Service (5005) is NOT running (optional)${NC}"
fi

if [ "$AI_SERVICE_UP" = false ]; then
    echo -e "\n${RED}ERROR: AI Advisor Service must be running!${NC}"
    echo "Start services with:"
    echo "  ./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel"
    exit 1
fi

# Run the test script with all arguments passed through
echo -e "\n${BLUE}Running tests...${NC}\n"
"$PYTHON_BIN" "$TEST_SCRIPT" "$@"
TEST_EXIT_CODE=$?

echo -e "\n${BLUE}========================================${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Tests completed successfully${NC}"
else
    echo -e "${YELLOW}⊘ Some tests did not pass (exit code: $TEST_EXIT_CODE)${NC}"
fi
echo -e "${BLUE}========================================${NC}\n"

exit $TEST_EXIT_CODE
