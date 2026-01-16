# LoRA Job Processor Debugging Guide

## Quick Start: Debugging Your Hanging LoRA Jobs

### 1. **Run the Quick Diagnostic** (30 seconds)
```bash
python3 debug_lora_job_processor.py
```

This will:
- Check if services are running
- Identify hung/stuck jobs
- Test AI Advisor directly
- Show recent job history
- Provide recommendations

### 2. **Monitor Jobs in Real-Time** (continuous)
```bash
python3 monitor_lora_jobs.py
```

This shows a live dashboard of:
- Service health status
- Queue statistics
- Active jobs and their elapsed time
- Real-time alerts for stuck jobs

---

## Understanding Job Processing Flow

### Job States
```
pending → queued → analyzing → completed
           ↓ (on error)
           failed → queued (retry up to 3x)
```

### Processing Steps
1. **pending/queued**: Waiting in queue
2. **analyzing**: Sending request to AI Advisor service
3. **completed**: Analysis finished successfully
4. **failed**: Error occurred or retries exhausted

### Timeout Configuration
- Default timeout for AI Advisor: **300 seconds** (5 minutes)
- Service startup wait: **30 seconds** max
- Retry limit: **3 attempts**

---

## Common Hanging Issues & Solutions

### Issue 1: Jobs Stuck in "analyzing" State

**Symptom:** Job status shows "analyzing" but never progresses

**Likely Causes:**
1. **AI Advisor service hung or crashed**
2. **GPU memory exhausted** (LoRA loading issue)
3. **Request timeout** to AI Advisor
4. **Network connectivity** issue

**Debug Steps:**

```bash
# Check if AI Advisor is responding
curl http://localhost:5100/health

# Check AI Advisor logs
tail -50 logs/ai_advisor_service_*.log

# Check for GPU memory issues
nvidia-smi  # or mlx_gpu_utils for MLX
ps aux | grep ai_advisor

# Check job database for specifics
sqlite3 mondrian.db "SELECT id, advisor, mode, status, error FROM jobs WHERE status='analyzing' ORDER BY created_at DESC LIMIT 5;"
```

**Quick Fix:**
```bash
# Kill stuck AI Advisor
pkill -f ai_advisor_service

# Clear stuck jobs
python3 clear_jobs.py

# Restart services
python3 mondrian/job_service_v2.3.py --port 5005 --db mondrian.db &
python3 mondrian/start_services.py --mode=lora
```

---

### Issue 2: Jobs Never Make It to "analyzing"

**Symptom:** Jobs stay in "pending" or "queued" state

**Likely Causes:**
1. **Job processor thread crashed**
2. **AI Advisor not ready** (still loading model)
3. **Database locked** or transaction issues

**Debug Steps:**

```bash
# Check if job processor is running
ps aux | grep process_job_worker

# Check for database locks
sqlite3 mondrian.db ".databases"

# Look for startup messages in logs
grep -i "processor started\|waiting for" logs/job_service_*.log

# Check AI Advisor loading time
grep -i "loading\|ready\|health" logs/ai_advisor_service_*.log | head -20
```

**Quick Fix:**
```bash
# Restart job service with verbose logging
python3 mondrian/job_service_v2.3.py --port 5005 --db mondrian.db --debug

# Ensure AI Advisor has fully loaded
sleep 20  # Wait for AI Advisor to initialize

# Manually trigger job processing
curl -X POST http://localhost:5005/process-pending
```

---

### Issue 3: Intermittent Failures (Some Jobs Succeed, Others Hang)

**Symptom:** 50/50 success rate, random failures

**Likely Causes:**
1. **LoRA adapter loading inconsistency**
2. **GPU memory not cleaned up** between jobs
3. **Model inference timeout** on specific image combinations
4. **Race condition** in job processor

**Debug Steps:**

