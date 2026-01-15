#!/bin/bash

# Test script that mimics the exact iOS app API flow
# This exercises the same endpoints in the same order as the iOS app
# Now includes RAG (Retrieval-Augmented Generation) endpoints
# Supports mode switching for comparing different configurations

BASE_URL="http://127.0.0.1:5005"
RAG_URL="http://127.0.0.1:5400"
AI_ADVISOR_URL="http://127.0.0.1:5100"

# Parse command line arguments
MODE=""
LORA_PATH=""
AUTO_RESTART=false
ADVISOR="ansel"
TEST_IMAGE="test_image.png"

while [[ $# -gt 0 ]]; do
    case $1 in
        --mode=*)
            MODE="${1#*=}"
            shift
            ;;
        --lora-path=*)
            LORA_PATH="${1#*=}"
            shift
            ;;
        --auto-restart)
            AUTO_RESTART=true
            shift
            ;;
        --advisor=*)
            ADVISOR="${1#*=}"
            shift
            ;;
        --image=*)
            TEST_IMAGE="${1#*=}"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --mode=<mode>          Service mode: base, rag, lora, lora+rag, ab-test"
            echo "  --lora-path=<path>     Path to LoRA adapter (required for lora modes)"
            echo "  --auto-restart         Automatically restart services if mode doesn't match"
            echo "  --advisor=<name>       Advisor to use (default: ansel)"
            echo "  --image=<path>         Test image path (default: test_image.png)"
            echo "  --help, -h             Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --mode=base"
            echo "  $0 --mode=rag"
            echo "  $0 --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel --auto-restart"
            echo "  $0 --mode=lora+rag --lora-path=./models/qwen3-vl-4b-lora-ansel"
            exit 0
            ;;
        *)
            # Legacy: positional arguments for backward compatibility
            if [[ -z "$ADVISOR" || "$ADVISOR" == "ansel" ]]; then
                ADVISOR="$1"
            elif [[ -z "$TEST_IMAGE" || "$TEST_IMAGE" == "test_image.png" ]]; then
                TEST_IMAGE="$1"
            fi
            shift
            ;;
    esac
done

echo "🎨 Mondrian iOS API Flow Test (with Mode Support)"
echo "=================================================="
echo "Job Service URL: $BASE_URL"
echo "AI Advisor URL: $AI_ADVISOR_URL"
echo "RAG Service URL: $RAG_URL"
echo "Advisor: $ADVISOR"
echo "Test Image: $TEST_IMAGE"
if [[ -n "$MODE" ]]; then
    echo "Mode: $MODE"
fi
if [[ -n "$LORA_PATH" ]]; then
    echo "LoRA Path: $LORA_PATH"
fi
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Function to check and optionally restart services with mode
check_and_restart_services() {
    if [[ -z "$MODE" ]]; then
        return  # No mode specified, skip check
    fi
    
    echo -e "${CYAN}🔍 Checking service mode...${NC}"
    
    # Check AI Advisor Service health
    HEALTH_RESPONSE=$(curl -s "$AI_ADVISOR_URL/health" 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ AI Advisor Service is not running${NC}"
        
        if [[ "$AUTO_RESTART" == true ]]; then
            echo -e "${YELLOW}🔄 Auto-restarting services in $MODE mode...${NC}"
            restart_services
            return
        else
            echo -e "${YELLOW}To start services: ./mondrian.sh --restart --mode=$MODE${NC}"
            if [[ -n "$LORA_PATH" ]]; then
                echo -e "${YELLOW}                    --lora-path=$LORA_PATH${NC}"
            fi
            exit 1
        fi
    fi
    
    # Parse current mode
    CURRENT_MODE=$(echo "$HEALTH_RESPONSE" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('model_mode', 'base'))" 2>/dev/null)
    IS_FINE_TUNED=$(echo "$HEALTH_RESPONSE" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('fine_tuned', False))" 2>/dev/null)
    
    echo "Current mode: $CURRENT_MODE, Fine-tuned: $IS_FINE_TUNED"
    
    # Check if mode matches
    MODE_MATCHES=false
    case "$MODE" in
        base)
            [[ "$CURRENT_MODE" == "base" ]] && MODE_MATCHES=true
            ;;
        rag)
            # RAG doesn't change service mode
            MODE_MATCHES=true
            ;;
        lora|lora+rag)
            [[ "$CURRENT_MODE" == "fine_tuned" && "$IS_FINE_TUNED" == "True" ]] && MODE_MATCHES=true
            ;;
        ab-test)
            [[ "$CURRENT_MODE" == "ab_test" ]] && MODE_MATCHES=true
            ;;
    esac
    
    if [[ "$MODE_MATCHES" == false ]]; then
        echo -e "${YELLOW}⚠️  Service mode mismatch: expected $MODE, got $CURRENT_MODE${NC}"
        
        if [[ "$AUTO_RESTART" == true ]]; then
            echo -e "${YELLOW}🔄 Auto-restarting services in $MODE mode...${NC}"
            restart_services
        else
            echo -e "${YELLOW}Tip: Add --auto-restart to automatically restart services${NC}"
            echo -e "${YELLOW}Or manually run: ./mondrian.sh --restart --mode=$MODE${NC}"
            if [[ -n "$LORA_PATH" ]]; then
                echo -e "${YELLOW}                 --lora-path=$LORA_PATH${NC}"
            fi
        fi
    else
        echo -e "${GREEN}✅ Service mode matches: $MODE${NC}"
    fi
    echo ""
}

