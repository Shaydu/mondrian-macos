# Restart Services with RAG Integration

## Issue Detected

The test ran but produced **identical outputs** because the running AI Advisor Service is `ai_advisor_service_v1.13.py` (old version), but we modified `ai_advisor_service.py` (new version with RAG integration).

## Solution: Restart Services

You need to stop the old services and start the new ones with RAG support.

### Step 1: Stop All Services

Find and kill the running Python services:

```bash
# Find all running Mondrian services
ps aux | grep python3 | grep -E "(ai_advisor|job_service|rag_service|caption|embedding)"

# Kill them (replace PID with actual process IDs from above)
kill <PID1> <PID2> <PID3> <PID4> <PID5>

# Or use killall (more aggressive):
killall -9 python3
```

### Step 2: Start Services in Order

**Terminal 1: Caption Service**
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 caption_service.py
```

**Terminal 2: Embedding Service**
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 embedding_service.py
```

**Terminal 3: RAG Service**
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 rag_service.py
```

**Terminal 4: AI Advisor Service (NEW VERSION WITH RAG!)**
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py --use_mlx --rag_service_url http://127.0.0.1:5400
```

**Terminal 5: Job Service (UPDATED VERSION WITH enable_rag!)**
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 job_service_v2.3.py
```

### Step 3: Verify Services Are Running

```bash
# Check all services
curl http://localhost:5200/health  # Caption Service
curl http://localhost:5300/health  # Embedding Service
curl http://localhost:5400/health  # RAG Service
curl http://localhost:5100/health  # AI Advisor Service
curl http://localhost:5005/health  # Job Service
```

**IMPORTANT**: Check that AI Advisor Service returns something like:
```json
{
  "status": "UP",
  "script": "ai_advisor_service.py",   <-- Should be .py, NOT v1.13.py
  "rag_service_url": "http://127.0.0.1:5400"  <-- NEW FIELD!
}
```

### Step 4: Run Test Again

```bash
cd /Users/shaydu/dev/mondrian-macos
python3 test_advisor_ansel_output_to_file.py
```

### Step 5: Check Logs for RAG Activity

While the test runs, watch Terminal 4 (AI Advisor Service) for these log lines:

```
[RAG] Querying RAG service for similar images (top_k=3)...
[RAG] Retrieved 3 similar images
[RAG] Augmented prompt with 3 similar images (XXX chars added)
```

And watch Terminal 3 (RAG Service) for:

```
[DEBUG] Generating caption for query image: ...
[DEBUG] Query image caption: ...
[DEBUG] Query embedding dimension: 384
[DEBUG] Found 20 results, returning top 3
```

## Alternative: Quick Health Check Script

Save this as `check_rag_integration.sh`:

```bash
#!/bin/bash
echo "Checking AI Advisor Service..."
curl -s http://localhost:5100/health | jq .

echo -e "\nExpected fields:"
echo "  - script: should be 'ai_advisor_service.py' (not v1.13.py)"
echo "  - rag_service_url: should exist"
```

Run it:
```bash
chmod +x check_rag_integration.sh
./check_rag_integration.sh
```

## Expected Behavior After Restart

### RAG-Enabled Job (enable_rag=true)

**AI Advisor Service Logs:**
```
[DEBUG] Enable RAG: True
[RAG] Querying RAG service for similar images (top_k=3)...
[RAG] Retrieved 3 similar images
[RAG] Augmented prompt with 3 similar images (567 chars added)
[DEBUG] RAG-augmented advisor prompt length: 1234 chars
```

**RAG Service Logs:**
```
[DEBUG] Generating caption for query image: mike-shrub.jpg
[DEBUG] Query image caption: This is a breathtaking, high-resolution...
[DEBUG] Query embedding dimension: 384
[DEBUG] Found 20 results, returning top 3
```

### Baseline Job (enable_rag=false)

**AI Advisor Service Logs:**
```
[DEBUG] Enable RAG: False
[DEBUG] Advisor prompt loaded, length: 567 chars
```

No RAG queries should appear in logs.

## Troubleshooting

### Services Won't Stop

```bash
# Force kill all Python processes (nuclear option)
sudo killall -9 python3

# Or reboot your Mac
sudo shutdown -r now
```

### Port Already in Use

```bash
# Find what's using port 5100
lsof -i :5100

# Kill specific process
kill -9 <PID>
```

### Still Getting Identical Outputs

1. **Check AI Service is new version:**
   ```bash
   curl http://localhost:5100/health | grep "script"
   ```
   Should show: `"script":"ai_advisor_service.py"`

2. **Manually test RAG endpoint:**
   ```bash
   curl -X POST http://localhost:5400/search_by_image \
     -F "image=@source/mike-shrub.jpg" \
     -F "top_k=3"
   ```
   Should return JSON with 3 similar images.

3. **Check enable_rag is being sent:**
   Look for this in Job Service (Terminal 5) logs:
   ```
   [JOB] Starting job ... enable_rag: True
   [JOB] Sending request to AI service with data: {'enable_rag': 'true', ...}
   ```

## Success Criteria

After restarting services and re-running the test, you should see:

1. ✅ Different feedback in RAG vs baseline outputs
2. ✅ RAG output mentions similar images or comparative language
3. ✅ RAG service logs show `/search_by_image` being called
4. ✅ AI Advisor Service logs show prompt augmentation

If outputs are STILL identical after restart, there may be a deeper issue with the prompt augmentation or the model not incorporating the context.
