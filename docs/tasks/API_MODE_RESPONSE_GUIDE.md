# API Response Documentation: Analysis Mode Information

## Summary

All major API endpoints now return analysis mode information (`baseline`, `rag`, `lora`, `rag+lora`, or `ab_test`).

## API Endpoints Returning Mode

### 1. **`/analyze` - Direct Analysis Endpoint**

**Request:**
```bash
POST /analyze
Content-Type: multipart/form-data

file=<image>
advisor=ansel
mode=rag
```

**Response:**
```json
{
  "html": "<div>...</div>",
  "mode_used": "rag",
  "metadata": {
    "mode_used": "rag",
    "requested_mode": "rag",
    "effective_mode": "rag",
    "fallback_occurred": false,
    "overall_grade": "A",
    "advisor_id": "ansel"
  }
}
```

### 2. **`/status/<job_id>` - Job Status Endpoint** ✨ NEW

**Request:**
```bash
GET /status/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag)",
  "filename": "image.jpg",
  "advisor": "ansel",
  "status": "done",
  "mode": "rag",
  "enable_rag": true,
  "current_step": "Completed",
  "progress_percentage": 100,
  "llm_thinking": "",
  "analysis_url": "http://localhost:5005/analysis/550e8400-e29b-41d4-a716-446655440000",
  "status_url": "http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000",
  "stream_url": "http://localhost:5005/stream/550e8400-e29b-41d4-a716-446655440000"
}
```

**New Fields Added:**
- `mode`: The analysis mode (baseline, rag, lora, etc.)
- `enable_rag`: Whether RAG was enabled

### 3. **`/job/<job_id>/full-data` - Complete Job Data**

**Request:**
```bash
GET /job/550e8400-e29b-41d4-a716-446655440000/full-data
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "image.jpg",
  "advisor": "ansel",
  "status": "done",
  "mode": "rag",
  "enable_rag": true,
  "prompt": "Analyze this image...",
  "prompt_length": 2048,
  "llm_outputs": {
    "ansel": {
      "composition": 8.5,
      "lighting": 7.5,
      "mode_used": "rag"
    }
  },
  "analysis_markdown": "<div>...</div>",
  "timestamps": {
    "created_at": "2026-01-14T10:30:00",
    "started_at": "2026-01-14T10:30:05",
    "completed_at": "2026-01-14T10:35:30"
  }
}
```

### 4. **`/upload` - File Upload**

**Request:**
```bash
POST /upload
Content-Type: multipart/form-data

file=<image>
advisor=ansel
mode=lora
enable_rag=false
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000 (lora)",
  "filename": "image.jpg",
  "advisor": "ansel",
  "advisors_used": ["ansel"],
  "status": "queued",
  "enable_rag": false,
  "status_url": "http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000",
  "stream_url": "http://localhost:5005/stream/550e8400-e29b-41d4-a716-446655440000"
}
```

### 5. **`/analysis/<job_id>` - Analysis HTML**

**Request:**
```bash
GET /analysis/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```html
<!DOCTYPE html>
<html>
<head>...</head>
<body>
  <div class="analysis">
    <!-- Mode badge renders here -->
    <div style="background: #3d5a3d; padding: 6px 12px;">
      LORA
    </div>
    
    <!-- Rest of analysis HTML -->
    <h2>Image Analysis</h2>
    ...
  </div>
