# Bytes-to-String Fix for TypeError

## Problem Discovered
After implementing the 500 error handler, we discovered the actual error:

```
TypeError: a bytes-like object is required, not 'str'
File: ai_advisor_service.py, line 669
Code: SYSTEM_PROMPT.replace("<AdvisorName>", advisor)
```

The issue was that `SYSTEM_PROMPT` and advisor prompts were being loaded from the SQLite database as **bytes** instead of **strings**.

## Root Cause
SQLite TEXT columns can sometimes return `bytes` objects instead of `str` objects depending on:
- How the data was originally inserted
- The SQLite connection configuration
- Python/SQLite driver version

## Solution Implemented

### 1. Fixed `get_config()` in `sqlite_helper.py` (Lines 137-153)
Added automatic bytes-to-string decoding:

```python
def get_config(db_path, key):
    """Get a configuration value from the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key=?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            value = row[0]
            # Decode bytes to string if needed
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            return value
        return None
    except Exception as e:
        print(f"[ERROR] Failed to get config {key}: {e}")
        return None
```

### 2. Fixed `get_advisor_from_db()` in `sqlite_helper.py` (Lines 197-209)
Added helper function to decode all values:

```python
# Helper function to decode bytes to string if needed
def decode_if_bytes(val):
    if isinstance(val, bytes):
        return val.decode('utf-8')
    return val

row_map = {col: decode_if_bytes(row[i]) for i, col in enumerate(select_cols)}
```

### 3. Added Safety Check in `ai_advisor_service.py` (Lines 119-122)
Added redundant check for SYSTEM_PROMPT:

```python
# Ensure SYSTEM_PROMPT is a string (decode if bytes)
if isinstance(SYSTEM_PROMPT, bytes):
    SYSTEM_PROMPT = SYSTEM_PROMPT.decode('utf-8')
    print(f"[INFO] System prompt decoded from bytes to string")
```

## Testing

### Before Fix
```bash
curl -X POST http://localhost:5100/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "advisor": "ansel",
    "image_path": "/path/to/image.jpg",
    "enable_rag": false
  }'
```

**Response (500 error)**:
```json
{
  "error": "a bytes-like object is required, not 'str'",
  "type": "TypeError",
  "traceback": "...SYSTEM_PROMPT.replace..."
}
```

### After Fix
Same request should now succeed with HTML analysis output (status 200).

## Files Modified

1. `/Users/shaydu/dev/mondrian-macos/mondrian/sqlite_helper.py`
   - Lines 137-153: Updated `get_config()` to decode bytes
   - Lines 197-209: Updated `get_advisor_from_db()` to decode bytes

2. `/Users/shaydu/dev/mondrian-macos/mondrian/ai_advisor_service.py`
   - Lines 119-122: Added safety check for SYSTEM_PROMPT

## Why This Fix Works

1. **Comprehensive**: Fixes the issue at the database layer, so all text data is properly decoded
2. **Safe**: Uses `isinstance()` check before decoding, so it won't break if data is already a string
3. **UTF-8**: Uses UTF-8 encoding which is standard for text data
4. **Defensive**: Multiple layers of protection (database layer + application layer)

## Related Issues Fixed

This fix also resolves potential bytes issues with:
- Advisor names
- Advisor bios
- Advisor years
- Focus areas (JSON strings)
- Category names
- URLs
- Any other TEXT columns in the database

## Next Steps

1. Restart services to apply the fix
2. Test image analysis with the batch script
3. All 12 images should now analyze successfully

## Prevention

To prevent this issue in the future when inserting data into SQLite:
- Always ensure strings are properly encoded as UTF-8 strings, not bytes
- Use `text_factory = str` on SQLite connections if needed:
  ```python
  conn = sqlite3.connect(db_path)
  conn.text_factory = str  # Force TEXT columns to return str
  ```



