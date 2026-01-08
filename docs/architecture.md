# Mondrian System Architecture

## Overview

Mondrian is a photography composition analysis system that uses **local MLX vision models** running natively on Apple Silicon to provide creative feedback from multiple artistic perspectives.

**Current Stack**: Python 3.12 + MLX + Qwen3-VL-4B-Instruct (4-bit quantized) on macOS

---

## System Architecture

```
┌─────────────────┐
│   iOS Client    │  (SwiftUI App)
│   Mac Client    │  (curl/API)
└────────┬────────┘
         │ HTTP
         ▼
┌──────────────────────────────────────────────────────────┐
│                   macOS Server (localhost)               │
│                                                          │
│  ┌──────────────────┐         ┌──────────────────────┐  │
│  │  Job Service     │────────►│ AI Advisor Service   │  │
│  │  Port: 5005      │  HTTP   │ Port: 5100           │  │
│  │                  │         │                      │  │
│  │ - Job tracking   │         │ - Prompt assembly    │  │
│  │ - Image optimize │         │ - MLX inference      │  │
│  │ - Status mgmt    │         │ - HTML formatting    │  │
│  │ - SSE streaming  │         │ - Model caching      │  │
│  └────────┬─────────┘         └───────────┬──────────┘  │
│           │                               │             │
│           │                               ▼             │
│           │                   ┌──────────────────────┐  │
│           │                   │   MLX Vision Model   │  │
│           │                   │   (Apple Silicon)    │  │
│           │                   │                      │  │
│           │                   │ - Qwen3-VL-4B-4bit   │  │
│           │                   │ - mlx_vlm library    │  │
│           │                   │ - Metal acceleration │  │
│           │                   │ - Cached in memory   │  │
│           │                   └──────────────────────┘  │
│           ▼                                             │
│  ┌──────────────────┐         ┌──────────────────────┐  │
│  │  SQLite DB       │         │  Filesystem          │  │
│  │  mondrian.db     │         │                      │  │
│  │                  │         │  source/*.jpg (input)│  │
│  │ - Job status     │         │  analysis/*.html(out)│  │
│  │ - Advisors       │         │  prompts/*.md (cfg)  │  │
│  │ - Focus areas    │         │  thumbnails/ (1320px)│  │
│  │ - LLM outputs    │         │                      │  │
│  │ - Status history │         │                      │  │
│  └──────────────────┘         └──────────────────────┘  │
│                                                          │
│  ┌──────────────────┐                                    │
│  │ Monitoring       │  (Optional)                        │
│  │ Service          │                                    │
│  │ Port: 5007       │                                    │
│  │                  │                                    │
│  │ - Health checks  │                                    │
│  │ - Job cleanup    │                                    │
│  │ - Service restart│                                    │
│  │ - Web dashboard  │                                    │
│  └──────────────────┘                                    │
└──────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Runtime
- **Language**: Python 3.12
- **Platform**: macOS (Apple Silicon - M1/M2/M3)
- **ML Framework**: MLX (Apple's Machine Learning framework)
- **Vision Model**: Qwen3-VL-4B-Instruct-MLX-4bit
- **Database**: SQLite 3
- **Web Framework**: Flask

### Key Libraries
```python
# ML/Vision
mlx-vlm==0.3.9+         # MLX vision-language models
mlx>=0.4.0              # Apple's ML framework
Pillow>=10.0.0          # Image processing

# Web/API
Flask>=2.3.0            # HTTP services
requests>=2.31.0        # Inter-service communication

