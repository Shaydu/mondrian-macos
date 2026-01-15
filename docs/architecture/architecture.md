# Mondrian System Architecture

## Overview

Mondrian is a photography analysis system that provides AI-powered feedback from virtual "advisors" (master photographers). The system analyzes user images across 8 dimensional rubrics and provides actionable recommendations.

---

## System Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           iOS App (Client)                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/REST
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Job Service (Port 5005)                             │
│  - Job queue management                                                  │
│  - Real-time status updates                                              │
│  - Thinking stream relay                                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Internal API
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   AI Advisor Service (Port 5100)                         │
│  - MLX Vision Model (Qwen2-VL)                                          │
│  - Strategy Pattern for analysis modes                                   │
│  - Dimensional scoring (8 dimensions)                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              ┌──────────┐   ┌──────────┐   ┌──────────┐
              │ SQLite   │   │ Adapters │   │ Reference│
              │ Database │   │ (LoRA)   │   │ Images   │
              └──────────┘   └──────────┘   └──────────┘
```

---

## Analysis Mode Strategy Pattern

The system supports four analysis modes, implemented using the **Strategy Pattern** for clean separation of concerns and runtime flexibility.

### Mode Overview

| Mode | Passes | Model | Context | Speed | Best For |
|------|--------|-------|---------|-------|----------|
| `baseline` | 1 | Base Qwen3-VL | Prompt only | Fastest | Quick feedback, testing |
| `rag` | 2 | Base Qwen3-VL | Prompt + retrieved examples | Medium | Comparative analysis |
| `lora` | 1 | Fine-tuned Qwen3-VL | Learned advisor style | Fast | Production recommendations |
| `rag_lora` | 2 | Fine-tuned Qwen3-VL | Learned style + retrieved examples | Medium | Advanced: personalized recommendations with reference context |

### Strategy Pattern Class Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      AnalysisContext                            │
├─────────────────────────────────────────────────────────────────┤
│ - strategy: AnalysisStrategy                                    │
│ - config: Config                                                │
├─────────────────────────────────────────────────────────────────┤
│ + set_strategy(mode: str, advisor_id: str) -> AnalysisContext   │
│ + analyze(image_path: str, advisor_id: str) -> AnalysisResult   │
│ + effective_mode: str                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 <<abstract>> AnalysisStrategy                   │
├─────────────────────────────────────────────────────────────────┤
│ + analyze(image_path, advisor_id, config) -> AnalysisResult     │
│ + is_available(advisor_id: str) -> bool                         │
│ + get_fallback() -> Optional[AnalysisStrategy]                  │
│ + name: str                                                     │
└─────────────────────────────────────────────────────────────────┘
                              △
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴─────────┐  ┌────────┴────────┐ ┌─────────┴────────┐ ┌──────────┴──────────┐
│ BaselineStrategy│  │  RAGStrategy    │ │  LoRAStrategy   │ │ RAGLoRAStrategy    │
├─────────────────┤  ├─────────────────┤ ├─────────────────┤ ├────────────────────┤
│ Single-pass     │  │ Two-pass        │ │ Single-pass     │ │ Two-pass           │
│ Prompt only     │  │ Base model      │ │ Fine-tuned      │ │ Fine-tuned model   │
│ Always available│  │ With retrieval  │ │ Adapter weights │ │ + RAG retrieval    │
├─────────────────┤  ├─────────────────┤ ├─────────────────┤ ├────────────────────┤
│ fallback: None  │  │ fallback:       │ │ fallback:       │ │ fallback: None     │
│                 │  │   Baseline      │ │   RAG           │ │ (explicit failure) │
└─────────────────┘  └─────────────────┘ └─────────────────┘ └────────────────────┘
```

### Fallback Chain

Each strategy defines its fallback, creating an automatic degradation path:

