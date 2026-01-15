# iOS E2E Test - Mode Comparison Guide

## Quick Start - Test Different Modes

The iOS end-to-end test now supports automatic service mode switching! You can easily test different modes without manually restarting services.

---

## New Usage (Recommended) 🚀

### Test Base Mode
```bash
python3 test/test_ios_e2e_three_mode_comparison.py --mode=base
```
- Automatically restarts services in base mode if needed
- Runs complete iOS workflow test
- Saves output to `analysis_output/ios_e2e_base_<timestamp>/`

### Test RAG Mode
```bash
python3 test/test_ios_e2e_three_mode_comparison.py --mode=rag
```
- Automatically configures services for RAG
- Tests with retrieval-augmented generation
- Saves output to `analysis_output/ios_e2e_rag_<timestamp>/`

### Test LoRA Mode
```bash
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel
```
- Automatically restarts services with LoRA adapter
- Tests fine-tuned model
- Saves output to `analysis_output/ios_e2e_lora_<timestamp>/`

### Test Combined Mode (LoRA + RAG)
```bash
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora+rag \
    --lora-path=./models/qwen3-vl-4b-lora-ansel
```
- Combines LoRA fine-tuning with RAG
- Best of both approaches
- Saves output to `analysis_output/ios_e2e_lora+rag_<timestamp>/`

---

## How It Works

### Automatic Service Management

1. **Mode Detection**: Test checks what mode services are currently running in
2. **Auto-Restart**: If mode doesn't match, automatically restarts services with correct mode
3. **Validation**: Verifies services started correctly before running test
4. **Test Execution**: Runs complete iOS workflow (upload → SSE stream → results)

### Service Health Check

The test queries the AI Advisor Service health endpoint to check:
- Is the service running?
- What mode is it in? (base, fine_tuned, ab_test)
- Is a LoRA adapter loaded?
- Does it match what we want to test?

If mode doesn't match, the test automatically runs:
```bash
./mondrian.sh --restart --mode=<desired-mode> [--lora-path=<path>]
```

---

## Comparison Workflow

### Compare RAG vs LoRA

```bash
# Test 1: RAG mode
python3 test/test_ios_e2e_three_mode_comparison.py --mode=rag
# → Saves to: analysis_output/ios_e2e_rag_20260114_123456/

# Test 2: LoRA mode
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel
# → Saves to: analysis_output/ios_e2e_lora_20260114_123500/

# Compare outputs
open analysis_output/ios_e2e_rag_20260114_123456/analysis_summary.html
open analysis_output/ios_e2e_lora_20260114_123500/analysis_summary.html
```

### Compare All Three Modes

```bash
# Test base
python3 test/test_ios_e2e_three_mode_comparison.py --mode=base

# Test RAG
python3 test/test_ios_e2e_three_mode_comparison.py --mode=rag

# Test LoRA
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel

# Each creates its own output directory for easy comparison
```

---

## Output Files

Each test creates a timestamped directory with:

```
analysis_output/ios_e2e_<mode>_<timestamp>/
├── advisor_bio.html           # Advisor bio page
├── analysis_summary.html      # Summary view (top 3 recommendations)
├── analysis_detailed.html     # Full detailed analysis
├── sse_stream.log            # Server-Sent Events stream log
├── sse_events.json           # Structured SSE events
├── status_polling.log        # Status polling log (fallback)
└── metadata.json             # Test metadata and file references
```

---

## Advanced Options

### Disable Auto-Restart

If you want to manually manage services:

```bash
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --no-auto-restart
```

The test will check mode but won't restart services automatically.

### A/B Testing Mode

```bash
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=ab-test \
    --lora-path=./models/qwen3-vl-4b-lora-ansel
```

Services will randomly route between base and LoRA models.

---

## Legacy Usage (Still Supported)

The old multi-mode test still works:

