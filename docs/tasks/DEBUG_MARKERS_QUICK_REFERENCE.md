# Debug Markers Quick Reference Card

## What to Watch For in Terminal Output

When you run `./mondrian.sh --restart` and upload an image, look for these patterns:

### BASELINE Flow
```
[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Mode: baseline
[UPLOAD] Enable RAG: false
[UPLOAD] Flow: BASELINE + DEFAULT MODEL

[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Mode: baseline
[JOB] Flow: BASELINE + DEFAULT MODEL

[BASELINE] ========== BASELINE ANALYSIS STARTED ==========
[BASELINE] Advisor: ansel
[BASELINE] Flow: Single-pass baseline (no RAG, no fine-tuning)
[BASELINE] ✓ Advisor prompt loaded
```

### RAG Flow
```
[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Mode: rag
[UPLOAD] Enable RAG: true
[UPLOAD] Flow: RAG + DEFAULT MODEL

[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Mode: rag
[JOB] Flow: RAG + DEFAULT MODEL

[RAG] ========== RAG ANALYSIS STARTED (2-PASS) ==========
[RAG] Advisor: ansel
[RAG] Flow: Two-pass RAG with dimensional comparison
[RAG] [INFO] Pass 1: Analyzing image...
[RAG] [INFO] Pass 2: Comparing with advisor portfolio...
```

### LORA Flow
```
[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Mode: lora
[UPLOAD] Enable RAG: false
[UPLOAD] Flow: BASELINE + LORA

[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Mode: lora
[JOB] Flow: BASELINE + LORA

[STRATEGY] ========== ANALYSIS STARTED ==========
[STRATEGY] Mode: lora
[STRATEGY] ✓ Using requested mode: lora
[STRATEGY] Executing analysis with lora strategy...
```

## grep Commands to Filter Output

```bash
# Watch only upload events
tail -f logs/*.log | grep "\[UPLOAD\]"

# Watch only baseline mode
tail -f logs/*.log | grep "\[BASELINE\]"

# Watch only RAG mode  
tail -f logs/*.log | grep "\[RAG\]"

# Watch only LORA mode
tail -f logs/*.log | grep "\[STRATEGY\]" | grep "lora"

# Watch flow confirmations
tail -f logs/*.log | grep -E "Flow:|Mode:"

# Watch successes
tail -f logs/*.log | grep "✓"

# Watch warnings/fallbacks
tail -f logs/*.log | grep "⚠"

# Watch all analysis markers
tail -f logs/*.log | grep -E "\[BASELINE\]|\[RAG\]|\[STRATEGY\]"
```

## What Each Marker Means

| Marker | Meaning | What to Expect |
|--------|---------|-----------------|
| `[UPLOAD]` | Job being submitted | Mode, RAG flag, advisors |
| `[JOB]` | Job processing starting | Mode, flow type |
| `[STRATEGY]` | Strategy pattern analysis | Unified flow entry |
| `[BASELINE]` | Baseline analysis flow | Single-pass analysis |
| `[RAG]` | RAG analysis flow | Two-pass with portfolio |
| `✓` | Operation succeeded | Expected in normal flow |
| `⚠️` | Fallback occurred | Mode changed (unexpected) |
| `✗` | Operation failed | Error occurred |

## How to Confirm Mode is Working

### Upload Test
```bash
# 1. Upload an image
curl -F "file=@source/test.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag" \
     http://127.0.0.1:5005/upload

# 2. Check the job_id in response
# Should show: "uuid (rag)" ✓
# NOT: "uuid (rag) (rag)" ✗
```

### Terminal Confirmation
```bash
# In separate terminal, watch logs during upload
tail -f logs/*.log | grep -E "\[UPLOAD\]|\[JOB\]|\[RAG\]"

# You should see:
# [UPLOAD] Mode: rag ✓
# [UPLOAD] Enable RAG: true ✓
# [JOB] Flow: RAG + DEFAULT MODEL ✓
# [RAG] ========== RAG ANALYSIS STARTED (2-PASS) ========== ✓
```

