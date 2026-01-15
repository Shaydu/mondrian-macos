# Shell Test Script - Mode Comparison Guide

## Updated: test_ios_api_flow.sh

The iOS API flow shell script now supports mode switching! 🚀

---

## Quick Start

### Test with Base Mode
```bash
./test/test_ios_api_flow.sh --mode=base --auto-restart
```

### Test with RAG Mode
```bash
./test/test_ios_api_flow.sh --mode=rag --auto-restart
```

### Test with LoRA Mode
```bash
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --auto-restart
```

### Test with Combined Mode (LoRA + RAG)
```bash
./test/test_ios_api_flow.sh \
    --mode=lora+rag \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --auto-restart
```

---

## Command-Line Options

```bash
./test/test_ios_api_flow.sh [OPTIONS]

Options:
  --mode=<mode>          Service mode: base, rag, lora, lora+rag, ab-test
  --lora-path=<path>     Path to LoRA adapter (required for lora modes)
  --auto-restart         Automatically restart services if mode doesn't match
  --advisor=<name>       Advisor to use (default: ansel)
  --image=<path>         Test image path (default: test_image.png)
  --help, -h             Show help
```

---

## How It Works

### 1. Mode Check
The script checks the AI Advisor Service health endpoint:
```bash
curl http://127.0.0.1:5100/health
```

Parses the response to find:
- Current `model_mode` (base, fine_tuned, ab_test)
- Whether LoRA adapter is loaded (`fine_tuned` flag)

### 2. Mode Validation
Compares requested mode vs current mode:
- **base**: Expects `model_mode=base`
- **rag**: Any mode works (RAG is runtime behavior)
- **lora/lora+rag**: Expects `model_mode=fine_tuned` and `fine_tuned=True`
- **ab-test**: Expects `model_mode=ab_test`

### 3. Auto-Restart (if `--auto-restart` flag set)
If mode doesn't match, automatically runs:
```bash
./mondrian.sh --restart --mode=<desired-mode> [--lora-path=<path>]
```

### 4. Test Execution
Runs complete iOS app flow:
1. Fetch advisors list
2. Upload image
3. Stream SSE updates
4. Get analysis results
5. Index image (RAG)
6. Search similar images (RAG)

---

## Comparison Workflow

### Compare RAG vs LoRA

```bash
# Test 1: RAG mode
./test/test_ios_api_flow.sh --mode=rag --auto-restart
# Saves to: ../analysis_output/<timestamp>/

# Test 2: LoRA mode  
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --auto-restart
# Saves to: ../analysis_output/<timestamp>/

# Compare outputs
diff ../analysis_output/<timestamp1>/analysis_api.html \
     ../analysis_output/<timestamp2>/analysis_api.html
```

### Compare All Modes

```bash
# Run tests in sequence (services auto-restart for each)
./test/test_ios_api_flow.sh --mode=base --auto-restart
./test/test_ios_api_flow.sh --mode=rag --auto-restart
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --auto-restart

# Each test creates timestamped output directory
ls -lt ../analysis_output/
```

---

## Output Files

Each test creates a timestamped directory:

```
../analysis_output/<timestamp>/
├── analysis_api.html     # Analysis from API endpoint
├── analysis_sse.html     # Analysis from SSE stream (if received)
├── sse_event.json        # SSE event data
└── summary.txt           # Test summary with mode info
```

### Summary File Example

```
================================================================================
iOS API Flow Test Summary
================================================================================
Test Date: Wed Jan 14 15:30:45 PST 2026
Job ID: abc123-def456-ghi789
Advisor: ansel
Test Image: test_image.png
Mode: lora
LoRA Path: ./models/qwen3-vl-4b-lora-ansel

Test Results:
-------------
✅ Step 1: Fetch Advisors - SUCCESS
✅ Step 2: Upload Image - SUCCESS
✅ Step 3: SSE Stream - SUCCESS (received analysis_html)
✅ Step 4: Get Analysis - SUCCESS
✅ Step 5: RAG Index - SUCCESS
✅ Step 6: RAG Search - SUCCESS
...
```

---

## Examples

### Basic Test (No Mode Switching)
```bash
# Uses default mode (whatever is currently running)
./test/test_ios_api_flow.sh
```

### Test with Custom Image and Advisor
```bash
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --advisor=cartier-bresson \
    --image=source/my-photo.jpg \
    --auto-restart
```

### Manual Mode Check (No Auto-Restart)
```bash
# Check mode but don't auto-restart
./test/test_ios_api_flow.sh --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel

# Script will warn if mode doesn't match:
# ⚠️  Service mode mismatch: expected lora, got base
# Tip: Add --auto-restart to automatically restart services
# Or manually run: ./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
```

---

## Backward Compatibility

The script still supports the old positional argument style:

```bash
# Old style (still works)
./test/test_ios_api_flow.sh ansel test_image.png

# Equivalent to:
./test/test_ios_api_flow.sh --advisor=ansel --image=test_image.png
```

---

## Integration with Service Launcher

The script integrates with `mondrian.sh`:

```bash
# Manually start services in specific mode
./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel

# Then run test (no auto-restart needed)
./test/test_ios_api_flow.sh --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
```

Or let the test handle it:

```bash
# Test handles everything
./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --auto-restart
```

---

## Troubleshooting

### Error: "AI Advisor Service is not running"

```bash
# With auto-restart, script will start services
./test/test_ios_api_flow.sh --mode=base --auto-restart

# Without auto-restart, you need to start manually
./mondrian.sh --restart --mode=base
./test/test_ios_api_flow.sh --mode=base
```

### Error: "Service mode mismatch"

Services are running in wrong mode. Either:

**Option 1**: Let script restart them
```bash
./test/test_ios_api_flow.sh --mode=lora --lora-path=... --auto-restart
```

**Option 2**: Manually restart
```bash
./mondrian.sh --restart --mode=lora --lora-path=...
./test/test_ios_api_flow.sh --mode=lora --lora-path=...
```

### Python JSON Parsing Errors

The script uses Python for JSON parsing. Requires Python 3:
```bash
python3 --version  # Should be 3.6+
```

---

## Tips

### Quick Mode Comparison Script

Create a comparison script:

```bash
#!/bin/bash
# compare_modes.sh

echo "Testing all modes..."

./test/test_ios_api_flow.sh --mode=base --auto-restart
BASE_DIR=$(ls -td ../analysis_output/* | head -1)

./test/test_ios_api_flow.sh --mode=rag --auto-restart
RAG_DIR=$(ls -td ../analysis_output/* | head -1)

./test/test_ios_api_flow.sh \
    --mode=lora \
    --lora-path=./models/qwen3-vl-4b-lora-ansel \
    --auto-restart
LORA_DIR=$(ls -td ../analysis_output/* | head -1)

echo ""
echo "Output directories:"
echo "  Base: $BASE_DIR"
echo "  RAG:  $RAG_DIR"
echo "  LoRA: $LORA_DIR"
```

### Open All Results

```bash
# After running tests
for dir in ../analysis_output/*/; do
    echo "Opening: $dir"
    open "$dir/analysis_api.html" || open "$dir/analysis_sse.html"
done
```

---

**Created**: January 14, 2026
**Status**: Ready to Use
**Test Script**: `test/test_ios_api_flow.sh`