# Database
sqlite3                 # Built-in SQLite support
```

### Model Details
- **Name**: `lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit`
- **Size**: ~2.4GB (4-bit quantization)
- **Parameters**: 4B
- **Context**: Vision + language understanding
- **Acceleration**: Metal (Apple Silicon GPU)
- **Loading**: Cached in memory at service startup (~30-60s first load)

---

## Components

### 1. Job Service ([job_service_v2.3.py](../mondrian/job_service_v2.3.py))

**Purpose**: Main orchestration service - handles image uploads, job tracking, progress updates, and coordinates multi-advisor analysis.

**Port**: 5005

**Key Endpoints**:
```
POST   /upload              - Upload image and create job
GET    /status/<job_id>     - Get job status with progress
GET    /stream/<job_id>     - Server-Sent Events (SSE) for real-time updates
GET    /analysis/<job_id>   - Get completed analysis (HTML)
GET    /summary/<job_id>    - Get critical recommendations summary
GET    /image/<filename>    - Serve optimized images (1320px)
GET    /jobs                - List recent jobs
GET    /health              - Health check
```

**Workflow**:
1. **Upload** - Receives image via multipart/form-data
2. **Optimize** - Resize to 1320px max width (optimized for iPhone Pro Max)
3. **Process Advisors** - Sequential analysis by each selected advisor:
   - Ansel Adams, Georgia O'Keeffe, Piet Mondrian, Frank Gehry, Vincent van Gogh
4. **Stream Progress** - Real-time SSE updates with:
   - `progress_percentage` (0-100)
   - `current_step` (human-readable status)
   - `llm_thinking` (model's current analysis focus)
   - `current_advisor` / `total_advisors`
5. **Generate Output** - Format HTML with all 8 feedback dimensions per advisor
6. **Store Results** - Save to database and filesystem

**Progress Phases**:
- **0-10%**: Image processing and optimization
- **10-90%**: Advisor analysis (distributed across advisors)
- **90-100%**: Finalizing HTML output

**Configuration**:
```bash
python3 mondrian/job_service_v2.3.py \
  --port 5005 \
  --db mondrian.db \
  --ai_service_url http://127.0.0.1:5100/analyze
```

---

### 2. AI Advisor Service ([ai_advisor_service_v1.13.py](../mondrian/ai_advisor_service_v1.13.py))

**Purpose**: Interfaces with MLX vision model to generate creative feedback. Caches model in memory for fast repeated inference.

**Port**: 5100

**Key Endpoints**:
```
POST   /analyze            - Analyze image with specific advisor
GET    /health             - Health check with model info
```

**Backend Options**:
- **MLX (default)**: Native Apple Silicon inference via `mlx_vlm`
- **Ollama (legacy)**: External Ollama server (deprecated, kept for compatibility)

**MLX Implementation**:
```python
# Model cached at startup (global variables)
MLX_MODEL_CACHE = None
MLX_PROCESSOR_CACHE = None

# Load once at service startup (~30-60 seconds)
from mlx_vlm import load, generate
model, processor = load("lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit")

# Subsequent requests reuse cached model (fast)
response = generate(model, processor, image, prompt)
```

**Workflow**:
1. **Receive Request** - advisor ID, job ID, image (multipart file)
2. **Load Prompts** - System prompt + advisor-specific prompt from database
3. **Compose Prompt** - Merge prompts with HTML output structure
4. **Run Model** - Generate analysis via MLX (uses cached model)
5. **Stream Updates** - Send "thinking" updates to Job Service every 0.5s
6. **Return HTML** - Formatted critique with 8 feedback dimensions

**Prompt Structure**:
```python
full_prompt = (
    SYSTEM_PROMPT.replace("<AdvisorName>", advisor_name)  # HTML structure
    + "\n\n"
    + advisor_prompt  # Advisor-specific guidance
    + "\n\nAnalyze the provided image."
)
```

**Configuration**:
```bash
python3 mondrian/ai_advisor_service_v1.13.py \
  --port 5100 \
  --db mondrian.db \
  --model lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit \
  --backend mlx \
  --model_timeout 600
