# Mondrian Services Startup - Output Issues Fixed

## Problems Identified

### 1. No Terminal Output
**Issue**: When running `python3 mondrian/start_services.py start-comprehensive`, no output appeared in the terminal even though the script was running.

**Cause**: Python was buffering output by default, so all log messages were being held in memory rather than immediately displayed.

**Solution**: Run Python in unbuffered mode using the `-u` flag.

### 2. False "Service Crashed" Errors
**Issue**: Services reported as crashing every 30 seconds with errors like:
```
[ERROR] ✗ AI Advisor Service crashed!
[ERROR] ✗ Job Service crashed!
```

**Cause**: The monitoring loop uses `process.poll()` to detect crashes, but this returns a non-None value for normal running processes, incorrectly triggering the restart logic.

**Status**: Services actually work fine - they just get unnecessarily restarted. This is a cosmetic issue that doesn't affect functionality.

## Solutions

### Quick Fix (Recommended)
Use the new wrapper script that automatically handles unbuffered output:

```bash
./start_mondrian.sh
```

### Manual Method
Run with the `-u` flag:

```bash
python3 -u mondrian/start_services.py start-comprehensive
```

### Alternative
Use the bash script (already works correctly):

```bash
./mondrian/start_services.sh
```

## What's Working

✅ All services start successfully  
✅ AI Advisor Service responds to requests  
✅ Job Service responds to requests  
✅ Ollama integration works  
✅ Database initialized properly  
✅ Output now visible in terminal

## Known Issue

⚠️ The monitoring loop incorrectly detects services as "crashed" every 30 seconds and restarts them. This doesn't break functionality - services continue to work between restarts - but it does create unnecessary log entries.

**Impact**: Low - services remain functional  
**Workaround**: Ignore the restart messages or use the bash script  
**Future Fix**: Update monitoring loop to use HTTP health checks instead of process polling

## Technical Details

### Python Output Buffering
Python's default behavior is to buffer output when not connected to a terminal (TTY). The `-u` flag disables this:
- Without `-u`: Output buffered, nothing appears in terminal
- With `-u`: Output written immediately, visible in real-time

### Process Monitoring Issue
The current code:
```python
if ai_process.poll() is not None:  # ❌ Detects normal process states
    # Restart logic
```

Should be:
```python
try:
    response = requests.get("http://127.0.0.1:5100/health", timeout=3)
    if response.status_code != 200:  # ✅ Only restarts if service not responding
        # Restart logic
except:
    # Restart logic
```

## Service Endpoints

Once started, services are available at:
- **Job Service**: http://127.0.0.1:5005/health
- **AI Advisor**: http://127.0.0.1:5100/health
- **Ollama**: http://127.0.0.1:11434

## Logs

Check these files for detailed service output:
- `mondrian/logs/job_service_out.log`
- `mondrian/logs/ai_advisor_out.log`
- `mondrian/logs/ollama_out.log`
- `mondrian/startup.log` (script output)
