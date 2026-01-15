# Complete Testing Guide for Embeddings & RAG+LoRA

This guide covers all testing approaches for the embedding support and RAG+LoRA implementation.

## Quick Start

### 1. Run All Tests

```bash
# Make sure services are running
./start_mondrian.sh

# In another terminal, run tests
cd test
./run_embedding_tests.sh
```

### 2. Run Specific Test Suite

```bash
# Embedding E2E tests
python3 test/test_embeddings_e2e.py

# RAG+LoRA E2E tests  
python3 test/test_rag_lora_e2e.py

# Unit tests (no service required)
python3 test/test_embeddings_unit.py
```

## Test Files Overview

| File | Type | Purpose | Service Required |
|------|------|---------|-----------------|
| `test_embeddings_e2e.py` | E2E | Complete embedding workflow | ✅ Yes |
| `test_embeddings_unit.py` | Unit | Isolated function testing | ❌ No* |
| `test_rag_lora_e2e.py` | E2E | RAG+LoRA specific tests | ✅ Yes |
| `run_embedding_tests.sh` | Runner | Master test orchestrator | ✅ (optional) |
| `TEST_SUITE_README.md` | Doc | Detailed test documentation | - |

*Unit tests don't require running services but may skip if CLIP is not installed

## Testing Scenarios

### Scenario 1: Local Development Testing

**Goal:** Quick validation during development

```bash
# Terminal 1: Start services
./start_mondrian.sh

# Terminal 2: Run unit tests (fast, no service needed)
python3 test/test_embeddings_unit.py -v

# Terminal 3: Run specific E2E test
python3 test/test_embeddings_e2e.py --mode rag
```

**Expected Duration:** 5-10 minutes

### Scenario 2: Full Integration Testing

**Goal:** Complete validation of all features

```bash
# Ensure CLIP is installed
pip install torch clip

# Populate embeddings
python tools/rag/index_with_metadata.py \
  --advisor ansel \
  --metadata-file advisor_image_manifest.yaml

# Start services
./start_mondrian.sh

# Run full test suite
test/run_embedding_tests.sh
```

**Expected Duration:** 20-30 minutes

### Scenario 3: Embedding-Focused Testing

**Goal:** Verify embedding functionality specifically

```bash
# Start services
./start_mondrian.sh

# Run embedding tests with embeddings enabled
python3 test/test_embeddings_e2e.py --mode all --verbose

# Run RAG+LoRA with embeddings
python3 test/test_rag_lora_e2e.py --with-embeddings --timing
```

**Expected Duration:** 15-20 minutes

### Scenario 4: Performance Testing

**Goal:** Measure and validate performance

```bash
# Start services
./start_mondrian.sh

# Run E2E tests with timing
python3 test/test_embeddings_e2e.py --verbose

# Run RAG+LoRA with detailed timing
python3 test/test_rag_lora_e2e.py --timing --verbose
```

**Expected Output Includes:**
- Duration of each analysis
- Pass 1 / Pass 2 / Query durations
- Overhead from embeddings
- Timing comparisons

### Scenario 5: CI/CD Pipeline Testing

**Goal:** Automated testing for deployment

```bash
# Run tests without interactive components
python3 test/test_embeddings_unit.py

# Only if services are available
if [ -f /.dockerenv ]; then
    python3 test/test_embeddings_e2e.py
    python3 test/test_rag_lora_e2e.py
fi
```

## Understanding Test Output

### Successful Test Run

```
==========================================
Embedding Support E2E Tests
==========================================

Prerequisites
==========================================
[TEST] Service Health Check... ✓ PASS Service running at http://localhost:5200
[TEST] Test Image Availability... ✓ PASS Found at .../photo-*.jpg (XXX bytes)

Test 1: RAG with Embeddings
================================================================================
[TEST] Analyze with rag mode (embeddings=true)... ✓ PASS Duration: 8.45s

Response Validation
────────────────────────────────────────

[TEST] Response Structure Validation... ✓ PASS All required fields present
[TEST] Mode Verification... ✓ PASS Mode correctly set to 'rag'
[TEST] Dimensional Analysis Validation... ✓ PASS All 8 dimensions present
[TEST] Overall Grade Validation... ✓ PASS Grade: A

...more tests...

Test Summary
================================================================================
✓ Passed:  12
✗ Failed:  0
⊘ Skipped: 1

All tests passed! (12/13)
```

### Test with Skips

```
⊘ Skipped: 3

Skipped Tests:
  ⊘ Embedding metadata (similar_images not required)
  ⊘ RAG+LoRA mode (adapter not available)
  ⊘ Performance comparison (second analysis skipped)
```

### Failed Test

```
[TEST] Analyze with rag mode (embeddings=true)... ✗ FAIL HTTP 500: 
  Internal server error...

Some tests failed (1/7)
```

**What to do:**
1. Check service logs: `tail -f logs/*.log`
2. Run test with `--verbose` for more details
3. Verify prerequisites are met

## Debugging Failed Tests

### 1. Check Service Logs

```bash
# Watch all service logs
tail -f logs/*.log

# Or specific service
tail -f logs/ai_advisor_service_*.log
```

### 2. Verbose Test Execution

```bash
# Embedding E2E with verbose
python3 test/test_embeddings_e2e.py --verbose

# RAG+LoRA with verbose
python3 test/test_rag_lora_e2e.py --verbose
```

### 3. Direct API Testing

```bash
# Test RAG mode with embeddings
curl -X POST http://localhost:5200/analyze \
  -F "advisor=ansel" \
  -F "image=@source/photo-*.jpg" \
  -F "mode=rag" \
  -F "enable_embeddings=true" \
  -F "response_format=json" | jq .

# Check error in detail
curl -X POST http://localhost:5200/analyze \
  -F "advisor=ansel" \
  -F "image=@source/photo-*.jpg" \
  -F "mode=rag_lora" | jq '.error // .'
```

