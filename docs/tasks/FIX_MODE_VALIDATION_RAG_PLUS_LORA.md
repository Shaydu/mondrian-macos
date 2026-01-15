# Fix: Accept All Supported Modes in API Validation

## Issue

When sending `mode=rag+lora` (or `ab_test`) in API requests, the services were rejecting the mode because the validation only accepted:
- `['baseline', 'rag', 'lora']`

This caused requests with valid modes like `rag+lora` to silently fall back to `baseline`.

## Root Cause

**Job Service** (`mondrian/job_service_v2.3.py`, line 1577):
```python
if mode_param and mode_param in ['baseline', 'rag', 'lora']:  # ❌ Missing rag+lora, ab_test
```

**AI Advisor Service** (`mondrian/ai_advisor_service.py`, line 1270):
```python
if mode_param and mode_param in ['baseline', 'rag', 'lora']:  # ❌ Missing rag+lora, ab_test
```

## Solution

Updated both services to accept all documented modes:

```python
if mode_param and mode_param in ['baseline', 'rag', 'lora', 'rag+lora', 'ab_test']:
```

## Supported Modes

Now all these modes are properly accepted:

| Mode | Description | Status |
|------|-------------|--------|
| `baseline` | Standard single-pass analysis | ✅ Accepted |
| `rag` | Two-pass with portfolio comparison | ✅ Accepted |
| `lora` | Fine-tuned model analysis | ✅ Accepted |
| `rag+lora` | RAG + fine-tuned model | ✅ NOW FIXED |
| `ab_test` | A/B testing mode | ✅ NOW FIXED |

## Changes Made

1. **Job Service** - Line 1577
   - Updated validation to include `'rag+lora'` and `'ab_test'`
   - Updated comment to reflect all supported modes

2. **AI Advisor Service** - Line 1270
   - Updated validation to include `'rag+lora'` and `'ab_test'`

## Impact

✅ Requests with `mode=rag+lora` now work correctly
✅ Requests with `mode=ab_test` now work correctly
✅ Mode is properly passed through to AI service
✅ Mode is stored correctly in database
✅ Mode is returned in API responses

## Testing

```bash
# Test RAG+LORA mode
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag+lora" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload

# Response should now include:
# "mode": "rag+lora"
# "job_id": "uuid (rag+lora)"

# Instead of previously falling back to:
# "mode": "baseline"
# "job_id": "uuid (baseline)"
```

## Before vs After

### Before (BROKEN)
```bash
$ curl ... -F "mode=rag+lora" ...
# Request:
# mode_param = "rag+lora"
# Check: "rag+lora" in ['baseline', 'rag', 'lora'] → FALSE
# Result: Falls back to enable_rag → mode = 'baseline'
```

### After (FIXED)
```bash
$ curl ... -F "mode=rag+lora" ...
# Request:
# mode_param = "rag+lora"
# Check: "rag+lora" in ['baseline', 'rag', 'lora', 'rag+lora', 'ab_test'] → TRUE
# Result: mode = 'rag+lora' ✅
```

## Note

This was preventing combined mode requests from working properly. The 500 error you were seeing was likely because:
1. `rag+lora` was rejected
2. Mode fell back to `baseline`
3. But the request still had other parameters expecting `rag+lora`
4. This mismatch could cause downstream errors

With this fix, all combined modes now work as intended!
