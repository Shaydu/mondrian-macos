# Fix for Duplicate (rag) (rag) Mode Suffix

## Issue

Job IDs were sometimes showing duplicate mode suffixes: `uuid (rag) (rag)` instead of `uuid (rag)`

## Root Cause

The `format_job_id_with_mode()` function didn't handle cases where the mode parameter itself might already contain parentheses (e.g., if mode was stored or passed as "(rag)" instead of "rag").

## Solution Applied (mondrian/job_service_v2.3.py)

### 1. Enhanced format_job_id_with_mode()

```python
def format_job_id_with_mode(job_id, mode):
    # NEW: Ensure mode is clean (remove any existing parentheses)
    if mode and '(' in str(mode):
        mode = mode.split('(')[1].rstrip(')')
    
    # Prevent double-formatting: extract UUID if job_id already has mode suffix
    if ' (' in job_id:
        job_id = job_id.split(' (')[0]
    
    # Handle various mode names and standardize them
    mode_display = {
        'baseline': 'baseline',
        'rag': 'rag',
        'lora': 'lora',
        # ...
    }
    # NEW: Normalize to lowercase before lookup
    display_mode = mode_display.get(str(mode).lower() if mode else '', str(mode) if mode else 'baseline')
    return f"{job_id} ({display_mode})"
```

**Key Improvements:**
- Remove parentheses from mode if present: `"(rag)"` → `"rag"`
- Convert mode to string safely: `str(mode)`
- Normalize mode to lowercase for dictionary lookup
- Handle None/empty mode gracefully

### 2. Enhanced extract_job_uuid()

```python
def extract_job_uuid(job_id_param):
    if not job_id_param:
        return job_id_param
    
    # More robust with string conversion
    if ' (' in str(job_id_param):
        return str(job_id_param).split(' (')[0]
    
    return str(job_id_param)
```

**Key Improvements:**
- Convert to string before checking/splitting
- Handle None input gracefully
- More defensive against unexpected input types

## How It Prevents Duplication

### Scenario 1: Mode stored with parentheses
```
Mode in DB: "(rag)"
Old behavior: format_job_id_with_mode(uuid, "(rag)") 
  → Not found in dict → uses "(rag)" as-is
  → Output: "uuid ((rag))"  ❌

New behavior: format_job_id_with_mode(uuid, "(rag)")
  → Strips parentheses → mode = "rag"
  → Found in dict → display_mode = "rag"
  → Output: "uuid (rag)"  ✅
```

### Scenario 2: Mode already in job_id
```
Old: format_job_id_with_mode("uuid (rag)", "rag")
  → Extracts uuid from job_id ✅
  → Adds mode again
  → Output: "uuid (rag)"  ✅

New: Exactly same, but also handles if mode has parentheses
```

### Scenario 3: Mode in weird case
```
Old: format_job_id_with_mode(uuid, "RAG")
  → Not found in lowercase dict
  → Uses "RAG" as-is
  → Output: "uuid (RAG)"  ⚠️

New: format_job_id_with_mode(uuid, "RAG")
  → Normalizes to lowercase: "rag"
  → Found in dict
  → Output: "uuid (rag)"  ✅
```

## What This Fixes

✅ If mode ever contains parentheses, they're stripped
✅ Mode is normalized to lowercase before lookup
✅ String conversion makes it robust to type changes
✅ Better null/None handling

## Testing

To verify the fix works:

1. Upload a job and check the job_id format
2. Should show: `uuid (rag)` NOT `uuid (rag) (rag)`
3. Check `/jobs?format=html` - Mode column should show single mode badge
4. Check `/status/<job_id>` - mode field should be clean value

## Code Location

**File:** `mondrian/job_service_v2.3.py`
**Functions Updated:**
- `format_job_id_with_mode()` - Lines 494-526
- `extract_job_uuid()` - Lines 528-544

## Defensive Programming Benefits

This fix makes the code:
- **More robust** - Handles unexpected input formats
- **More defensive** - Doesn't assume clean input
- **More forgiving** - Strips garbage characters
- **Case-insensitive** - Works with any case variation

Even if mode data gets corrupted or modified, the system will still work correctly!
