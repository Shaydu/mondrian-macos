# LoRA Mode Metadata Fix - Implementation Summary

## Problem
The E2E test for LoRA mode was failing with:
```
✓ AI Advisor Service is running in fine-tuned mode
✗ Could not verify LORA mode was used
✗ End-to-End Test FAILED
```

## Root Causes

### 1. Field Name Mismatch
- **AI Advisor Service** returned: `"lora_enabled": true`
- **Tests checked for**: `"fine_tuned"` (field didn't exist)
- Result: Test defaulted to `False`, thinking LoRA wasn't working

### 2. Missing Metadata in Job Data
- AI Advisor Service returned HTML directly
- No `mode_used` or metadata was preserved
- Test couldn't verify which mode was actually used from job data

### 3. Test Always Passed
- Test printed warnings but never exited with failure code
- Always reported "PASSED" even when verification failed

## Solution Implemented

### Part 1: Fix Health Endpoint Field Name
**File:** `mondrian/ai_advisor_service.py` (line 2273)

Added `fine_tuned` field as alias:
```python
health_data.update({
    "lora_enabled": _IS_FINE_TUNED,
    "fine_tuned": _IS_FINE_TUNED,  # NEW: Alias for backward compatibility
    "model_mode": MODEL_MODE,
})
```

### Part 2: Return JSON with Metadata from AI Advisor
**File:** `mondrian/ai_advisor_service.py` (lines 1370-1398)

Modified `_analyze_image_with_strategy()` to return JSON with metadata:
```python
# Build metadata for verification
metadata = {
    "mode_used": result.mode_used,
    "requested_mode": context.requested_mode,
    "effective_mode": context.effective_mode,
    "fallback_occurred": context.fallback_occurred,
    "overall_grade": result.overall_grade,
    "advisor_id": result.advisor_id
}

# Return JSON structure with HTML and metadata
response_data = {
    "html": html,
    "mode_used": result.mode_used,
    "metadata": metadata
}
return Response(json.dumps(response_data), mimetype="application/json")
```

### Part 3: Parse JSON Response in Job Service
**File:** `mondrian/job_service_v2.3.py` (lines 870-900)

Updated to parse JSON and extract HTML + metadata:
```python
if 'application/json' in content_type:
    # New format: JSON with html and metadata
    response_data = resp.json()
    html_output = response_data.get('html', '')
    mode_used = response_data.get('mode_used', 'unknown')
    metadata = response_data.get('metadata', {})
    
    # Store full JSON (with metadata) for verification
    llm_outputs[adv] = {
        'html': html_output,
        'mode_used': mode_used,
        'metadata': metadata
    }
    llm_output = html_output  # Use HTML for display
else:
    # Legacy format: HTML only (backward compatibility)
    llm_output = resp.text.strip()
    llm_outputs[adv] = llm_output
```

### Part 4: Store JSON in Database
**File:** `mondrian/job_service_v2.3.py` (line 1074)

Convert llm_outputs dict to JSON string before storing:
```python
llm_outputs_json = json.dumps(llm_outputs)
update_job_status(..., llm_outputs=llm_outputs_json, ...)
```

### Part 5: Include llm_outputs in Status Endpoint
**File:** `mondrian/job_service_v2.3.py` (lines 1586-1610)

Added llm_outputs to status response for verification:
```python
# Include llm_outputs for mode verification (only if job is complete)
if row["status"] == "done" and llm_outputs_parsed:
    response_data["llm_outputs"] = llm_outputs_parsed
```

### Part 6: Handle New Format in extract_critical_recommendations
**File:** `mondrian/job_service_v2.3.py` (lines 3126-3129)

Extract HTML from new dict format:
```python
# Handle new format: dict with 'html' and 'metadata' keys
if isinstance(advisor_output, dict) and 'html' in advisor_output:
    advisor_output = advisor_output['html']
```

### Part 7: Fix Test Validation Logic
**File:** `test_lora_e2e.py` (lines 576-595)

Added strict validation that fails the test:
```python
# For lora mode, verification is REQUIRED
if mode == "lora" and not verified:
    print("✗ End-to-End Test FAILED")
    print("Failure Reason: LoRA mode verification failed")
    return None  # Fail the test
```

### Part 8: Fix Test to Read Top-Level Response
**File:** `test_lora_e2e.py` (lines 453-457, 489)

Fixed test to read `llm_outputs` from top level instead of nested `job` key:
```python
# Before:
status_data = response.json()
job = status_data.get('job', {})
llm_outputs = job.get('llm_outputs', '')

# After:
status_data = response.json()
llm_outputs = status_data.get('llm_outputs', '')
```

### Part 9: Restored --status Command (Bonus)
**File:** `scripts/start_services.py` (lines 574-577)

Added back the `--status` flag:
```python
if '--status' in sys.argv:
    print("Active jobs (10):")
    show_active_jobs()
    return
```

Fixed bug in `show_active_jobs()` (line 505):
```python
# Changed from: job.get('mode')
# To: job["mode"]
mode_str = f" [{job['mode']}]" if job["mode"] else ""
```

## Data Flow

```
1. iOS/Test uploads image with mode="lora"
   ↓
2. Job Service queues job with mode="lora"
   ↓
3. Job Service calls AI Advisor /analyze with mode="lora"
   ↓
4. AI Advisor uses AnalysisContext.set_strategy("lora", advisor_id)
   ↓
5. LoRAStrategy.analyze() executes and returns AnalysisResult
   ↓
6. AI Advisor returns JSON: {"html": "...", "mode_used": "lora", "metadata": {...}}
   ↓
7. Job Service parses JSON and stores:
   - llm_outputs[advisor] = {"html": "...", "mode_used": "lora", "metadata": {...}}
   ↓
8. Job Service stores JSON string in database
   ↓
9. Test queries /status endpoint
   ↓
10. Status endpoint returns llm_outputs with metadata
   ↓
11. Test verifies: mode_used == "lora" ✓
```

## Testing

### Prerequisites
Services must be running in LoRA mode:
```bash
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel
```

### Test Commands

1. **Verify health endpoint has both fields:**
```bash
curl -s http://127.0.0.1:5100/health | grep -E "(fine_tuned|lora_enabled)"
# Should show:
# "fine_tuned": true,
# "lora_enabled": true,
```

2. **Run LoRA E2E test (should PASS):**
```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
echo "Exit code: $?"
# Should show:
# ✓ LORA mode confirmed for ansel
# ✓ End-to-End Test PASSED
# Exit code: 0
```

3. **Check active jobs:**
```bash
./mondrian.sh --status
```

## Expected Test Output (After Fix)

```
[Step 6] Verifying LORA mode was used...
ℹ AI Advisor Service - Model Mode: fine_tuned, Fine-tuned: True
✓ ✓ AI Advisor Service is running in fine-tuned mode
ℹ Mode used: lora
✓ ✓ LORA mode confirmed for ansel

============================================================
  ✓ End-to-End Test PASSED
============================================================

Results:
  Job ID: abc123...
  Mode Requested: lora
  Mode Used: lora
  Fallback: No

Exit code: 0
```

## Backward Compatibility

- Legacy HTML-only responses still work (Job Service detects content-type)
- Both `lora_enabled` and `fine_tuned` fields available in health endpoint
- `extract_critical_recommendations()` handles both dict and string formats
- No breaking changes to existing functionality

## Files Modified

1. `mondrian/ai_advisor_service.py`
   - Line 2273: Added `fine_tuned` field to health endpoint
   - Lines 1370-1398: Modified to return JSON with metadata

2. `mondrian/job_service_v2.3.py`
   - Lines 870-900: Parse JSON response and extract HTML + metadata
   - Line 1074: Convert llm_outputs to JSON string before storing
   - Lines 1586-1610: Include llm_outputs in status endpoint response
   - Lines 3126-3129: Handle new dict format in extract_critical_recommendations

3. `test_lora_e2e.py`
   - Lines 576-595: Added strict validation that fails test on verification failure

4. `scripts/start_services.py`
   - Lines 540, 574-577: Restored `--status` command
   - Line 505: Fixed sqlite3.Row access bug