restart_services() {
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}Restarting Services in $MODE Mode${NC}"
    echo -e "${CYAN}================================${NC}"
    
    # Build restart command
    RESTART_CMD="./mondrian.sh --restart --mode=$MODE"
    if [[ -n "$LORA_PATH" ]]; then
        RESTART_CMD="$RESTART_CMD --lora-path=$LORA_PATH"
    fi
    
    echo "Running: $RESTART_CMD"
    
    # Execute restart
    if eval "$RESTART_CMD"; then
        echo -e "${GREEN}✅ Services restarted successfully${NC}"
        echo "Waiting for services to be ready..."
        sleep 5
    else
        echo -e "${RED}❌ Failed to restart services${NC}"
        exit 1
    fi
    echo ""
}

# Check services and restart if needed
check_and_restart_services

# Step 1: Fetch Advisors (like AdvisorSelectionView does)
echo -e "${BLUE}📋 Step 1: Fetching available advisors...${NC}"
echo "GET $BASE_URL/advisors"
ADVISORS_RESPONSE=$(curl -s "$BASE_URL/advisors")

if [[ $? -eq 0 ]] && [[ $ADVISORS_RESPONSE == *"advisors"* ]]; then
    echo -e "${GREEN}✅ Advisors fetched successfully${NC}"
    echo "Available advisors:"
    echo "$ADVISORS_RESPONSE" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | head -10 | while read name; do
        echo "  • $name"
    done
    echo ""
else
    echo -e "${RED}❌ Failed to fetch advisors${NC}"
    echo "Response: $ADVISORS_RESPONSE"
    exit 1
fi

# Create a test image if it doesn't exist
if [[ ! -f "$TEST_IMAGE" ]]; then
    echo -e "${YELLOW}⚠️  Test image not found, creating a minimal PNG...${NC}"
    # Create a 100x100 red square PNG
    echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==" | base64 -d > "$TEST_IMAGE"
    echo ""
fi

# Step 2: Upload Image (like uploadImage() in AdvisorSelectionView)
echo -e "${BLUE}📤 Step 2: Uploading image with advisor selection...${NC}"
echo "POST $BASE_URL/upload"
echo "  - image: $TEST_IMAGE"
echo "  - advisor: $ADVISOR"
echo "  - auto_analyze: true"

UPLOAD_RESPONSE=$(curl -s -X POST \
    -F "image=@$TEST_IMAGE" \
    -F "advisor=$ADVISOR" \
    -F "auto_analyze=true" \
    "$BASE_URL/upload")

echo "Upload Response:"
echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_RESPONSE"
echo ""

# Extract job ID (same as iOS app does in uploadImage())
JOB_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"job_id":"[^"]*"' | sed 's/"job_id":"//g' | sed 's/"//g')

if [[ -z "$JOB_ID" ]]; then
    echo -e "${RED}❌ Upload failed - no job_id received${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Upload successful!${NC}"
echo -e "Job ID: ${YELLOW}$JOB_ID${NC}"
echo ""

# Step 3: Stream Job Updates (like iOS SSEStreamServiceWithDelegate does)
echo -e "${BLUE}🌊 Step 3: Listening to SSE stream (exactly like iOS)...${NC}"
echo "GET $BASE_URL/stream/$JOB_ID"
echo "Waiting for SSE events: connected, status_update, analysis_complete, done"
echo ""

