# Bug Fix: Job ID Double Mode Suffix

## Problem
Job IDs were displaying with duplicate mode suffixes, like:
```
uuid-1234 (rag) (rag)
```

This happened when `format_job_id_with_mode()` was called on a job ID that was already formatted.

## Root Cause
The `format_job_id_with_mode()` function did not check if the job_id was already formatted before appending the mode suffix. If the same job ID was passed through the function twice, the mode would be appended twice.

## Solution
Modified `format_job_id_with_mode()` in `mondrian/job_service_v2.3.py` to:

1. **Prevent double-formatting**: Check if the job_id already contains " (" (indicating it's already formatted), and if so, extract just the UUID before re-formatting
2. **Handle all mode variations**: Support both `rag_lora` and `lora+rag` naming conventions
3. **Ensure single format**: Always return properly formatted job ID with mode suffix exactly once

### Code Changes
```python
def format_job_id_with_mode(job_id, mode):
    # Prevent double-formatting: extract UUID if job_id already has mode suffix
    if ' (' in job_id:
        job_id = job_id.split(' (')[0]
    
    # Handle various mode names and standardize them
    mode_display = {
        'baseline': 'baseline',
        'rag': 'rag',
        'lora': 'lora',
        'rag_lora': 'rag+lora',  # New: support rag_lora mode name
        'lora+rag': 'lora+rag',
        'ab_test': 'ab_test',
        'ab-test': 'ab_test'
    }
    display_mode = mode_display.get(mode, mode)
    return f"{job_id} ({display_mode})"
```

## Test Cases Passed
- ✅ Fresh UUID + mode → "uuid (mode)"
- ✅ Already formatted UUID → extracted and reformatted without duplication
- ✅ Mode change on formatted ID → UUID extracted and new mode applied
- ✅ All mode variations handled correctly

## Files Modified
- `mondrian/job_service_v2.3.py` - Updated `format_job_id_with_mode()` function

## Impact
- Job IDs now always display with exactly one mode suffix
- Function is now idempotent - can be called multiple times safely
- Supports all mode naming conventions (rag_lora and lora+rag)
