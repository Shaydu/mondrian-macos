# iOS End-to-End Test Guide

## Overview

This guide covers all available end-to-end tests for the Mondrian iOS API. These tests simulate the complete iOS workflow across different analysis modes:

1. **Baseline** - Single-pass prompt-only analysis (always available)
2. **RAG** - Two-pass with retrieval-augmented generation
3. **LoRA** - Single-pass with fine-tuned adapter weights
4. **RAG+LoRA** - Two-pass hybrid combining LoRA voice with RAG context

## What's Covered in This Guide

This guide documents **three** complementary iOS E2E test suites:

1. **[test_lora_e2e.py](../test_lora_e2e.py)** - Standalone LoRA test with mode verification
2. **[test/test_ios_e2e_three_mode_comparison.py](test_ios_e2e_three_mode_comparison.py)** - Auto-restart capable test
3. **[test/rag-embeddings/test_ios_e2e_four_modes.py](rag-embeddings/test_ios_e2e_four_modes.py)** - Comprehensive 4-mode comparison

**Note:** The 4-mode test and embedding tests have been moved to `test/rag-embeddings/`. See [rag-embeddings-test-guide.md](rag-embeddings/rag-embeddings-test-guide.md) for details.

## Choosing the Right Test

| Test File | Best For | Modes Supported | Auto-Restart | Mode Verification |
|-----------|----------|-----------------|--------------|-------------------|
| [rag-embeddings/test_ios_e2e_four_modes.py](rag-embeddings/test_ios_e2e_four_modes.py) | Complete multi-mode comparison | base, rag, lora, rag_lora | No | **Yes** |
| [test_lora_e2e.py](../test_lora_e2e.py) | Quick LoRA testing with verification | baseline, rag, lora | No | **Yes** |
| [test_ios_e2e_three_mode_comparison.py](test_ios_e2e_three_mode_comparison.py) | Testing with service restarts | base, rag, lora, lora+rag | **Yes** | **Yes** |

**Quick Decision:**
- **Need to verify LoRA mode actually works?** → Use `test_lora_e2e.py`
- **Want automatic service restarts?** → Use `test_ios_e2e_three_mode_comparison.py`
- **Want comprehensive 4-mode side-by-side comparison + text diffs?** → Use `test_ios_e2e_four_modes.py`

## Quick Start

All tests require the virtual environment to be activated:

```bash
cd /Users/shaydu/dev/mondrian-macos
source mondrian/venv/bin/activate
```

---

## Test 1: Standalone LoRA E2E Test (test_lora_e2e.py)

**Location:** `test_lora_e2e.py` (project root)

**Best For:** Quick LoRA testing with mode verification to ensure the adapter is actually being used.

### Basic Usage

```bash
# Test LoRA mode with default image
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel

# Test with mode selection
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag
```

### Comparison Mode

Run LoRA vs Baseline comparison side-by-side:

```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare
```

This will:
1. Run LoRA mode test
2. Run baseline mode test
3. Generate side-by-side comparison HTML in `analysis_output/`

### Command-Line Options

| Option | Description | Default | Required |
|--------|-------------|---------|----------|
| `--image` | Path to test image | - | **Yes** |
| `--advisor` | Advisor ID | `ansel` | No |
| `--mode` | Analysis mode (`baseline`, `rag`, `lora`) | `lora` | No |
| `--compare` | Run LoRA vs baseline comparison | `False` | No |
| `--job-service-url` | Custom Job Service URL | `http://127.0.0.1:5005` | No |
| `--ai-advisor-url` | Custom AI Advisor URL | `http://127.0.0.1:5100` | No |

### Mode Verification

This test **verifies** that the requested mode was actually used:

```
[Step 6] Verifying LORA mode was used...
ℹ AI Advisor Service - Model Mode: fine_tuned, Fine-tuned: True
✓ AI Advisor Service is running in fine-tuned mode
ℹ Mode used: lora
✓ LORA mode confirmed for ansel
```

**What it checks:**
- AI Advisor Service is running in correct mode (fine-tuned vs base)
- Job metadata confirms the mode used
- Detects if fallback to baseline/RAG occurred

**If fallback occurred:**
```
✗ Fallback occurred! Requested 'lora' but used 'baseline'
ℹ Requested mode: lora
```

### Output Structure

```
analysis_output/
├── lora_e2e_lora_20260114_152345/
│   ├── analysis_detailed.html
│   ├── analysis_summary.html
│   ├── advisor_bio.html
│   ├── sse_stream.log
│   ├── sse_events.json
│   ├── status_polling.log
│   └── metadata.json
└── lora_e2e_comparison_20260114_152400.html  ← (if --compare used)
```

