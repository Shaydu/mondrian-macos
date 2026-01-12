#!/bin/bash
# Test script for ENABLE_RAG flag implementation
# Tests both baseline (false) and RAG (true) modes

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "Testing ENABLE_RAG Flag Implementation"
echo "========================================="
echo ""

# Check if services are running
echo "Checking if services are running..."
if ! curl -s http://localhost:5100/health > /dev/null 2>&1; then
    echo -e "${RED}✗ AI Service not running on port 5100${NC}"
    echo "Start with: cd mondrian && python3 ai_advisor_service.py --port 5100"
    exit 1
fi

if ! curl -s http://localhost:5005/health > /dev/null 2>&1; then
    echo -e "${RED}✗ Job Service not running on port 5005${NC}"
    echo "Start with: cd mondrian && python3 job_service_v2.3.py --port 5005"
    exit 1
fi

echo -e "${GREEN}✓ Both services are running${NC}"
echo ""

# Check test image
TEST_IMAGE="${1:-mondrian/source/advisor/photographer/ansel/Adams_The_Tetons_and_the_Snake_River.jpg}"
if [ ! -f "$TEST_IMAGE" ]; then
    echo -e "${RED}✗ Test image not found: $TEST_IMAGE${NC}"
    echo "Usage: $0 <path_to_test_image>"
    exit 1
fi

echo "Using test image: $TEST_IMAGE"
echo ""

# Check database state
echo "Checking database state..."
ADVISOR_COUNT=$(sqlite3 mondrian/mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel'" 2>/dev/null || echo "0")
echo "Advisor profiles in database: $ADVISOR_COUNT"

if [ "$ADVISOR_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}⚠️  No advisor profiles found${NC}"
    echo "RAG mode will fall back to baseline until you run:"
    echo "  python3 tools/rag/index_ansel_dimensional_profiles.py"
    echo ""
fi

# Test 1: Baseline mode (enable_rag=false)
echo "========================================="
echo "TEST 1: Baseline Mode (enable_rag=false)"
echo "========================================="
echo ""

RESPONSE1=$(curl -s -X POST http://localhost:5005/upload \
  -F "image=@$TEST_IMAGE" \
  -F "advisor=ansel" \
  -F "enable_rag=false")

JOB_ID1=$(echo "$RESPONSE1" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])" 2>/dev/null || echo "")

if [ -z "$JOB_ID1" ]; then
    echo -e "${RED}✗ Failed to upload image${NC}"
    echo "Response: $RESPONSE1"
    exit 1
fi

echo -e "${GREEN}✓ Image uploaded${NC}"
echo "Job ID: $JOB_ID1"
echo "Status URL: http://localhost:5005/status/$JOB_ID1"
echo ""
echo "Waiting for baseline analysis to complete..."

# Wait for completion (max 2 minutes)
for i in {1..120}; do
    STATUS=$(curl -s "http://localhost:5005/status/$JOB_ID1" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
    if [ "$STATUS" = "done" ]; then
        echo -e "${GREEN}✓ Baseline analysis complete${NC}"
        break
    elif [ "$STATUS" = "error" ]; then
        echo -e "${RED}✗ Baseline analysis failed${NC}"
        exit 1
    fi
    sleep 1
    if [ $((i % 10)) -eq 0 ]; then
        echo "  Still processing... ($i seconds)"
    fi
done

echo ""
echo "Check logs for: [BASELINE] ===== SINGLE-PASS BASELINE ANALYSIS (NO RAG) ====="
echo ""

# Test 2: RAG mode (enable_rag=true)
echo "========================================="
echo "TEST 2: RAG Mode (enable_rag=true)"
echo "========================================="
echo ""

RESPONSE2=$(curl -s -X POST http://localhost:5005/upload \
  -F "image=@$TEST_IMAGE" \
  -F "advisor=ansel" \
  -F "enable_rag=true")

JOB_ID2=$(echo "$RESPONSE2" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])" 2>/dev/null || echo "")

if [ -z "$JOB_ID2" ]; then
    echo -e "${RED}✗ Failed to upload image${NC}"
    echo "Response: $RESPONSE2"
    exit 1
fi

echo -e "${GREEN}✓ Image uploaded${NC}"
echo "Job ID: $JOB_ID2"
echo "Status URL: http://localhost:5005/status/$JOB_ID2"
echo ""
echo "Waiting for RAG analysis to complete (2-pass, takes longer)..."

# Wait for completion (max 3 minutes for 2-pass)
for i in {1..180}; do
    STATUS=$(curl -s "http://localhost:5005/status/$JOB_ID2" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
    if [ "$STATUS" = "done" ]; then
        echo -e "${GREEN}✓ RAG analysis complete${NC}"
        break
    elif [ "$STATUS" = "error" ]; then
        echo -e "${RED}✗ RAG analysis failed${NC}"
        exit 1
    fi
    sleep 1
    if [ $((i % 10)) -eq 0 ]; then
        echo "  Still processing... ($i seconds)"
    fi
done

echo ""
echo "Check logs for:"
echo "  [RAG] 2-PASS RAG WORKFLOW ACTIVATED"
echo "  [RAG PASS 1] Extracting dimensional profile..."
echo "  [RAG QUERY] Searching for similar Ansel Adams images..."
echo "  [RAG PASS 2] ===== FULL ANALYSIS WITH RAG CONTEXT ====="
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "Baseline Job: http://localhost:5005/status/$JOB_ID1"
echo "RAG Job:      http://localhost:5005/status/$JOB_ID2"
echo ""
echo -e "${GREEN}✓ Both tests completed${NC}"
echo ""
echo "To view results:"
echo "  curl http://localhost:5005/status/$JOB_ID1 | python3 -m json.tool"
echo "  curl http://localhost:5005/status/$JOB_ID2 | python3 -m json.tool"
echo ""
echo "To compare outputs, save HTML and open in browser:"
echo "  curl http://localhost:5005/status/$JOB_ID1 | python3 -c \"import sys, json; print(json.load(sys.stdin)['analysis_markdown'])\" > baseline.html"
echo "  curl http://localhost:5005/status/$JOB_ID2 | python3 -c \"import sys, json; print(json.load(sys.stdin)['analysis_markdown'])\" > rag.html"
echo "  open baseline.html rag.html"




