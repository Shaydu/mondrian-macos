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
         │ HTTP (mode: baseline/rag/lora)
         ▼
┌──────────────────────────────────────────────────────────┐
│                   macOS Server (localhost)               │
│                                                          │
│  ┌──────────────────┐         ┌──────────────────────┐  │
│  │  Job Service     │────────►│ AI Advisor Service   │  │
│  │  Port: 5005      │  HTTP   │ Port: 5100           │  │
│  │                  │         │                      │  │
│  │ - Job tracking   │         │ - Strategy selection │  │
│  │ - Image optimize │         │ - Fallback chain     │  │
│  │ - Status mgmt    │         │ - Prompt assembly    │  │
│  │ - SSE streaming  │         │ - HTML formatting    │  │
│  └────────┬─────────┘         └───────────┬──────────┘  │
│           │                               │             │
│           │                               ▼             │
│           │                   ┌──────────────────────┐  │
│           │                   │ Analysis Strategies  │  │
│           │                   │   (user selects)     │  │
│           │                   │                      │  │
│           │                   │ • LoRA Strategy      │  │
│           │                   │   (Fine-tuned)       │  │
│           │                   │                      │  │
│           │                   │ • RAG Strategy       │  │
│           │                   │   (w/ Retrieval)     │  │
│           │                   │                      │  │
│           │                   │ • Baseline Strategy  │  │
│           │                   │   (Prompt only)      │  │
│           │                   │                      │  │
│           │                   └───────────┬──────────┘  │
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
│           │                   │ - LoRA adapters      │  │
│           │                   └──────────────────────┘  │
│           │                                             │
│           │                   ┌──────────────────────┐  │
│           │                   │  RAG System (v2.4)   │  │
│           │                   │                      │  │
│           │       ┌───────────┤ Caption Service      │  │
│           │       │           │ Port: 5200           │  │
│           │       │           └──────────┬───────────┘  │
│           │       │                      │             │
│           │       │           ┌──────────▼───────────┐  │
│           │       │           │ Embedding Service    │  │
│           │       │           │ Port: 5300           │  │
│           │       │           └──────────┬───────────┘  │
│           │       │                      │             │
│           │       │           ┌──────────▼───────────┐  │
│           │       └──────────►│  RAG Service         │  │
│           │                   │  Port: 5400          │  │
│           │                   │                      │  │
│           │                   │ - Index images       │  │
│           │                   │ - Semantic search    │  │
│           │                   └──────────┬───────────┘  │
│           ▼                               ▼             │
│  ┌──────────────────┐         ┌──────────────────────┐  │
│  │  SQLite DB       │         │  Filesystem          │  │
│  │  mondrian.db     │         │                      │  │
│  │                  │         │  source/*.jpg (input)│  │
│  │ - Job status     │         │  analysis/*.html(out)│  │
│  │ - Advisors       │         │  prompts/*.md (cfg)  │  │
│  │ - Focus areas    │         │  thumbnails/ (1320px)│  │
│  │ - LLM outputs    │         │  adapters/ (LoRA)    │  │
│  │ - Status history │         │                      │  │
│  │ - Image captions │◄────────┤  (RAG integration)   │  │
│  │ - Embeddings     │         │                      │  │
│  │ - Dim. profiles  │         │                      │  │
│  └──────────────────┘         └──────────────────────┘  │
│                                                          │
│  ┌──────────────────┐                                    │
│  │ Monitoring       │  (v2.4-MONITORING-RAG)             │
│  │ Service          │                                    │
│  │ Port: 5007       │                                    │
│  │                  │                                    │
│  │ - Health checks  │  Manages 5 services:               │
│  │ - Job cleanup    │  • Caption (5200)                  │
│  │ - Service restart│  • Embedding (5300)                │
│  │ - Web dashboard  │  • RAG (5400)                      │
│  │ - Auto-startup   │  • AI Advisor (5100)               │
│  │                  │  • Job Service (5005)              │
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

### 4. Analysis Strategies ([mondrian/strategies/](../mondrian/strategies/))

**Purpose**: Implement three analysis modes using Strategy Pattern for flexible, extensible analysis approaches.

**Architecture**: Three independent strategies that clients can select based on their needs.

#### Strategy Overview

| Strategy | Description | Availability | Use Case |
|----------|-------------|--------------|----------|
| **Baseline** | Single-pass with prompt only | Always available | Default, fast analysis |
| **RAG** | Two-pass with retrieval context | Requires dimensional profiles | Comparative analysis with reference images |
| **LoRA** | Single-pass with fine-tuned adapter | Requires trained adapter | Domain-specific, learned preferences |

#### 4a. BaselineStrategy ([baseline.py](../mondrian/strategies/baseline.py))

**Mode**: `baseline`

**Description**: Traditional single-pass analysis using only the advisor prompt and system instructions.

**Workflow**:
1. Load advisor prompt from database
2. Compose full prompt with system instructions
3. Run MLX model inference
4. Parse JSON response
5. Return `AnalysisResult`

**Availability**: Always available (no prerequisites)

**Performance**: 20-40s per analysis (fastest mode)

#### 4b. RAGStrategy ([rag.py](../mondrian/strategies/rag.py))

**Mode**: `rag`

**Description**: Two-pass analysis that retrieves similar reference images and their dimensional profiles to provide comparative context.

**Workflow**:
1. Load advisor prompt from database
2. **First pass**: Quick analysis to get dimensional scores
3. **Retrieve**: Find similar images using dimensional similarity
4. **Augment**: Enhance prompt with dimensional profiles of similar images
5. **Second pass**: Generate analysis with comparative context
6. Parse JSON response
7. Return `AnalysisResult` with similarity metadata

**Availability**: Requires dimensional profiles in database for the advisor

**Database Requirement**:
```sql
SELECT COUNT(*) FROM dimensional_profiles
WHERE advisor_id = 'ansel'
```

**Performance**: 40-80s per analysis (two model passes)

#### 4c. LoRAStrategy ([lora.py](../mondrian/strategies/lora.py))

**Mode**: `lora`

**Description**: Single-pass analysis using a fine-tuned LoRA adapter that has learned the advisor's aesthetic preferences from reference images.

**Workflow**:
1. Check if adapter exists for advisor (`adapters/{advisor_id}/adapters.safetensors`)
2. Load base model + apply LoRA adapter (cached after first use)
3. Compose full prompt
4. Run inference with fine-tuned model
5. Parse JSON response
6. Return `AnalysisResult` with adapter metadata

**Availability**: Requires trained adapter file

**Adapter Structure**:
```
adapters/
├── ansel/
│   ├── adapters.safetensors    # LoRA weights (~150MB)
│   └── adapter_config.json      # Configuration
├── okeefe/
│   └── ...
└── mondrian/
    └── ...
```

**Model Loading**:
```python
from mlx_vlm import load
from mlx_vlm.trainer.utils import apply_lora_layers

# Load base model
model, processor = load("lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit")

# Apply LoRA adapter
model = apply_lora_layers(model, "adapters/ansel")
```

**Caching**: LoRA models are cached globally per advisor (avoids reloading on each request)

**Performance**: 25-45s per analysis (slightly slower than baseline due to adapter overhead)

#### AnalysisResult Structure

All strategies return a standardized `AnalysisResult` dataclass:

```python
@dataclass
class AnalysisResult:
    dimensional_analysis: Dict[str, Any]  # 8 dimensions with scores and comments
    overall_grade: str                     # Letter grade (A+, A, A-, B+, etc.)
    mode_used: str                         # Actual mode used ("baseline", "rag", or "lora")
    advisor_id: str                        # Advisor identifier
    metadata: Dict[str, Any]               # Strategy-specific metadata
```

**Example Response**:
```json
{
  "dimensional_analysis": {
    "composition": {"score": 8, "comment": "..."},
    "lighting": {"score": 7, "comment": "..."},
    ...
  },
  "overall_grade": "A-",
  "mode_used": "rag",
  "advisor_id": "ansel",
  "metadata": {
    "similar_images_count": 5,
    "raw_response_length": 2847
  }
}
```

#### AnalysisContext ([context.py](../mondrian/strategies/context.py))

**Purpose**: Manages strategy selection and execution.

**Usage**:
```python
from mondrian.strategies import AnalysisContext

# Create context
context = AnalysisContext()

# Set strategy (user-selected mode)
context.set_strategy("rag", "ansel")

# Execute analysis
result = context.analyze(
    image_path="source/photo.jpg",
    advisor_id="ansel",
    thinking_callback=lambda msg: print(f"[Thinking] {msg}")
)

# Access results
print(f"Grade: {result.overall_grade}")
print(f"Mode: {result.mode_used}")
```

**API Integration**:
```python
POST /analyze
{
  "image": "<base64>",
  "advisor_id": "ansel",
  "mode": "rag"  # or "baseline" or "lora"
}

Response:
{
  "analysis": {...},
  "mode_used": "rag",
  "metadata": {...}
}
```

#### Strategy Selection Logic

Clients specify mode in request → Service validates availability → Returns error if unavailable

**No automatic fallback** - clients must explicitly choose mode

**Availability Check**:
```python
# Check which modes are available for an advisor
availability = AnalysisContext.get_available_modes("ansel")
# {"baseline": True, "rag": True, "lora": False}
```

---

### 5. RAG System (v2.4) - Image Semantic Search

**Purpose**: Enable semantic search across indexed images using natural language queries.

**Components**:

#### 5a. Caption Service ([caption_service.py](../mondrian/caption_service.py))

**Port**: 5200

**Purpose**: Generate descriptive captions for images using MLX vision model.

**Key Endpoints**:
```
POST   /caption    - Generate caption for image
GET    /health     - Health check
```

**Model**: Qwen3-VL-4B-Instruct-MLX (same as AI Advisor)
**Performance**: ~2-5 seconds per image on Apple Silicon

#### 5b. Embedding Service ([embedding_service.py](../mondrian/embedding_service.py))

**Port**: 5300

**Purpose**: Convert text captions to 384-dimensional embedding vectors.

**Key Endpoints**:
```
POST   /embed      - Generate embedding for text
GET    /health     - Health check
```

**Model**: `sentence-transformers/all-MiniLM-L6-v2`
**Performance**: ~100ms per caption

#### 5c. RAG Service ([rag_service.py](../mondrian/rag_service.py))

**Port**: 5400

**Purpose**: Orchestrate indexing and semantic search operations.

**Key Endpoints**:
```
POST   /index      - Index an image (caption + embed + store)
POST   /search     - Search for similar images by query
GET    /health     - Health check with dependency status
```

**Workflow**:
1. **Index**: image → caption → embedding → database
2. **Search**: query → embedding → similarity search → results

**Database Integration**:
- Stores captions and embeddings in `image_captions` table
- 384-dimensional vectors stored as BLOB
- Cosine similarity search for retrieval

**Configuration**:
```bash
python3 mondrian/rag_service.py \
  --port 5400 \
  --db mondrian.db \
  --caption_url http://127.0.0.1:5200 \
  --embedding_url http://127.0.0.1:5300
```

---

### 6. Monitoring Service ([monitoring_service.py](../mondrian/monitoring_service.py))

**Purpose**: Comprehensive service monitoring, health checks, and job cleanup.

**Port**: 5007 (web dashboard)

**Version**: v2.4-MONITORING-RAG

**Features**:
- **Health Monitoring**: Continuous health checks for all 5 services
- **Job Cleanup**: Auto-mark timed-out jobs as errored (15min timeout)
- **Service Restart**: Automatic restart of failed services
- **Auto-Startup**: Manages startup of all services in dependency order
- **Web Dashboard**: Real-time monitoring at `http://127.0.0.1:5007/monitor`

**Managed Services** (startup order):
1. Caption Service (Port 5200)
2. Embedding Service (Port 5300)
3. RAG Service (Port 5400)
4. AI Advisor Service (Port 5100)
5. Job Service (Port 5005)

**Configuration**:
```json
{
  "services": {
    "caption_service": {"port": 5200, ...},
    "embedding_service": {"port": 5300, ...},
    "rag_service": {"port": 5400, ...},
    "ai_advisor": {"port": 5100, ...},
    "job_service": {"port": 5005, ...}
  },
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

### 7. Database ([mondrian.db](../mondrian.db))

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

**`image_captions` table** (RAG system - image semantic search):
```sql
CREATE TABLE image_captions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    caption TEXT NOT NULL,
    embedding BLOB NOT NULL,        -- 384-dimensional vector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, image_path)
);
```

**`dimensional_profiles` table** (RAG strategy - dimensional similarity):
```sql
CREATE TABLE dimensional_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisor_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    job_id TEXT,
    composition REAL NOT NULL,
    lighting REAL NOT NULL,
    focus_sharpness REAL NOT NULL,
    color_harmony REAL NOT NULL,
    subject_isolation REAL NOT NULL,
    depth_perspective REAL NOT NULL,
    visual_balance REAL NOT NULL,
    emotional_impact REAL NOT NULL,
    overall_grade TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(advisor_id, image_path)
);
```

**Stored Configuration**:
- `system_prompt`: Main system prompt with HTML structure (stored in DB, not files)

---

## Data Flow

### Complete Analysis Flow

```
1. iOS/Mac Client
   ↓ POST /upload {image: file, advisor: "all", mode: "baseline"}

2. Job Service (Port 5005)
   ↓ Create job record
   ↓ Save image to source/
   ↓ Optimize image (resize to 1320px)
   ↓ Save to thumbnails/

3. For each advisor (Ansel, O'Keeffe, Mondrian, Gehry, Van Gogh):
   ↓ POST /analyze {advisor, job_id, image_file, mode}

4. AI Advisor Service (Port 5100)
   ↓ Create AnalysisContext
   ↓ Set strategy based on mode (baseline/rag/lora)
   ↓ Validate strategy availability for advisor
   ↓ Execute selected strategy:
   │
   ├─► BaselineStrategy:
   │   ↓ Load advisor prompt from database
   │   ↓ Compose full prompt
   │   ↓ Run MLX model (cached)
   │   ↓ Return AnalysisResult
   │
   ├─► RAGStrategy:
   │   ↓ Load advisor prompt
   │   ↓ First pass: Get dimensional scores
   │   ↓ Query dimensional_profiles for similar images
   │   ↓ Augment prompt with similar images context
   │   ↓ Second pass: Generate analysis with context
   │   ↓ Return AnalysisResult with similarity metadata
   │
   └─► LoRAStrategy:
       ↓ Check adapter exists (adapters/{advisor}/adapters.safetensors)
       ↓ Load base model + apply LoRA adapter (cached)
       ↓ Compose full prompt
       ↓ Run fine-tuned model
       ↓ Return AnalysisResult with adapter metadata

   ↓ Stream "thinking" updates to Job Service
   ↓ Return JSON analysis with mode_used metadata

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
│   ├── strategies/                  # Analysis Strategy Pattern
│   │   ├── __init__.py              # Module exports
│   │   ├── base.py                  # Abstract classes (AnalysisStrategy, AnalysisResult)
│   │   ├── baseline.py              # BaselineStrategy (prompt only)
│   │   ├── rag.py                   # RAGStrategy (with retrieval)
│   │   ├── lora.py                  # LoRAStrategy (fine-tuned)
│   │   └── context.py               # AnalysisContext (strategy manager)
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
├── adapters/                        # LoRA fine-tuned adapters
│   ├── ansel/
│   │   ├── adapters.safetensors     # LoRA weights (~150MB)
│   │   └── adapter_config.json      # Configuration
│   ├── okeefe/
│   ├── mondrian/
│   ├── gehry/
│   └── vangogh/
├── mondrian.db                      # SQLite database
├── init_database.py                 # Database initialization
├── start_services.sh                # Service startup script
└── docs/
    ├── architecture.md              # This file
    ├── RAG_INTEGRATION_COMPLETE.md  # RAG system documentation
    └── architecture/
        └── rag-roadmap.md           # RAG enhancement roadmap
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

### Network Configuration

When services start with `./mondrian.sh`, available IP addresses are displayed:

```bash
[NETWORK] Configure your iOS app with one of these addresses:
Local (same machine): http://127.0.0.1:5005
en0: http://10.0.0.131:5005       # WiFi network
en1: http://192.168.1.100:5005    # Ethernet
```

**iOS App Configuration:**
```swift
// Use the IP shown in startup output for your connection type
let baseURL = "http://10.0.0.131:5005"  // Example WiFi address
APIService.shared.configure(baseURL: baseURL)
```

### Complete API Workflow

#### Phase 1: Upload & Stream (Real-time Updates)

**1. Upload Image**
```swift
POST /upload
Content-Type: multipart/form-data

Parameters:
  - image: Data (required)
  - advisor: "all" | "ansel" | "okeefe,mondrian" (optional, default: "all")
  - auto_analyze: "true" (optional, default: "true")

Response (201 Created):
{
  "job_id": "abc-123-def",
  "filename": "photo-uuid.jpg",
  "advisor": "all",
  "status": "queued",
  "status_url": "http://10.0.0.131:5005/status/abc-123-def",
  "stream_url": "http://10.0.0.131:5005/stream/abc-123-def"
}
```

**2. Connect to SSE Stream**
```swift
// Open EventSource connection
let eventSource = EventSource(url: streamURL)

// Handle SSE events
eventSource.onMessage { event in
    switch event.type {
    case "connected":
        // Connection established
    case "status_update":
        // Update progress UI
        let jobData = event.data["job_data"]
        updateProgress(jobData["progress_percentage"])
        updateStatus(jobData["current_step"])
    case "thinking_update":
        // Show live AI feedback
        showThinking(event.data["thinking"])
    case "done":
        // Analysis complete - close stream and fetch results
        eventSource.close()
        fetchResults(jobId)
    }
}
```

#### Phase 2: Retrieve Results

Two endpoint options after analysis completes (status = "done"):

**Option A: Summary-First (Recommended)**
```swift
// 1. Get quick preview (3 lowest-scoring dimensions)
GET /summary/{job_id}
Returns: HTML with priority improvements
Use case: Immediate feedback, smaller payload

// 2. Get full analysis (optional, all 8 dimensions)
GET /analysis/{job_id}
Returns: Complete HTML with all dimensions
Use case: Detailed review when user requests
```

**Option B: Full Analysis Only**
```swift
// Get complete analysis directly
GET /analysis/{job_id}
Returns: Complete HTML with all 8 dimensions
Use case: When user wants full details immediately
```

### Critical URL Construction Rules

⚠️ **IMPORTANT**: Always use the SAME base URL throughout the workflow:

```swift
// ✅ CORRECT: Use consistent base URL
let baseURL = "http://10.0.0.131:5005"  // From server startup

// Upload
let uploadURL = "\(baseURL)/upload"

// Stream (from upload response)
let streamURL = uploadResponse.stream_url  // Already has correct base

// Results (construct with same base)
let analysisURL = "\(baseURL)/analysis/\(jobId)"
let summaryURL = "\(baseURL)/summary/\(jobId)"

// ❌ WRONG: Don't mix different IPs/hostnames
// Upload to: http://10.0.0.131:5005/upload
// Fetch from: http://127.0.0.1:5005/analysis/...  ❌ Will fail!
```

### Common Integration Issues

#### Issue: "Not Found" (404) After Analysis Completes

**Symptom**: SSE stream completes successfully with "done" event, but `GET /analysis/{job_id}` returns 404.

**Root Causes**:
1. **Base URL Mismatch**: iOS app using different IP than server bound to
   - Example: Server uses `10.0.0.131:5005`, app requests from `127.0.0.1:5005` ❌
   
2. **Incorrect job_id**: Using truncated or modified job ID
   - Use exact job_id from upload response
   
3. **Premature Request**: Fetching before status is "done"
   - Wait for SSE "done" event before requesting results

**Solution**:
```swift
class MondrianAPIService {
    let baseURL: String  // Set once from server startup output
    
    func handleSSEEvent(_ event: SSEEvent) {
        if event.type == "done" {
            // Only fetch after "done" event
            Task {
                let analysis = try await fetchAnalysis(jobId)
                displayInWebView(analysis)
            }
        }
    }
    
    func fetchAnalysis(_ jobId: String) async throws -> String {
        // Use same baseURL throughout
        let url = URL(string: "\(baseURL)/analysis/\(jobId)")!
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        switch http.statusCode {
        case 200:
            return String(data: data, encoding: .utf8) ?? ""
        case 202:
            throw APIError.notReady  // Status not "done" yet
        case 404:
            throw APIError.notFound  // Job doesn't exist or wrong URL
        default:
            throw APIError.serverError
        }
    }
}
```

### SSE Event Types

```json
// connected - Initial connection established
{
  "type": "connected",
  "job_id": "abc-123"
}

// status_update - Progress and status changes
{
  "type": "status_update",
  "job_data": {
    "status": "analyzing",
    "current_step": "Analyzing with Ansel Adams",
    "progress_percentage": 45,
    "current_advisor": 2,
    "total_advisors": 3,
    "step_phase": "advisor_analysis"
  }
}

// thinking_update - Live AI analysis feedback
{
  "type": "thinking_update",
  "job_id": "abc-123",
  "thinking": "Evaluating tonal range and composition balance..."
}

// done - Analysis complete, ready to fetch results
{
  "type": "done",
  "job_id": "abc-123"
}
```

### Testing iOS Integration

Verify the complete workflow with the included test script:

```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian/test
python3 test_full_ios_workflow.py
```

This simulates the complete iOS app experience and validates all endpoints.

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

### External Resources

- **MLX Framework**: https://github.com/ml-explore/mlx
- **MLX-VLM**: https://github.com/Blaizzy/mlx-vlm
- **Qwen3-VL Model**: https://huggingface.co/lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit
- **Flask Documentation**: https://flask.palletsprojects.com/

### Related Documentation

- **[README_LORA_PLAN.md](../README_LORA_PLAN.md)** - Complete LoRA fine-tuning implementation plan
  - Comprehensive 6-phase roadmap for training advisor-specific adapters
  - Training scripts, evaluation framework, and integration guide
  - 8-10 day implementation timeline with detailed workbook

- **[docs/RAG_INTEGRATION_COMPLETE.md](RAG_INTEGRATION_COMPLETE.md)** - RAG system integration guide
  - Caption, Embedding, and RAG service setup
  - Database schema for image_captions table
  - Testing and monitoring instructions

- **[docs/architecture/rag-roadmap.md](architecture/rag-roadmap.md)** - RAG enhancement roadmap
  - Future enhancements for RAG system
  - Image metadata ingestion plan
  - Dimensional profile enrichment

- **[docs/LORA_FINETUNING_GUIDE.md](LORA_FINETUNING_GUIDE.md)** - LoRA fine-tuning technical guide
  - 700+ lines of comprehensive guidance
  - Hyperparameter tuning reference
  - MLX-native training approach

### Strategy Pattern Implementation

The Strategy Pattern implementation provides three analysis modes:

1. **Baseline** - Always available, single-pass prompt-based analysis
2. **RAG** - Requires dimensional_profiles table, two-pass with retrieval context
3. **LoRA** - Requires trained adapters, single-pass with fine-tuned model

See [mondrian/strategies/](../mondrian/strategies/) for implementation details.

---

**Last Updated**: 2026-01-14
**Author**: Mondrian Development Team
**Stack**: Python 3.12 + MLX + Qwen3-VL-4B on Apple Silicon
**Architecture**: Strategy Pattern with Baseline, RAG, and LoRA modes
