# Complete Job ID Mode Display Fix

## Problem Statement
Job IDs were displaying with duplicate mode suffixes in the iOS app, showing:
```
Job ID: uuid-1234 (rag) (rag)
```

Instead of:
```
Job ID: uuid-1234 (rag)
```

## Root Causes Identified and Fixed

### Issue 1: Double Formatting Prevention
**File:** `mondrian/job_service_v2.3.py` - `format_job_id_with_mode()` function

**Problem:** The function didn't check if a job_id was already formatted before appending the mode.

**Solution:** Added defensive check to extract UUID if job_id already contains mode:
```python
# Prevent double-formatting: extract UUID if job_id already has mode suffix
if ' (' in job_id:
    job_id = job_id.split(' (')[0]
```

This makes the function idempotent - safe to call multiple times.

### Issue 2: URL Construction Using Formatted IDs
**File:** `mondrian/job_service_v2.3.py` - `/status` endpoint

**Problem:** URLs in the response were being built with the formatted job_id parameter instead of the extracted UUID.

**Solution:** Changed from:
```python
status_url = f"{host_url}/status/{job_id}"        # job_id might be formatted!
analysis_url = f"{host_url}/analysis/{job_id}"    # job_id might be formatted!
stream_url = f"{host_url}/stream/{job_id}"        # job_id might be formatted!
```

To:
```python
status_url = f"{host_url}/status/{job_uuid}"      # Always use bare UUID
analysis_url = f"{host_url}/analysis/{job_uuid}"  # Always use bare UUID
stream_url = f"{host_url}/stream/{job_uuid}"      # Always use bare UUID
```

### Issue 3: Mode Name Variations
**Added support for:**
- `rag_lora` → displays as `rag+lora`
- `lora+rag` → displays as `lora+rag`

## How It Works Now

1. **Upload endpoint** returns formatted job ID: `uuid (mode)` ✓
2. **Status endpoint** receives the job_id parameter:
   - Extracts UUID using `extract_job_uuid()` ✓
   - Formats it exactly once using updated `format_job_id_with_mode()` ✓
3. **URLs in response** use bare UUID so they work with any endpoint ✓
4. **Multiple calls** to formatting function are safe (idempotent) ✓

## Testing

All scenarios tested and working:
```
✓ Fresh UUID + mode → "uuid (mode)"
✓ Already formatted UUID → extracted and reformatted without duplication
✓ Mode change on formatted ID → UUID extracted and new mode applied
✓ All mode variations handled correctly
```

## Files Modified
- `mondrian/job_service_v2.3.py`:
  - Updated `format_job_id_with_mode()` function
  - Fixed `/status` endpoint to use `job_uuid` in URLs
  - Updated `/summary` endpoint to handle already-formatted job IDs

## Result
iOS app now displays job IDs with exactly one mode suffix:
```
Job ID: f47ac10b-58cc-4372-a567-0e02b2c3d479 (rag)
        └─ Clean, single mode indicator
```
