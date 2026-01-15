# API Request/Response Logging

## Overview

All API requests and responses are now automatically logged to the console when you run `./mondrian.sh`.

This logging is added via Flask `before_request` and `after_request` hooks in both services:
- **Job Service** (port 5005) - logs with `[API REQUEST]` and `[API RESPONSE]` tags
- **AI Advisor Service** (port 5100) - logs with `[AI SERVICE REQUEST]` and `[AI SERVICE RESPONSE]` tags

---

## What Gets Logged

### Request Logging

For every API request, you'll see:

```
[API REQUEST] POST /upload
[API REQUEST] Query: {} | Form: {'advisor': '<str>', 'mode': 'rag', 'auto_analyze': '<str>'} | Files: {'file': '<image.jpg>'}
```

**Logged Information:**
- ✅ HTTP method (GET, POST, PUT, DELETE, etc.)
- ✅ Endpoint path (/upload, /status, /analyze, etc.)
- ✅ **Query parameters** - From URL query string
- ✅ **Form parameters** - All form fields (with special logging for `mode`)
- ✅ **JSON body** - For JSON requests
- ✅ **File uploads** - Filename (not content)

### Response Logging

For every API response, you'll see:

```
[API RESPONSE] ✅ 201 POST /upload

[API RESPONSE] ✅ 200 GET /status/550e8400-e29b-41d4-a716-446655440000

[API RESPONSE] ❌ 400 POST /upload

[API RESPONSE] ⚠️ 500 POST /analyze
```

**Status Code Colors:**
- ✅ 2xx Success (green checkmark)
- ↪️ 3xx Redirect (arrow)
- ❌ 4xx Client Error (red X)
- ⚠️ 5xx Server Error (warning)

---

## Example Log Output

When you run `./mondrian.sh` and make requests, you'll see:

```bash
$ ./mondrian.sh

====================================================================================================
[API REQUEST] POST /upload
[API REQUEST] Query: {} | Form: {'advisor': 'ansel', 'mode': 'rag', 'auto_analyze': 'true'} | Files: {'file': '<photo.jpg>'}
====================================================================================================

[API RESPONSE] ✅ 201 POST /upload

====================================================================================================
[API REQUEST] GET /status/550e8400-e29b-41d4-a716-446655440000
[API REQUEST] Query: {} | No parameters
====================================================================================================

[API RESPONSE] ✅ 200 GET /status/550e8400-e29b-41d4-a716-446655440000

====================================================================================================
[AI SERVICE REQUEST] POST /analyze
[AI SERVICE REQUEST] Form: {'advisor': 'ansel', 'mode': 'rag', 'job_id': '<uuid>', 'enable_rag': 'false'}
====================================================================================================

[AI SERVICE RESPONSE] ✅ 200 POST /analyze
```

---

## Mode Parameter Logging

The `mode` parameter is **always logged explicitly**, even if other parameters are hidden:

### Job Service Logs

```
[API REQUEST] POST /upload
[API REQUEST] Form: {'advisor': 'ansel', 'mode': 'rag', 'auto_analyze': '<str>'}
```

Notice: `mode: 'rag'` is shown in full, while other parameters show type hints.

### AI Service Logs

```
[AI SERVICE REQUEST] POST /analyze
[AI SERVICE REQUEST] Form: {'advisor': 'ansel', 'mode': 'lora', 'job_id': '<uuid>', 'enable_rag': 'false'}
```

This makes it easy to verify which analysis mode is being used.

---

## How to Use the Logs

### 1. Verify Mode is Being Sent

```bash
./mondrian.sh &

# In another terminal:
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload

# Look for in terminal:
# [API REQUEST] Form: {'advisor': 'ansel', 'mode': 'rag', ...}
```

### 2. Debug API Issues

If an endpoint returns an error, check the logs to see:
- What parameters were sent
- Which endpoint was called
- What status code was returned

```bash
# If upload fails with 400:
[API RESPONSE] ❌ 400 POST /upload

# Check what parameters were sent to debug the issue
[API REQUEST] POST /upload
[API REQUEST] Form: {'advisor': 'invalid_advisor', 'mode': 'rag', ...}
```

### 3. Monitor Flow Through Services

Watch requests travel between services:

```
Terminal 1 (Job Service on 5005):
[API REQUEST] POST /upload
[API RESPONSE] ✅ 201 POST /upload

Terminal 2 (AI Service on 5100):
[AI SERVICE REQUEST] POST /analyze
[AI SERVICE RESPONSE] ✅ 200 POST /analyze
```

---

## Implementation Details

### Job Service (mondrian/job_service_v2.3.py)

