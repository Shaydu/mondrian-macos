# 500 Error Fix - Error Details Instead of Generic HTML

## Problem
The `ai_advisor_service.py` was returning generic Flask 500 HTML error pages instead of detailed error information:

```html
<!doctype html>
<html lang=en>
<title>500 Internal Server Error</title>
<h1>Internal Server Error</h1>
<p>The server encountered an internal error and was unable to complete your request.</p>
```

This made it impossible to debug issues when the `/analyze` endpoint failed.

## Solution Implemented

### 1. Global Flask Error Handler
Added a global error handler in `ai_advisor_service.py` after Flask app initialization (line ~92-109):

```python
@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler that returns JSON error details instead of HTML"""
    import traceback
    error_trace = traceback.format_exc()
    print(f"[ERROR] ========================================")
    print(f"[ERROR] Unhandled exception in Flask app:")
    print(f"[ERROR] {e}")
    print(f"[ERROR] {error_trace}")
    print(f"[ERROR] ========================================")
    
    return jsonify({
        "error": str(e),
        "type": type(e).__name__,
        "traceback": error_trace
    }), 500
```

**Effect**: Any unhandled exception in the Flask app now returns JSON with:
- Error message
- Exception type
- Full traceback

### 2. Try-Except Wrapper on _analyze_image Function
Wrapped the entire `_analyze_image()` function (line ~583-750) with a try-except block that:

- Executes all analysis logic inside a try block
- Catches any exception and returns a structured JSON error response
- Includes detailed context (job_id, advisor, image_path)
- Logs the full traceback to stdout for debugging

```python
def _analyze_image(advisor, abs_image_path, job_id, job_service_url, enable_rag=False):
    """Common analysis logic shared by both endpoints"""
    try:
        # ... all analysis logic here ...
        return Response(html_output, mimetype="text/html")
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        # ... detailed logging ...
        return jsonify({
            "error": str(e),
            "type": type(e).__name__,
            "job_id": job_id,
            "advisor": advisor,
            "image_path": abs_image_path,
            "traceback": error_trace
        }), 500
```

**Effect**: If any step of the analysis fails, the client receives:
```json
{
  "error": "Error message here",
  "type": "ExceptionType",
  "job_id": "abc-123",
  "advisor": "ansel",
  "image_path": "/path/to/image.jpg",
  "traceback": "Full Python traceback..."
}
```

## Testing the Fix

### 1. Start Services
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 start_services.py --restart
```

### 2. Test with Correct Request (Success Case)
```bash
curl -X POST http://localhost:5100/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "advisor": "ansel",
    "image_path": "/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/af.jpg",
    "enable_rag": false
  }' -v
```

**Expected**: HTML response with analysis (status 200)

### 3. Test with Invalid Advisor (Error Case)
```bash
curl -X POST http://localhost:5100/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "advisor": "invalid_advisor",
    "image_path": "/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/af.jpg",
    "enable_rag": false
  }' -v | python3 -m json.tool
```

**Expected**: JSON error response with type, message, and traceback

### 4. Test with Missing Image (Error Case)
```bash
curl -X POST http://localhost:5100/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "advisor": "ansel",
    "image_path": "/nonexistent/path/image.jpg",
    "enable_rag": false
  }' -v | python3 -m json.tool
```

**Expected**: JSON error response with 404 or detailed error

### 5. Test /health Endpoint
```bash
curl http://localhost:5100/health | python3 -m json.tool
```

**Expected**: JSON health response (unchanged)

## Benefits

1. **Debugging**: Full Python traceback instead of generic HTML
2. **Machine-Readable**: JSON responses can be parsed by client applications
3. **Context**: Error response includes job_id, advisor, image_path for correlation
4. **Logging**: All errors are logged to stdout for service monitoring
5. **Backwards Compatible**: Normal success responses still return HTML for iOS app

## Files Modified

- `/Users/shaydu/dev/mondrian-macos/mondrian/ai_advisor_service.py`
  - Lines ~92-109: Added global Flask error handler
  - Lines ~583-750: Wrapped _analyze_image with try-except block

## Next Steps

If you still see 500 errors after restarting services:

1. Check the service logs:
   ```bash
   tail -100 /Users/shaydu/dev/mondrian-macos/logs/ai_advisor_out.log
   tail -100 /Users/shaydu/dev/mondrian-macos/logs/ai_advisor_err.log
   ```

2. Make a test request and capture the JSON error response to understand what failed

3. The traceback in the JSON response will show exactly where the failure occurred






