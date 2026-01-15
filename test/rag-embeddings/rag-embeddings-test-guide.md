# RAG & Embeddings Test Guide

## Overview

This directory contains tests for RAG (Retrieval-Augmented Generation) and embedding functionality across all analysis modes.

| Test File | Purpose |
|-----------|---------|
| `test_ios_e2e_four_modes.py` | Complete 4-mode comparison (baseline, rag, lora, rag_lora) |
| `test_rag_lora_e2e.py` | RAG + LoRA end-to-end test |
| `test_embeddings_e2e.py` | Embeddings end-to-end test |
| `test_embeddings_unit.py` | Embeddings unit tests |
| `run_embedding_tests.sh` | Shell script to run all embedding tests |

---

## Quick Start

```bash
cd /Users/shaydu/dev/mondrian-macos
source mondrian/venv/bin/activate

# Run 4-mode comparison
python3 test/rag-embeddings/test_ios_e2e_four_modes.py

# Run embedding tests
bash test/rag-embeddings/run_embedding_tests.sh
```

---

## Test 1: Four-Mode Comparison (test_ios_e2e_four_modes.py)

**Best For:** Complete side-by-side comparison of all four analysis modes with full debugging.

### Changing the Source Image

Edit the constant at line ~57 in the test file:
```python
TEST_IMAGE = "source/mike-shrub.jpg"  # Change to your image path
```

### Usage

```bash
# Run all four modes (default)
python3 test/rag-embeddings/test_ios_e2e_four_modes.py

# Run specific mode
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --mode=base
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --mode=rag
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --mode=lora --lora-path=./adapters/ansel
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --mode=rag_lora --lora-path=./adapters/ansel

# Legacy flags
python3 test/rag-embeddings/test_ios_e2e_four_modes.py --baseline --rag --lora --rag-lora
```

### Call/Data Flow

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

### Post-Test (When 2+ Modes Complete)

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

### Output Files

**Per-mode directory** (`analysis_output/ios_e2e_{mode}_{timestamp}/`):

| File | Description |
|------|-------------|
| `analysis_summary.html` | Top 3 recommendations |
| `analysis_detailed.html` | Full dimensional feedback |
| `advisor_bio.html` | Advisor profile/background |
| `sse_stream.log` | Raw SSE event stream |
| `sse_events.json` | Parsed SSE events |
| `api_requests.log` | API request/response log |
| `metadata.json` | Job info + service health snapshot |

**Comparison files** (in `analysis_output/`):

| File | Description |
|------|-------------|
| `ios_e2e_four_mode_TIMESTAMP.html` | Side-by-side iframe comparison |
| `mode_diff_TIMESTAMP.html` | Text diff between mode outputs |

### Browser Viewing

```bash
cd analysis_output && python3 -m http.server 8080
# Open: http://localhost:8080/ios_e2e_four_mode_TIMESTAMP.html
# Open: http://localhost:8080/mode_diff_TIMESTAMP.html
```

---

## Test 2: RAG + LoRA E2E (test_rag_lora_e2e.py)

**Best For:** Testing the RAG+LoRA hybrid mode specifically.

### Usage

```bash
python3 test/rag-embeddings/test_rag_lora_e2e.py
```

### Call/Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Check services (Job Service + AI Advisor)                        │
├─────────────────────────────────────────────────────────────────────┤
│ 2. Upload image with mode=rag_lora                                  │
│    → POST /upload                                                   │
├─────────────────────────────────────────────────────────────────────┤
│ 3. Stream SSE updates                                               │
│    → Monitors: Pass 1 (extract) → Query → Pass 2 (analyze)          │
├─────────────────────────────────────────────────────────────────────┤
│ 4. Fetch results                                                    │
│    → GET /analysis/{job_id}                                         │
│    → GET /summary/{job_id}                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Output Location

Results saved to `analysis_output/rag_lora_e2e_{timestamp}/`

---

## Test 3: Embeddings E2E (test_embeddings_e2e.py)

**Best For:** Testing the full embedding computation and storage pipeline.

### Usage

```bash
python3 test/rag-embeddings/test_embeddings_e2e.py
```

### Call/Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Load test image                                                  │
├─────────────────────────────────────────────────────────────────────┤
│ 2. Compute embedding via CLIP model                                 │
│    → Uses mondrian/services/embedding_service.py                    │
├─────────────────────────────────────────────────────────────────────┤
│ 3. Store embedding in database                                      │
│    → Writes to dimensional_profiles table                           │
├─────────────────────────────────────────────────────────────────────┤
│ 4. Verify retrieval                                                 │
│    → Query similar embeddings                                       │
│    → Validate cosine similarity                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Storage

Embeddings stored in:
- Database: `mondrian/mondrian.db` → `dimensional_profiles` table
- Columns: `image_path`, `advisor_id`, `embedding` (blob), `dimensions` (JSON)

---

## Test 4: Embeddings Unit (test_embeddings_unit.py)

**Best For:** Quick unit tests for embedding functions.

### Usage

```bash
python3 test/rag-embeddings/test_embeddings_unit.py
```

### What It Tests

- Embedding vector dimensionality
- Cosine similarity calculation
- Embedding normalization
- Database read/write operations

---

## Running All Embedding Tests

```bash
bash test/rag-embeddings/run_embedding_tests.sh
```

This runs both unit and E2E embedding tests.

---

## Prerequisites

### For All Tests
- Services running (Job Service port 5005, AI Advisor port 5100)
- Virtual environment: `source mondrian/venv/bin/activate`

### For RAG Modes
- Dimensional profiles in database:
```bash
sqlite3 mondrian/mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel'"
```

### For LoRA Modes
- LoRA adapter exists:
```bash
ls -la adapters/ansel/adapters.safetensors
```

---

## Starting Services

```bash
# Baseline
./mondrian.sh --restart

# RAG
./mondrian.sh --restart --mode=rag

# LoRA
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

# RAG+LoRA
./mondrian.sh --restart --mode=rag_lora --lora-path=./adapters/ansel
```

---

## Output Structure

```
analysis_output/
├── ios_e2e_baseline_TIMESTAMP/
│   ├── analysis_detailed.html
│   ├── analysis_summary.html
│   ├── advisor_bio.html
│   ├── sse_stream.log
│   ├── sse_events.json
│   ├── api_requests.log
│   └── metadata.json
├── ios_e2e_rag_TIMESTAMP/
│   └── ... (same structure)
├── ios_e2e_lora_TIMESTAMP/
│   └── ... (same structure)
├── ios_e2e_rag_lora_TIMESTAMP/
│   └── ... (same structure)
├── ios_e2e_four_mode_TIMESTAMP.html   ← Side-by-side comparison
└── mode_diff_TIMESTAMP.html           ← Text diff between modes
```

---

## Metadata Example

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