```bash
# Monitor GPU memory
watch -n 1 nvidia-smi

# Check for memory leaks
sqlite3 mondrian.db "SELECT status, COUNT(*) FROM jobs GROUP BY status;"

# Compare successful vs failed job patterns
sqlite3 mondrian.db "SELECT advisor, mode, status, COUNT(*) FROM jobs GROUP BY advisor, mode, status;"

# Check for timeout patterns
grep -i "timeout\|504\|503" logs/ai_advisor_service_*.log | wc -l
```

**Quick Fix:**
```bash
# Set longer timeout for LoRA mode (edit job_service_v2.3.py)
# Find: timeout=300,
# Change: timeout=600,

# Force GPU cache clearing between jobs
pkill -f ai_advisor_service
sleep 5
python3 mondrian/start_services.py --mode=lora --model-cache-clean
```

---

### Issue 4: LoRA-Specific Hanging

**Symptom:** Jobs work in baseline/rag mode but hang in lora mode

**Likely Causes:**
1. **LoRA adapter not loading properly**
2. **Adapter path incorrect**
3. **GPU memory insufficient** for LoRA inference
4. **Incompatible model version**

**Debug Steps:**

```bash
# Test adapter loading directly
curl -X POST http://localhost:5100/analyze \
  -F "image=@source/test.jpg" \
  -F "advisor=ansel" \
  -F "mode=lora" \
  --max-time 30

# Check adapter files
ls -lh adapters/ansel*/
du -sh adapters/ansel

# Verify adapter configuration
head -20 adapters/ansel/adapter_config.json

# Check service logs for adapter errors
grep -i "adapter\|lora\|load" logs/ai_advisor_service_*.log
```

**Quick Fix:**
```bash
# Use baseline mode as workaround
python3 mondrian/start_services.py --mode=baseline

# Or fall back to RAG mode
python3 mondrian/start_services.py --mode=rag

# Retrain adapter with better data
python3 train_mlx_lora.py --advisor ansel --epochs 3 --batch-size 4
```

---

## Detailed Debugging Procedures

### Procedure A: Trace a Single Job

```bash
# Get job ID from recent jobs
JOB_ID=$(sqlite3 mondrian.db "SELECT id FROM jobs ORDER BY created_at DESC LIMIT 1;")

# Monitor status
watch -n 1 "sqlite3 mondrian.db \"SELECT id, status, current_step, progress_percentage, error FROM jobs WHERE id='$JOB_ID';\""

# Check for updates in real-time
tail -f logs/job_service_*.log | grep $JOB_ID

# Get full job details
sqlite3 mondrian.db -header -column "SELECT * FROM jobs WHERE id='$JOB_ID';"
```

### Procedure B: Check Request Flow

```bash
# 1. Verify Job Service receives the request
curl -X POST http://localhost:5005/jobs \
  -F "image=@source/test.jpg" \
  -F "advisor=ansel" \
  -F "mode=lora"

# 2. Check if job was created
sqlite3 mondrian.db "SELECT id, status FROM jobs ORDER BY created_at DESC LIMIT 1;"

# 3. Monitor job status
JOB_ID=<from-above>
curl http://localhost:5005/status/$JOB_ID

# 4. Check AI Advisor directly (bypass job service)
curl -X POST http://localhost:5100/analyze \
  -F "image=@source/test.jpg" \
  -F "advisor=ansel" \
  -F "mode=lora" \
  -F "enable_rag=false" \
  --max-time 60

# 5. Check logs at each stage
tail -20 logs/job_service_*.log
tail -20 logs/ai_advisor_service_*.log
```

### Procedure C: Database Health Check

```bash
# Check for corrupted database
sqlite3 mondrian.db "PRAGMA integrity_check;"

# Check for locked tables
sqlite3 mondrian.db ".tables"
sqlite3 mondrian.db "SELECT COUNT(*) FROM jobs;"

# Find problematic jobs
sqlite3 mondrian.db "SELECT id, status, error, retry_count FROM jobs WHERE error IS NOT NULL;"

# Get statistics
sqlite3 mondrian.db "SELECT 
  status, 
  COUNT(*) as count,
  AVG(CAST((julianday(last_activity) - julianday(created_at)) * 86400 AS FLOAT)) as avg_duration_s
FROM jobs 
GROUP BY status;"
```