### 4. Unit Test Isolation

```bash
# Run single unit test
python3 test/test_embeddings_unit.py TestEmbeddingComputation -v

# Run specific test method
python3 test/test_embeddings_unit.py TestEmbeddingComputation.test_embedding_computation -v
```

## Common Issues & Solutions

### Issue: "Service not available"

**Symptom:**
```
✗ FAIL Cannot connect to http://localhost:5200
```

**Solution:**
```bash
# Start services
./start_mondrian.sh

# Or start individual services
python3 mondrian/ai_advisor_service.py --port 5200
```

### Issue: "RAG+LoRA mode not available"

**Symptom:**
```
⊘ SKIP RAG+LoRA mode not available (adapter or profiles missing)
```

**Solution:**
```bash
# Check adapter exists
ls adapters/ansel/

# Check database has profiles
sqlite3 mondrian/mondrian.db \
  "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel';"

# Check adapter has weights
ls adapters/ansel/adapters.safetensors
```

### Issue: "CLIP not installed"

**Symptom:**
```
⊘ SKIP CLIP not installed - embeddings will be disabled
```

**Solution:**
```bash
pip install torch clip
```

### Issue: "Test image not found"

**Symptom:**
```
⊘ SKIP Test image not found at source/photo-*.jpg
```

**Solution:**
```bash
# Use available test image
ls source/*.jpg
# Update TEST_IMAGE_PATH in test file
```

### Issue: "Timeout during test"

**Symptom:**
```
✗ FAIL Request timeout (service took too long)
```

**Solution:**
```bash
# Check system resources
top  # Is CPU/memory exhausted?
ps aux | grep python3  # How many processes running?

# Restart service
pkill -f ai_advisor_service
./start_mondrian.sh
```

## Test Customization

### Running Specific Modes

```bash
# RAG only
python3 test/test_embeddings_e2e.py --mode rag

# RAG+LoRA only
python3 test/test_embeddings_e2e.py --mode rag_lora
```

### Testing Without Embeddings

```bash
# Compare behavior with/without embeddings
python3 test/test_embeddings_e2e.py --no-embeddings
```

### Performance Measurement

```bash
# See timing information
python3 test/test_rag_lora_e2e.py --timing

# Compare modes
python3 test/test_embeddings_e2e.py --verbose
```

## Metrics & Benchmarks

### Timing Targets

```
RAG Mode
├── Pass 1: 3-5s
├── Query: 0.5-2s
├── Pass 2: 3-5s
└── Total: 6-12s

RAG+LoRA Mode
├── Pass 1: 2-4s
├── Query: 0.5-2s
├── Pass 2: 2-4s
└── Total: 5-10s

Embedding Overhead: <1s (typically 0.1-0.5s)
```

### Dimensional Analysis

```
Expected Fields:
├── composition
├── lighting
├── focus_sharpness
├── color_harmony
├── subject_isolation
├── depth_perspective
├── visual_balance
└── emotional_impact

Score Range: 0-10 (or 0-100, depending on implementation)
Comments: Required for each dimension
Grade: A+, A, A-, B+, B, B-, C+, C, C-, D, F, or N/A
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Embedding Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install torch clip
      
      - name: Run unit tests
        run: python3 test/test_embeddings_unit.py
```

### Local Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running embedding unit tests..."
python3 test/test_embeddings_unit.py

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Test Report Generation

### Save Test Results

```bash
# Run tests and save output
python3 test/test_embeddings_e2e.py 2>&1 | tee test_results_$(date +%Y%m%d_%H%M%S).log

# Unit tests with report
python3 test/test_embeddings_unit.py -v 2>&1 | tee unit_test_results.log
```

### Create Test Summary

```bash
#!/bin/bash
# Generate test summary

DATE=$(date +%Y-%m-%d_%H:%M:%S)
REPORT_DIR="test_reports"
mkdir -p "$REPORT_DIR"

echo "Test Suite Summary - $DATE" > "$REPORT_DIR/summary_$DATE.txt"
echo "" >> "$REPORT_DIR/summary_$DATE.txt"

echo "=== Unit Tests ===" >> "$REPORT_DIR/summary_$DATE.txt"
python3 test/test_embeddings_unit.py -v 2>&1 | tail -20 >> "$REPORT_DIR/summary_$DATE.txt"

echo "" >> "$REPORT_DIR/summary_$DATE.txt"
echo "=== E2E Tests ===" >> "$REPORT_DIR/summary_$DATE.txt"
python3 test/test_embeddings_e2e.py 2>&1 | tail -20 >> "$REPORT_DIR/summary_$DATE.txt"

echo "Summary saved to: $REPORT_DIR/summary_$DATE.txt"
cat "$REPORT_DIR/summary_$DATE.txt"
```

## Next Steps

1. **Run unit tests first** - No service required, fastest feedback
2. **Start services** - Required for E2E tests
3. **Run E2E tests** - Complete integration validation
4. **Check performance** - Compare timing with benchmarks
5. **Review logs** - Verify embedding computation and retrieval

## Additional Resources

- [Implementation Summary](../EMBEDDING_IMPLEMENTATION_COMPLETE.md)
- [Test Suite README](TEST_SUITE_README.md)
- [RAG+LoRA Strategy](../mondrian/strategies/rag_lora.py)
- [API Documentation](../docs/)
- [Service Start Guide](../START_SERVICES_GUIDE.md)

## Support

For issues or questions:

1. Check this guide's troubleshooting section
2. Review service logs
3. Run tests with `--verbose` flag
4. Check issue tracker
5. Contact team