```python
@app.before_request
def log_request_details():
    """Log incoming API request details"""
    method = request.method
    endpoint = request.path
    
    # Extract parameters from query, form, JSON, files
    # Log with proper formatting
    print(f"[API REQUEST] {method} {endpoint}")
    print(f"[API REQUEST] {params_str}")

@app.after_request
def log_response_details(response):
    """Log outgoing API response status"""
    status_code = response.status_code
    # Status code colored with emoji
    print(f"[API RESPONSE] {status_label} {status_code} {method} {endpoint}")
```

### AI Advisor Service (mondrian/ai_advisor_service.py)

Same structure but prefixed with `[AI SERVICE REQUEST]` and `[AI SERVICE RESPONSE]`.

---

## What's NOT Logged

For security and performance:
- ❌ Image file contents
- ❌ Sensitive data (passwords, tokens)
- ❌ Large JSON payloads (just logged as `<json>`)
- ❌ Binary data

---

## Customization

### To Change Log Level

Edit the Flask app initialization:

```python
# In job_service_v2.3.py or ai_advisor_service.py

@app.before_request
def log_request_details():
    # Can add verbosity level check:
    if os.getenv("LOG_LEVEL", "INFO") == "DEBUG":
        # Log everything
    else:
        # Log only critical endpoints
```

### To Filter by Endpoint

```python
@app.before_request
def log_request_details():
    if request.path == "/upload":  # Only log upload
        print(f"[API REQUEST] {request.method} {request.path}")
```

---

## Logs Files

These logs print to stdout/stderr. To capture to file:

```bash
# Redirect all output to log file
./mondrian.sh > mondrian.log 2>&1

# Or use tee to see and save
./mondrian.sh 2>&1 | tee mondrian.log

# Follow logs in real-time
tail -f mondrian.log
```

---

## Example: Full Request/Response Cycle

```bash
$ ./mondrian.sh

# Client makes upload request:
curl -F "file=@photo.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload

# Output in Job Service terminal:
====================================================================================================
[API REQUEST] POST /upload
[API REQUEST] Query: {} | Form: {'advisor': 'ansel', 'mode': 'rag', 'auto_analyze': 'true'} | Files: {'file': '<photo.jpg>'}
====================================================================================================

[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Job ID: 550e8400-e29b-41d4-a716-446655440000
[UPLOAD] Mode: rag
[UPLOAD] Enable RAG: False
[UPLOAD] Advisors: ['ansel']
[UPLOAD] =====================================

[API RESPONSE] ✅ 201 POST /upload

# Then background job processes:
[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Job ID: 550e8400-e29b-41d4-a716-446655440000
[JOB] Mode: rag
[JOB] Flow: RAG + DEFAULT MODEL
[JOB] ====================================

# Job Service calls AI Service:
====================================================================================================
[AI SERVICE REQUEST] POST /analyze
[AI SERVICE REQUEST] Form: {'advisor': 'ansel', 'mode': 'rag', 'job_id': '550e8400-e29b-41d4-a716-446655440000', 'enable_rag': 'false'}
====================================================================================================

[STRATEGY] ========== ANALYSIS STARTED ==========
[STRATEGY] Mode: rag
[STRATEGY] Advisor: ansel
[STRATEGY] ==========================================

[RAG] ========== RAG ANALYSIS STARTED (2-PASS) ==========
[RAG] Flow: Two-pass RAG with dimensional comparison
[RAG] ========================================================

[STRATEGY] ✓ Analysis complete. Overall grade: 8/10
[STRATEGY] ✓ Mode used in result: rag

[AI SERVICE RESPONSE] ✅ 200 POST /analyze

# Client polls status:
curl http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000

# Output:
====================================================================================================
[API REQUEST] GET /status/550e8400-e29b-41d4-a716-446655440000
[API REQUEST] Query: {} | No parameters
====================================================================================================

[API RESPONSE] ✅ 200 GET /status/550e8400-e29b-41d4-a716-446655440000
```

---

## Debugging Common Issues

### Issue: Mode not being sent

Look for in logs:
```
[API REQUEST] Form: {'advisor': 'ansel', 'mode': 'baseline', 'auto_analyze': 'true'}
```

If `mode` is missing:
- Client isn't sending it
- Default 'baseline' will be used

### Issue: Wrong mode being used

Check request vs result:
```
# Request shows:
[API REQUEST] Form: {'mode': 'rag', ...}

# Response shows:
[API RESPONSE] ✅ 201 ...
{"mode": "lora", ...}  ← MISMATCH!
```

### Issue: Service not responding

Check for missing response log:
```
[API REQUEST] POST /analyze
# ... (no response log)
```

If no response log appears, service likely crashed or timed out.

---

## Performance Impact

Logging has minimal performance impact:
- String formatting is lightweight
- Only basic print() calls
- No file I/O (unless redirected)
- Disabled for large request bodies

---

**All API logging is now active in `./mondrian.sh`!** 🚀
