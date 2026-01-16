# Root Cause Analysis: Job Termination Issue

## Problem
Jobs were starting successfully but then the restart script was getting "Terminated" (exit code 143 = SIGTERM). The output showed:

```
Port 5100 still in use, attempting port-based cleanup...
Killing process on port 5100 (PID None)...
Terminated
```

## Root Cause

**The restart script itself was receiving SIGTERM signals intended for child processes.**

### How it happened:

1. **Signal handling issue**: When the `start_services.py` script tried to kill stuck processes using `os.kill(pid, signal.SIGTERM)`, the signal handling was not properly isolated.

2. **Unsafe subprocess calls**: The code used `os.kill()` directly with raw signals instead of using safer subprocess-based signal handling. This made the parent process vulnerable to receiving stray signals.

3. **Race condition**: When multiple services were being killed during cleanup, SIGTERM signals could escape the subprocess context and affect the parent Python process, terminating the entire restart operation.

### In `kill_process_on_port()` function (line 204):
```python
# BEFORE (problematic):
os.kill(pid, signal.SIGTERM)  # Raw signal to PID - not isolated
```

This could affect the parent process in certain conditions, especially when:
- The PID parsing failed (showing "PID None")
- Multiple signals were sent rapidly
- Signal handlers weren't properly registered

## Solution

### 1. **Safer subprocess-based signal handling** (line 195-250)
Replaced direct `os.kill()` calls with subprocess commands:
```python
# AFTER (fixed):
subprocess.run(['kill', '-TERM', str(pid)], timeout=3, capture_output=True)
```

Benefits:
- Signals are sent via shell commands (more isolated)
- Better error handling with timeouts
- Prevents signal bleed-back to parent process

### 2. **Signal handler for parent process** (line 23-32)
Added signal handlers to the parent script:
```python
def signal_handler(signum, frame):
    """Handle signals during cleanup phase."""
    global _in_cleanup
    if _in_cleanup:
        print("[DEBUG] Received signal {signum} during cleanup phase - ignoring")
        return
    raise KeyboardInterrupt()

signal.signal(signal.SIGTERM, signal_handler)
```

Benefits:
- Parent process now ignores SIGTERM during cleanup phase
- Prevents accidental termination of restart script
- Logs signal events for debugging

### 3. **Cleanup phase protection** (line 264-305)
Wrapped cleanup in try/finally with global flag:
```python
_in_cleanup = True  # Set flag before cleanup
try:
    # ... perform cleanup ...
finally:
    _in_cleanup = False  # Clear flag after cleanup
```

## Testing the Fix

To verify the fix works:

```bash
# Kill any stuck services manually
pkill -f "job_service_v2.3"
pkill -f "ai_advisor_service"
pkill -f "summary_service"

# Now try restart - should work without terminating
./mondrian.sh --restart
```

## Expected Behavior After Fix

1. Services are cleaned up safely without the parent script getting killed
2. Port 5100 (and other ports) are freed properly
3. Services restart successfully
4. No "Terminated" messages on port cleanup

## Files Changed
- `scripts/start_services.py`: Updated signal handling and process cleanup logic

## Verification
If you see the restart complete successfully with all services starting, the issue is fixed.
