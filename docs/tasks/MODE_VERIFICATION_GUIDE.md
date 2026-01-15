# Mode Verification & Debug Markers Guide

## Overview

This guide explains how to verify which flow (Baseline, RAG, or LORA) is being executed in Mondrian, and how to use the comprehensive debug markers that have been added to the system.

## Database Schema Fix

**Issue Fixed:** The `mode` column was missing from the database schema, which could cause duplicate mode suffixes in job IDs.

**Solution Applied:**
- Added `mode` column to `EXPECTED_COLUMNS` in `mondrian/sqlite_helper.py`
- Updated `create_jobs_table()` to include `mode TEXT DEFAULT 'baseline'`
- Updated migration logic to properly add the column with default value

The database will automatically migrate on next restart.

## Debug Markers in Output

### What to Look For

All debug markers follow this pattern: `[CONTEXT] Message`

#### Job Service Markers (mongodb/job_service_v2.3.py)

```
[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Job ID: <uuid>
[UPLOAD] Mode: baseline|rag|lora
[UPLOAD] Enable RAG: true|false
[UPLOAD] Advisors: [advisor1, advisor2]
[UPLOAD] Flow: RAG|BASELINE + LORA|DEFAULT MODEL
[UPLOAD] =====================================

[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Job ID: <uuid>
[JOB] Filename: <filename>
[JOB] Advisors: [advisors]
[JOB] Mode: baseline|rag|lora
[JOB] Enable RAG: true|false
[JOB] Host URL: <url>
[JOB] Flow: RAG|BASELINE + LORA|DEFAULT MODEL
[JOB] ====================================
```

#### AI Advisor Service Markers (mondrian/ai_advisor_service.py)

**Strategy Analysis (NEW - Unified flow entry point):**
```
[STRATEGY] ========== ANALYSIS STARTED ==========
[STRATEGY] Mode: baseline|rag|lora
[STRATEGY] Advisor: <advisor_id>
[STRATEGY] Image: <image_path>
[STRATEGY] Job ID: <uuid>
[STRATEGY] Job Service URL: <url>
[STRATEGY] Response Format: html|json
[STRATEGY] ==========================================

[STRATEGY] ✓ Using requested mode: <mode>
  OR
[STRATEGY] ⚠️  FALLBACK OCCURRED: <requested_mode> -> <effective_mode>

[STRATEGY] Executing analysis with <mode> strategy...
[STRATEGY] ✓ Analysis complete. Overall grade: <grade>
[STRATEGY] ✓ Mode used in result: <mode>
```

**Baseline Analysis (if not using strategy pattern):**
```
[BASELINE] ========== BASELINE ANALYSIS STARTED ==========
[BASELINE] Advisor: <advisor_id>
[BASELINE] Image path: <path>
[BASELINE] Job ID: <uuid>
[BASELINE] Custom prompt: Yes|No
[BASELINE] Response format: html|json
[BASELINE] Flow: Single-pass baseline (no RAG, no fine-tuning)
[BASELINE] =============================================

[BASELINE] ✓ Advisor prompt loaded, length: <length> chars
[BASELINE] ✓ Using custom prompt instead, length: <length> chars
[BASELINE] ✓ Full prompt prepared, length: <length> chars
[BASELINE] Saving full prompt to job service...
```

**RAG Analysis:**
```
[RAG] ========== RAG ANALYSIS STARTED (2-PASS) ==========
[RAG] Advisor: <advisor_id>
[RAG] Image path: <path>
[RAG] Job ID: <uuid>
[RAG] Job service URL: <url>
[RAG] Custom prompt: Yes|No
[RAG] Response format: html|json
[RAG] Enable embeddings: true|false
[RAG] Flow: Two-pass RAG with dimensional comparison
[RAG] ========================================================

[RAG] [INFO] Pass 1: Analyzing image...
[RAG] [INFO] Pass 2: Comparing with advisor portfolio...
```

## How to View Debug Markers

### 1. Terminal Output (./mondrian.sh --restart)

When you restart services, all markers will appear in the terminal:

```bash
cd /Users/shaydu/dev/mondrian-macos
./mondrian.sh --restart
```

Look for:
- `[JOB]` markers when jobs are queued
- `[STRATEGY]` markers when analysis starts
- `[BASELINE]` or `[RAG]` markers showing which flow is executing

### 2. iOS Debug Logs

Debug markers are also sent to iOS debug logs:

```bash
# If on iOS simulator
xcrun simctl spawn booted log stream --predicate 'eventMessage contains[cd] "BASELINE" OR eventMessage contains[cd] "RAG" OR eventMessage contains[cd] "STRATEGY"'

# Or check Xcode console when app is running
# In Xcode: View > Debug Area > Show Console
```