---

## Test 2: Three-Mode Comparison with Auto-Restart

**Location:** `test/test_ios_e2e_three_mode_comparison.py`

**Best For:** Testing different modes with automatic service restart handling.

### Basic Usage

```bash
# Run all three modes (default)
python3 test/test_ios_e2e_three_mode_comparison.py
python3 test/test_ios_e2e_three_mode_comparison.py --all

# Run specific mode (with auto-restart)
python3 test/test_ios_e2e_three_mode_comparison.py --mode=base
python3 test/test_ios_e2e_three_mode_comparison.py --mode=rag
python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./adapters/ansel
python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora+rag --lora-path=./adapters/ansel
```

### Auto-Restart Feature

This test can **automatically restart services** if the current mode doesn't match the test mode:

```bash
# With auto-restart (default)
python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./adapters/ansel

# Without auto-restart (manual service management)
python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./adapters/ansel --no-auto-restart
```

**What it does:**
1. Checks AI Advisor Service health and running mode
2. If mode doesn't match, runs `./mondrian.sh --restart --mode={mode}`
3. Waits for services to be ready
4. Validates LoRA adapter exists (if needed)
5. Runs the test

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--mode` | Service mode (`base`, `rag`, `lora`, `lora+rag`, `ab-test`) | - |
| `--lora-path` | Path to LoRA adapter (required for lora modes) | - |
| `--auto-restart` | Automatically restart services if mode doesn't match | `True` |
| `--no-auto-restart` | Don't auto-restart services | `False` |
| `--baseline` | Run baseline test (legacy) | - |
| `--rag` | Run RAG test (legacy) | - |
| `--lora` | Run LoRA test (legacy) | - |

### When to Use Auto-Restart

**Use `--auto-restart` (default) when:**
- You're switching between different modes frequently
- You want the test to handle service management
- You're running automated test suites

**Use `--no-auto-restart` when:**
- Services are already running in the correct mode
- You're doing rapid iteration on a single mode
- You want full control over service lifecycle

---

## Test 3: Four-Mode Comprehensive Test (test_ios_e2e_four_modes.py)

**Location:** `test/rag-embeddings/test_ios_e2e_four_modes.py`

**Best For:** Complete side-by-side comparison of all four analysis modes with full debugging.

> **See also:** [rag-embeddings-test-guide.md](rag-embeddings/rag-embeddings-test-guide.md) for detailed call/data flow diagrams.

### Changing the Source Image

Edit the constant at line ~57 in the test file:
```python
TEST_IMAGE = "source/mike-shrub.jpg"  # Change to your image path
```

Or use any image in the `source/` directory.

### Run All Four Modes (Default)

```bash
python3 test/rag-embeddings/test_ios_e2e_four_modes.py
```

### Run Specific Mode

```bash
# Baseline (no prep needed)
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --mode=base

# RAG (needs dimensional profiles)
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --mode=rag

# LoRA (needs trained adapter)
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --mode=lora --lora-path=./adapters/ansel

# RAG+LoRA (needs both adapter AND profiles)
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --mode=rag_lora --lora-path=./adapters/ansel
```

### Run Specific Tests (Legacy API)

```bash
# Baseline only
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --baseline

# RAG only
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --rag

# LoRA only
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --lora

# RAG+LoRA only
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --rag-lora

# Multiple modes
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --baseline --rag --lora --rag-lora
```

---

## Call/Data Flow Summary (Four-Mode Test)

### Per-Mode Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. verify_service_mode(mode)                                        │
│    → GET /health on AI Advisor (port 5100)                          │
│    → Saves health snapshot for metadata                             │
├─────────────────────────────────────────────────────────────────────┤
│ 2. upload_image(mode, output_dir)                                   │
│    → POST /upload on Job Service (port 5005)                        │
│    → Logs request/response to api_requests.log                      │
│    → Returns job_id, stream_url                                     │
├─────────────────────────────────────────────────────────────────────┤
│ 3. stream_sse_updates(stream_url)                                   │
│    → GET stream_url (SSE connection)                                │
│    → Logs events to sse_stream.log, sse_events.json                 │
├─────────────────────────────────────────────────────────────────────┤
│ 4. get_analysis_html(job_id)                                        │
│    → GET /analysis/{job_id}                                         │
│    → Returns full HTML                                              │
├─────────────────────────────────────────────────────────────────────┤
│ 5. save_outputs(...)                                                │
│    → GET /summary/{job_id} → analysis_summary.html                  │
│    → GET /advisor/{advisor} → advisor_bio.html                      │
│    → Saves all files + metadata.json with health snapshot           │
└─────────────────────────────────────────────────────────────────────┘
```

