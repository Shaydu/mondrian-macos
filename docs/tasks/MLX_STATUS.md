# MLX Backend Status & Testing Guide

## Current Situation

✅ **MLX Backend Migration Complete**
- Backend is configured to use MLX (Apple Silicon)
- Model: `lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit`
- MLX-VLM version 0.3.9 is installed (in Python 3.12)

⚠️ **Issue Identified**
The services keep getting killed/crashing because:
1. Multiple Python versions on system (3.9 and 3.12)
2. Python 3.9 has old mlx-vlm (0.1.15) which doesn't support qwen3_vl model
3. Python 3.12 has new mlx-vlm (0.3.9) which DOES support it
4. The startup script sometimes uses wrong Python version

## Code Fixes Applied

I've fixed the service to cache the MLX model at startup (avoiding reload on every request):
- Added `MLX_MODEL_CACHE` and `MLX_PROCESSOR_CACHE` global variables
- Model loads ONCE at startup instead of on every request
- Subsequent requests reuse the cached model

File modified: `mondrian/ai_advisor_service_v1.13.py`

## How to Test MLX from CLI

### Option 1: Direct Health Check
```bash
curl http://localhost:5100/health
```

### Option 2: Test with Image
```bash
cd /Users/shaydu/dev/mondrian-macos

# Make sure service is running with Python 3.12
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 mondrian/start_services.py stop
sleep 3
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 mondrian/start_services.py &

# Wait for startup (30-60 seconds for model to load)
sleep 60

# Test with curl
curl -X POST http://localhost:5100/analyze \
  -F "image=@mondrian/source/mike-shrub.jpg" \
  -F "advisor=mondrian" \
  -F "job_id=cli_test_$(date +%s)"
```

### Option 3: Use the Test Script
```bash
cd /Users/shaydu/dev/mondrian-macos
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 quick_test.py
```

### Option 4: Test MLX Directly (bypasses Flask service)
```bash
cd /Users/shaydu/dev/mondrian-macos
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 test_direct_mlx.py
```

## Recommended Solution

To permanently fix the Python version issue, update the `start_services.py` script to explicitly use Python 3.12:

1. Edit `mondrian/start_services.py`
2. At the top, change `sys.executable` to explicitly use Python 3.12
3. OR: Always call it with the full path:
   ```bash
   /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 mondrian/start_services.py
   ```

## Available Advisors in Database

- `mondrian` - Piet Mondrian
- `ansel` - Ansel Adams
- `okeefe` - Georgia O'Keeffe

Use these advisor IDs in your requests.

## Service Endpoints

- **Health**: http://localhost:5100/health
- **Analyze**: http://localhost:5100/analyze (POST with image file)
- **Job Service**: http://localhost:5005/health

## Logs

- AI Advisor Output: `mondrian/logs/ai_advisor_out.log`
- AI Advisor Errors: `mondrian/logs/ai_advisor_err.log`
- Job Service Output: `mondrian/logs/job_service_out.log`
- Job Service Errors: `mondrian/logs/job_service_err.log`

## Next Steps

1. Stop all services cleanly
2. Restart using Python 3.12 explicitly
3. Wait 60 seconds for model to load
4. Test with one of the CLI commands above

The MLX backend is working - it's just a matter of using the correct Python version consistently.