</body>
</html>
```

**Mode Badge Colors:**
- `baseline`: Blue (#3d5a80)
- `rag`: Brown (#5a4a3d)
- `lora`: Green (#3d5a3d)
- `ab_test`: Purple (#5a3d5a)

## Mode Values Explained

| Mode | Meaning | RAG | LORA | Description |
|------|---------|-----|------|-------------|
| `baseline` | Standard | ✗ | ✗ | Single-pass analysis with base model |
| `rag` | RAG Only | ✓ | ✗ | Two-pass with portfolio comparison |
| `lora` | LoRA Only | ✗ | ✓ | Single-pass with fine-tuned model |
| `rag+lora` | RAG + LoRA | ✓ | ✓ | Two-pass with fine-tuned model |
| `ab_test` | A/B Test | varies | varies | Experimental comparison mode |

## iOS Implementation Guide

### Quick Check - Parse Mode from Job ID

```swift
let jobIdWithMode = "550e8400-e29b-41d4-a716-446655440000 (rag)"
let mode = jobIdWithMode.split(separator: "(").last?.dropLast() ?? "baseline"
// mode = "rag"
```

### Better Approach - Use Explicit Mode Field

From `/status/<job_id>`:
```swift
struct JobStatus: Codable {
    let job_id: String
    let mode: String  // ✨ NEW: Direct access to mode
    let status: String
    let progress_percentage: Int
    let enable_rag: Bool  // ✨ NEW: RAG flag
}

// Usage:
let status = try decoder.decode(JobStatus.self, from: data)
print("Mode: \(status.mode)")
print("RAG Enabled: \(status.enable_rag)")

// Set UI based on mode
switch status.mode {
case "baseline":
    showBaselineIndicator()
case "rag":
    showRAGIndicator()
case "lora":
    showLoraIndicator()
case "rag+lora":
    showRAGPlusLoraIndicator()
default:
    showDefaultIndicator()
}
```

## Complete Response Flow Example

### Scenario: Upload image in LoRA mode

```
1. POST /upload → Returns job_id with (lora) suffix
   {
     "job_id": "abc123-def456 (lora)",
     "status": "queued"
   }

2. GET /status/abc123-def456 → Returns detailed status with explicit mode
   {
     "mode": "lora",
     "status": "analyzing",
     "progress_percentage": 45,
     "enable_rag": false
   }

3. When done, GET /status/abc123-def456 → Final status
   {
     "mode": "lora",
     "status": "done",
     "progress_percentage": 100,
     "analysis_url": "http://localhost:5005/analysis/abc123-def456"
   }

4. GET /analysis/abc123-def456 → HTML with LoRA badge at top
   <!-- Green LORA badge displays here -->

5. GET /job/abc123-def456/full-data → Complete data for archiving
   {
     "mode": "lora",
     "llm_outputs": { ... }
   }
```

## Important Notes

### Mode Changes/Fallback

If the requested mode couldn't be used and fallback occurred:
- The `mode` field in `/status` shows the actual mode used
- The badge in `/analysis` shows the actual mode
- The metadata in `/analyze` shows both requested and effective mode

### RAG vs Enable_RAG

These are complementary:
- `mode`: The analysis method used (baseline, rag, lora, etc.)
- `enable_rag`: Boolean flag specifically for RAG feature
  - `mode=rag` implies `enable_rag=true`
  - `mode=lora` could have `enable_rag=true` if combining both

### Backward Compatibility

- Job IDs still have mode suffix in parentheses: `uuid (rag)`
- New explicit `mode` field makes parsing easier on clients
- All changes are additive - existing clients won't break

## Testing Mode in API Response

```bash
# Test 1: Check /status endpoint
curl http://localhost:5005/status/YOUR_JOB_ID | jq '.mode'

# Test 2: Check /full-data endpoint
curl http://localhost:5005/job/YOUR_JOB_ID/full-data | jq '.mode'

# Test 3: Check /analyze endpoint
curl -F "file=@image.jpg" -F "advisor=ansel" -F "mode=rag" \
     http://localhost:5100/analyze | jq '.metadata.mode_used'
```

## Summary of Changes

✅ **`/status` endpoint** now includes:
- Explicit `mode` field (baseline, rag, lora, etc.)
- Explicit `enable_rag` boolean flag
- Easier for iOS/clients to parse without string manipulation

✅ **All endpoints** provide mode information:
- `/analyze` - metadata.mode_used
- `/status` - mode field (new)
- `/job/<id>/full-data` - mode field
- `/upload` - job_id with mode suffix
- `/analysis` - badge display in HTML

✅ **No breaking changes** - all additions are new fields
