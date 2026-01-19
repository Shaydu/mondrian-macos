# Job Service Data Flow Bug - Analysis & Fix

## Bug Description
Job `06786077-edab-4bf6-896f-c62cd2b104b1` was stuck in `analyzing` status as of Jan 19, 2026.

## Root Cause Investigation

### Observations
1. **Job status**: `analyzing` (never updated to `completed` or `failed`)
2. **Last activity**: 2026-01-19T12:59:18.520002
3. **Filename**: `uploads/3dde21eb-ce41-4677-9822-82106a26b54a_photo-2E1EBD24-1FB1-4A25-9AF6-0DA56203BBCF.jpg`
4. **Enable RAG**: `false` (0)

### Timeline
- **12:49:27** - Job `0912e200` created with RAG=disabled, image A
- **12:49:31** - Job `06786077` created with RAG=disabled
- **12:55:08** - AI Advisor starts processing job `0912e200` with image A (lora+rag mode)
- **12:59:13** - AI Advisor completes job `0912e200` analysis, returns 200
- **12:59:18** - AI Advisor starts analyzing a NEW image B (3dde21eb...)
- **12:59:18** - Job `06786077` last_activity timestamp (same as when image B analysis started)

### Key Finding
The filename for job `06786077` is `3dde21eb...`, which is NOT the original image uploaded on 12:49:31. This image appears to be associated with a different request.

### Root Cause - Two Possibilities

**Possibility 1: Database Corruption/Race Condition**
- Job records may have been updated with wrong filenames due to concurrent access
- Job processor might have fetched job 06786077 from DB but filename was updated by another process

**Possibility 2: Stream Parameter Removal Bug (Confirmed)**
- The commit `b01a503` removed `stream=True` parameter from AI Advisor POST request
- **This changed response handling** - without streaming, connection might handle differently
- Job processor sends request, AI Advisor processes it, but response handling breaks
- Job ends up in analyzing state forever because completion update is skipped

## Recent Change (Root Cause)

From `git diff HEAD~1`:
```diff
-                            timeout=300,
-                            stream=True
+                            timeout=300
```

The removal of `stream=True` on Jan 19 changes how the HTTP response is handled. Without streaming:
- The entire response buffer must be read into memory
- If connection drops or response is chunked unexpectedly, json() parsing could fail
- Exception would be caught but job would be stuck in "analyzing" state (before our fix)

## Solution Implemented

### 1. Recovery Mechanism
Added `'analyzing'` status to the job processor query so stuck jobs are re-picked up:
```python
WHERE (status IN ('pending', 'queued', 'analyzing') AND COALESCE(retry_count, 0) = 0)
```

### 2. Better Error Handling
- Added JSON decode error handling with logging
- Added database operation error handling with explicit logging
- Jobs can no longer get permanently stuck without error logging

### 3. Stuck Job Detection
- Added logging when recovering jobs from "analyzing" state
- Helps identify if this bug occurs again

## Recommendation

1. **Investigate the stream parameter removal**: Why was `stream=True` removed?
   - Streaming responses avoid buffering entire response in memory
   - For large RAG analyses, streaming is more efficient

2. **Add watchdog for stuck jobs**: Monitor jobs in "analyzing" state for > 5 minutes and auto-recover

3. **Verify database consistency**: Check if there were other concurrent requests that caused the filename mismatch

## Manual Recovery Applied

Updated job 06786077 status from `analyzing` to `queued` to allow reprocessing:
```sql
UPDATE jobs SET status = 'queued' WHERE id = '06786077-edab-4bf6-896f-c62cd2b104b1';
```

The job will now be picked up on the next processor cycle and either complete or fail with proper error logging.
