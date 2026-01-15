# How Mode is Determined - API Switch vs Startup

## Summary

**Mode is determined by API request parameter, NOT startup configuration.** Each job can have a different mode. The mode is passed per-request through the `mode` form parameter.

---

## How Mode is Determined

### 1. **Per-Request API Parameter** ✨ PRIMARY METHOD

Mode is specified when uploading an image via the `mode` form parameter:

```bash
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag" \
     http://localhost:5005/upload
```

**Valid mode values:**
- `baseline` - Standard single-pass analysis
- `rag` - Two-pass with portfolio comparison
- `lora` - Fine-tuned model analysis
- `rag+lora` - Combined approach
- `ab_test` - A/B testing

### 2. **Mode Selection Logic** (from job_service_v2.3.py, lines 1495-1506)

```python
# Extract mode parameter (baseline, rag, or lora)
mode_param = request.form.get('mode')

# Priority order:
if mode_param and mode_param in ['baseline', 'rag', 'lora']:
    mode = mode_param  # Use explicit mode parameter ✨ FIRST PRIORITY
    print(f"[UPLOAD] Mode parameter from request: '{mode_param}'")
elif enable_rag:
    mode = 'rag'  # Backward compatibility with enable_rag=true ✨ SECOND PRIORITY
    print(f"[UPLOAD] Mode derived from enable_rag: '{mode}'")
else:
    mode = 'baseline'  # Default mode ✨ THIRD PRIORITY (default)
    print(f"[UPLOAD] Mode defaulting to: '{mode}'")
```

### 3. **Mode Passing Flow**

```
API Request with mode parameter
    ↓
Job Service (/upload endpoint)
    ├─ Extracts mode from form data
    ├─ Stores mode in database
    ├─ Passes mode to job queue
    ↓
Process Job
    ├─ Retrieves mode from database
    ├─ Passes mode to AI Advisor Service
    ↓
AI Advisor Service (/analyze)
    ├─ Receives mode parameter
    ├─ Routes to appropriate strategy (baseline/rag/lora)
    ├─ Executes analysis with selected mode
    ↓
Results
    ├─ Mode stored in job record
    ├─ Mode returned in API response
    └─ Mode displayed in UI/badge
```

---

## Mode Selection Priority

### Priority Order (What takes precedence)

1. **Explicit `mode` parameter** (HIGHEST)
   ```python
   if mode_param and mode_param in ['baseline', 'rag', 'lora']:
       mode = mode_param
   ```

2. **`enable_rag` flag** (for backward compatibility)
   ```python
   elif enable_rag:
       mode = 'rag'
   ```

3. **Default to baseline** (LOWEST)
   ```python
   else:
       mode = 'baseline'
   ```

### Examples

| Request | `mode` param | `enable_rag` | Result | Notes |
|---------|-------------|--------------|--------|-------|
| `mode=lora` | `lora` | ❌ false | LORA | Explicit mode wins |
| `mode=rag` | `rag` | ❌ false | RAG | Explicit mode used |
| ❌ none | ❌ none | ✅ true | RAG | Backward compat kicks in |
| ❌ none | ❌ none | ❌ false | BASELINE | Default used |
| `mode=baseline` | `baseline` | ✅ true | BASELINE | Explicit mode overrides |

---

## NOT Determined at Startup

### What is NOT used to determine mode:

❌ **Environment variables** - No `MODE` env var
❌ **Command-line arguments** - No `--mode` startup flag
❌ **Configuration files** - No mode settings in config
❌ **Global service state** - Services don't lock to one mode

### What IS determined at startup:

✅ **LoRA adapter availability** - Model loading at startup
✅ **Model strategy** - Base model, fine-tuned model, or A/B test
✅ **Service ports and health checks**

---

## Per-Job vs Per-Service

| Aspect | Mode | Model Strategy |
|--------|------|-----------------|
| **When determined** | Per request (API call) | At startup (./start_services.py) |
| **Can change** | Every job can be different | Fixed for service lifetime |
| **Set by** | `mode` form parameter | Initialization arguments |
| **Stored where** | Database (jobs.mode) | Service memory state |
| **Example** | Job1=baseline, Job2=rag, Job3=lora | All jobs use same model |

---

## Code Flow: Mode Determination

### Job Service (job_service_v2.3.py)

