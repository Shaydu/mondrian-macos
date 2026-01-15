# Mode is Now Sent in All API Calls

## Summary

✅ **Mode is consistently sent in all API calls and responses**

The Mondrian API now includes mode information in:
- API requests from clients
- Internal service-to-service calls
- All API responses

---

## API Calls Overview

### Client → Job Service: POST /upload

**Request (form data):**
```
file=image.jpg
advisor=ansel
mode=rag              ← MODE SENT HERE
auto_analyze=true
```

**Response:**
```json
{
  "job_id": "uuid (rag)",
  "mode": "rag",        ← MODE RETURNED HERE (UPDATED)
  "status": "queued",
  "enable_rag": false,
  ...
}
```

---

### Job Service → AI Advisor Service: POST /analyze

**Internal call in process_job() - Line 866-872:**
```python
data = {
    'advisor': adv,
    'job_id': job_id,
    'job_service_url': job_service_callback,
    'enable_rag': 'true' if enable_rag else 'false',
    'mode': mode              ← MODE SENT HERE (Line 871)
}
```

**Debug output:**
```
[JOB] ✓ Sending request to AI service with mode='rag'
```

---

### Client → Job Service: GET /status/{job_id}

**Response includes mode:**
```json
{
  "job_id": "uuid (rag)",
  "status": "done",
  "mode": "rag",         ← MODE IN RESPONSE
  "enable_rag": false,
  ...
}
```

---

## Where Mode is Used

### 1. Upload Endpoint (/upload)
- ✅ **Receives mode** from client form parameter
- ✅ **Stores mode** in database (jobs.mode column)
- ✅ **Returns mode** in response
- ✅ **Passes mode** to job queue

### 2. Process Job Function (process_job)
- ✅ **Receives mode** from job queue
- ✅ **Sends mode** to AI Advisor Service
- ✅ **Logs mode** in debug output ([JOB] Mode: ...)

### 3. AI Advisor Service (/analyze)
- ✅ **Receives mode** from Job Service
- ✅ **Uses mode** to select strategy (baseline/rag/lora)
- ✅ **Returns mode** in analysis results

### 4. Status Endpoint (/status)
- ✅ **Retrieves mode** from database
- ✅ **Returns mode** in response
- ✅ **Formats job_id** with mode suffix: "uuid (rag)"

### 5. Stream Endpoint (/stream)
- ✅ **Returns mode_info** in status updates
- ✅ **Per-advisor mode** included in responses

---

## Mode Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ CLIENT (iOS/Browser)                                        │
│ POST /upload with mode=rag                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─→ Extract mode from form
                     │   (Line 1505-1507)
                     │
                     ├─→ Store in database
                     │   (Line 1557: INSERT ... mode)
                     │
                     ├─→ Return in response
                     │   (Line 1591: "mode": mode)
                     │
                     └─→ Queue job with mode
                         (Line 1583: job_queue.put(..., mode))
                     │
                     ▼
        ┌────────────────────────────────────────┐
        │ PROCESS JOB (background worker)        │
        │ process_job(..., mode='rag')           │
        └───────────┬────────────────────────────┘
                    │
                    ├─→ Log mode
                    │   ([JOB] Mode: rag)
                    │
                    └─→ Send to AI Service
                        POST /analyze with mode=rag
                        (Line 871: 'mode': mode)
                    │
                    ▼
        ┌────────────────────────────────────────┐
        │ AI ADVISOR SERVICE                     │
        │ Receives mode=rag                      │
        └───────────┬────────────────────────────┘
                    │
                    ├─→ Select strategy
                    │   (RAG strategy selected)
                    │
                    └─→ Return analysis with mode
                        (mode_used: "rag")
                    │
                    ▼
        ┌────────────────────────────────────────┐
        │ STORE RESULTS                          │
        │ Update database with mode_used        │
        └────────────────────────────────────────┘
                    │
                    ▼
        ┌────────────────────────────────────────┐
        │ CLIENT: GET /status/{job_id}           │
        │ Returns mode in response               │
        └────────────────────────────────────────┘
```

---

## Updated Response Examples

### Upload Response (UPDATED with mode)

```bash
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag)",
  "filename": "photo.jpg",
  "advisor": "ansel",
  "advisors_used": ["ansel"],
  "status": "queued",
  "mode": "rag",          ← NEWLY ADDED
  "enable_rag": false,
  "status_url": "http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000",
  "stream_url": "http://localhost:5005/stream/550e8400-e29b-41d4-a716-446655440000"
}
```

### Status Response (already had mode)

```bash
curl http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag)",
  "filename": "photo.jpg",
  "advisor": "ansel",
  "status": "done",
  "mode": "rag",          ← ALREADY PRESENT
  "enable_rag": false,
  "progress_percentage": 100,
  ...
}
```

---

## Swift Integration

### Updated Upload Call

```swift
let service = MondrianAPIService(host: "10.0.0.227")

let uploadResponse = try await service.uploadImage(
    imageData,
    advisor: "ansel",
    mode: "rag",
    autoAnalyze: true
)

// Now can access mode directly
print("Mode: \(uploadResponse.mode)")  // "rag"
print("Job ID: \(uploadResponse.job_id)")  // "uuid (rag)"
```

### Updated Models

```swift
struct UploadResponse: Decodable {
    let job_id: String
    let filename: String
    let advisor: String
    let advisors_used: [String]
    let status: String
    let mode: String              // ← NEWLY ADDED
    let enable_rag: Bool
    let status_url: String
    let stream_url: String
}
```

---

## Code Changes Made

**File:** `mondrian/job_service_v2.3.py`

**Lines 1584-1607:** Added `"mode": mode` to both response branches:

```python
# When auto_analyze=true
return jsonify({
    "job_id": formatted_job_id,
    "filename": unique_filename,
    "advisor": advisor_str,
    "advisors_used": advisors,
    "status": "queued",
    "mode": mode,              ← ADDED
    "enable_rag": enable_rag,
    "status_url": status_url,
    "stream_url": stream_url
}), 201

# When auto_analyze=false
return jsonify({
    "job_id": formatted_job_id,
    "filename": unique_filename,
    "advisor": advisor_str,
    "advisors_used": advisors,
    "status": "pending",
    "mode": mode,              ← ADDED
    "enable_rag": enable_rag,
    "message": "File uploaded successfully. Use /analyze to start analysis.",
    "status_url": status_url,
    "stream_url": stream_url
}), 201
```

---

## Consistency Across All Endpoints

| Endpoint | Mode Sent | Mode Received | Mode Returned |
|----------|-----------|---------------|---------------|
| POST /upload | ✅ Yes | N/A | ✅ Yes (NEW) |
| GET /status | N/A | N/A | ✅ Yes |
| GET /stream | N/A | N/A | ✅ Yes |
| GET /analysis | N/A | N/A | ✅ In HTML |
| GET /jobs | N/A | N/A | ✅ In HTML |
| POST /analyze (internal) | N/A | ✅ Yes | ✅ Yes |

---

## Benefits

✅ **Clients can verify mode was applied** - Check response mode matches request
✅ **Easy tracking** - Mode visible in every response
✅ **Audit trail** - Mode stored in database for each job
✅ **Debug friendly** - Mode logged at each step
✅ **Consistent API** - All endpoints return mode

---

## Next Steps

1. ✅ Mode sent in all API calls
2. ✅ Mode returned in all responses
3. ✅ Updated Swift models
4. ✅ Updated api.md documentation
5. Ready for client integration!