### Post-Test Flow (When 2+ Modes Complete)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 6. create_four_mode_comparison_html(dirs...)                        │
│    → Generates ios_e2e_four_mode_TIMESTAMP.html                     │
├─────────────────────────────────────────────────────────────────────┤
│ 7. create_text_diff_comparison(mode_dirs)                           │
│    → Extracts text from each summary HTML                           │
│    → Generates mode_diff_TIMESTAMP.html with side-by-side diff      │
└─────────────────────────────────────────────────────────────────────┘
```

### Outputs Per Mode

Each mode directory (`ios_e2e_{mode}_{timestamp}/`) contains:

| File | Description |
|------|-------------|
| `analysis_summary.html` | Top 3 recommendations |
| `analysis_detailed.html` | Full dimensional feedback |
| `advisor_bio.html` | Advisor profile/background |
| `sse_stream.log` | Raw SSE event stream |
| `sse_events.json` | Parsed SSE events |
| `api_requests.log` | API request/response log |
| `metadata.json` | Job info + service health snapshot |

### Comparison Files (in `analysis_output/`)

| File | Description |
|------|-------------|
| `ios_e2e_four_mode_TIMESTAMP.html` | Side-by-side iframe comparison |
| `mode_diff_TIMESTAMP.html` | Text diff between mode outputs |

### Browser Viewing

After tests complete, view results in browser:

```bash
# Start HTTP server
cd analysis_output && python3 -m http.server 8080

# Open in browser
open http://localhost:8080/ios_e2e_four_mode_TIMESTAMP.html
open http://localhost:8080/mode_diff_TIMESTAMP.html
```

## Requirements & Prerequisites

### General Requirements
All tests require:
- Services running (Job Service on port 5005, AI Advisor on port 5100)
- Virtual environment activated: `source mondrian/venv/bin/activate`
- Test image available (default: `source/mike-shrub.jpg`)

### For Baseline Mode
✅ No special requirements - just running services

### For RAG Mode
✅ Dimensional profiles must exist in database:
```bash
# Check if profiles exist
sqlite3 mondrian/mondrian.db \
  "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel'"
```

### For LoRA Mode
✅ LoRA adapter must exist:
```bash
ls -la adapters/ansel/adapters.safetensors
```

**Note:** `test_lora_e2e.py` will check for adapter and provide helpful error messages if missing.

### For RAG+LoRA Mode
✅ **Both** required:
- LoRA adapter: `adapters/ansel/adapters.safetensors`
- Dimensional profiles: Records in `dimensional_profiles` table

### Test-Specific Notes

**test_lora_e2e.py:**
- Requires `--image` parameter (no default)
- Verifies adapter is loaded (mode verification)
- Will fail gracefully if adapter missing in LoRA mode

**test_ios_e2e_three_mode_comparison.py:**
- Can auto-restart services with `--auto-restart` (default)
- Handles service mode switching automatically
- Validates LoRA adapter availability before restart

**test_ios_e2e_four_modes.py:**
- Uses default test image (`source/mike-shrub.jpg`)
- Skips modes if prerequisites missing (graceful degradation)
- Does NOT restart services automatically

## Starting Services in Correct Mode

The test requires services to be running. Start them in the appropriate mode:

```bash
# Baseline (default)
./mondrian.sh --restart

# RAG (uses base model with retrieval)
./mondrian.sh --restart --mode=rag

# LoRA (uses fine-tuned model)
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

# RAG+LoRA (uses fine-tuned model + retrieval)
./mondrian.sh --restart --mode=rag_lora --lora-path=./adapters/ansel
```

## Understanding Mode Availability

### Auto-Detection
The test checks availability:

```python
# For LoRA/RAG+LoRA
check_lora_adapter()  # Checks adapters/ansel/adapters.safetensors exists

