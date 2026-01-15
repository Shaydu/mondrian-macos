#!/bin/bash
# Master Test Runner for Embedding Support & RAG+LoRA
# Runs all test suites in order with summary

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$PROJECT_ROOT/test"

# Results
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
TEST_RESULTS=()

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_section() {
    echo -e "\n${YELLOW}>>> $1${NC}\n"
}

run_test() {
    local test_name="$1"
    local test_file="$2"
    local args="${3:-}"
    
    print_section "Running: $test_name"
    
    if [ ! -f "$test_file" ]; then
        echo -e "${RED}✗ Test file not found: $test_file${NC}"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        TEST_RESULTS+=("FAILED: $test_name (file not found)")
        return 1
    fi
    
    # Run the test
    if python3 "$test_file" $args; then
        echo -e "\n${GREEN}✓ $test_name passed${NC}"
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
        TEST_RESULTS+=("PASSED: $test_name")
        return 0
    else
        echo -e "\n${RED}✗ $test_name failed${NC}"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        TEST_RESULTS+=("FAILED: $test_name")
        return 1
    fi
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if services are running
    echo -e "${YELLOW}Checking services...${NC}"
    
    if curl -s http://localhost:5200/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ AI Advisor Service is running${NC}"
    else
        echo -e "${RED}✗ AI Advisor Service not running${NC}"
        echo -e "  Start with: ./start_mondrian.sh"
        return 1
    fi
    
    # Check Python
    if command -v python3 &> /dev/null; then
        echo -e "${GREEN}✓ Python3 is available${NC}"
    else
        echo -e "${RED}✗ Python3 not found${NC}"
        return 1
    fi
    
    # Check test image
    if [ -f "$PROJECT_ROOT/source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg" ]; then
        echo -e "${GREEN}✓ Test image found${NC}"
    else
        echo -e "${YELLOW}⚠ Test image not found (some tests will skip)${NC}"
    fi
    
    return 0
}

print_summary() {
    print_header "Test Summary"
    
    echo -e "Results from all test suites:\n"
    
    local passed=0
    local failed=0
    local skipped=0
    
    for result in "${TEST_RESULTS[@]}"; do
        if [[ $result == PASSED* ]]; then
            echo -e "${GREEN}✓${NC} ${result#PASSED: }"
            passed=$((passed + 1))
        elif [[ $result == FAILED* ]]; then
            echo -e "${RED}✗${NC} ${result#FAILED: }"
            failed=$((failed + 1))
        fi
    done
    
    echo -e "\n${BLUE}Summary:${NC}"
    echo -e "  ${GREEN}Passed:${NC}  $passed"
    echo -e "  ${RED}Failed:${NC}  $failed"
    
    if [ $failed -eq 0 ] && [ $passed -gt 0 ]; then
        echo -e "\n${GREEN}✓ All tests passed!${NC}\n"
        return 0
    else
        echo -e "\n${RED}✗ Some tests failed${NC}\n"
        return 1
    fi
}

main() {
    local run_unit_only=false
    local run_e2e_only=false
    local verbose=""
    
    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --unit-only)
                run_unit_only=true
                ;;
            --e2e-only)
                run_e2e_only=true
                ;;
            --verbose)
                verbose="--verbose"
                ;;
            --help)
                echo "Usage: ./run_tests.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --unit-only     Run only unit tests (no service required)"
                echo "  --e2e-only      Run only E2E tests (requires service)"
                echo "  --verbose       Verbose output"
                echo "  --help          Show this help"
                exit 0
                ;;
        esac
    done
    
    print_header "Test Suite: Embeddings & RAG+LoRA"
    
    echo "Test Directory: $TEST_DIR"
    echo "Start Time: $(date)"
    echo ""
    
    # Check prerequisites (skip if unit-only)
    if [ "$run_unit_only" = false ]; then
        if ! check_prerequisites; then
            echo -e "${YELLOW}Skipping E2E tests (prerequisites not met)${NC}"
            run_e2e_only=false
        fi
    fi
    
    echo ""
    
    # Unit Tests (no service required)
    if [ "$run_e2e_only" = false ]; then
        print_section "PHASE 1: Unit Tests"
        run_test \
            "Embedding Unit Tests" \
            "$TEST_DIR/test_embeddings_unit.py" \
            "-v" || true
    fi
    
    # E2E Tests (requires service)
    if [ "$run_unit_only" = false ]; then
        print_section "PHASE 2: Embedding E2E Tests"
        run_test \
            "Embedding Support E2E" \
            "$TEST_DIR/test_embeddings_e2e.py" \
            "$verbose" || true
        
        print_section "PHASE 3: RAG+LoRA E2E Tests"
        run_test \
            "RAG+LoRA Strategy E2E" \
            "$TEST_DIR/test_rag_lora_e2e.py" \
            "--timing $verbose" || true
    fi
    
    # Print final summary
    print_summary
    
    exit_code=$?
    echo "End Time: $(date)"
    
    return $exit_code
}

# Run main
main "$@"
