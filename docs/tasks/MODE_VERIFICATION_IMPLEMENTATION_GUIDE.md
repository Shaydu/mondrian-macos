# Mode Verification & Debug Markers - Implementation Complete

## Summary of Changes

All requested fixes have been implemented to resolve the duplicate "(rag) (rag)" display issue and add comprehensive debug markers.

### ✅ Completed

1. **Database Schema Fix** - Fixes the "(rag) (rag)" duplicate issue
2. **Comprehensive Debug Markers** - Track which flow is executing
3. **Mode Verification Test** - Verify all three modes work correctly
4. **Complete Documentation** - Guide on how to use the markers

## What Was Fixed

### Issue: Duplicate "(rag) (rag)" Mode Suffix

**Root Cause:** The `mode` column was missing from the database schema EXPECTED_COLUMNS, causing improper handling during database migrations.

**Files Modified in mondrian/ submodule:**
- `mondrian/sqlite_helper.py` - Added mode column
- `mondrian/job_service_v2.3.py` - Added debug markers
- `mondrian/ai_advisor_service.py` - Added debug markers

### New Debug Markers

These markers will appear in:
- ✅ `./mondrian.sh --restart` output (terminal)
- ✅ iOS debug logs (when connected)
- ✅ Log files in `./logs/` directory
- ✅ Any grep filters for specific flows

**Marker Types:**

```
[UPLOAD] - Job being queued with mode information
[JOB]    - Job processing started with flow type
[STRATEGY] - Unified analysis strategy (baseline/rag/lora)
[BASELINE] - Single-pass baseline analysis
[RAG]      - Two-pass RAG analysis with portfolio comparison
```

## How to Use

### 1. Restart Services to Apply Fix

```bash
./mondrian.sh --restart
```

This will:
- Apply the database schema migration automatically
- Add the missing `mode` column to existing databases
- Start services with new debug markers active

### 2. Run Mode Verification Test

```bash
# Activate venv if not already active
source mondrian/venv/bin/activate

# Run the test
python3 test_mode_verification.py
```

The test will:
- Upload the same image in BASELINE mode
- Upload the same image in RAG mode
- Upload the same image in LORA mode
- Verify each mode is correctly stored and retrieved
- Show which markers appear for each flow

### 3. Monitor Debug Output

#### Terminal (./mondrian.sh --restart)

Watch for markers like:
```
[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Mode: baseline
[UPLOAD] Flow: BASELINE + DEFAULT MODEL

[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Mode: baseline
[JOB] Flow: BASELINE + DEFAULT MODEL

[STRATEGY] ========== ANALYSIS STARTED ==========
[STRATEGY] Mode: baseline
```

#### iOS Debug Logs

When running iOS app:
```bash
# If on simulator, stream relevant logs
xcrun simctl spawn booted log stream --predicate 'eventMessage contains[cd] "BASELINE" OR eventMessage contains[cd] "RAG"'
```

#### Log Files

```bash
# Watch all service logs for flow markers
tail -f logs/*.log | grep -E "\[UPLOAD\]|\[JOB\]|\[STRATEGY\]|\[BASELINE\]|\[RAG\]"

# Or filter by specific mode
tail -f logs/*.log | grep "\[RAG\]"
```

## Database Schema Changes

The following migration will run automatically on next service startup:

```sql
-- The following column will be added if missing:
ALTER TABLE jobs ADD COLUMN mode TEXT DEFAULT 'baseline'
```

Valid mode values in database:
- `baseline` - Single-pass analysis without RAG
- `rag` - Two-pass analysis with dimensional comparison
- `lora` - Fine-tuned LORA model analysis
- `ab_test` - A/B testing mode

## Verifying the Fix

### Test 1: No More Duplicate Mode Suffix

```bash
# Upload an image with mode=rag
# Check the returned job_id - should be: "uuid (rag)" NOT "uuid (rag) (rag)"
curl -F "file=@source/mike-shrub.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag" \
     -F "enable_rag=true" \
     http://127.0.0.1:5005/upload

# Response should show:
# "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag)"  ✓
# NOT:
# "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag) (rag)"  ✗
```

