# Mondrian: Three-Mode Analysis Architecture

## Slide 1: Analysis Modes Overview

### Three Ways to Analyze Photographs

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS MODES                                │
├─────────────────┬─────────────────┬─────────────────────────────┤
│    BASELINE     │      RAG        │         LoRA                │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ Single-pass     │ Two-pass        │ Single-pass                 │
│ Prompt only     │ + Retrieved     │ + Fine-tuned                │
│                 │   examples      │   adapter                   │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ ⚡ Fastest      │ 📊 Comparative  │ 🎯 Most Accurate            │
│ Always works    │ Needs profiles  │ Needs trained adapter       │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

| Mode | Speed | Quality | Requirements |
|------|-------|---------|--------------|
| **Baseline** | ~10s | Good | None |
| **RAG** | ~15s | Better | Dimensional profiles in DB |
| **LoRA** | ~12s | Best | Trained adapter file |

**Automatic Fallback**: `lora → rag → baseline`

---

## Slide 2: How LoRA Fine-Tuning Works

### Teaching the Model an Advisor's Style

```
┌──────────────────────────────────────────────────────────────────┐
│                    TRAINING PIPELINE                              │
└──────────────────────────────────────────────────────────────────┘

   Reference Images          Dimensional Profiles         Training
   ┌─────────────┐          ┌─────────────────┐          ┌────────┐
   │ 📷 Ansel's  │    +     │ composition: 10 │    →     │ LoRA   │
   │   Portfolio │          │ lighting: 10    │          │Adapter │
   │ (8 images)  │          │ focus: 9        │          │ (~50MB)│
   └─────────────┘          │ ...             │          └────────┘
                            └─────────────────┘
                                    ↓
                            ┌─────────────────┐
                            │ Fine-tuned for  │
                            │ Ansel's scoring │
                            │ patterns        │
                            └─────────────────┘
```

### Key Benefits of LoRA

1. **Small adapters** (~50MB vs 16GB base model)
2. **Fast training** (~15 min on M1 Mac)
3. **Per-advisor customization** - each advisor gets their own adapter
4. **Preserves base model** - adapters are additive, not destructive

### Training Command
```bash
python training/train_lora.py --advisor ansel
```

---

## Slide 3: Strategy Pattern Architecture

### Clean Separation with Automatic Fallback

```
┌─────────────────────────────────────────────────────────────────┐
│                      AnalysisContext                             │
│  - Selects strategy based on mode                                │
│  - Handles automatic fallback                                    │
│  - Tracks requested vs effective mode                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 <<abstract>> AnalysisStrategy                    │
│  + analyze(image, advisor) → AnalysisResult                      │
│  + is_available(advisor) → bool                                  │
│  + get_fallback() → Strategy                                     │
└─────────────────────────────────────────────────────────────────┘
                              △
          ┌───────────────────┼───────────────────┐
          │                   │                   │
┌─────────┴─────────┐ ┌───────┴───────┐ ┌────────┴────────┐
│ BaselineStrategy  │ │  RAGStrategy  │ │  LoRAStrategy   │
│ fallback: None    │ │ fallback:     │ │ fallback:       │
│ (terminal)        │ │   Baseline    │ │   RAG           │
└───────────────────┘ └───────────────┘ └─────────────────┘
```

### API Usage
```python
from mondrian.strategies import AnalysisContext

context = AnalysisContext()
context.set_strategy("lora", "ansel")

print(f"Using: {context.effective_mode}")  # May fallback if unavailable

result = context.analyze(image_path, "ansel")
print(f"Grade: {result.overall_grade}")
```

### Configuration
```bash
# Environment variable
export ANALYSIS_MODE=lora

# Or per-request via API
curl -X POST /analyze -F "image=@photo.jpg" -F "mode=lora"
```

---

## Quick Reference

### File Structure
```
mondrian/
├── strategies/           # Strategy Pattern implementation
│   ├── base.py          # Abstract base class
│   ├── baseline.py      # Prompt-only analysis
│   ├── rag.py           # Retrieval-augmented
│   ├── lora.py          # Fine-tuned adapter
│   └── context.py       # Strategy selection
├── config.py            # ANALYSIS_MODE setting
│
training/
├── prepare_dataset.py   # Convert profiles → training data
├── train_lora.py        # LoRA training script
│
adapters/
└── ansel/               # Per-advisor adapters
    └── adapters.safetensors
```

### Model: Qwen3-VL-8B-4bit
- **Parameters**: 8 billion (4-bit quantized)
- **Memory**: ~5-6GB (fits M1 16GB)
- **Capabilities**: Vision + Language understanding

### 8 Dimensional Rubric
| Dimension | Description |
|-----------|-------------|
| Composition | Rule of thirds, framing |
| Lighting | Quality, direction, contrast |
| Focus & Sharpness | DOF, accuracy |
| Color Harmony | Palette, balance |
| Subject Isolation | Background separation |
| Depth & Perspective | Layering |
| Visual Balance | Weight distribution |
| Emotional Impact | Viewer engagement |

---

*Last Updated: 2025-01-13*