---

## Performance Analysis

### Measure Job Processing Time

```bash
# Check average processing time per mode
sqlite3 mondrian.db "SELECT 
  mode,
  status,
  COUNT(*) as count,
  AVG(CAST((julianday(last_activity) - julianday(created_at)) * 86400 AS FLOAT)) as avg_seconds
FROM jobs
GROUP BY mode, status
ORDER BY mode;"
```

### Identify Bottlenecks

```bash
# Which step takes longest?
sqlite3 mondrian.db "SELECT 
  current_step,
  COUNT(*) as jobs_in_step
FROM jobs
WHERE status IN ('analyzing', 'processing')
GROUP BY current_step;"

# Time distribution
sqlite3 mondrian.db "SELECT 
  CASE 
    WHEN CAST((julianday(last_activity) - julianday(created_at)) * 86400 AS FLOAT) < 5 THEN '<5s'
    WHEN CAST((julianday(last_activity) - julianday(created_at)) * 86400 AS FLOAT) < 15 THEN '5-15s'
    WHEN CAST((julianday(last_activity) - julianday(created_at)) * 86400 AS FLOAT) < 30 THEN '15-30s'
    WHEN CAST((julianday(last_activity) - julianday(created_at)) * 86400 AS FLOAT) < 60 THEN '30-60s'
    ELSE '>60s'
  END as duration_bucket,
  COUNT(*) as jobs
FROM jobs
WHERE status = 'completed'
GROUP BY duration_bucket
ORDER BY duration_bucket;"
```

---

## Emergency Recovery

### Nuclear Option: Reset Everything

```bash
# Kill all services
pkill -f "job_service\|ai_advisor\|mondrian"

# Clear jobs database
rm mondrian.db
python3 init_database.py

# Clean caches
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null

# Restart
python3 mondrian/job_service_v2.3.py --port 5005 --db mondrian.db &
python3 mondrian/start_services.py --mode=lora
```

### Selective Job Cleanup

```bash
# Delete failed jobs only
sqlite3 mondrian.db "DELETE FROM jobs WHERE status = 'failed';"

# Delete jobs from specific advisor
sqlite3 mondrian.db "DELETE FROM jobs WHERE advisor = 'ansel';"

# Delete jobs older than 1 hour
sqlite3 mondrian.db "DELETE FROM jobs WHERE datetime(created_at) < datetime('now', '-1 hour');"

# Clear all jobs (use with caution!)
sqlite3 mondrian.db "DELETE FROM jobs;"
```

---

## Log Analysis

### Watch Logs in Real-Time

```bash
# Job service logs
tail -f logs/job_service_*.log | grep -E "ERROR|WARN|processing"

# AI Advisor logs
tail -f logs/ai_advisor_service_*.log | grep -E "ERROR|timeout|loaded"

# Combined monitoring
tail -f logs/*.log | grep -E "job.*lora|processing|timeout|error" | head -50
```

### Find Specific Issues

```bash
# Find timeout errors
grep -r "timeout\|Timeout" logs/ | head -10

# Find OOM (out of memory) errors
grep -r "memory\|CUDA\|OOM" logs/ | head -10

# Find connection errors
grep -r "Connection\|refused\|refused" logs/ | head -10

# Find specific job errors
JOB_ID=<your-job-id>
grep $JOB_ID logs/*.log
```

---

## Testing & Verification

### Test Complete Flow

