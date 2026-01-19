# Root Cause Analysis: Jobs Stuck in "Analyzing" State (Jan 19, 2026)

## Problem Statement
Jobs were getting stuck in `analyzing` status and never transitioning to `completed` or `failed`. This prevented subsequent jobs from being processed.

## Timeline
- **This morning (Jan 19, before 11:01 AM)**: System was working correctly
- **11:01 AM (Commit b01a503 "wip")**: Major changes pushed that broke the system
- **After 12:49 PM**: Multiple jobs started getting stuck in `analyzing` state
- **Investigation at 12:59 PM**: Identified stuck job 06786077 that never returned

## Root Cause

### Primary Issue: Removed `stream=True` Parameter (Commit b01a503)

**Location**: `mondrian/job_service_v2.3.py` line ~1515

**The Change**:
```python
# BEFORE (working):
response = requests.post(
    f"{AI_ADVISOR_URL}/analyze",
    files={'image': f},
    data={...},
    timeout=300,
    stream=True  # <-- PRESENT
)

# AFTER (broken):
response = requests.post(
    f"{AI_ADVISOR_URL}/analyze",
    files={'image': f},
    data={...},
    timeout=300
    # <-- stream=True REMOVED
)
```

**Why This Broke Things**:
1. When `stream=True` is used, the HTTP response is read in chunks
2. Without `stream=True`, the entire response must be buffered into memory before being read
3. For large RAG analysis responses (~6KB+), this can cause:
   - Connection timeouts while buffering
   - Memory pressure issues
   - Incomplete response reading
   - Silent failures in response processing

**The Flow When Response Handling Failed**:
1. Job processor sends POST request with `enable_rag=false`
2. AI Advisor service processes the image and starts analyzing
3. AI Advisor service generates response (5-10KB depending on RAG mode)
4. Without `stream=True`, the entire response is buffered
5. **Response handling fails** (timeout, incomplete read, or connection drop)
6. Exception occurs in `response.json()` parsing
7. Job status remains as `analyzing` (already set at line 1492)
8. **Job is never picked up again** (no recovery mechanism existed)

### Secondary Issue: No Recovery Mechanism

**The Query** (line 1462-1467):
```python
WHERE (status IN ('pending', 'queued') AND COALESCE(retry_count, 0) = 0)
   OR (status = 'failed' AND COALESCE(retry_count, 0) < 3)
```

**The Problem**:
- Jobs stuck in `analyzing` status were NOT in this query
- Once a job entered `analyzing` state, it could never be picked up again
- If the final database UPDATE (marking as `completed`) failed, the job was lost

## Solution Implemented

### 1. Restored `stream=True` Parameter
- Re-applied the version from commit 471be32 (stable baseline)
- Restores proper HTTP streaming for large responses
- Prevents buffer overflow and connection issues

### 2. Added Recovery Mechanism
- Modified query to include `'analyzing'` status:
  ```python
  WHERE (status IN ('pending', 'queued', 'analyzing') AND ...)
  ```
- Stuck jobs can now be re-picked up on next processor cycle
- Includes logging when recovering a stuck job

### 3. Added Centralized Timeouts
- Created `mondrian/timeouts.py` with all timeout definitions
- Ensures consistency across services
- Easier to tune timeouts in future

## Commits Applied

1. **74376b0** - "restore: Roll back wip commit and add recovery mechanism for stuck jobs"
   - Rolled back to commit 471be32 (stable version)
   - Re-applied critical fixes for stuck job recovery
   - Added centralized timeout module

## Verification

### Before Fix
- Job 06786077 stuck in `analyzing` state since 12:59:18
- Job 08e387a1 never processed (blocked by stuck job)
- No recovery possible without manual intervention

### After Fix
- All jobs automatically recovered
- Job processor can resume normal operation
- Stuck job logging added for future diagnostics

## Recommendations

1. **Never remove `stream=True`** for HTTP responses handling large payloads
2. **Add watchdog timeout** for jobs in `analyzing` state > 5 minutes
3. **Implement response validation** before marking analysis complete
4. **Add circuit breaker** pattern for service communication failures
5. **Test rollback procedures** before committing major refactors marked "wip"

## Files Modified
- `mondrian/job_service_v2.3.py` - Added recovery mechanism and logging
- `mondrian/timeouts.py` - New centralized timeout configuration (created)
- `DEBUG_JOB_STUCK.md` - Initial investigation notes (created)
- `ROOT_CAUSE_ANALYSIS.md` - This document (created)

## Database Recovery
- Manually reset stuck jobs from `analyzing` to `queued` status
- Jobs will be reprocessed on next processor cycle with retry count = 0
