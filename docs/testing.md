# Testing Guide - Mode Comparison & iOS E2E Tests

## Overview

This guide explains how to test Mondrian with different service modes (base, RAG, LoRA, etc.) and compares their outputs. Two testing approaches are provided: a comprehensive Python test and a quick shell script test.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding Modes](#understanding-modes)
3. [Python E2E Test](#python-e2e-test)
4. [Shell Script Test](#shell-script-test)
5. [Service Management](#service-management)
6. [Output Analysis](#output-analysis)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Test Base Mode
```bash
# Python
python3 test/test_ios_e2e_three_mode_comparison.py --mode=base

# Shell
./test/test_ios_api_flow.sh --mode=base --auto-restart
```

### Test LoRA Mode
```bash
# Python
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel

# Shell
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --auto-restart
```

### Test RAG Mode
```bash
# Python
python3 test/test_ios_e2e_three_mode_comparison.py --mode=rag

# Shell
./test/test_ios_api_flow.sh --mode=rag --auto-restart
```

---

## Understanding Modes

Mondrian supports multiple service modes for different analysis strategies:

### 1. **Base Mode**
- **Description**: Base model only, no enhancements
- **What it does**: Uses Qwen3-VL-4B model directly
- **Use case**: Baseline performance testing, general analysis
- **Speed**: Fastest ⚡
- **Command**:
  ```bash
  ./mondrian.sh --restart --mode=base
  ```

### 2. **RAG Mode** (Retrieval-Augmented Generation)
- **Description**: Base model with retrieval-augmented generation
- **What it does**: Retrieves similar images from portfolio for context
- **Use case**: Context-aware analysis, reference-based recommendations
- **Speed**: Moderate (includes similarity search)
- **Requirements**: RAG services (caption, embedding, rag services)
- **Command**:
  ```bash
  ./mondrian.sh --restart --mode=rag
  ```

### 3. **LoRA Mode** (Low-Rank Adaptation)
- **Description**: Base model fine-tuned with LoRA adapter
- **What it does**: Uses trained domain-specific adapter weights
- **Use case**: Domain-specialized analysis, improved consistency
- **Speed**: Comparable to base (minimal overhead)
- **Requirements**: Trained LoRA adapter
- **Command**:
  ```bash
  ./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
  ```

### 4. **LoRA+RAG Mode** (Combined)
- **Description**: Fine-tuned model with retrieval augmentation
- **What it does**: Uses LoRA adapter + retrieves similar images
- **Use case**: Best of both approaches
- **Speed**: Moderate (includes search + LoRA)
- **Requirements**: Trained adapter + RAG services
- **Command**:
  ```bash
  ./mondrian.sh --restart --mode=lora+rag --lora-path=./models/qwen3-vl-4b-lora-ansel
  ```

### 5. **A/B Test Mode**
- **Description**: Randomly routes between base and LoRA models
- **What it does**: Splits traffic for comparison
- **Use case**: Gradual rollout, A/B testing
- **Split ratio**: Configurable (default 50/50)
- **Command**:
  ```bash
  ./mondrian.sh --restart --mode=ab-test --lora-path=./models/qwen3-vl-4b-lora-ansel --ab-split=0.5
  ```

---

## Python E2E Test

### Test File Location
```
test/test_ios_e2e_three_mode_comparison.py
```

### Features
- ✅ Automatic service restart
- ✅ Mode validation
- ✅ Complete iOS workflow simulation
- ✅ SSE stream monitoring
- ✅ HTML output capture
- ✅ Comprehensive logging

### Basic Usage

#### Single Mode Test
```bash
# Test LoRA mode (auto-restarts services)
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel
```

#### All Three Modes (Sequential)
```bash
# Legacy multi-mode test (no auto-restart)
python3 test/test_ios_e2e_three_mode_comparison.py --all
```

#### Specific Modes
```bash
# Base only
python3 test/test_ios_e2e_three_mode_comparison.py --mode=base

# RAG only
python3 test/test_ios_e2e_three_mode_comparison.py --mode=rag

# LoRA + RAG combined
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora+rag \
    --lora-path=./models/qwen3-vl-4b-lora-ansel
```

### Command-Line Options
```bash
python3 test/test_ios_e2e_three_mode_comparison.py --help

Options:
  --mode=<mode>           Mode: base, rag, lora, lora+rag, ab-test
  --lora-path=<path>      Path to LoRA adapter (required for lora modes)
  --auto-restart          Automatically restart services (default: True)
  --no-auto-restart       Don't auto-restart services
  --baseline              Legacy: run baseline test
  --rag                   Legacy: run RAG test
  --lora                  Legacy: run LoRA test
  --all                   Legacy: run all three modes
```

### Output Structure
```
analysis_output/ios_e2e_<mode>_<timestamp>/
├── advisor_bio.html          # Advisor information
├── analysis_summary.html     # Summary view (top recommendations)
├── analysis_detailed.html    # Full detailed analysis
├── sse_stream.log           # Server-Sent Events log
├── sse_events.json          # Structured SSE events
├── status_polling.log       # Status polling log (fallback)
└── metadata.json            # Test metadata
```

### Example Session
```bash
$ python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel

================================================================================
iOS End-to-End Test: LORA Mode
================================================================================

Test Image: source/mike-shrub.jpg
Advisor: ansel
Mode: lora
LoRA Path: ./models/qwen3-vl-4b-lora-ansel

[STEP 1] Checking Services
✓ Job Service (port 5005) - UP
ℹ Current mode: base, Fine-tuned: False
⚠ Service mode mismatch: expected lora, got base
ℹ Auto-restarting services with correct mode...

================================================================================
Restarting Services in LORA Mode
================================================================================

[MODE] LoRA fine-tuned model
✓ Services restarted in LORA mode

[STEP 2] Uploading Image (LORA)
✓ Upload successful - Job ID: abc123

[STEP 3] Streaming SSE Updates
✓ SSE Connected
ℹ Status: analyzing (50%)
✓ Analysis Complete!

[STEP 4] Fetching Analysis Results
✓ Retrieved HTML output (125,432 bytes)

[STEP 5] Saving Output Files
✓ Analysis Details HTML saved
✓ Metadata saved

================================================================================
TEST COMPLETE
================================================================================

Output Directory: analysis_output/ios_e2e_lora_20260114_153045/
```

---

## Shell Script Test

### Test File Location
```
test/test_ios_api_flow.sh
```

### Features
- ✅ Fast command-line testing
- ✅ Automatic service restart
- ✅ Complete iOS API flow
- ✅ RAG integration testing
- ✅ Simple output format

### Basic Usage

#### Single Mode Test
```bash
# Test LoRA mode (auto-restart)
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --auto-restart
```

#### Different Advisors
```bash
# Test with different advisor
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --advisor=cartier-bresson \
    --auto-restart
```

#### Custom Test Image
```bash
# Test with custom image
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --image=source/my-photo.jpg \
    --auto-restart
```

### Command-Line Options
```bash
./test/test_ios_api_flow.sh --help

Options:
  --mode=<mode>          Mode: base, rag, lora, lora+rag, ab-test
  --lora-path=<path>     Path to LoRA adapter
  --auto-restart         Auto-restart services if mode mismatch
  --advisor=<name>       Advisor name (default: ansel)
  --image=<path>         Test image path
  --help, -h             Show help
```

### Output Structure
```
../analysis_output/<timestamp>/
├── analysis_api.html     # Analysis from API endpoint
├── analysis_sse.html     # Analysis from SSE stream (if received)
├── sse_event.json        # SSE event data
└── summary.txt           # Test summary
```

### Example Session
```bash
$ ./test/test_ios_api_flow.sh --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel --auto-restart

🎨 Mondrian iOS API Flow Test (with Mode Support)
==================================================
Job Service URL: http://127.0.0.1:5005
AI Advisor URL: http://127.0.0.1:5100
RAG Service URL: http://127.0.0.1:5400
Advisor: ansel
Test Image: test_image.png
Mode: lora
LoRA Path: ./models/qwen3-vl-4b-lora-ansel

🔍 Checking service mode...
Current mode: base, Fine-tuned: False
⚠️  Service mode mismatch: expected lora, got base
🔄 Auto-restarting services in lora mode...

================================
Restarting Services in LORA Mode
================================

✓ Services restarted successfully
Waiting for services to be ready...

✅ All required services are running

📤 Step 2: Uploading image with advisor selection...
✅ Upload successful!
Job ID: abc123

🌊 Step 3: Listening to SSE stream...
✅ SSE: Connected
📊 SSE: Status Update - Status: analyzing
✅ SSE: Analysis complete event received
✅ SSE: Stream complete

✅ Analysis received: 125,432 characters

📄 Analysis Preview (first 1000 chars):
========================================
...
========================================

✅ 🏁 Test Complete!

Summary:
  Job ID: abc123
  Mode: lora
  LoRA Path: ./models/qwen3-vl-4b-lora-ansel
  Final Status: done
  Analysis Length: 125,432 chars
  Output Directory: ../analysis_output/20260114_153045/
```

---

## Service Management

### Using mondrian.sh

The service launcher (`mondrian.sh`) controls which mode services run in:

#### Start Services in Specific Mode
```bash
# Base mode (default)
./mondrian.sh --restart --mode=base

# RAG mode
./mondrian.sh --restart --mode=rag

# LoRA mode
./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel

# LoRA+RAG combined
./mondrian.sh --restart --mode=lora+rag --lora-path=./models/qwen3-vl-4b-lora-ansel

# A/B test (70% LoRA, 30% base)
./mondrian.sh --restart --mode=ab-test --lora-path=./models/qwen3-vl-4b-lora-ansel --ab-split=0.7
```

#### Stop All Services
```bash
./mondrian.sh --stop
```

#### View Help
```bash
./mondrian.sh --help
```

### Service Configuration

The AI Advisor Service accepts mode configuration via command-line arguments:

```bash
python3 mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode fine_tuned
```

Available modes:
- `--model_mode base` - Base model only
- `--model_mode fine_tuned` - LoRA adapter only
- `--model_mode ab_test` - A/B testing (requires `--ab_test_split`)

---

## Output Analysis

### Comparing Modes

#### Quick Comparison Workflow
```bash
# 1. Test base mode
python3 test/test_ios_e2e_three_mode_comparison.py --mode=base
BASE_DIR=$(ls -td analysis_output/* | head -1)

# 2. Test LoRA mode
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel
LORA_DIR=$(ls -td analysis_output/* | head -1)

# 3. Compare outputs
diff $BASE_DIR/analysis_summary.html $LORA_DIR/analysis_summary.html

# 4. Open in browser
open $BASE_DIR/analysis_summary.html
open $LORA_DIR/analysis_summary.html
```

#### What to Look For

**Output Quality**:
- Clarity and coherence of analysis
- Consistency with advisor style
- Format compliance (JSON/HTML validity)

**Performance**:
- Analysis duration (check logs)
- SSE stream responsiveness
- API response times

**Differences**:
- Recommendations quality
- Grading consistency
- Reference images accuracy (RAG mode)
- Fine-tuning improvements (LoRA mode)

#### Analysis Files

Each test generates multiple HTML files:

1. **advisor_bio.html** - Advisor information page
2. **analysis_summary.html** - Summary view (top 3 recommendations)
3. **analysis_detailed.html** - Complete detailed analysis
4. **sse_stream.log** - Raw SSE events
5. **metadata.json** - Test metadata and configuration

---

## Troubleshooting

### Services Won't Start

**Symptom**: "Port still in use" error

**Solution**:
```bash
# Manually kill processes
lsof -ti :5100 | xargs kill -9
lsof -ti :5005 | xargs kill -9

# Then restart
./mondrian.sh --restart --mode=<mode>
```

### LoRA Mode Fails

**Symptom**: "Service mode mismatch" or LoRA loading errors

**Solution**:
1. Verify LoRA adapter files exist:
   ```bash
   ls -la ./models/qwen3-vl-4b-lora-ansel/
   # Should contain: adapter_config.json, adapter_model.safetensors
   ```

2. Check logs:
   ```bash
   # Look for LoRA loading errors
   grep -i "lora" /tmp/mondrian*.log
   ```

3. Fall back to base model:
   ```bash
   ./mondrian.sh --restart --mode=base
   python3 test/test_ios_e2e_three_mode_comparison.py --mode=base
   ```

### Auto-Restart Not Working

**Solution**:
1. Ensure `mondrian.sh` is executable:
   ```bash
   chmod +x ./mondrian.sh
   ```

2. Try without auto-restart:
   ```bash
   # Manually start services
   ./mondrian.sh --restart --mode=<mode>
   
   # Run test without auto-restart
   python3 test/test_ios_e2e_three_mode_comparison.py \
       --mode=<mode> \
       --no-auto-restart
   ```

### SSE Stream Timeout

**Symptom**: "Timeout waiting for analysis" or SSE stream hangs

**Solution**:
1. Check AI Advisor Service is running:
   ```bash
   curl -I http://127.0.0.1:5100/health
   ```

2. Increase timeout in test (edit script):
   ```python
   max_retries = 1800  # 30 minutes (increase if needed)
   ```

3. Check logs for errors:
   ```bash
   tail -f /var/log/mondrian*.log
   ```

### Mode Mismatch Warning

**Message**: "Service mode mismatch: expected lora, got base"

**Reasons**:
- Services were started in different mode
- Auto-restart is disabled
- Service restart failed

**Solutions**:
1. Enable auto-restart (add `--auto-restart` flag)
2. Manually restart services:
   ```bash
   ./mondrian.sh --restart --mode=<desired-mode>
   ```
3. Verify mode changed:
   ```bash
   curl http://127.0.0.1:5100/health | python3 -m json.tool
   ```

---

## Tips & Best Practices

### 1. Test Sequentially for Clean Results
```bash
# Test each mode separately with delays
./test/test_ios_api_flow.sh --mode=base --auto-restart
sleep 10

./test/test_ios_api_flow.sh --mode=rag --auto-restart
sleep 10

./test/test_ios_api_flow.sh --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel --auto-restart
```

### 2. Use Same Test Image
For consistent comparisons, use the same test image across all modes:
```bash
./test/test_ios_api_flow.sh --mode=base --image=source/test.jpg
./test/test_ios_api_flow.sh --mode=rag --image=source/test.jpg
./test/test_ios_api_flow.sh --mode=lora --image=source/test.jpg
```

### 3. Compare with Specific Advisors
Test with different advisors to see mode differences:
```bash
./test/test_ios_api_flow.sh --mode=base --advisor=ansel
./test/test_ios_api_flow.sh --mode=lora --advisor=ansel --lora-path=./models/qwen3-vl-4b-lora-ansel
```

### 4. Monitor Resource Usage
During tests, monitor system resources:
```bash
# In separate terminal
watch -n 1 'ps aux | grep python | head -5'

# Or use Activity Monitor
open -a "Activity Monitor"
```

### 5. Keep Test Outputs Organized
```bash
# Archive results by mode
mkdir -p test_results
mv analysis_output/ios_e2e_base_*/ test_results/base/
mv analysis_output/ios_e2e_rag_*/ test_results/rag/
mv analysis_output/ios_e2e_lora_*/ test_results/lora/
```

---

## Related Documentation

- [MONDRIAN_MODE_COMPARISON_GUIDE.md](../MONDRIAN_MODE_COMPARISON_GUIDE.md) - Service modes reference
- [IOS_TEST_MODE_COMPARISON_GUIDE.md](../IOS_TEST_MODE_COMPARISON_GUIDE.md) - Python test guide
- [SHELL_TEST_MODE_GUIDE.md](../SHELL_TEST_MODE_GUIDE.md) - Shell test guide
- [LORA_STRATEGY_IMPLEMENTED.md](../LORA_STRATEGY_IMPLEMENTED.md) - LoRA implementation details
- [docs/API.md](./API.md) - API reference
- [docs/architecture/data-flow.md](./architecture/data-flow.md) - System architecture

---

**Document**: docs/testing.md
**Created**: January 14, 2026
**Status**: Complete
**Last Updated**: January 14, 2026