# For RAG/RAG+LoRA
check_dimensional_profiles()  # Queries database for profiles
```

### Graceful Failures
- If adapter unavailable → LoRA/RAG+LoRA tests skipped with warning
- If profiles unavailable → RAG/RAG+LoRA tests skipped with warning
- Baseline always runs (no dependencies)

## Output Structure

```
analysis_output/
├── ios_e2e_baseline_20260114_152345/
│   ├── analysis_detailed.html
│   ├── analysis_summary.html
│   ├── advisor_bio.html
│   ├── sse_stream.log
│   ├── sse_events.json
│   ├── api_requests.log          ← API request/response log
│   └── metadata.json             ← Includes service health snapshot
├── ios_e2e_rag_20260114_152400/
│   └── ... (same structure)
├── ios_e2e_lora_20260114_152425/
│   └── ... (same structure)
├── ios_e2e_rag_lora_20260114_152450/
│   └── ... (same structure)
├── ios_e2e_four_mode_20260114_152500.html  ← Side-by-side comparison
└── mode_diff_20260114_152500.html          ← Text diff between modes
```

## Metadata Example (metadata.json)

```json
{
  "job_id": "abc123def456",
  "mode": "rag_lora",
  "advisor": "ansel",
  "test_image": "source/mike-shrub.jpg",
  "timestamp": "2026-01-14T15:24:50.123456",
  "files": {
    "advisor_bio_html": "advisor_bio.html",
    "analysis_summary_html": "analysis_summary.html",
    "analysis_detailed_html": "analysis_detailed.html",
    "sse_stream_log": "sse_stream.log",
    "sse_events_json": "sse_events.json",
    "api_requests_log": "api_requests.log",
    "status_polling_log": "status_polling.log"
  },
  "service_health": {
    "status": "healthy",
    "model_mode": "fine_tuned",
    "lora_enabled": true,
    "lora_path": "./adapters/ansel",
    "advisor": "ansel"
  }
}
```

## Comparison View Features

The auto-generated comparison HTML (`ios_e2e_four_mode_*.html`) shows:

### Section 1: Advisor Bio
- Side-by-side advisor backgrounds in iframes
- Downloadable links to each version

### Section 2: Analysis Summary
- Top 3 recommendations from each mode
- Easy visual comparison of key differences

### Section 3: Full Analysis
- Complete dimensional feedback comparison
- Spot differences in recommendations

### Section 4: Supporting Files
- Links to SSE logs
- Links to metadata JSON
- Links to raw event streams

## Troubleshooting

### "Services are down" Error
```bash
# Option 1: Start services manually
./mondrian.sh --restart --mode=rag_lora --lora-path=./adapters/ansel

# Option 2: Use three-mode test with auto-restart
python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./adapters/ansel
```

### "LoRA adapter not found" Warning

**For test_lora_e2e.py:**
```bash
# The test will fail with helpful error message
# Either train adapter or use --mode baseline
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
```

**For test_ios_e2e_four_modes.py:**
```bash
# Either train adapter or don't request LoRA mode
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --baseline --rag
```

### "Dimensional profiles not found" Warning
```bash
# First generate profiles by analyzing some images in baseline/LoRA mode
# Then run RAG/RAG+LoRA tests
```

### Mode Verification Failed (test_lora_e2e.py)

If you see:
```
✗ Fallback occurred! Requested 'lora' but used 'baseline'
```

This means:
- LoRA adapter exists but service couldn't load it
- Service is running in wrong mode
- LoRA model loading failed

**Fix:**
```bash
# Restart services in correct mode
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

# Or use three-mode test with auto-restart
python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./adapters/ansel
```

### Auto-Restart Failed (test_ios_e2e_three_mode_comparison.py)

If auto-restart fails:
```bash
# Check if mondrian.sh is executable
chmod +x mondrian.sh

# Try manual restart first
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

# Then run test without auto-restart
python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./adapters/ansel --no-auto-restart
```

### SSE Client Not Available
The tests automatically fall back to status polling if `sseclient-py` is not installed:
```bash
pip install sseclient-py
```

### Missing --image Parameter (test_lora_e2e.py)
```bash
# This test REQUIRES --image parameter
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel
```

## Performance Expectations

### Typical Timings (per mode)

| Mode | Pass 1 | Query | Pass 2 | Total |
|------|--------|-------|--------|-------|
| Baseline | N/A | N/A | ~4-5s | ~4-5s |
| RAG | ~4-5s | ~0.5s | ~4-5s | ~9-10s |
| LoRA | N/A | N/A | ~4-5s | ~4-5s |
| RAG+LoRA | ~4-5s | ~0.5s | ~4-5s | ~9-10s |

*Note: Timings depend on model loading, GPU speed, image size, and system load*

## Integration with CI/CD

For automated testing:

```bash
#!/bin/bash
set -e

# Start services in test mode
./mondrian.sh --restart --mode=rag_lora --lora-path=./adapters/ansel

# Wait for services
sleep 10

# Run all four modes
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --all