```

**Performance**:
- **First request**: 30-60s (model loading + inference)
- **Subsequent requests**: 20-40s (inference only, model cached)
- **Memory**: ~3-4GB resident for cached model

---

### 3. MLX Vision Model (In-Process)

**Purpose**: On-device vision-language model running via Apple's MLX framework.

**Integration**: Runs as Python library within AI Advisor Service process (not a separate service)

**Model**: Qwen3-VL-4B-Instruct-MLX-4bit
- 4-bit quantization for efficiency
- Optimized for Apple Silicon Metal acceleration
- Loaded once at startup, cached in memory
- ~2.4GB model file size

**Advantages over Ollama**:
- ✅ No external server required
- ✅ Faster startup (no TCP overhead)
- ✅ Native Metal acceleration on Apple Silicon
- ✅ Lower memory footprint
- ✅ Direct Python integration

**Library**: `mlx-vlm` (>=0.3.9)
- Provides `load()`, `generate()`, `apply_chat_template()`
- Handles image preprocessing automatically
- Supports streaming (though we return full response)

---

### 4. Monitoring Service ([monitoring_service.py](../mondrian/monitoring_service.py)) *(Optional)*

**Purpose**: Comprehensive service monitoring, health checks, and job cleanup.

**Port**: 5007 (web dashboard)

**Features**:
- **Health Monitoring**: Continuous health checks for Job Service and AI Advisor
- **Job Cleanup**: Auto-mark timed-out jobs as errored (15min timeout)
- **Service Restart**: Automatic restart of failed services
- **Web Dashboard**: Real-time monitoring at `http://127.0.0.1:5007/monitor`

**Configuration** ([monitoring_config.json](../mondrian/monitoring_config.json)):
```json
{
  "cleanup": {
    "enabled": true,
    "interval": 60,
    "job_timeout": 900
  },
  "monitoring": {
    "health_check_interval": 30,
    "job_check_interval": 5
  }
}
```

---

### 5. Database ([mondrian.db](../mondrian.db))

**Schema**:

**`advisors` table**:
```sql
CREATE TABLE advisors (
    id TEXT PRIMARY KEY,           -- 'ansel', 'okeefe', 'mondrian', etc.
    name TEXT NOT NULL,            -- 'Ansel Adams'
    bio TEXT NOT NULL,
    prompt TEXT,                   -- Advisor-specific prompt
    years TEXT,                    -- '1902-1984'
    created_at TEXT,
    updated_at TEXT
);
```

**`focus_areas` table**:
```sql
CREATE TABLE focus_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisor_id TEXT NOT NULL,
    title TEXT NOT NULL,          -- 'Black & White Photography'
    description TEXT NOT NULL,     -- 'Mastery of contrast...'
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (advisor_id) REFERENCES advisors(id)
);
```

**`jobs` table**:
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,           -- UUID
    filename TEXT,                 -- 'image.jpg'
    advisor TEXT,                  -- 'ansel' or 'all'
    status TEXT,                   -- 'started', 'processing', 'analyzing', 'done', 'error'
    current_step TEXT,             -- Human-readable status
    llm_thinking TEXT,             -- Real-time model thinking
    analysis_markdown TEXT,        -- Final HTML output
    llm_outputs TEXT,              -- JSON map: {advisor: html}
    prompt TEXT,                   -- Full prompt sent to model
    current_advisor INTEGER,       -- 1-3
    total_advisors INTEGER,        -- 3
    step_phase TEXT,               -- 'image_processing', 'advisor_analysis', etc.
    progress_percentage INTEGER DEFAULT 0,  -- 0-100
    status_history TEXT,           -- JSON array of updates
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT,
    last_activity TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**`config` table**:
```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT
);
```

**Stored Configuration**:
- `system_prompt`: Main system prompt with HTML structure (stored in DB, not files)

---

## Data Flow

### Complete Analysis Flow