```bash
# 1. Create test job
JOB_ID=$(python3 -c "
import requests
with open('source/mike-shrub.jpg', 'rb') as f:
    r = requests.post('http://localhost:5005/jobs',
        files={'image': f},
        data={'advisor': 'ansel', 'mode': 'lora'})
print(r.json()['job_id'])
")

echo "Job ID: $JOB_ID"

# 2. Poll for completion (max 60 seconds)
for i in {1..30}; do
  STATUS=$(curl -s http://localhost:5005/status/$JOB_ID | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  echo "[$i/30] Status: $STATUS"
  [ "$STATUS" = "completed" ] && echo "✓ SUCCESS" && exit 0
  [ "$STATUS" = "failed" ] && echo "✗ FAILED" && exit 1
  sleep 2
done

echo "✗ TIMEOUT after 60 seconds"
exit 2
```

### Stress Test

```bash
# Submit 10 parallel jobs
for i in {1..10}; do
  python3 -c "
import requests
with open('source/mike-shrub.jpg', 'rb') as f:
    r = requests.post('http://localhost:5005/jobs',
        files={'image': f},
        data={'advisor': 'ansel', 'mode': 'lora'})
print(f'Job {i}: {r.json()[\"job_id\"][:8]}...')
  " &
done

# Monitor queue
sleep 1
watch -n 1 "sqlite3 mondrian.db 'SELECT status, COUNT(*) FROM jobs GROUP BY status;'"
```

---

## Prevention & Best Practices

1. **Monitor regularly**
   - Run `python3 monitor_lora_jobs.py` during peak usage
   - Set alerts for jobs > 5 minutes in "analyzing"

2. **Restart services daily**
   - GPU memory can fragment over time
   - Adapters may need reloading
   ```bash
   pkill -f mondrian
   sleep 5
   python3 mondrian/start_services.py --mode=lora
   ```

3. **Check logs frequently**
   - Set up log rotation: `logrotate /etc/logrotate.d/mondrian`
   - Archive logs weekly for analysis

4. **Validate adapter health**
   - Verify adapter files weekly: `ls -lh adapters/`
   - Test adapter loading: `python3 test_lora_fix.py`

5. **Size your resources**
   - For LoRA: GPU needs ~6GB VRAM
   - Monitor: `watch nvidia-smi`
   - Keep free: ≥2GB unused

---

## Support & Escalation

### If debug_lora_job_processor.py recommends retraining:
```bash
python3 train_mlx_lora.py --advisor ansel --epochs 3
python3 mondrian/start_services.py --mode=lora
python3 test_lora_fix.py  # Verify
```

### If you see "AI Advisor service not responding":
```bash
# Check if model is loading
tail -50 logs/ai_advisor_service_*.log | grep -i "loading\|qwen\|ready"

# Try increasing timeout
# Edit: mondrian/job_service_v2.3.py
# Find: max_wait_attempts = 300
# Change: max_wait_attempts = 600  # 60 seconds instead of 30
```

### If GPU memory errors appear:
```bash
# Reduce batch size or increase inference timeout
# Edit: mondrian/ai_advisor_service.py
# Look for model initialization parameters

# Or use quantization
python3 mondrian/start_services.py --mode=lora --quantize-4bit
```

---

## Quick Reference Commands

```bash
# All-in-one debug
python3 debug_lora_job_processor.py

# Real-time monitoring
python3 monitor_lora_jobs.py

# Clear stuck jobs
python3 clear_jobs.py

# Quick service restart
pkill -f mondrian && sleep 2
python3 mondrian/start_services.py --mode=lora

# Check queue size
sqlite3 mondrian.db "SELECT COUNT(*) FROM jobs WHERE status='pending';"

# List stuck jobs
sqlite3 mondrian.db "SELECT id, advisor, elapsed_minutes FROM (
  SELECT id, advisor, CAST((julianday('now') - julianday(created_at)) * 1440 AS INT) as elapsed_minutes
  FROM jobs WHERE status='analyzing'
) WHERE elapsed_minutes > 5;"

# Kill a specific job
curl -X DELETE http://localhost:5005/jobs/{job-id}

# View last error
sqlite3 mondrian.db "SELECT error FROM jobs WHERE error IS NOT NULL ORDER BY created_at DESC LIMIT 1;"
```

---

Last updated: 2026-01-16
For issues, check: logs/ directory and database at mondrian.db