### Database Confirmation
```bash
# Query the database
sqlite3 mondrian/mondrian.db "SELECT id, mode, enable_rag FROM jobs ORDER BY created_at DESC LIMIT 3;"

# Output should show:
# uuid|rag|1    ← RAG job
# uuid|baseline|0  ← Baseline job
# uuid|lora|0      ← LORA job
```

## iOS Debug Logs

When running on iOS device with debugger attached:

### Xcode Console
1. Open Xcode while app is running
2. View → Debug Area → Show Console
3. Filter for markers: `cmd+f` then search for `BASELINE` or `RAG`

### Command Line (Simulator)
```bash
# Stream logs from iOS simulator
xcrun simctl spawn booted log stream --predicate 'eventMessage contains[cd] "BASELINE" OR eventMessage contains[cd] "RAG"'
```

### Expected iOS Output Format
```
[BASELINE] ========== BASELINE ANALYSIS STARTED ==========
[RAG] ========== RAG ANALYSIS STARTED (2-PASS) ==========
[STRATEGY] ========== ANALYSIS STARTED ==========
```

## Quick Test Script

```bash
#!/bin/bash
# Test all three modes

MODES=("baseline" "rag" "lora")
IMAGE="source/mike-shrub.jpg"
ADVISOR="ansel"

for MODE in "${MODES[@]}"; do
    echo "Testing $MODE..."
    curl -F "file=@$IMAGE" \
         -F "advisor=$ADVISOR" \
         -F "mode=$MODE" \
         http://127.0.0.1:5005/upload
    sleep 2
done

echo "Done! Check logs for markers."
```

## Troubleshooting Markers

### Problem: No markers appearing
```bash
# Check if services are running
ps aux | grep "job_service\|advisor_service"

# Restart services
./mondrian.sh --restart

# Verify logs exist
ls -la logs/
```

### Problem: Wrong mode showing
```bash
# Clear database
python3 clear_jobs.py

# Restart services
./mondrian.sh --restart

# Try again
python3 test_mode_verification.py
```

### Problem: Mode shows as baseline instead of rag
```bash
# Check the enable_rag parameter was sent
# Verify in [UPLOAD] marker: Enable RAG: true

# Check database
sqlite3 mondrian/mondrian.db "SELECT id, mode, enable_rag FROM jobs WHERE mode='rag' LIMIT 1;"
```

## Complete Example Session

```bash
# Terminal 1: Start services and watch logs
./mondrian.sh --restart
# Let it start, then in another terminal...

# Terminal 2: Test RAG mode
python3 test_mode_verification.py

# In Terminal 1, you should see markers appearing for each mode:
# [UPLOAD] Mode: baseline
# [UPLOAD] Mode: rag  
# [UPLOAD] Mode: lora
# [JOB] Mode: baseline
# [JOB] Mode: rag
# [JOB] Mode: lora
# [BASELINE] ========== BASELINE ANALYSIS STARTED ==========
# [RAG] ========== RAG ANALYSIS STARTED (2-PASS) ==========
# [STRATEGY] ========== ANALYSIS STARTED ==========

# Terminal 3: Verify database
sqlite3 mondrian/mondrian.db "SELECT id, mode FROM jobs ORDER BY created_at DESC LIMIT 3;"
# Should show 3 different modes
```

## Key Points to Remember

1. **[UPLOAD]** markers show what mode was requested
2. **[JOB]** markers show job processing starting
3. **[BASELINE]** or **[RAG]** markers show which flow is executing
4. **Flow:** field shows the exact flow (RAG vs LORA etc)
5. **✓** checkmarks show normal operation
6. **⚠️** warnings show unusual behavior (fallbacks)
7. Database `mode` field should match the markers

## Still Having Issues?

Check the full guide: **MODE_VERIFICATION_GUIDE.md**
Check implementation details: **MODE_VERIFICATION_IMPLEMENTATION_GUIDE.md**