```
1. iOS/Mac Client
   ↓ POST /upload {image: file, advisor: "all"}

2. Job Service (Port 5005)
   ↓ Create job record
   ↓ Save image to source/
   ↓ Optimize image (resize to 1320px)
   ↓ Save to thumbnails/

3. For each advisor (Ansel, O'Keeffe, Mondrian, Gehry, Van Gogh):
   ↓ POST /analyze {advisor, job_id, image_file}

4. AI Advisor Service (Port 5100)
   ↓ Load advisor prompt from database
   ↓ Compose full prompt
   ↓ Run MLX model (cached)
   ↓ Stream "thinking" updates to Job Service
   ↓ Return HTML analysis

5. Job Service
   ↓ Collect all advisor outputs
   ↓ Format combined HTML
   ↓ Store in analysis/
   ↓ Update job status to "done"

6. Client
   ↓ GET /analysis/{job_id}
   ↓ Display HTML in WebView
```

### Real-Time Progress Updates (SSE)

```
Client opens: EventSource("http://127.0.0.1:5005/stream/{job_id}")

Job Service emits:
- status_update: {status, current_step, progress_percentage}
- thinking_update: {llm_thinking}
- advisor_update: {current_advisor, total_advisors}
- completion: {status: "done"}

Client closes EventSource on "completion" event
```

---

## Advisors

**Available Advisors** (stored in `advisors` table):

1. **Ansel Adams** (`ansel`) - Photographer, 1902-1984
   - Focus: Tonal range, Zone System, landscape composition, dramatic light

2. **Georgia O'Keeffe** (`okeefe`) - Painter, 1887-1986
   - Focus: Close-up abstraction, bold colors, organic forms, simplification

3. **Piet Mondrian** (`mondrian`) - Painter, 1872-1944
   - Focus: Geometric abstraction, primary colors, asymmetric balance, grid harmony

4. **Frank Gehry** (`gehry`) - Architect, 1929-
   - Focus: Deconstructivist forms, spatial dynamics, material expression, sculptural volumes

5. **Vincent van Gogh** (`vangogh`) - Painter, 1853-1890
   - Focus: Expressive brushwork, emotional color, swirling motion, intense contrasts

**Feedback Dimensions** (all advisors provide these 8):
1. Composition
2. Lighting
3. Focus & Sharpness
4. Color Harmony
5. Subject Isolation
6. Depth & Perspective
7. Visual Balance
8. Emotional Impact

---

## File Structure

```
mondrian-macos/
├── mondrian/
│   ├── job_service_v2.3.py          # Main orchestration
│   ├── ai_advisor_service_v1.13.py  # MLX inference
│   ├── monitoring_service.py        # Health checks & cleanup
│   ├── config.py                    # Environment config
│   ├── sqlite_helper.py             # Database utilities
│   ├── prompts/
│   │   ├── system.md                # HTML structure (also in DB)
│   │   ├── ansel.md                 # Advisor prompts (also in DB)
│   │   ├── okeefe.md
│   │   ├── mondrian.md
│   │   ├── gehry.md
│   │   └── vangogh.md
│   ├── source/                      # Uploaded images
│   ├── thumbnails/                  # Optimized (1320px)
│   ├── analysis/                    # HTML outputs
│   └── logs/                        # Service logs
├── mondrian.db                      # SQLite database
├── init_database.py                 # Database initialization
├── start_services.sh                # Service startup script
└── docs/
    └── architecture.md              # This file
```

---

## Startup

### Recommended Startup (MLX Backend)

```bash
# From project root
cd /Users/shaydu/dev/mondrian-macos

# Ensure Python 3.12 is used (required for mlx-vlm 0.3.9+)
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 mondrian/start_services.py

# Or if Python 3.12 is default:
python3 mondrian/start_services.py
```

**Startup Sequence**:
1. Initialize database (if needed)
2. Start AI Advisor Service (port 5100)
   - Loads MLX model (30-60s)
   - Caches in memory
3. Start Job Service (port 5005)
4. Health checks confirm both services ready
5. System ready to accept requests

**First Request Timing**:
- If model already cached: 20-40s
- If model needs loading: 50-100s

---

## Environment Variables

**Configuration** ([mondrian/config.py](../mondrian/config.py)):