```
rag_lora (requested)
    │
    ├─ adapter exists AND profiles exist? ──Yes──► Use RAG+LoRA
    │
    No
    ▼
lora (fallback)
    │
    ├─ adapter exists? ──Yes──► Use LoRA
    │
    No
    ▼
rag (fallback)
    │
    ├─ profiles exist? ──Yes──► Use RAG
    │
    No
    ▼
baseline (terminal)
    │
    └─ always available ──────► Use Baseline
```

### RAG+LoRA Mode: Advanced Hybrid Strategy

The `rag_lora` mode combines the strengths of both LoRA and RAG for the most comprehensive analysis:

**What it does:**
1. **Pass 1** (LoRA): Extract dimensional profile using fine-tuned model
2. **Query Phase** (RAG): Retrieve portfolio images that excel in dimensions needing improvement
3. **Pass 2** (LoRA + Context): Generate analysis with LoRA model, augmented with reference examples

**Key benefits:**
- **Personalized Voice**: The fine-tuned LoRA model captures the advisor's learned scoring patterns and style preferences
- **Contextual Examples**: Retrieved reference images show specific portfolio examples of strong execution
- **Comparative Feedback**: Users see how their scores compare to advisor's portfolio distribution
- **Actionable**: References help users understand what improvement looks like

**Requirements:**
- LoRA adapter must exist for the advisor (trained weights)
- Dimensional profiles must exist in database (scored reference images)
- Both conditions are required; no fallback if either is missing

**Metadata Tracking:**
Each result includes detailed timing information:
```python
metadata={
    "pass1_duration": 3.2,          # Dimensional extraction time
    "query_duration": 0.5,          # Reference image retrieval time
    "pass2_duration": 4.1,          # Comparative analysis generation time
    "total_duration": 7.8,          # Total wall-clock time
    "raw_response_length": 2847,    # Response JSON size
    "adapter_path": "adapters/ansel",
    "representative_images_count": 3
}
```

### Strategy Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class AnalysisResult:
    """Unified result from any analysis strategy."""
    dimensional_analysis: Dict[str, Any]
    overall_grade: str
    mode_used: str
    advisor_id: str
    metadata: Optional[Dict[str, Any]] = None


class AnalysisStrategy(ABC):
    """Abstract base for analysis strategies."""

    @abstractmethod
    def analyze(self, image_path: str, advisor_id: str, config) -> AnalysisResult:
        """Execute analysis using this strategy."""
        pass

    @abstractmethod
    def is_available(self, advisor_id: str) -> bool:
        """Check if strategy can be used for given advisor."""
        pass

    @abstractmethod
    def get_fallback(self) -> Optional['AnalysisStrategy']:
        """Return fallback strategy or None if terminal."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier for logging/headers."""
        pass
```

### Context Class

```python
class AnalysisContext:
    """Manages strategy selection with automatic fallback."""

    STRATEGIES = {
        'baseline': BaselineStrategy,
        'rag': RAGStrategy,
        'lora': LoRAStrategy,
        'rag_lora': RAGLoRAStrategy
    }

    def __init__(self, config):
        self.config = config
        self._strategy = None
        self._effective_mode = None

    def set_strategy(self, mode: str, advisor_id: str) -> 'AnalysisContext':
        """Set strategy with fallback chain."""
        strategy = self.STRATEGIES[mode]()

        while strategy and not strategy.is_available(advisor_id):
            strategy = strategy.get_fallback()

        self._strategy = strategy
        self._effective_mode = strategy.name
        return self

    def analyze(self, image_path: str, advisor_id: str) -> AnalysisResult:
        """Execute current strategy."""
        return self._strategy.analyze(image_path, advisor_id, self.config)

    @property
    def effective_mode(self) -> str:
        return self._effective_mode
