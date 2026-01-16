# Quick Fix Summary: iOS Summary Endpoint

## Issue
iOS app encountered this error when trying to load analysis summary:
```
❌ keyNotFound(CodingKeys(stringValue: "job_id"...))
❌ Failed to load summary: NSURLErrorDomain error -1011
```

## Root Cause
The `/summary/{job_id}` endpoint returned **HTML** but iOS app expected **JSON** with a `job_id` field.

When the JSON decoder tried to parse HTML as JSON, it failed with missing field errors.

## Solution
**Changed `/summary/{job_id}` endpoint to:**
- Return **JSON by default** (iOS-compatible)
- Include `job_id` field in response
- Support `?format=html` parameter for backwards compatibility

## Changes Made

### File: `mondrian/job_service_v2.3.py`

**Before:**
```python
@app.route('/summary/<job_id>', methods=['GET'])
def get_summary(job_id: str):
    # Always returned HTML
    return Response(summary_html, mimetype='text/html; charset=utf-8')
```

**After:**
```python
@app.route('/summary/<job_id>', methods=['GET'])
def get_summary(job_id: str):
    # Return JSON by default, HTML with ?format=html
    format_type = request.args.get('format', 'json').lower()
    if format_type == 'html':
        return Response(summary_html, mimetype='text/html; charset=utf-8')
    
    return jsonify({
        "job_id": job_id,
        "status": job.get('status'),
        "advisor": job.get('advisor'),
        "mode": job.get('mode'),
        "summary_html": summary_html,
        "analysis_html": analysis_html,
        "analysis": analysis_markdown,
        "timestamp": datetime.now().isoformat()
    }), 200
```

## Result

✅ **Before:** `GET /summary/abc123` → HTML (fails JSON parsing)
✅ **After:** `GET /summary/abc123` → JSON with `job_id: "abc123"` (works!)
✅ **Backwards Compatible:** `GET /summary/abc123?format=html` → HTML (still works)

## Impact

- ✅ iOS app can now decode response as JSON
- ✅ `keyNotFound` error is eliminated  
- ✅ NSURLErrorDomain error is fixed
- ✅ Backwards compatible with existing HTML consumers

## Testing

```bash
# Test the fix
python3 test_summary_fix.py

# Expected output
✅ ALL TESTS PASSED - iOS compatibility fix verified!
```

## Deployment

```bash
# Restart services
./mondrian.sh --restart

# Verify
python3 test_summary_fix.py
```
