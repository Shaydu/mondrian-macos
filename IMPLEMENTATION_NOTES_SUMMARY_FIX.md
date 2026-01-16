# Implementation Notes: iOS API Compatibility Fix

## Problem Statement

The iOS app was unable to parse the `/summary/{job_id}` endpoint response, resulting in:
- Swift `DecodingError: keyNotFound` for `job_id` field
- `NSURLErrorDomain error -1011` (HTTP parsing error)
- "Failed to load summary" error in UI

The root cause was that the endpoint returned HTML while the iOS app expected JSON.

## Technical Details

### Error Flow (Before Fix)

1. **iOS App Code:**
   ```swift
   let response = try await URLSession.shared.data(from: summaryURL)
   let summary = try JSONDecoder().decode(SummaryResponse.self, from: response)
   // ❌ Error: keyNotFound(job_id)
   ```

2. **Backend Response:**
   ```
   Content-Type: text/html; charset=utf-8
   <html>
     <head>...</head>
     <body>...</body>
   </html>
   ```

3. **JSON Decoder Attempts to Parse HTML**
   - HTML is not valid JSON
   - Missing `job_id` key
   - Throws `keyNotFound` error

### Error Flow (After Fix)

1. **iOS App Code:**
   ```swift
   let response = try await URLSession.shared.data(from: summaryURL)
   let summary = try JSONDecoder().decode(SummaryResponse.self, from: response)
   // ✅ Success: SummaryResponse(job_id: "abc123", ...)
   ```

2. **Backend Response:**
   ```
   Content-Type: application/json; charset=utf-8
   {
     "job_id": "abc123-def456-789",
     "status": "completed",
     "advisor": "ansel",
     "mode": "baseline",
     "created_at": "2026-01-16T18:49:25.123456",
     "summary_html": "<html>...</html>",
     "analysis_html": "<html>...</html>",
     "analysis": "Detailed markdown...",
     "timestamp": "2026-01-16T18:49:25.000000"
   }
   ```

3. **JSON Decoder Parses Successfully**
   - Valid JSON structure
   - All required fields present
   - iOS app receives complete data

## Implementation Details

### Endpoint Changes

**Route:** `GET /summary/{job_id}`

**Default Behavior (JSON):**
- Request: `GET /summary/abc123`
- Response: `200 OK` with JSON body
- Content-Type: `application/json; charset=utf-8`

**Legacy Behavior (HTML):**
- Request: `GET /summary/abc123?format=html`
- Response: `200 OK` with HTML body
- Content-Type: `text/html; charset=utf-8`

### JSON Response Structure

```json
{
  "job_id": "string - UUID of the analysis job",
  "status": "string - 'completed', 'pending', 'analyzing', etc.",
  "advisor": "string - 'ansel', 'okeefe', etc.",
  "mode": "string - 'baseline' or 'rag'",
  "created_at": "string - ISO 8601 timestamp when job was created",
  "summary_html": "string - HTML summary view",
  "analysis_html": "string - Full HTML analysis",
  "analysis": "string - Markdown analysis text",
  "timestamp": "string - ISO 8601 timestamp of response"
}
```

### Code Implementation