```bash
# Run all three modes in sequence (no auto-restart)
python3 test/test_ios_e2e_three_mode_comparison.py --all

# Run specific tests
python3 test/test_ios_e2e_three_mode_comparison.py --baseline
python3 test/test_ios_e2e_three_mode_comparison.py --rag
python3 test/test_ios_e2e_three_mode_comparison.py --lora

# Creates comparison HTML
python3 test/test_ios_e2e_three_mode_comparison.py --baseline --rag --lora
```

**Note**: Legacy mode doesn't automatically restart services, so make sure services are in the right mode first.

---

## Troubleshooting

### Error: "Port still in use"

Services couldn't restart. Manually kill and restart:

```bash
./mondrian.sh --stop
sleep 2
./mondrian.sh --restart --mode=<your-mode>
```

### Error: "--lora-path required"

LoRA modes need the adapter path:

```bash
python3 test/test_ios_e2e_three_mode_comparison.py \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel
```

### Services won't start

Check Python 3.12 is installed:

```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 --version
```

### Mode mismatch warning

If you see "Service mode mismatch" but test continues, it means:
- Services are running in different mode
- Auto-restart is disabled
- Test will run but may not use expected mode

Enable auto-restart (default) to fix this automatically.

---

## Example Session

```bash
# Terminal session showing complete workflow

$ python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel

================================================================================
iOS End-to-End Test: LORA Mode
================================================================================

Test Image: source/mike-shrub.jpg
Advisor: ansel
Mode: lora
LoRA Path: ./models/qwen3-vl-4b-lora-ansel
Auto-restart: True
Timestamp: 2026-01-14 15:30:45

[STEP 1] Checking Services
✓ Job Service (port 5005) - UP
✓ AI Advisor Service (port 5100) - UP
ℹ Current mode: base, Fine-tuned: False
⚠ Service mode mismatch: expected lora, got base
ℹ Auto-restarting services with correct mode...

================================================================================
Restarting Services in LORA Mode
================================================================================

ℹ Running: ./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
✓ Services restarted in LORA mode

ℹ Waiting for services to be ready...
✓ Services restarted successfully

✓ All required services are running

[STEP 2] Uploading Image (LORA)
ℹ Image: source/mike-shrub.jpg
ℹ Advisor: ansel
ℹ Mode: lora
✓ Upload successful - Job ID: abc123...

[STEP 3] Streaming SSE Updates
✓ [15:30:50] SSE Connected - Job: abc123
ℹ [15:30:51] Status: analyzing (10%) - Loading model
ℹ [15:30:55] Status: analyzing (50%) - Analyzing image
✓ [15:31:10] Analysis Complete!
✓ [15:31:10] Stream Done

[STEP 4] Fetching Analysis Results
✓ Retrieved HTML output (125,432 bytes)

[STEP 5] Saving Output Files
✓ Analysis Details HTML saved to: analysis_output/ios_e2e_lora_20260114_153045/analysis_detailed.html
✓ Analysis Summary HTML saved to: analysis_output/ios_e2e_lora_20260114_153045/analysis_summary.html
✓ Advisor Bio HTML saved to: analysis_output/ios_e2e_lora_20260114_153045/advisor_bio.html
✓ Metadata saved to: analysis_output/ios_e2e_lora_20260114_153045/metadata.json

================================================================================
TEST COMPLETE
================================================================================

✓ LORA mode test completed successfully

Output Directory:
  analysis_output/ios_e2e_lora_20260114_153045/

View outputs:
  open analysis_output/ios_e2e_lora_20260114_153045/analysis_summary.html
  open analysis_output/ios_e2e_lora_20260114_153045/analysis_detailed.html
  open analysis_output/ios_e2e_lora_20260114_153045/advisor_bio.html
```

---

## Key Benefits

✅ **Automatic Mode Switching** - No manual service restarts
✅ **Mode Validation** - Ensures services are in correct mode
✅ **Clean Separation** - Each test gets its own output directory
✅ **Easy Comparison** - Run multiple tests, compare outputs
✅ **Backward Compatible** - Legacy multi-mode tests still work
✅ **Safe** - Validates configuration before running test

---

**Created**: January 14, 2026
**Status**: Ready to Use
**Test File**: `test/test_ios_e2e_three_mode_comparison.py`