```python
@app.route("/upload", methods=["POST"])
def upload():
    # Extract mode from request
    mode_param = request.form.get('mode')
    enable_rag = request.form.get('enable_rag') == 'true'
    
    # Apply priority logic
    if mode_param and mode_param in ['baseline', 'rag', 'lora']:
        mode = mode_param
    elif enable_rag:
        mode = 'rag'
    else:
        mode = 'baseline'
    
    # Store mode in database
    cursor.execute("""
        INSERT INTO jobs (..., mode) VALUES (..., ?)
    """, (..., mode))
    
    # Pass mode to job queue
    job_queue.put((job_id, filename, advisors, host_url, enable_rag, mode))
```

### Process Job (job_service_v2.3.py)

```python
def process_job(job_id, filename, advisors, host_url=None, enable_rag=False, mode='baseline'):
    # mode is passed as parameter from job queue
    print(f"[JOB] Mode: {mode}")
    
    # Send to AI Advisor Service with mode
    response = requests.post(
        f"{job_service_url}/analyze",
        files={'image': image_file},
        data={
            'advisor': advisor,
            'mode': mode,  # Pass mode to AI service
            'job_id': job_id,
            'job_service_url': job_service_url
        }
    )
```

### AI Advisor Service (ai_advisor_service.py)

```python
@app.route("/analyze", methods=["POST"])
def analyze():
    # Extract mode from request
    mode_param = request.form.get("mode")
    enable_rag = request.form.get("enable_rag") == 'true'
    
    # Apply same priority logic
    if mode_param and mode_param in ['baseline', 'rag', 'lora']:
        mode = mode_param
    elif enable_rag:
        mode = 'rag'
    else:
        mode = 'baseline'
    
    # Route to appropriate strategy
    from mondrian.strategies.context import AnalysisContext
    context = AnalysisContext()
    context.set_strategy(mode, advisor)  # Use mode to select strategy
    result = context.analyze(image_path, advisor)
```

---

## API Examples

### Example 1: Upload with explicit mode

```bash
# Upload with LORA mode
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=lora" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload

# Response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000 (lora)",
#   "status": "queued",
#   "mode": "lora"
# }
```

### Example 2: Upload with RAG mode

```bash
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload

# Response: mode will be "rag"
```

### Example 3: Upload with no mode (defaults to baseline)

```bash
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload

# Response: mode will be "baseline"
```

### Example 4: Backward compatibility with enable_rag

```bash
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "enable_rag=true" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload

# Response: mode will be "rag" (derived from enable_rag flag)
```

---

## What Controls Model Selection

### At Startup

The **model strategy** is set via startup arguments (NOT mode):

```bash
# Start AI Advisor Service
python3 ai_advisor_service.py \
    --port 5100 \
    --mlx_model "lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit" \
    --lora_path "/path/to/lora/adapter" \
    --job_service_url "http://127.0.0.1:5005"
```

This determines if LoRA is **available** for the service.

### At Request Time

The **mode** is specified via API parameter:

```bash
# Tell the service which flow to use
-F "mode=lora"  # Use LoRA if available
-F "mode=rag"   # Use RAG flow
-F "mode=baseline"  # Use baseline only
```

This determines which flow to **use** for this specific job.

---

## Summary Table

| Question | Answer | Where |
|----------|--------|-------|
| **When is mode determined?** | Per API request | At request time |
| **How is mode specified?** | `mode` form parameter | In /upload or /analyze |
| **Can different jobs have different modes?** | Yes ✅ | Each job independently |
| **Is mode set at startup?** | No ❌ | It's per-request |
| **What happens if mode not specified?** | Defaults to baseline | Priority logic |
| **Can you change mode mid-service?** | Yes ✅ | Next request can use different mode |
| **Is there a global mode setting?** | No ❌ | Mode is always per-request |

---

## Startup vs Runtime

### **Startup** (Service Initialization)

Controls:
- ✅ Model availability (which models are loaded)
- ✅ LoRA adapter availability
- ✅ Service ports and health checks

Does NOT determine:
- ❌ Which mode to use per job
- ❌ Per-request flow selection

### **Runtime** (Per Request)

Controls:
- ✅ Which mode to use for this job
- ✅ Analysis strategy selection
- ✅ Flow execution path

Does NOT control:
- ❌ Which models are available
- ❌ Service infrastructure

---

## Key Takeaway

**Mode is 100% determined by the API request parameter, NOT startup configuration.**

Each job can choose its own mode independently:
- Job 1: baseline
- Job 2: rag
- Job 3: lora
- Job 4: rag
- Job 5: baseline

All from the same service without restart or reconfiguration!

This allows flexible runtime control while keeping service configuration stable and efficient.