### 3. Log Files

All output is also captured in:
```
/Users/shaydu/dev/mondrian-macos/logs/
```

Look for files matching the service (ai_advisor_service, job_service_v2.3)

### 4. Using grep to Filter

To see only mode-related output:

```bash
# Watch for job queuing
tail -f logs/*.log | grep -E "\[UPLOAD\]|\[JOB\]|\[STRATEGY\]"

# Watch for specific mode
tail -f logs/*.log | grep "\[BASELINE\]"
tail -f logs/*.log | grep "\[RAG\]"
tail -f logs/*.log | grep "\[LORA\]"
```

## Running Mode Verification Test

The test script `test_mode_verification.py` will upload the same image in all three modes and verify each flow:

```bash
# Make sure venv is activated
source mondrian/venv/bin/activate

# Run the test
python3 test_mode_verification.py
```

What the test does:
1. Checks if services are running
2. Uploads image in BASELINE mode
3. Waits for completion and verifies mode in database
4. Uploads image in RAG mode
5. Waits for completion and verifies mode in database
6. Uploads image in LORA mode
7. Waits for completion and verifies mode in database
8. Prints summary showing which modes were verified

Output will show:
```
[STEP 1] Uploading image for BASELINE mode...
✓ Upload successful - Job ID: uuid (baseline)
[BASELINE] Waiting for analysis to complete...
[BASELINE] Status: started | Progress: 0% | Mode: baseline
[BASELINE] Status: analyzing | Progress: 15% | Mode: baseline
✓ Job completed successfully!
✓ Mode verification: baseline (matches expected: baseline)

[STEP 2] Uploading image for RAG mode...
✓ Upload successful - Job ID: uuid (rag)
[RAG] Waiting for analysis to complete...
[RAG] Status: started | Progress: 0% | Mode: rag
[RAG] Status: analyzing | Progress: 20% | Mode: rag
✓ Job completed successfully!
✓ Mode verification: rag (matches expected: rag)
```

## Understanding the Flows

### BASELINE Flow

- **Markers**: `[BASELINE]` + `[UPLOAD]` + `[JOB]`
- **What happens**:
  1. Image uploaded with `mode=baseline`
  2. Single-pass analysis
  3. No RAG dimensional comparison
  4. Uses base model (not fine-tuned)
- **Database**: `mode='baseline'`, `enable_rag=0`

### RAG Flow

- **Markers**: `[RAG]` + `[UPLOAD]` + `[JOB]`
- **What happens**:
  1. Image uploaded with `mode=rag` and `enable_rag=true`
  2. Pass 1: Initial analysis
  3. Pass 2: Dimensional comparison with advisor portfolio
  4. Uses base model with RAG comparison
- **Database**: `mode='rag'`, `enable_rag=1`

### LORA Flow

- **Markers**: `[STRATEGY]` + `[LORA]` + `[UPLOAD]` + `[JOB]`
- **What happens**:
  1. Image uploaded with `mode=lora`
  2. Uses strategy pattern to load LORA fine-tuned model
  3. May include RAG if also enabled
- **Database**: `mode='lora'`, `enable_rag=0` or `1`

## Troubleshooting

### Issue: No mode markers appearing

**Solution:**
1. Verify services are running: `./mondrian.sh --status`
2. Restart services: `./mondrian.sh --restart`
3. Check that logs are being written: `ls -la logs/`
4. Verify terminal isn't redirecting stderr

### Issue: Database still shows duplicate mode

**Solution:**
1. Clear database and restart: `python3 clear_jobs.py`
2. Restart services: `./mondrian.sh --restart`
3. The schema migration will automatically add the mode column

### Issue: Mode showing (rag) (rag)

**This has been fixed:**
- The database schema now properly handles the mode column
- The `format_job_id_with_mode()` function prevents double-formatting
- Jobs are always stored with clean mode values in the database

## Database Schema

The updated schema now includes:

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    filename TEXT,
    advisor TEXT,
    -- ... other fields ...
    enable_rag INTEGER DEFAULT 0,
    mode TEXT DEFAULT 'baseline'  -- <-- ADDED
)
```

Valid mode values:
- `baseline`: Standard single-pass analysis
- `rag`: Two-pass analysis with dimensional comparison
- `lora`: Fine-tuned LORA model analysis
- `ab_test`: A/B testing mode (shows both baseline and alternative)

## Next Steps

After verifying the flows:

1. **Monitor actual iOS requests** in the app
2. **Compare outputs** between modes to see differences
3. **Check performance** - RAG may be slower due to 2-pass analysis
4. **Verify LORA quality** - Compare results with baseline

The debug markers make it easy to track exactly which code path is being executed at any time.