```bash
# Network
MONDRIAN_HOST=127.0.0.1      # Local only (iOS connects via USB/network)

# Ports
JOB_SERVICE_PORT=5005
AI_ADVISOR_PORT=5100

# Model
MODEL_NAME=lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit

# Database
DATABASE_PATH=mondrian.db

# Timeouts
MODEL_TIMEOUT=600            # 10 minutes max per inference
JOB_TIMEOUT=900              # 15 minutes max per job

# Monitoring
HEALTH_CHECK_INTERVAL=30
JOB_CHECK_INTERVAL=5
CLEANUP_ENABLED=true
CLEANUP_INTERVAL=60
```

---

## Performance Characteristics

### Timing
- **Image optimization**: ~100-500ms
- **Model inference (cached)**: 20-40 seconds per advisor
- **Model inference (first load)**: 50-100 seconds
- **Total job time (3 advisors)**: ~60-120 seconds

### Resource Usage
- **Memory**: 3-4GB (MLX model cached in RAM)
- **GPU**: Metal acceleration on Apple Silicon (M1/M2/M3)
- **Disk**: Minimal (~100KB-1MB per image, ~100KB per analysis HTML)

### Scalability
- **Current**: Sequential processing (one job at a time)
- **Bottleneck**: MLX model inference (20-40s per advisor)
- **Optimization**: Model cached in memory = fastest possible on-device inference

---

## iOS Integration

### Recommended Flow

**1. Upload & Stream**:
```swift
// Upload image
POST /upload
  - image: Data
  - advisor: "all"
  - auto_analyze: true

→ Returns: {job_id, stream_url, status_url}

// Open SSE stream
EventSource(stream_url)
  - status_update: Update progress bar
  - thinking_update: Show live feedback
  - completion: Fetch results
```

**2. Retrieve Results**:
```swift
// After "completion" event
GET /summary/{job_id}     // Fast, top 5 recommendations
GET /analysis/{job_id}    // Full HTML analysis

// Display in WebView with iOS CSS
```

### SSE Event Types

```json
// status_update
{
  "status": "analyzing",
  "current_step": "Summoning Ansel Adams",
  "progress_percentage": 45,
  "current_advisor": 2,
  "total_advisors": 3
}

// thinking_update
{
  "llm_thinking": "Analyzing tonal range and composition balance..."
}

// completion
{
  "status": "done",
  "job_id": "abc-123"
}
```

---

## Migration from Ollama

**Previous Architecture**: Ollama server running separately, accessed via HTTP API

**Current Architecture**: MLX library integrated directly into AI Advisor Service

**Benefits**:
- ✅ No external dependencies (no Ollama server to manage)
- ✅ Faster startup (no TCP overhead)
- ✅ Native Apple Silicon optimization
- ✅ Simpler deployment (fewer moving parts)
- ✅ Lower memory footprint

**Backwards Compatibility**:
- Ollama backend still available via `--backend ollama` flag
- Legacy code preserved in `ai_advisor_service_v1.13.py`
- Default is now `--backend mlx`

---

## Logging

**Log Files** ([mondrian/logs/](../mondrian/logs/)):

```
ai_advisor_out.log           # AI Advisor stdout (model loading, inference)
ai_advisor_err.log           # AI Advisor errors
job_service_out.log          # Job Service stdout (job tracking, progress)
job_service_err.log          # Job Service errors
monitoring_service.log       # Health checks, cleanup, restarts
```

**Log Format**:
```
[INFO] AI Advisor Service v1.13-BASE64-HTTP-MLX starting...
[INFO] Backend: mlx
[INFO] Model: lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit
[INFO] Pre-loading MLX model at startup...
[INFO] ✓ MLX model loaded and cached successfully!
```

---

## Testing

### Health Checks

```bash
# Check AI Advisor
curl http://127.0.0.1:5100/health

# Check Job Service
curl http://127.0.0.1:5005/health
```

### End-to-End Test

