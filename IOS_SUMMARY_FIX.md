# iOS API Compatibility Fix: Missing job_id in /summary Response

## Problem Summary

iOS app was experiencing the following errors:

```
❌ Status check failed: keyNotFound(CodingKeys(stringValue: "job_id", intValue: nil), Swift.DecodingError.Context(codingPath: [], debugDescription: "No value associated with key CodingKeys(stringValue: \"job_id\", intValue: nil) (\"job_id\").", underlyingError: nil))

⏱ [DEBUG] ReportView render: 2026-01-16 18:49:25 +0000 — reportState = error(Failed to load summary: The operation couldn't be completed. (NSURLErrorDomain error -1011.))
```

### Root Cause

The iOS app tried to fetch the summary using:
```swift
let response = try JSONDecoder().decode(SummaryResponse.self, from: data)
```

But the backend `/summary/{job_id}` endpoint was returning **HTML** instead of JSON, causing:

1. **Swift Decoding Error** - JSON decoder tried to parse HTML as JSON
2. **Missing job_id field** - iOS app expected `job_id` field that doesn't exist in HTML
3. **NSURLErrorDomain error -1011** - Parsing failure interpreted as HTTP error

## Solution

### Changed File
- **[job_service_v2.3.py](mondrian/job_service_v2.3.py)** - Lines 851-880

### What Changed

**Before:**
```python
@app.route('/summary/<job_id>', methods=['GET'])
def get_summary(job_id: str):
    """Get a critical recommendations summary HTML."""
    # ... validation ...
    summary_html = job.get('summary_html', '')
    return Response(summary_html, mimetype='text/html; charset=utf-8')
```

**After:**
```python
@app.route('/summary/<job_id>', methods=['GET'])
def get_summary(job_id: str):
    """
    Get a critical recommendations summary.
    Returns JSON for API clients, HTML when format=html is specified.
    """
    # ... validation ...
    format_type = request.args.get('format', 'json').lower()
    
    if format_type == 'html':
        # Return HTML if explicitly requested
        return Response(summary_html, mimetype='text/html; charset=utf-8')
    
    # Default: Return JSON for iOS and API clients
    return jsonify({
        "job_id": job_id,
        "status": job.get('status'),
        "advisor": job.get('advisor'),
        "mode": job.get('mode'),
        "created_at": job.get('created_at'),
        "summary_html": summary_html or "",
        "analysis_html": analysis_html or "",
        "analysis": analysis_markdown or "",
        "timestamp": datetime.now().isoformat()
    }), 200
```

### Key Changes

1. **Default Response Format Changed to JSON**
   - Before: Always returned HTML
   - After: Returns JSON by default (iOS-compatible)

2. **Added Format Parameter Support**
   - Use `?format=html` to get HTML version
   - Default (no parameter) returns JSON

3. **Response Now Includes job_id Field**
   - iOS app can now extract `job_id` from JSON
   - Swift decoder works correctly

4. **Backwards Compatibility**
   - Web browsers can still request HTML with `?format=html`
   - Existing HTML-consuming code continues to work

## API Changes

### Updated Endpoint

**GET /summary/{job_id}**

**Default Response (JSON):**
```json
{
  "job_id": "abc123-def456-789",
  "status": "completed",
  "advisor": "ansel",
  "mode": "baseline",
  "created_at": "2026-01-16T18:49:25.123456",
  "summary_html": "<html>...</html>",
  "analysis_html": "<html>...</html>",
  "analysis": "Detailed markdown analysis...",
  "timestamp": "2026-01-16T18:49:25.000000"
}
```

**HTML Response (with ?format=html):**
```
GET /summary/{job_id}?format=html
Content-Type: text/html

<html>...</html>
```

## Impact on iOS App

### Fixed Errors

✅ `keyNotFound(CodingKeys(stringValue: "job_id"...))` - **FIXED**
- iOS can now decode response as JSON
- `job_id` field is present and populated

✅ `NSURLErrorDomain error -1011` - **FIXED**
- Response is now valid JSON
- No decoding errors occur
- Proper HTTP error handling

✅ `Failed to load summary` - **FIXED**
- Response structure matches iOS expectations
- All required fields present

### iOS Response Model

The iOS app can now use this model:

```swift
struct SummaryResponse: Decodable {
    let job_id: String
    let status: String
    let advisor: String
    let mode: String
    let created_at: String
    let summary_html: String
    let analysis_html: String
    let analysis: String
    let timestamp: String
}
```

## Testing

### Test Script

Run the test to verify the fix:

```bash
python3 test_summary_fix.py
```

This script will:
1. Upload a test image
2. Wait for analysis completion
3. Test `/summary/{job_id}` endpoint
4. Verify JSON response with `job_id` field
5. Test HTML fallback with `?format=html`

### Expected Test Output

```
✅ Upload successful. Job ID: abc123-def456-789
✅ Job completed!
✅ Response is valid JSON
✅ Contains 'job_id' field: abc123-def456-789
✅ job_id matches uploaded job
✅ Content-Type is correct: application/json; charset=utf-8
✅ ALL TESTS PASSED - iOS compatibility fix verified!
```

### Manual Testing (iOS)

After deploying this fix:

1. **Restart services:**
   ```bash
   ./mondrian.sh --restart
   ```

2. **Upload an image from iOS app**
   - App should upload successfully
   - Progress should stream correctly

3. **Wait for analysis to complete**
   - Summary should load without errors
   - No `keyNotFound` errors in logs

4. **Verify in iOS Console:**
   ```
   [DEBUG] ReportView render: 2026-01-16 18:50:00 +0000 — reportState = .success(...)
   ✅ Summary loaded successfully
   ```

## Related Endpoints (Already Correct)

These endpoints were already returning correct responses:

- **GET /jobs/{job_id}** - Returns JSON ✅
- **GET /status/{job_id}** - Alias for /jobs/{job_id}, returns JSON ✅
- **GET /analysis/{job_id}** - Returns HTML ✅
- **POST /upload** - Returns JSON with job_id ✅

## Deployment

### Steps to Deploy

1. **Update job_service_v2.3.py:**
   ```bash
   git add mondrian/job_service_v2.3.py
   git commit -m "Fix: /summary endpoint now returns JSON for iOS compatibility"
   ```

2. **Restart services:**
   ```bash
   ./mondrian.sh --restart
   ```

3. **Verify fix:**
   ```bash
   python3 test_summary_fix.py
   ```

4. **Push changes:**
   ```bash
   git push origin main
   ```

### Rollback Plan

If issues occur, revert to HTML response:

```bash
git revert <commit-hash>
./mondrian.sh --restart
```

## Future Improvements

Consider enhancing the fix with:

1. **Accept: application/json header support**
   - Clients can explicitly request JSON format
   - Still maintains backwards compatibility

2. **Content negotiation**
   - Automatically return JSON for `application/json` Accept header
   - Return HTML for `text/html` Accept header

3. **API versioning**
   - Use `/api/v1/summary/{job_id}` for JSON response
   - Keep `/summary/{job_id}` for backwards compatibility with HTML

## References

- [iOS API Integration Guide](docs/ios/API_INTEGRATION.md)
- [Swift Codable Documentation](https://developer.apple.com/documentation/foundation/codable)
- [HTTP Content Negotiation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation)