```

### File Structure

```
mondrian/
├── strategies/
│   ├── __init__.py          # Exports public API
│   ├── base.py              # AnalysisStrategy ABC, AnalysisResult
│   ├── baseline.py          # BaselineStrategy
│   ├── rag.py               # RAGStrategy
│   ├── lora.py              # LoRAStrategy
│   ├── rag_lora.py          # RAGLoRAStrategy (new)
│   └── context.py           # AnalysisContext
│
├── ai_advisor_service.py    # Flask API using AnalysisContext
├── config.py                # ANALYSIS_MODE = "baseline" | "rag" | "lora" | "rag_lora"
└── ...
```

---

## 8 Dimensional Rubric

All strategies produce scores across these dimensions:

| Dimension | Field Name | Description |
|-----------|------------|-------------|
| Composition | `composition` | Rule of thirds, framing, visual structure |
| Lighting | `lighting` | Light quality, direction, contrast |
| Focus & Sharpness | `focus_sharpness` | Sharpness, focus accuracy, depth of field |
| Color Harmony | `color_harmony` | Color palette, balance, relationships |
| Subject Isolation | `subject_isolation` | Subject separation from background |
| Depth & Perspective | `depth_perspective` | Layering, depth perception |
| Visual Balance | `visual_balance` | Weight distribution, compositional balance |
| Emotional Impact | `emotional_impact` | Emotional resonance, viewer engagement |

Each dimension has:
- **Score**: 0-10 integer
- **Comment**: Qualitative feedback
- **Improvement Steps**: Actionable recommendations (for scores < 7)

---

## Database Schema

### Core Tables

```sql
-- Advisor definitions
CREATE TABLE advisors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    prompt TEXT,
    bio TEXT,
    focus_areas TEXT,  -- JSON array
    category TEXT
);

-- Dimensional profiles for RAG
CREATE TABLE dimensional_profiles (
    id TEXT PRIMARY KEY,
    advisor_id TEXT NOT NULL,
    image_path TEXT NOT NULL,

    -- 8 dimensional scores
    composition_score REAL,
    lighting_score REAL,
    focus_sharpness_score REAL,
    color_harmony_score REAL,
    subject_isolation_score REAL,
    depth_perspective_score REAL,
    visual_balance_score REAL,
    emotional_impact_score REAL,

    -- 8 dimensional comments
    composition_comment TEXT,
    lighting_comment TEXT,
    -- ... etc

    UNIQUE(advisor_id, image_path)
);

-- System configuration
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

---

## Configuration

### Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `ANALYSIS_MODE` | `baseline` \| `rag` \| `lora` | `rag` | Default analysis mode |
| `EMBEDDINGS_ENABLED` | `true` \| `false` | `false` | Visual similarity (hybrid) |

### Config File (`mondrian/config.py`)

```python
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(_BASE_DIR, "mondrian.db")

# Analysis mode: "baseline" | "rag" | "lora"
ANALYSIS_MODE = os.environ.get("ANALYSIS_MODE", "rag")

# LoRA adapter directory
LORA_ADAPTER_DIR = os.path.join(_BASE_DIR, "..", "adapters")
```

---

## API Endpoints

### AI Advisor Service (Port 5100)

#### POST /analyze

Analyze an image using the selected mode and advisor.

**Request:**
```bash
curl -X POST http://localhost:5100/analyze \
  -F "image=@photo.jpg" \
  -F "advisor=ansel" \
  -F "mode=rag"
```

**Response Headers:**
```
X-Analysis-Mode: rag          # Actual mode used
X-Requested-Mode: lora        # Originally requested (if different)
X-Advisor-ID: ansel
```

**Response Body:**
```json
{
  "dimensional_analysis": {
    "composition": {"score": 8, "comment": "..."},
    "lighting": {"score": 7, "comment": "..."},
    ...
  },
  "overall_grade": "B+",
  "mode_used": "rag",
  "advisor_id": "ansel"
}
```

---

## Related Documentation

- [Data Flow](data-flow.md) - Detailed request/response flows
- [RAG Architecture](rag.md) - Retrieval-augmented generation details
- [LoRA Tuning Roadmap](../LoRA/tuning-roadmap.md) - Fine-tuning implementation

---

**Last Updated:** 2026-01-13