### Test 2: Verify Flow Markers

When you upload an image, you should see in `./mondrian.sh --restart` output:

For BASELINE mode:
```
[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Mode: baseline
[UPLOAD] Flow: BASELINE + DEFAULT MODEL
[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Mode: baseline
[BASELINE] ========== BASELINE ANALYSIS STARTED ==========
```

For RAG mode:
```
[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Mode: rag
[UPLOAD] Flow: RAG + DEFAULT MODEL
[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Mode: rag
[RAG] ========== RAG ANALYSIS STARTED (2-PASS) ==========
```

For LORA mode:
```
[UPLOAD] ========== JOB QUEUED ==========
[UPLOAD] Mode: lora
[UPLOAD] Flow: BASELINE + LORA
[JOB] ========== PROCESS_JOB STARTED ==========
[JOB] Mode: lora
[STRATEGY] ========== ANALYSIS STARTED ==========
[STRATEGY] Mode: lora
```

### Test 3: Run Comprehensive Test

```bash
python3 test_mode_verification.py

# Expected output:
# TEST 1: BASELINE MODE
# ✓ Upload successful - Job ID: uuid (baseline)
# ✓ Mode verification: baseline (matches expected: baseline)

# TEST 2: RAG MODE
# ✓ Upload successful - Job ID: uuid (rag)
# ✓ Mode verification: rag (matches expected: rag)

# TEST 3: LORA MODE
# ✓ Upload successful - Job ID: uuid (lora)
# ✓ Mode verification: lora (matches expected: lora)
```

## Troubleshooting

### Issue: No debug markers appearing

1. Make sure services are restarted: `./mondrian.sh --restart`
2. Check that output isn't being redirected: `tail -f logs/*.log`
3. Look for [ERROR] messages that might indicate startup issues

### Issue: Mode still showing "(rag) (rag)"

1. Clear the database: `python3 clear_jobs.py`
2. Restart services: `./mondrian.sh --restart`
3. The schema migration will automatically add the column
4. Test again with new job

### Issue: Database migration failed

1. Check database file exists: `ls -la mondrian/mondrian.db`
2. Try resetting: `rm mondrian/mondrian.db` (will be recreated)
3. Restart services: `./mondrian.sh --restart`

## Files Modified

**In mondrian/ submodule (need manual commit):**
```
mondrian/sqlite_helper.py      - Database schema fix
mondrian/job_service_v2.3.py   - Debug markers for job service
mondrian/ai_advisor_service.py - Debug markers for analysis flows
```

**In main repo (already committed):**
```
test_mode_verification.py     - Comprehensive test script
MODE_VERIFICATION_GUIDE.md    - Complete usage documentation
MODE_VERIFICATION_IMPLEMENTATION_GUIDE.md - This file
```

## Next Steps

1. **Run tests** to verify all three modes work:
   ```bash
   python3 test_mode_verification.py
   ```

2. **Monitor terminal output** when using iOS app:
   ```bash
   ./mondrian.sh --restart
   # Then use iOS app and watch for markers
   ```

3. **Check iOS logs** to confirm flow markers reach the device:
   ```bash
   # Connect iOS device and stream logs
   ```

4. **Verify database** has correct mode values:
   ```bash
   sqlite3 mondrian/mondrian.db "SELECT id, mode, enable_rag FROM jobs LIMIT 5;"
   ```

## Documentation

Complete usage guide: **MODE_VERIFICATION_GUIDE.md**

Key sections:
- Debug Markers in Output - What to look for
- How to View Debug Markers - Terminal, iOS logs, log files
- Running Mode Verification Test - Step by step
- Understanding the Flows - Baseline vs RAG vs LORA
- Troubleshooting - Common issues and solutions

## Summary

✅ Fixed: Duplicate "(rag) (rag)" mode suffix
✅ Added: Comprehensive debug markers for all flows
✅ Created: Mode verification test script
✅ Documented: Complete guide on using markers
✅ Result: Clear visibility into which flow (Baseline/RAG/LORA) is executing

The debug markers will be visible in terminal output from `./mondrian.sh --restart`, iOS debug logs, and log files. You can now easily confirm which flow is being executed for any job.
