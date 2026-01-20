# Mondrian Docker Deployment - Testing Guide

## Pre-Deployment Testing (Local)

### 1. Build the Image
```bash
docker build -t mondrian:latest .
```

### 2. Run Container with GPU
```bash
docker run --gpus all \
  -p 5100:5100 \
  -p 5005:5005 \
  -p 5006:5006 \
  --name mondrian-test \
  mondrian:latest
```

### 3. Wait for Services to Start
Services take 2-3 minutes to initialize. Watch the logs:
```bash
docker logs -f mondrian-test
```

Look for:
```
✓ AI Advisor service is ready - starting job processing
Summary Service initialized
Job Service ready
```

---

## Post-Deployment Testing

### Health Checks

**Test AI Advisor Service (5100):**
```bash
curl -s http://localhost:5100/health | jq .
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "advisor": "running",
    "database": "connected",
    "cuda": "available"
  }
}
```

**Test Job Service (5005):**
```bash
curl -s http://localhost:5005/health | jq .
```

**Test Summary Service (5006):**
```bash
curl -s http://localhost:5006/health | jq .
```

---

### API Testing

#### 1. Get Model Info
```bash
curl -s http://localhost:5100/model-info | jq .
```

Shows loaded model, quantization method, VRAM usage, etc.

#### 2. Create an Analysis Job

**Simple analysis:**
```bash
curl -X POST http://localhost:5005/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "/app/uploads/test_image.jpg",
    "mode": "base",
    "advisor_id": "ansel"
  }' | jq .
```

Response:
```json
{
  "job_id": "abc123def456",
  "status": "queued",
  "created_at": "2026-01-20T12:34:56Z"
}
```

#### 3. Check Job Status
```bash
curl -s http://localhost:5005/jobs/abc123def456 | jq .
```

Shows:
- `status`: queued, processing, completed, failed
- `progress`: percentage complete
- `result`: analysis output (when done)

#### 4. List All Jobs
```bash
curl -s http://localhost:5005/jobs | jq .
```

---

### Testing with Real Image

#### 1. Copy test image into container
```bash
docker cp /path/to/photo.jpg mondrian-test:/app/uploads/photo.jpg
```

#### 2. Create analysis job
```bash
curl -X POST http://localhost:5005/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "/app/uploads/photo.jpg",
    "mode": "rag",
    "advisor_id": "ansel"
  }' | jq .
```

#### 3. Poll for completion
```bash
JOB_ID="abc123def456"

while true; do
  STATUS=$(curl -s http://localhost:5005/jobs/$JOB_ID | jq -r .status)
  echo "Job Status: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    curl -s http://localhost:5005/jobs/$JOB_ID | jq .
    break
  fi
  
  sleep 5
done
```

---

### Advanced Testing

#### 1. Test Different Modes

**Base mode (no RAG, no LoRA):**
```bash
curl -X POST http://localhost:5005/jobs \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/app/uploads/photo.jpg", "mode": "base"}'
```

**RAG mode (with retrieval augmentation):**
```bash
curl -X POST http://localhost:5005/jobs \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/app/uploads/photo.jpg", "mode": "rag"}'
```

**LoRA mode (fine-tuned adapter):**
```bash
curl -X POST http://localhost:5005/jobs \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/app/uploads/photo.jpg", "mode": "lora", "adapter": "ansel"}'
```

#### 2. Test Inference Backends

Restart with different backend:

**BitsAndBytes (4-bit quantized):**
```bash
docker run --gpus all -p 5100:5100 -p 5005:5005 -p 5006:5006 \
  -e BACKEND=bnb \
  mondrian:latest
```

**vLLM (fastest):**
```bash
docker run --gpus all -p 5100:5100 -p 5005:5005 -p 5006:5006 \
  -e BACKEND=vllm \
  mondrian:latest
```

#### 3. GPU Utilization

While container is running, check GPU usage in another terminal:
```bash
watch -n 1 nvidia-smi
```

Look for:
- VRAM usage increasing during inference
- GPU utilization ramping up
- Process list showing Python processes

---

### Performance Testing

#### 1. Measure Latency
```bash
time curl -X POST http://localhost:5005/jobs \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/app/uploads/photo.jpg", "mode": "base"}' \
  > /dev/null
```

Typical times:
- First inference: 10-30 seconds (model loading + inference)
- Subsequent: 5-15 seconds (inference only)

#### 2. Test Concurrent Requests
```bash
for i in {1..5}; do
  curl -X POST http://localhost:5005/jobs \
    -H "Content-Type: application/json" \
    -d '{"image_path": "/app/uploads/photo.jpg", "mode": "base"}' &
done
wait
```

