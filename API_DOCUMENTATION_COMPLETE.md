# API Documentation Complete - Mode Information Added

## What Was Done

Comprehensive API documentation has been created in `docs/API.md` with complete information about retrieving the analysis mode (`baseline`, `rag`, `lora`, `rag+lora`, `ab_test`) from all API endpoints.

## Documentation Location

📍 **`docs/API.md`** - Complete Mondrian API Reference

## Key Sections Added

### 1. **Analysis Modes Section**
- Overview of all 5 supported modes
- Mode comparison table (speed, detail, passes, portfolio, model)
- When to use each mode

### 2. **Mode in API Responses**
- Summary table showing where mode is available
- How to extract mode from each endpoint

### 3. **Endpoint Documentation with Mode**

#### `/upload` - Upload & Queue
- Mode parameter accepted
- Returns mode in job_id suffix: `"uuid (rag)"`

#### `/status/<job_id>` ✨ BEST FOR MODE
- **Explicit `mode` field** (recommended for iOS)
- **Explicit `enable_rag` field**
- Easy JSON parsing: `response.mode`

#### `/analyze` - Direct Analysis
- Mode in `metadata.mode_used`
- Also returns `metadata.requested_mode` and `metadata.effective_mode`
- Shows if fallback occurred

#### `/analysis/<job_id>` - HTML
- Mode badge embedded in HTML
- Color-coded by mode (Blue/Brown/Green/Purple)

#### `/job/<job_id>/full-data` - Complete Data
- Mode in response
- Enable_rag flag
- Per-advisor mode_used in llm_outputs

### 4. **Code Examples**

#### Python
```python
def get_analysis_mode(job_id):
    response = requests.get(f'http://localhost:5005/status/{job_id}')
    status = response.json()
    mode = status['mode']  # Direct field
    return mode
```

#### Swift (iOS)
```swift
struct JobStatus: Codable {
    let job_id: String
    let mode: String         // ✨ Direct access
    let enable_rag: Bool     // ✨ Direct access
    let status: String
}

let status = try await getJobStatus(jobId: jobId)
print("Mode: \(status.mode)")
```

#### Bash/cURL
```bash
# Get mode from /status endpoint
curl http://localhost:5005/status/UUID | jq '.mode'

# Get complete data
curl http://localhost:5005/job/UUID/full-data | jq '.mode'
```

### 5. **Best Practices**

✅ **DO:**
- Use explicit `mode` field from `/status` endpoint
- Check both `mode` and `enable_rag` fields
- Poll status at reasonable intervals (2-5 seconds)
- Save mode with analysis results

❌ **DON'T:**
- Parse mode from job_id string when explicit field exists
- Assume mode implies RAG is enabled
- Poll too frequently
- Ignore fallback information

## API Endpoints Summary

| Endpoint | Mode Available | Field Name | Format |
|----------|---------------|-----------:---------|
| `/upload` | ✓ | job_id suffix | "(rag)" |
| **`/status`** | ✓ | **mode** | "rag" |
| `/analyze` | ✓ | metadata.mode_used | "rag" |
| `/analysis` | ✓ | HTML badge | Visual |
| `/job/.../full-data` | ✓ | mode | "rag" |

## Complete Workflow Example

```bash
# 1. Upload with mode
curl -F "file=@image.jpg" -F "advisor=ansel" -F "mode=rag" http://localhost:5005/upload

# 2. Check status with explicit mode field
curl http://localhost:5005/status/UUID | jq '{mode, enable_rag, progress_percentage, status}'

# Response:
# {
#   "mode": "rag",
#   "enable_rag": true,
#   "progress_percentage": 45,
#   "status": "analyzing"
# }

# 3. Get analysis HTML with mode badge
curl http://localhost:5005/analysis/UUID > analysis.html

# 4. Archive with mode info
curl http://localhost:5005/job/UUID/full-data | jq '.mode'
```

## Client Integration Quick Start

### For iOS Developers

1. **Parse mode from `/status` endpoint:**
   ```swift
   let mode = statusResponse.mode  // Direct field access
   ```

