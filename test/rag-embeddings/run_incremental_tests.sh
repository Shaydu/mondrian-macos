#!/bin/bash
# Incremental Mode Test Runner
# Runs all four modes sequentially and reports which ones pass/fail

# Don't use 'set -e' as we need to handle test failures gracefully
set +e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_DIR="$PROJECT_DIR/test/rag-embeddings"
LOG_DIR="$PROJECT_DIR/logs/tests"
RESULT_FILE="$LOG_DIR/incremental_test_results.txt"

# Test configurations (mode, mode_arg1, mode_arg2, description)
TESTS=(
    "baseline,--mode=base,,Base model only"
    "rag,--mode=rag,,Base model with RAG"
    "lora,--mode=lora,--lora-path=./adapters/ansel,Base model with LoRA"
    "lora_rag,--mode=lora+rag,--lora-path=./adapters/ansel,LoRA model with RAG"
)

# Test results
declare -A RESULTS
declare -a PASSED_TESTS
declare -a FAILED_TESTS

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_fail() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Create log directory
mkdir -p "$LOG_DIR"

# Start
print_header "INCREMENTAL MODE TEST SUITE"
echo "Project: $PROJECT_DIR"
echo "Test directory: $TEST_DIR"
echo "Results will be saved to: $RESULT_FILE"
echo ""

# Clear results file
> "$RESULT_FILE"

# Change to project directory
cd "$PROJECT_DIR"

# Ensure venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_info "Activating virtual environment..."
    source mondrian/venv/bin/activate
fi

print_step "Stopping any running services..."
./mondrian.sh --stop 2>/dev/null || true
sleep 3

# Run each test
for test_config in "${TESTS[@]}"; do
    IFS=',' read -r mode mode_arg1 mode_arg2 description <<< "$test_config"
    
    print_header "TEST: $description"
    echo "Test: $mode"
    
    {
        echo ""
        echo "========== $mode ($(date)) =========="
        echo "Description: $description"
        echo ""
    } >> "$RESULT_FILE"
    
    # Build command
    restart_cmd="./mondrian.sh --restart $mode_arg1 --no-monitor"
    if [ -n "$mode_arg2" ]; then
        restart_cmd="$restart_cmd $mode_arg2"
    fi
    
    # Start service - capture output to file and run in background
    print_step "Starting service: $restart_cmd"
    service_log="$LOG_DIR/service_startup_${mode}_$$.log"
    
    # Run service startup directly in background
    bash -c "cd '$PROJECT_DIR' && $restart_cmd" > "$service_log" 2>&1 &
    service_pid=$!
    print_success "Service process started (PID: $service_pid)"
    
    # Wait for services to initialize with better polling
    print_step "Waiting for services to initialize..."
    max_wait=90
    waited=0
    service_ready=false
    
    while [ $waited -lt $max_wait ]; do
        # Check if AI Advisor service is responding
        if curl -s -m 5 http://localhost:5100/health > /dev/null 2>&1; then
            print_success "Service is responding"
            service_ready=true
            break
        fi
        
        # Also check if the process is still running
        if ! kill -0 $service_pid 2>/dev/null; then
            print_fail "Service process has terminated"
            {
                echo "Service process terminated unexpectedly"
                echo "Service startup log:"
                cat "$service_log"
                echo ""
            } >> "$RESULT_FILE"
            RESULTS[$mode]="FAILED (process died)"
            FAILED_TESTS+=("$mode")
            service_ready=false
            break
        fi
        
        printf "."
        sleep 2
        waited=$((waited + 2))
    done
    
    if [ "$service_ready" = false ]; then
        if [ $waited -ge $max_wait ]; then
            print_fail "Service did not respond within $max_wait seconds"
            {
                echo "Status: FAILED (service not ready after $max_wait seconds)"
                echo "Service log last 30 lines:"
                tail -30 "$service_log"
                echo ""
            } >> "$RESULT_FILE"
        fi
        RESULTS[$mode]="FAILED (service not ready)"
        FAILED_TESTS+=("$mode")
        continue
    fi
    
    echo ""  # New line after dots
    sleep 2  # Additional buffer
    
    # Run test
    print_step "Running test (this may take a minute)..."
    test_script="$TEST_DIR/test_mode_${mode}.py"
    
    if [ ! -f "$test_script" ]; then
        print_fail "Test script not found: $test_script"
        RESULTS[$mode]="FAILED (script not found)"
        FAILED_TESTS+=("$mode")
        {
            echo "Status: FAILED (script not found)"
            echo ""
        } >> "$RESULT_FILE"
        continue
    fi
    
    # Run test with verbose output to see progress
    print_info "Test output:"
    test_output=$(python3 "$test_script" --verbose 2>&1)
    test_exit_code=$?
    
    echo "$test_output" | tee -a "$RESULT_FILE"
    
    if [ $test_exit_code -eq 0 ]; then
        print_success "Test passed"
        RESULTS[$mode]="PASSED"
        PASSED_TESTS+=("$mode")
        {
            echo "Status: PASSED"
            echo ""
        } >> "$RESULT_FILE"
    else
        print_fail "Test failed (exit code: $test_exit_code)"
        RESULTS[$mode]="FAILED"
        FAILED_TESTS+=("$mode")
        {
            echo "Status: FAILED"
            echo ""
        } >> "$RESULT_FILE"
    fi
    
    # Stop service for next test
    print_step "Stopping service..."
    ./mondrian.sh --stop 2>/dev/null || true
    sleep 3
done

# Print summary
print_header "TEST SUMMARY"

echo "Passed: ${#PASSED_TESTS[@]}"
for test in "${PASSED_TESTS[@]}"; do
    print_success "$test"
done

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    echo ""
    echo "Failed: ${#FAILED_TESTS[@]}"
    for test in "${FAILED_TESTS[@]}"; do
        print_fail "$test"
    done
fi

# Print to results file
{
    echo ""
    echo "========== SUMMARY =========="
    echo "Total tests: ${#TESTS[@]}"
    echo "Passed: ${#PASSED_TESTS[@]}"
    echo "Failed: ${#FAILED_TESTS[@]}"
    echo ""
    echo "Passed tests:"
    for test in "${PASSED_TESTS[@]}"; do
        echo "  ✓ $test"
    done
    echo ""
    echo "Failed tests:"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  ✗ $test"
    done
} >> "$RESULT_FILE"

print_step "Results saved to: $RESULT_FILE"
echo ""

# Determine exit code
if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    print_header "ALL TESTS PASSED ✓"
    echo -e "${GREEN}All modes are working!${NC}"
    echo ""
    exit 0
else
    print_header "SOME TESTS FAILED ✗"
    echo -e "${RED}${#FAILED_TESTS[@]} mode(s) failed.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Check logs/ai_advisor_service_*.log for crash details"
    echo "2. Review results: cat $RESULT_FILE"
    echo "3. Test individual modes manually if needed"
    echo ""
    exit 1
fi
