# Summary of Fixes for Analysis Failed Errors

## Problems Identified

### 1. **Termination Issue (Exit 143 - SIGTERM)**
**Root Cause:** The restart script was receiving SIGTERM signals when trying to kill stuck services.
- Direct `os.kill()` calls allowed signals to affect parent process
- No signal handlers to protect parent during cleanup

**Fixes Applied:**
- Replaced `os.kill()` with safer `subprocess.run(['kill', ...])` commands
- Added signal handler to ignore SIGTERM during cleanup phase
- Wrapped cleanup in try/finally with `_in_cleanup` flag

### 2. **Database Path Ambiguity**
**Root Cause:** Multiple database files and relative paths caused jobs to use wrong database.
- `/home/doo/dev/mondrian-macos/mondrian.db` (valid with data)
- `/home/doo/dev/mondrian-macos/mondrian/mondrian.db` (empty)

**Fixes Applied:**
- Removed empty `mondrian/mondrian.db` file
- Added `db_path` config entry to database: `/home/doo/dev/mondrian-macos/mondrian.db`
- Updated job_service to read `db_path` from config table
- Added explicit `--db` parameter to start_services.py
- All services now use absolute path to single database

### 3. **AI Advisor Service Not Ready When Jobs Start**
**Root Cause:** Job processor tried to analyze immediately at startup before AI Advisor model finished loading.
- Services start with 1-second delays
- AI Advisor needs ~16 seconds to load the Qwen3-VL-4B model
- First jobs failed with "Connection refused" errors

**Fixes Applied:**
- Added startup wait in `process_job_worker()` that polls AI Advisor `/health` endpoint
- Waits up to 30 seconds before attempting first job
- Logs waiting progress every 2 seconds
- Jobs don't start until AI Advisor responds with status="UP"

### 4. **No Retry Logic for Transient Failures**
**Root Cause:** Jobs failed once due to connection issues and never retried.
- When connection failed, job was marked as "failed" permanently
- Client couldn't fetch summary (endpoint returns 400 for non-completed jobs)

**Fixes Applied:**
- Added `retry_count` column to jobs table
- Jobs now retry up to 3 times on connection failures
- "Connection refused" errors trigger automatic retry
- Only after 3 failed attempts does job go to "failed" state
- Retry attempts logged with clear status messages
- Clear distinction between temporary failure (queued for retry) and permanent failure

## Files Modified

### 1. `scripts/start_services.py`
- Added signal handler for SIGTERM protection during cleanup
- Replaced unsafe `os.kill()` with subprocess-based kill commands
- Added `--db` parameter to job_service startup
- Set global `_in_cleanup` flag during cleanup phase

### 2. `mondrian/job_service_v2.3.py`
- Added startup wait for AI Advisor service availability
- Added `retry_count` column to database schema
- Modified job query to find retryable jobs with retry_count < 3
- Updated error handling to increment retry count on connection failures
- Added detailed logging for retry attempts
- Clear distinction between temporary and permanent failures

### 3. `mondrian.db` Configuration
- Added entry: `INSERT INTO config (key, value) VALUES ('db_path', '/home/doo/dev/mondrian-macos/mondrian.db')`

### 4. Cleanup
- Removed `/home/doo/dev/mondrian-macos/mondrian/mondrian.db` (empty file)

## Expected Behavior After Fixes

1. **Restart Stability**
   - Restart script no longer terminates unexpectedly
   - Services clean up properly without parent process being killed

2. **Correct Database Usage**
   - All services read from single database at known path
   - No ambiguity about which database is being used

3. **Reliable Job Processing**
   - Job processor waits for AI Advisor to be ready before processing
   - No more "Connection refused" errors on first jobs

4. **Automatic Recovery**
   - Transient failures automatically retry up to 3 times
   - Jobs that fail due to service being unavailable recover automatically
   - User sees clearer status: "queued for retry" vs "permanently failed"

## Testing

To verify the fixes:

```bash
# Kill any stuck services
pkill -f "job_service"
pkill -f "ai_advisor"
pkill -f "summary_service"

# Restart services
./mondrian.sh --restart

# Should see:
# - Services starting without termination
# - Job processor waiting for AI Advisor
# - Jobs processing successfully after service is ready
```

## Logs to Monitor

Check these logs to verify fixes are working:

1. **Service startup**: `/logs/job_service_v2.3_*.log`
2. **AI Advisor loading**: `/logs/ai_advisor_service_linux_*.log`
3. **Job processing**: Look for "Job processor started" and "AI Advisor service is ready"

## Known Limitations

- Maximum retry count is 3 attempts (configurable if needed)
- Retry delay starts at 1 second between checks
- Clients still need to handle 400 responses from `/summary` for non-completed jobs