2. **Check RAG flag:**
   ```swift
   if statusResponse.enable_rag {
       // Show RAG comparison UI
   }
   ```

3. **Display mode badge:**
   ```swift
   switch statusResponse.mode {
   case "baseline": showBlueBadge()
   case "rag": showBrownBadge()
   case "lora": showGreenBadge()
   default: showDefaultBadge()
   }
   ```

### For Web Developers

1. **Fetch mode during polling:**
   ```javascript
   const response = await fetch(`/status/${jobId}`);
   const data = await response.json();
   console.log(`Mode: ${data.mode}`);
   ```

2. **Display mode indicator:**
   ```html
   <div class="mode-badge" data-mode="${data.mode}">
       ${data.mode.toUpperCase()}
   </div>
   ```

### For Backend Developers

1. **Store mode with analysis:**
   ```python
   analysis = {
       'mode': response['mode'],
       'enable_rag': response['enable_rag'],
       'results': response['llm_outputs']
   }
   ```

2. **Track analytics:**
   ```python
   analytics.log({
       'event': 'analysis_completed',
       'mode': response['mode'],
       'duration': (completed - started).seconds
   })
   ```

## Documentation Structure

```
docs/API.md
├── Overview
│   ├── Services
│   └── Supported Modes
├── Authentication & Base URLs
├── Core Endpoints
│   ├── /upload (with mode parameter)
│   ├── /status (with explicit mode field) ✨
│   ├── /analyze (with metadata)
│   ├── /analysis (with badge)
│   ├── /job/.../full-data (with complete data)
│   └── /stream (with SSE events)
├── Analysis Modes
│   ├── Mode comparison table
│   └── When to use each mode
├── Mode in API Responses ✨ NEW
│   ├── Summary table
│   └── Extraction by endpoint
├── Examples (Python, Swift, Bash)
├── Error Responses
├── Best Practices
└── Support Resources
```

## Key Features

✅ **Complete Coverage**
- All 5 endpoints documented
- All 5 modes explained
- Multiple programming languages

✅ **Mode-Specific Information**
- Where to find mode in each endpoint
- How to extract mode
- Code examples for each language

✅ **Practical Examples**
- Real cURL commands
- Python implementation
- Swift for iOS
- Error handling

✅ **Best Practices**
- What to do
- What to avoid
- Rate limiting info

## Related Documentation

For additional mode information, see:
- `API_MODE_RESPONSE_GUIDE.md` - Detailed API responses
- `MODE_DATA_AVAILABILITY_QUICK_REF.md` - Quick reference
- `LORA_BADGE_VISUAL_GUIDE.md` - Badge colors and meanings
- `MODE_VERIFICATION_GUIDE.md` - Debug markers for verification

## Testing the Documentation

```bash
# Verify all endpoints return mode
bash -c '
for endpoint in "/status/UUID" "/job/UUID/full-data"; do
  curl "http://localhost:5005$endpoint" | jq ".mode"
done
'

# Test /status returns both mode and enable_rag
curl http://localhost:5005/status/UUID | jq "{mode, enable_rag}"
```

## Next Steps

1. **Use `/status` endpoint** for most mode retrieval
   - Most direct field access
   - No string parsing needed
   - Includes enable_rag flag

2. **Display mode badge** from `/analysis` endpoint
   - Shows analysis type visually
   - Color-coded for quick recognition

3. **Archive mode info** with analysis results
   - Store from `/job/.../full-data`
   - Use for analytics and comparison

4. **Update clients** to use explicit mode field
   - Old: Parse from job_id
   - New: Use response.mode directly

---

**Documentation Complete!** All API endpoints, modes, and client integration are now documented in `docs/API.md`. 📚

The documentation includes:
- ✅ All 5 endpoints with mode information
- ✅ Extracting mode from each endpoint
- ✅ Code examples in Python, Swift, and Bash
- ✅ Best practices and common mistakes
- ✅ Error handling information
- ✅ Complete workflow examples