# Generate report from comparison HTML
echo "✓ Test complete. View results at:"
ls -t analysis_output/*.html | head -1
```

## Common Workflows

### Quick LoRA Verification
**Goal:** Verify LoRA adapter is working correctly

```bash
# Run standalone test with mode verification
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel

# Check for successful verification in output:
# ✓ LORA mode confirmed for ansel
```

### LoRA vs Baseline Comparison
**Goal:** Compare LoRA fine-tuned output vs baseline

```bash
# Automatic comparison mode
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare

# View comparison HTML
open analysis_output/lora_e2e_comparison_*.html
```

### Testing After Training New LoRA Adapter
**Goal:** Validate newly trained adapter works end-to-end

```bash
# Step 1: Restart services with new adapter
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

# Step 2: Run verification test
python3 test_lora_e2e.py --image source/test-image.jpg --advisor ansel

# Step 3: Check mode verification output
# Should see: ✓ AI Advisor Service is running in fine-tuned mode
```

### Quick Mode Switching
**Goal:** Test different modes without manual service restarts

```bash
# Three-mode test handles restarts automatically
python3 test/test_ios_e2e_three_mode_comparison.py --mode=baseline
python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./adapters/ansel
python3 test/test_ios_e2e_three_mode_comparison.py --mode=rag
```

### Complete Multi-Mode Analysis
**Goal:** Generate comprehensive comparison across all modes

```bash
# Ensure services are running (any mode is fine)
./mondrian.sh --restart

# Run all four modes and generate comparison
python3 test/rag-embeddings/test_ios_e2e_four_modes.py

# View side-by-side comparison
open analysis_output/ios_e2e_four_mode_*.html
```

### CI/CD Integration Example
**Goal:** Automated testing in build pipeline

```bash
#!/bin/bash
set -e

# Use three-mode test with auto-restart for reliability
python3 test/test_ios_e2e_three_mode_comparison.py \
  --mode=lora \
  --lora-path=./adapters/ansel \
  --auto-restart

# Check exit code for success/failure
if [ $? -eq 0 ]; then
  echo "✓ LoRA E2E test passed"
else
  echo "✗ LoRA E2E test failed"
  exit 1
fi
```

## Architecture Notes

### LoRA Mode
- Loads base model + applies LoRA adapter weights
- Single-pass with learned advisor style
- No retrieval phase

### RAG Mode
- Uses base model with retrieval
- Two-pass: extract dimensions, retrieve examples, augment prompt
- No fine-tuning

### RAG+LoRA Mode
- **Pass 1**: Use LoRA model to extract dimensional scores
- **Query**: Retrieve portfolio images matching those dimensions
- **Pass 2**: Use LoRA model with RAG-augmented prompt
- Combines learned style (LoRA) with contextual examples (RAG)

## Advanced Usage

### Custom Test Image

**For test_lora_e2e.py:**
```bash
# Specify image via command line
python3 test_lora_e2e.py --image path/to/your/image.jpg --advisor ansel
```

**For test_ios_e2e_four_modes.py:**
```bash
# Edit TEST_IMAGE constant in script
TEST_IMAGE = "path/to/your/image.jpg"
```

**For test_ios_e2e_three_mode_comparison.py:**
```bash
# Edit TEST_IMAGE constant in script
TEST_IMAGE = "path/to/your/image.jpg"
```

### Custom Advisor

All tests support custom advisors:

**test_lora_e2e.py:**
```bash
python3 test_lora_e2e.py --image source/test.jpg --advisor custom_advisor
```

**test_ios_e2e_four_modes.py and test_ios_e2e_three_mode_comparison.py:**
```python
# Edit ADVISOR constant in script:
ADVISOR = "custom_advisor"
```

### External Service URLs

**test_lora_e2e.py (command line):**
```bash
python3 test_lora_e2e.py \
  --image source/test.jpg \
  --advisor ansel \
  --job-service-url http://remote-server.com:5005 \
  --ai-advisor-url http://remote-server.com:5100
```

**All tests (edit script):**
```python
JOB_SERVICE_URL = "http://your-server.com:5005"
AI_ADVISOR_URL = "http://your-server.com:5100"
```

### Running Multiple Tests in Sequence

```bash
#!/bin/bash
# Example: Test all modes with different images

IMAGES=("source/image1.jpg" "source/image2.jpg" "source/image3.jpg")

for img in "${IMAGES[@]}"; do
  echo "Testing with $img"
  python3 test_lora_e2e.py --image "$img" --advisor ansel --compare
done

# Or use four-mode test for comprehensive comparison
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --all
```