# Capture SSE stream to file (handles fast streams better than while read)
STREAM_FILE="/tmp/mondrian_stream_$JOB_ID.txt"
curl -s -N \
    -H "Accept: text/event-stream" \
    -H "Cache-Control: no-cache" \
    -H "Connection: keep-alive" \
    "$BASE_URL/stream/$JOB_ID" > "$STREAM_FILE"

echo "📥 Stream completed, processing events..."
echo ""

# Process the captured stream
ANALYSIS_HTML=""
STATUS="unknown"
RECEIVED_ANALYSIS=false
EVENT_TYPE=""

while IFS= read -r line; do
    # Parse SSE event format
    if [[ $line == event:* ]]; then
        EVENT_TYPE=$(echo "$line" | sed 's/^event: *//')
        echo -e "${YELLOW}📨 SSE Event: $EVENT_TYPE${NC}"
    elif [[ $line == data:* ]]; then
        EVENT_DATA=$(echo "$line" | sed 's/^data: *//')
        
        case $EVENT_TYPE in
            "connected")
                JOB_ID_FROM_EVENT=$(echo "$EVENT_DATA" | grep -o '"job_id":"[^"]*"' | sed 's/"job_id":"//g' | sed 's/"//g')
                echo "✅ SSE: Connected to stream for job: $JOB_ID_FROM_EVENT"
                ;;
            
            "heartbeat")
                TIMESTAMP=$(echo "$EVENT_DATA" | grep -o '"timestamp":[^,}]*' | sed 's/"timestamp"://g')
                echo "💓 SSE: Heartbeat at $TIMESTAMP"
                ;;
            
            "status_update")
                # Parse status update
                JOB_STATUS=$(echo "$EVENT_DATA" | grep -o '"status":"[^"]*"' | sed 's/"status":"//g' | sed 's/"//g')
                CURRENT_STEP=$(echo "$EVENT_DATA" | grep -o '"current_step":"[^"]*"' | sed 's/"current_step":"//g' | sed 's/"//g')
                STEP_PHASE=$(echo "$EVENT_DATA" | grep -o '"step_phase":"[^"]*"' | sed 's/"step_phase":"//g' | sed 's/"//g')
                
                echo "📊 SSE: Status Update"
                echo "   Status: $JOB_STATUS"
                [[ -n "$CURRENT_STEP" ]] && echo "   Step: $CURRENT_STEP"
                [[ -n "$STEP_PHASE" ]] && echo "   Phase: $STEP_PHASE"
                
                # Check for error
                if [[ "$JOB_STATUS" == "error" ]]; then
                    echo -e "${RED}❌ Analysis failed!${NC}"
                    echo "Error: $CURRENT_STEP"
                    rm -f "$STREAM_FILE"
                    exit 1
                fi
                ;;
            
            "analysis_complete")
                echo -e "${GREEN}✅ SSE: Analysis complete event received${NC}"
                # Save event data and extract HTML using Python for proper JSON parsing
                echo "$EVENT_DATA" > /tmp/sse_event_data.json

                ANALYSIS_HTML=$(python3 -c "import json, sys; data=json.load(open('/tmp/sse_event_data.json')); print(data.get('analysis_html', ''))" 2>/dev/null)

                if [[ -n "$ANALYSIS_HTML" ]] && [[ ${#ANALYSIS_HTML} -gt 100 ]]; then
                    echo "📄 Received HTML analysis via SSE: ${#ANALYSIS_HTML} characters"
                    RECEIVED_ANALYSIS=true
                    STATUS="done"
                    # Will save this HTML later in the output directory
                else
                    echo "⚠️ Analysis HTML in event is empty or too short, will fetch via API"
                fi
                ;;
            
            "done")
                echo -e "${GREEN}✅ SSE: Stream complete (done event)${NC}"
                STATUS="done"
                ;;
        esac
    fi
done < "$STREAM_FILE"

echo ""

# Clean up stream file
rm -f "$STREAM_FILE"

# Step 4: Fetch Analysis if needed (like iOS does on 'done' event without analysis_complete)
ANALYSIS_RESPONSE=""
if [[ "$RECEIVED_ANALYSIS" == true ]]; then
    echo -e "${GREEN}✅ Using analysis from SSE (analysis_complete)${NC}"
    ANALYSIS_RESPONSE="$ANALYSIS_HTML"
elif [[ "$STATUS" == "done" ]]; then
    echo -e "${BLUE}📝 Step 4: Fetching analysis via API (didn't receive via SSE)...${NC}"
    echo "GET $BASE_URL/analysis/$JOB_ID"
    echo ""
    ANALYSIS_RESPONSE=$(curl -s "$BASE_URL/analysis/$JOB_ID")
else
    echo -e "${RED}❌ No analysis received${NC}"
    rm -f /tmp/sse_event_data.json
    exit 1
fi

ANALYSIS_LENGTH=${#ANALYSIS_RESPONSE}
if [[ $ANALYSIS_LENGTH -le 0 ]]; then
    echo -e "${RED}❌ Analysis is empty${NC}"
    rm -f /tmp/sse_event_data.json
    exit 1
fi

echo -e "${GREEN}✅ Analysis received: $ANALYSIS_LENGTH characters${NC}"
echo ""

# Create output directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="../analysis_output/${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

# Save analysis HTML from whichever source we got it
if [[ "$RECEIVED_ANALYSIS" == true ]]; then
    # Save SSE version
    SSE_FILE="$OUTPUT_DIR/analysis_sse.html"
    echo "$ANALYSIS_RESPONSE" > "$SSE_FILE"
    echo "Analysis from SSE saved to: $SSE_FILE"
else
    # Save API version
    API_FILE="$OUTPUT_DIR/analysis_api.html"
    echo "$ANALYSIS_RESPONSE" > "$API_FILE"
    echo "Analysis from API saved to: $API_FILE"
fi

# Also save full JSON event data if we got it via SSE
if [[ -f /tmp/sse_event_data.json ]]; then
    cp /tmp/sse_event_data.json "$OUTPUT_DIR/sse_event.json"
    echo "SSE event data saved to: $OUTPUT_DIR/sse_event.json"
fi

echo ""

# Show preview
echo -e "${BLUE}📄 Analysis Preview (first 1000 chars):${NC}"
echo "========================================"
echo "${ANALYSIS_RESPONSE:0:1000}"
if [[ $ANALYSIS_LENGTH -gt 1000 ]]; then
    echo "..."
    echo "(truncated - see full file for complete output)"
fi
echo "========================================"
echo ""

# Check for errors in the HTML
if echo "$ANALYSIS_RESPONSE" | grep -q "ERROR:"; then
    echo -e "${RED}⚠️  WARNING: Analysis contains ERROR messages${NC}"
    echo "Errors found:"
    echo "$ANALYSIS_RESPONSE" | grep "ERROR:"
    echo ""
fi

# Check for table tags (proper HTML rendering)
if echo "$ANALYSIS_RESPONSE" | grep -q "<table"; then
    echo "✅ HTML contains <table> tags - proper rendering expected"
elif echo "$ANALYSIS_RESPONSE" | grep -q "|"; then
    echo -e "${YELLOW}⚠️  HTML contains pipe characters - may be markdown format${NC}"
fi
echo ""

# Cleanup temp files
# Step 5: RAG - Index the analyzed image (NEW for iOS)
echo -e "${BLUE}🔍 Step 5: Indexing image for semantic search (RAG)...${NC}"
echo "POST $RAG_URL/index"
echo ""

# Get the actual image path from the job
IMAGE_PATH="source/$(echo "$UPLOAD_RESPONSE" | grep -o '"filename":"[^"]*"' | sed 's/"filename":"//g' | sed 's/"//g')"

INDEX_RESPONSE=$(curl -s -X POST "$RAG_URL/index" \
    -H "Content-Type: application/json" \
    -d "{\"job_id\": \"$JOB_ID\", \"image_path\": \"$IMAGE_PATH\"}")

if echo "$INDEX_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ Image indexed successfully${NC}"
    CAPTION=$(echo "$INDEX_RESPONSE" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('caption', 'N/A')[:100])" 2>/dev/null)
    echo "Caption: $CAPTION..."
    echo ""
else
    echo -e "${YELLOW}⚠️  Indexing failed or unavailable (RAG service may not be running)${NC}"
    echo "Response: $INDEX_RESPONSE"
    echo ""
fi

# Step 6: RAG - Search for similar images (NEW for iOS)
echo -e "${BLUE}🔎 Step 6: Searching for similar images...${NC}"
echo "POST $RAG_URL/search"
echo ""

# Use advisor name as search query for testing
SEARCH_QUERY="professional photography in the style of $ADVISOR"

SEARCH_RESPONSE=$(curl -s -X POST "$RAG_URL/search" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$SEARCH_QUERY\", \"top_k\": 5}")

if echo "$SEARCH_RESPONSE" | grep -q '"results"'; then
    echo -e "${GREEN}✅ Search completed${NC}"
    RESULT_COUNT=$(echo "$SEARCH_RESPONSE" | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data.get('results', [])))" 2>/dev/null)
    echo "Found $RESULT_COUNT similar images"
    
    # Show top result
    if [[ "$RESULT_COUNT" -gt 0 ]]; then
        echo ""
        echo "Top result:"
        echo "$SEARCH_RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
results = data.get('results', [])
if results:
    top = results[0]
    print(f\"  Job ID: {top.get('job_id', 'N/A')}\")
    print(f\"  Image: {top.get('image_path', 'N/A')}\")
    print(f\"  Similarity: {top.get('similarity', 0):.2f}\")
    print(f\"  Caption: {top.get('caption', 'N/A')[:80]}...\")
" 2>/dev/null
    fi
    echo ""
else
    echo -e "${YELLOW}⚠️  Search failed or unavailable (RAG service may not be running)${NC}"
    echo "Response: $SEARCH_RESPONSE"
    echo ""
fi

echo -e "${GREEN}🏁 Test Complete!${NC}"
echo ""

# Create summary.txt file
SUMMARY_FILE="$OUTPUT_DIR/summary.txt"
cat > "$SUMMARY_FILE" << SUMMARY_END
================================================================================
iOS API Flow Test Summary
================================================================================
Test Date: $(date)
Job ID: $JOB_ID
Advisor: $ADVISOR
Test Image: $TEST_IMAGE
Mode: ${MODE:-default}
$([ -n "$LORA_PATH" ] && echo "LoRA Path: $LORA_PATH")

Test Results:
-------------
✅ Step 1: Fetch Advisors - SUCCESS
✅ Step 2: Upload Image - SUCCESS
$([ "$RECEIVED_ANALYSIS" == true ] && echo "✅ Step 3: SSE Stream - SUCCESS (received analysis_html)" || echo "⚠️  Step 3: SSE Stream - Used API fallback")
✅ Step 4: Get Analysis - SUCCESS
$(echo "$INDEX_RESPONSE" | grep -q '"success":true' && echo "✅ Step 5: RAG Index - SUCCESS" || echo "⚠️  Step 5: RAG Index - FAILED")
$(echo "$SEARCH_RESPONSE" | grep -q '"results"' && echo "✅ Step 6: RAG Search - SUCCESS" || echo "⚠️  Step 6: RAG Search - FAILED")

Analysis Details:
-----------------
Status: $STATUS
Progress: 100%
Analysis Source: $([ "$RECEIVED_ANALYSIS" == true ] && echo "SSE analysis_complete event" || echo "API /analysis endpoint")
Analysis Length: $ANALYSIS_LENGTH characters

Output Files:
-------------
- Summary: $SUMMARY_FILE
$([ "$RECEIVED_ANALYSIS" == true ] && echo "- Analysis (SSE): $SSE_FILE" || echo "- Analysis (API): $API_FILE")
$([ -f "$OUTPUT_DIR/sse_event.json" ] && echo "- SSE Event JSON: $OUTPUT_DIR/sse_event.json" || echo "- SSE Event: Not captured")

================================================================================
SUMMARY_END

echo "Summary:"
echo "  Job ID: $JOB_ID"
echo "  Mode: ${MODE:-default}"
if [[ -n "$LORA_PATH" ]]; then
    echo "  LoRA Path: $LORA_PATH"
fi
echo "  Final Status: $STATUS"
echo "  Analysis Source: $([ "$RECEIVED_ANALYSIS" == true ] && echo "SSE analysis_complete event" || echo "API /analysis endpoint")"
echo "  Analysis Length: $ANALYSIS_LENGTH chars"
echo "  Output Directory: $OUTPUT_DIR"
echo ""
echo "iOS App Flow (Complete):"
echo "  1. ✅ Fetch advisors list (GET /advisors)"
echo "  2. ✅ Upload image with advisor (POST /upload with auto_analyze=true)"
echo "  3. ✅ Listen to SSE stream (GET /stream/{job_id})"
echo "  4. ✅ Get analysis HTML (via SSE or GET /analysis/{job_id})"
echo "  5. ✅ Index image for search (POST /rag/index)"
echo "  6. ✅ Search similar images (POST /rag/search)"
echo ""
echo "Note: RAG endpoints require the following services running:"
echo "  - Caption Service (port 5200)"
echo "  - Embedding Service (port 5300)"
echo "  - RAG Service (port 5400)
echo "  - Only listens to SSE events"
echo "  - Receives HTML via analysis_complete event or fetches via API on done event"
