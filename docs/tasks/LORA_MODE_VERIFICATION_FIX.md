# LORA Mode Verification Fix - Implementation Summary

## Problem
The LORA mode verification test was failing with:
```
✗ Could not verify LORA mode was used
ℹ This might mean the mode fell back to RAG or baseline
Expected mode: lora
Actual mode: unknown
Fallback occurred: True
```

However, the AI Advisor Service health endpoint confirmed it WAS running in fine-tuned mode:
```
"model_mode": "fine_tuned"
"fine_tuned": true
"lora_enabled": true
```

## Root Causes Identified

### Issue 1: Test tried to parse llm_outputs as JSON string
**File**: `test_lora_e2e.py` line 463

The test was doing:
```python
outputs = json.loads(llm_outputs)  # ❌ Tries to parse as JSON string
```

But the job service returns `llm_outputs` as an **already parsed dict**, not a JSON string.

### Issue 2: Inconsistent response structure handling
**File**: `test_lora_e2e.py` line 267

The `monitor_progress` function was accessing:
```python
job = status_data.get('job', {})  # ❌ No 'job' wrapper in response
status = job.get('status')
```

But the job service returns fields at the **top level** of the response, not nested under a 'job' key.

### Issue 3: Incomplete mode info during analysis
**File**: `mondrian/job_service_v2.3.py` lines 1613-1615

The `llm_outputs` was only included when `status == "done"`. This meant the test had to wait for complete analysis before it could verify the mode, and if anything went wrong during analysis, there was no intermediate way to confirm the mode was set correctly.

## Fixes Implemented

### Fix 1: Handle llm_outputs as dict in test
**File**: `test_lora_e2e.py:454-502`

Changed the verification function to:
```python
llm_outputs = status_data.get('llm_outputs')  # Don't default to ''

if llm_outputs:
    print_info(f"llm_outputs type: {type(llm_outputs)}")
    
    # Handle both string (legacy) and dict (new) formats
    if isinstance(llm_outputs, str):
        try:
            outputs = json.loads(llm_outputs)
        except json.JSONDecodeError:
            outputs = None
    else:
        outputs = llm_outputs  # Already a dict
```

**Benefits:**
- Correctly handles dict format from job service
- Backwards compatible with string format if needed
- Includes debug logging to show data types

### Fix 2: Access response fields at top level
**File**: `test_lora_e2e.py:266-296`

Changed from:
```python
job = status_data.get('job', {})
status = job.get('status')
progress = job.get('progress_percentage', 0)
```

To:
```python
status = status_data.get('status')
progress = status_data.get('progress_percentage', 0)
current_step = status_data.get('current_step', '')
thinking = status_data.get('llm_thinking', '')
```

**Benefits:**
- Correctly accesses flat response structure
- No longer fails on missing 'job' key
- Works with actual API response format

### Fix 3: Include partial mode info during analysis
**File**: `mondrian/job_service_v2.3.py:1613-1627`

Enhanced to include mode info even during analysis:
```python
if llm_outputs_parsed:
    if row["status"] == "done":
        response_data["llm_outputs"] = llm_outputs_parsed
    elif row["status"] in ["analyzing", "processing"]:
        # Include partial mode info for verification during analysis
        mode_info = {}
        for advisor, output in llm_outputs_parsed.items():
            if isinstance(output, dict) and output.get("mode_used"):
                mode_info[advisor] = {"mode_used": output.get("mode_used")}
        if mode_info:
            response_data["mode_info"] = mode_info
```

**Benefits:**
- Allows mode verification even before analysis completes
- Provides real-time feedback on whether correct mode was used
- Full data available after completion for complete verification

## Debug Output Added

The test now prints debug information to show the response structure:
```python
print_info(f"Status response keys: {list(status_data.keys())}")
print_info(f"Status: {status_data.get('status')}")
if 'llm_outputs' in status_data:
    print_info(f"llm_outputs type: {type(status_data['llm_outputs'])}")
```

This helps diagnose future issues quickly.

## Testing

To test the fix:

```bash
# Test LORA mode (with LoRA adapter)
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora

# Test baseline mode (should also work)
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline

# Test RAG mode
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag
```

## Expected Behavior After Fix

1. **For LORA mode**: Test will correctly identify `mode_used: "lora"` from job status and confirm it matches the expected mode
2. **For baseline/RAG modes**: Test will verify the correct mode was used
3. **Debug output**: Shows response structure and llm_outputs type for troubleshooting
4. **Test success**: Returns `✓ LORA mode confirmed for ansel` instead of failing

## Files Modified

1. **test_lora_e2e.py**
   - Fixed `verify_lora_mode()` function (lines 454-502)
   - Fixed `monitor_progress()` function (lines 266-296)
   - Added debug logging to response handling

2. **mondrian/job_service_v2.3.py**
   - Enhanced `/status/<job_id>` endpoint to include partial mode info during analysis (lines 1613-1627)
   - Backwards compatible with existing response format

## Backwards Compatibility

- Test handles both string and dict formats for `llm_outputs`
- Job service returns full `llm_outputs` when done, partial `mode_info` during processing
- Existing code that expects string format will continue to work
- No breaking changes to API response structure