```bash
# Upload image
curl -F "image=@source/test.jpg" \
     -F "advisor=ansel" \
     http://127.0.0.1:5005/upload

# Get status
curl http://127.0.0.1:5005/status/{job_id}

# Get results
curl http://127.0.0.1:5005/analysis/{job_id}
```

### Direct MLX Test

```bash
# Test MLX inference directly
python3 test_direct_mlx.py
```

---

## Troubleshooting

### Issue: Services won't start

**Solution**: Ensure Python 3.12 is used (MLX requires recent Python)
```bash
# Check Python version
python3 --version  # Should be 3.12.x

# Use explicit path if needed
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 mondrian/start_services.py
```

### Issue: MLX model not found

**Solution**: Model is auto-downloaded on first use
```bash
# First run will download ~2.4GB model
# Wait 2-5 minutes for download + loading
# Check logs: tail -f mondrian/logs/ai_advisor_out.log
```

### Issue: Slow first request

**Expected**: First request takes 50-100s (model loading + inference)
**Subsequent requests**: 20-40s (model cached)

### Issue: Memory errors

**Solution**: Ensure sufficient RAM (8GB+ recommended)
```bash
# Check memory
top -l 1 | grep PhysMem
```

---

## Future Enhancements

### Planned Features
1. **RAG + Grounding**: Retrieve relevant artistic principles based on image content
2. **Multi-image analysis**: Compare multiple images
3. **Batch processing**: Queue multiple jobs
4. **Result caching**: Skip analysis for identical images
5. **GPU monitoring**: Track Metal performance
6. **API authentication**: Production-ready security

### RAG Implementation (Planned)
- **Image captioning**: Lightweight model for quick scene description
- **Principle retrieval**: Vector similarity search (4-6 principles per advisor)
- **Enhanced prompts**: Inject relevant principles into analysis context
- **No client changes**: All improvements server-side only

See [RAG Implementation Plan](../.claude/plans/toasty-giggling-seal.md) for details.

---

## Dependencies

### Python Packages ([requirements.txt](../mondrian/requirements.txt))

```txt
# ML/Vision
mlx>=0.4.0
mlx-vlm>=0.3.9
Pillow>=10.0.0

# Web/API
Flask>=2.3.0
requests>=2.31.0

# Database (built-in)
# sqlite3

# Utilities
PyYAML>=6.0
```

### System Requirements
- **OS**: macOS (Apple Silicon - M1/M2/M3)
- **Python**: 3.12+
- **RAM**: 8GB+ (recommended 16GB+)
- **Disk**: 5GB+ (model + dependencies)

---

## Network Topology

```
iOS Device (connected via USB/WiFi)
    ↓
Mac (127.0.0.1 or local network IP)
    :5005 (Job Service)
    :5100 (AI Advisor Service)
    :5007 (Monitoring - optional)
```

**Connection Methods**:
- **USB**: iOS connects to Mac's localhost via USB relay
- **WiFi**: iOS connects to Mac's local IP (e.g., 192.168.1.x)
- **Local only**: Services listen on 127.0.0.1 (localhost)

---

## Security Notes

**Current State**: Development mode, no authentication

**Recommendations for Production**:
1. Add API key authentication
2. Enable HTTPS/TLS
3. Add rate limiting
4. Implement user quotas
5. Sanitize file uploads
6. Add CORS restrictions

---

## Version History

- **v1.13**: MLX backend with model caching, base64 image encoding
- **v2.3**: Job service with SSE streaming, progress tracking, multi-advisor support
- **Current**: MLX-first architecture, Ollama optional legacy support

---

## References

- **MLX Framework**: https://github.com/ml-explore/mlx
- **MLX-VLM**: https://github.com/Blaizzy/mlx-vlm
- **Qwen3-VL Model**: https://huggingface.co/lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit
- **Flask Documentation**: https://flask.palletsprojects.com/

---

**Last Updated**: 2026-01-08
**Author**: Mondrian Development Team
**Stack**: Python 3.12 + MLX + Qwen3-VL-4B on Apple Silicon