```python
@app.route('/summary/<job_id>', methods=['GET'])
def get_summary(job_id: str):
    """
    Get a critical recommendations summary.
    Returns JSON for API clients, HTML when format=html is specified.
    """
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    job = job_db.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if job['status'] != 'completed':
        return jsonify({"error": "Job not completed"}), 400
    
    # Check if requesting HTML format explicitly
    format_type = request.args.get('format', 'json').lower()
    
    if format_type == 'html':
        summary_html = job.get('summary_html', '')
        if not summary_html:
            return jsonify({"error": "No summary available"}), 404
        
        return Response(
            summary_html,
            mimetype='text/html; charset=utf-8',
            headers={'Cache-Control': 'no-cache'}
        )
    
    # Default: return JSON for iOS and API clients
    summary_html = job.get('summary_html', '')
    analysis_html = job.get('analysis_html', '')
    analysis_markdown = job.get('analysis_markdown', '')
    
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

## Design Decisions

### 1. JSON as Default Format

**Why:** 
- iOS app expects JSON (Swift Codable)
- RESTful API best practice
- JSON is machine-readable and language-agnostic

**Alternative Considered:**
- Content-Type negotiation via Accept header
- Pros: More RESTful, standard practice
- Cons: More complex, iOS app would need updating

### 2. Backwards Compatibility with format=html

**Why:**
- Existing HTML consumers (web dashboards, scripts) continue to work
- No breaking changes to API contract
- Gradual migration path

**Usage:**
```
GET /summary/{job_id}                # Returns JSON (new default)
GET /summary/{job_id}?format=html    # Returns HTML (legacy)
```

### 3. Including Both HTML and Markdown

**Why:**
- iOS app can display HTML directly in WebView
- Markdown available for text-based views
- Provides flexibility to iOS developers

**Fields:**
- `summary_html`: Rendered HTML for UI display
- `analysis_html`: Full analysis in HTML format
- `analysis`: Raw markdown for parsing/re-rendering

## Testing Strategy

### Unit Tests
```python
def test_summary_json_default():
    """Default response should be JSON"""
    response = client.get('/summary/test-job-id')
    assert response.status_code == 200
    assert response.json['job_id'] == 'test-job-id'

def test_summary_html_format():
    """?format=html should return HTML"""
    response = client.get('/summary/test-job-id?format=html')
    assert response.status_code == 200
    assert 'text/html' in response.headers['Content-Type']
```

### Integration Tests
```bash
# Test JSON response
curl http://localhost:5005/summary/abc123

# Test HTML response
curl http://localhost:5005/summary/abc123?format=html
```

### iOS Integration Tests
```swift
// Verify JSON decoding works
let url = URL(string: "http://localhost:5005/summary/abc123")!
let data = try await URLSession.shared.data(from: url).0
let summary = try JSONDecoder().decode(SummaryResponse.self, from: data)
XCTAssertEqual(summary.job_id, "abc123")
```

## Performance Implications

**Minimal Impact:**
- Same database query (job retrieval)
- Slightly different response formatting (JSON vs HTML)
- No additional processing needed

**Response Size:**
- JSON: ~1-2 KB (metadata + HTML embedded)
- HTML: ~5-10 KB (full HTML)
- iOS app handles both efficiently

## Potential Issues and Solutions

### Issue 1: Client Caches Old Responses
**Solution:** Cloud Cache-Control headers already set
```python
headers={'Cache-Control': 'no-cache'}
```

### Issue 2: Clients Expect HTML Content-Type
**Solution:** Add diagnostic logging
```python
logger.info(f"Summary requested for {job_id}: format={format_type}, " +
            f"client={request.user_agent}")
```

### Issue 3: Network Bandwidth
**Solution:** Monitor response sizes in production
- Both formats are reasonable size
- No compression issues expected

## Monitoring and Logging

### Recommended Logging
```python
@app.before_request
def log_request():
    if '/summary' in request.path:
        logger.info(f"Summary request: {request.path}, " +
                   f"format={request.args.get('format', 'default')}, " +
                   f"user_agent={request.user_agent}")
```

### Metrics to Track
- JSON vs HTML request ratio
- Response times for each format
- Error rates per format

## Future Enhancements

### 1. Content Negotiation (Accept Header)
```python
accept_header = request.headers.get('Accept', 'application/json')
if 'application/json' in accept_header:
    return jsonify(...)
elif 'text/html' in accept_header:
    return Response(html, mimetype='text/html')
```

### 2. API Versioning
```
GET /api/v1/summary/{job_id}     # JSON only
GET /api/v2/summary/{job_id}     # JSON or HTML
GET /summary/{job_id}             # Legacy HTML
```

### 3. Compression
```python
from flask_compress import Compress
Compress(app)  # Auto-compress responses
```

## References

- Flask Request/Response: https://flask.palletsprojects.com/api/
- Swift Codable: https://developer.apple.com/documentation/foundation/codable
- HTTP Content Negotiation: https://developer.mozilla.org/en-US/docs/Web/HTTP/Content_negotiation
- RESTful API Best Practices: https://restfulapi.net/