Monitor with: `docker stats mondrian-test`

#### 3. Measure Memory Usage
```bash
# Before any requests
docker stats mondrian-test --no-stream | grep mondrian-test

# During requests
docker stats mondrian-test
```

---

### Troubleshooting Tests

#### 1. Check Container Logs
```bash
# Last 100 lines
docker logs --tail 100 mondrian-test

# Real-time
docker logs -f mondrian-test

# Service-specific logs
docker exec mondrian-test tail -f /app/logs/ai_advisor_service_*.log
docker exec mondrian-test tail -f /app/logs/job_service_*.log
```

#### 2. Test Database Connectivity
```bash
docker exec mondrian-test sqlite3 mondrian.db "SELECT COUNT(*) FROM jobs;"
```

Should return a number (count of jobs in database)

#### 3. Check GPU Access
```bash
docker exec mondrian-test nvidia-smi
```

Should show GPU info inside container

#### 4. Test File Access
```bash
docker exec mondrian-test ls -la /app/uploads/
docker exec mondrian-test ls -la /app/logs/
```

---

### Integration Testing Script

Save this as `test_deployment.sh`:

```bash
#!/bin/bash
set -e

BASE_URL="${1:-http://localhost:5100}"
IMAGE_PATH="${2:-/app/uploads/test.jpg}"

echo "================================"
echo "Mondrian Deployment Test"
echo "================================"
echo ""

# Test 1: Health checks
echo "[1/5] Testing service health..."
curl -s $BASE_URL/health | jq . && echo "✓ AI Advisor healthy" || echo "✗ AI Advisor failed"
echo ""

# Test 2: Model info
echo "[2/5] Checking model info..."
curl -s $BASE_URL/model-info | jq . && echo "✓ Model info available" || echo "✗ Model info failed"
echo ""

# Test 3: Create job
echo "[3/5] Creating analysis job..."
JOB_RESPONSE=$(curl -s -X POST ${BASE_URL%:*}:5005/jobs \
  -H "Content-Type: application/json" \
  -d "{\"image_path\": \"$IMAGE_PATH\", \"mode\": \"base\"}")

JOB_ID=$(echo $JOB_RESPONSE | jq -r .job_id)
echo "✓ Job created: $JOB_ID"
echo ""

# Test 4: Check job status
echo "[4/5] Monitoring job status..."
for i in {1..30}; do
  STATUS=$(curl -s ${BASE_URL%:*}:5005/jobs/$JOB_ID | jq -r .status)
  echo "  Attempt $i: Status = $STATUS"
  
  if [ "$STATUS" = "completed" ]; then
    echo "✓ Job completed successfully"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "✗ Job failed"
    break
  fi
  
  sleep 5
done
echo ""

# Test 5: Get result
echo "[5/5] Retrieving results..."
curl -s ${BASE_URL%:*}:5005/jobs/$JOB_ID | jq .result
echo "✓ Results retrieved"
echo ""

echo "================================"
echo "Test Complete!"
echo "================================"
```

Run it:
```bash
chmod +x test_deployment.sh
./test_deployment.sh http://localhost:5100
```

---

## RunPod Specific Testing

Once deployed on RunPod, substitute the RunPod URL:

```bash
RUNPOD_URL="https://your-pod-id.runpod.io"

# Health check
curl -s $RUNPOD_URL/health | jq .

# Create job
curl -X POST $RUNPOD_URL:5005/jobs \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/app/uploads/photo.jpg", "mode": "rag"}'
```

---

## Expected Performance

| Operation | Time | GPU Memory |
|-----------|------|-----------|
| Service startup | 2-3 min | 8-10 GB |
| First inference | 10-30 sec | 10-12 GB |
| Subsequent | 5-15 sec | 10-12 GB |
| RAG retrieval | 2-5 sec | 10-12 GB |

---

## Success Criteria

✅ **Deployment is successful if:**
- [x] All services report healthy status
- [x] Model loads without CUDA errors
- [x] GPU memory shows proper allocation
- [x] Analysis jobs complete within expected time
- [x] Database persists job results
- [x] Logs are clean (no errors)
- [x] Concurrent requests are handled

❌ **If any of these fail:**
- Check logs for specific error messages
- Verify GPU drivers: `nvidia-smi`
- Verify VRAM: minimum 12GB, recommended 24GB
- Check disk space: `df -h /app`
- Verify database: `sqlite3 mondrian.db ".tables"`
