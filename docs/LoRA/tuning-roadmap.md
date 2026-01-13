# MLX-Native LoRA Fine-tuning Roadmap for Mondrian Advisors

## Executive Summary

This roadmap outlines a **pure MLX approach** for LoRA fine-tuning of vision-language models (Qwen2-VL) to improve photography recommendations based on advisor portfolios. The goal is to fine-tune the model on each advisor's reference images so it learns their aesthetic preferences and scoring patterns across our 8-dimensional rubric.

**Key Discovery**: MLX-VLM has **complete built-in LoRA support** with a full training pipeline, significantly simplifying implementation.

---

## Current Status

✅ **Phase 0: Investigation - COMPLETE**
- MLX-VLM LoRA API fully documented
- Training pipeline understood
- Dataset format requirements identified
- Integration approach planned

⏳ **Next: Phase 1 - Data Preparation & Training Setup**

---

## Mondrian System Context

### Current Architecture
- **Framework**: MLX (Apple Silicon optimized)
- **Model**: Qwen2-VL-2B-Instruct via `mlx-vlm`
- **Analysis Mode**: 2-pass RAG with dimensional comparison
- **8 Dimensional Rubric**:
  1. Composition (0-10)
  2. Lighting (0-10)
  3. Focus & Sharpness (0-10)
  4. Color Harmony (0-10)
  5. Subject Isolation (0-10)
  6. Depth & Perspective (0-10)
  7. Visual Balance (0-10)
  8. Emotional Impact (0-10)

### How LoRA Will Improve Recommendations

| Current Approach | With LoRA Fine-tuning |
|-----------------|----------------------|
| Model relies on prompts + RAG context | Model **learns** advisor's aesthetic from images |
| Reference images used for retrieval only | Reference images used to **train** the model |
| Generic scoring calibration | Advisor-specific scoring calibration |
| Statistical comparison to portfolio mean | Direct visual pattern recognition |

---

## Analysis Mode Architecture (Three Modes)

The API supports three independent analysis modes, selectable via configuration or per-request parameters:

### Mode Comparison

| Mode | Passes | Model | Context | Speed | Best For |
|------|--------|-------|---------|-------|----------|
| **Baseline** | 1 | Base Qwen2-VL | Prompt only | Fastest | Quick feedback, testing |
| **RAG** | 2 | Base Qwen2-VL | Prompt + retrieved examples | Medium | Comparative analysis |
| **LoRA** | 1 | Fine-tuned Qwen2-VL | Learned advisor style | Fast | Production recommendations |

### Configuration

#### Global Defaults (`mondrian/config.py`)

```python
# mondrian/config.py

import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(_BASE_DIR, "mondrian.db")

# Analysis mode: "baseline" | "rag" | "lora"
ANALYSIS_MODE = os.environ.get("ANALYSIS_MODE", "rag")

# LoRA adapter directory
LORA_ADAPTER_DIR = os.path.join(_BASE_DIR, "..", "adapters")

# Legacy toggles (for backward compatibility)
RAG_ENABLED = ANALYSIS_MODE == "rag"
LORA_ENABLED = ANALYSIS_MODE == "lora"
EMBEDDINGS_ENABLED = os.environ.get("EMBEDDINGS_ENABLED", "false").lower() == "true"
```

#### Per-Request Override

```bash
# API request with mode selection
# mode = "baseline" | "rag" | "lora"

curl -X POST http://localhost:5100/analyze \
  -F "image=@photo.jpg" \
  -F "advisor=ansel" \
  -F "mode=lora"
```

### Mode Details

#### 1. Baseline Mode (`mode=baseline`)

```
User Image → MLX Model (base) → JSON Response
                ↓
         System Prompt + Advisor Prompt
```

- **Single pass**: Direct analysis with advisor prompt
- **No retrieval**: No database queries for similar images
- **Use case**: Quick testing, low-latency requirements

#### 2. RAG Mode (`mode=rag`) - Current Default

```
User Image → Pass 1: Dimensional Extraction
                ↓
         Query dimensional_profiles table
                ↓
         Find similar advisor images
                ↓
         Pass 2: Comparative Analysis with context
                ↓
         JSON Response with references
```

- **Two passes**: Extract dimensions, then analyze with context
- **Retrieval**: Finds similar advisor portfolio images
- **Use case**: Rich comparative feedback with examples

#### 3. LoRA Mode (`mode=lora`) - New

```
User Image → MLX Model (with LoRA adapter) → JSON Response
                ↓
         System Prompt + Advisor Prompt
         (model has learned advisor's style)
```

- **Single pass**: Analysis with fine-tuned model
- **No retrieval**: Advisor style is embedded in weights
- **Use case**: Production, advisor-specific scoring

### Strategy Pattern Implementation

The analysis modes are implemented using the **Strategy Pattern**, allowing each mode to be encapsulated, tested independently, and swapped at runtime.

#### Class Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      AnalysisContext                            │
├─────────────────────────────────────────────────────────────────┤
│ - strategy: AnalysisStrategy                                    │
│ - advisor_id: str                                               │
│ - config: Config                                                │
├─────────────────────────────────────────────────────────────────┤
│ + set_strategy(mode: str) -> None                               │
│ + analyze(image_path: str) -> AnalysisResult                    │
│ + get_effective_mode() -> str                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 <<abstract>> AnalysisStrategy                   │
├─────────────────────────────────────────────────────────────────┤
│ + analyze(image_path, advisor_id, config) -> AnalysisResult     │
│ + is_available(advisor_id) -> bool                              │
│ + get_fallback() -> Optional[AnalysisStrategy]                  │
└─────────────────────────────────────────────────────────────────┘
                              △
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
┌─────────┴─────────┐ ┌───────┴───────┐ ┌────────┴────────┐
│ BaselineStrategy  │ │  RAGStrategy  │ │  LoRAStrategy   │
├───────────────────┤ ├───────────────┤ ├─────────────────┤
│ - model           │ │ - model       │ │ - model         │
│ - processor       │ │ - processor   │ │ - processor     │
│                   │ │ - db_path     │ │ - adapter_path  │
├───────────────────┤ ├───────────────┤ ├─────────────────┤
│ + analyze()       │ │ + analyze()   │ │ + analyze()     │
│ + is_available()  │ │ + is_available│ │ + is_available()│
│ + get_fallback()  │ │ + get_fallback│ │ + get_fallback()│
└───────────────────┘ └───────────────┘ └─────────────────┘
     returns None      returns Baseline   returns RAG
```

#### Abstract Base Class

```python
# mondrian/strategies/__init__.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class AnalysisResult:
    """Result from any analysis strategy."""
    dimensional_analysis: Dict[str, Any]
    overall_grade: str
    mode_used: str
    advisor_id: str
    metadata: Dict[str, Any] = None


class AnalysisStrategy(ABC):
    """
    Abstract base class for analysis strategies.

    Each strategy encapsulates a different approach to image analysis:
    - Baseline: Single-pass with prompt only
    - RAG: Two-pass with retrieval augmentation
    - LoRA: Single-pass with fine-tuned model
    """

    @abstractmethod
    def analyze(
        self,
        image_path: str,
        advisor_id: str,
        config: 'Config'
    ) -> AnalysisResult:
        """Perform image analysis using this strategy."""
        pass

    @abstractmethod
    def is_available(self, advisor_id: str) -> bool:
        """Check if this strategy can be used for the given advisor."""
        pass

    @abstractmethod
    def get_fallback(self) -> Optional['AnalysisStrategy']:
        """Return fallback strategy if this one is unavailable."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging and headers."""
        pass
```

#### Concrete Strategies

```python
# mondrian/strategies/baseline.py

class BaselineStrategy(AnalysisStrategy):
    """
    Single-pass analysis with system + advisor prompt only.
    No retrieval, no fine-tuning. Fastest mode.
    """

    def __init__(self, model=None, processor=None):
        self._model = model
        self._processor = processor

    @property
    def name(self) -> str:
        return "baseline"

    def analyze(
        self,
        image_path: str,
        advisor_id: str,
        config: 'Config'
    ) -> AnalysisResult:
        model, processor = self._get_model()
        advisor = get_advisor_from_db(config.db_path, advisor_id)

        # Build prompt without RAG context
        prompt = build_analysis_prompt(
            config.system_prompt,
            advisor['prompt']
        )

        # Single inference pass
        response = run_model_mlx(model, processor, image_path, prompt)
        parsed = parse_json_response(response)

        return AnalysisResult(
            dimensional_analysis=parsed.get('dimensional_analysis', {}),
            overall_grade=parsed.get('overall_grade', 'N/A'),
            mode_used=self.name,
            advisor_id=advisor_id
        )

    def is_available(self, advisor_id: str) -> bool:
        """Baseline is always available."""
        return True

    def get_fallback(self) -> Optional[AnalysisStrategy]:
        """No fallback - baseline is the last resort."""
        return None

    def _get_model(self):
        if self._model is None:
            self._model, self._processor = get_mlx_model()
        return self._model, self._processor
```

```python
# mondrian/strategies/rag.py

class RAGStrategy(AnalysisStrategy):
    """
    Two-pass analysis with retrieval-augmented generation.
    Pass 1: Extract dimensional profile
    Pass 2: Comparative analysis with similar advisor images
    """

    def __init__(self, model=None, processor=None, db_path=None):
        self._model = model
        self._processor = processor
        self._db_path = db_path

    @property
    def name(self) -> str:
        return "rag"

    def analyze(
        self,
        image_path: str,
        advisor_id: str,
        config: 'Config'
    ) -> AnalysisResult:
        model, processor = self._get_model()
        db_path = self._db_path or config.db_path

        # Pass 1: Dimensional extraction
        extraction_prompt = get_dimensional_extraction_prompt()
        pass1_response = run_model_mlx(model, processor, image_path, extraction_prompt)
        user_profile = extract_dimensional_profile(pass1_response)

        # Retrieve similar advisor images
        similar_images = find_similar_by_dimensions(
            db_path, advisor_id, user_profile, limit=3
        )

        # Build augmented prompt with RAG context
        advisor = get_advisor_from_db(db_path, advisor_id)
        augmented_prompt = augment_prompt_with_distribution_context(
            advisor['prompt'],
            user_profile,
            similar_images
        )

        # Pass 2: Comparative analysis
        full_prompt = build_analysis_prompt(config.system_prompt, augmented_prompt)
        pass2_response = run_model_mlx(model, processor, image_path, full_prompt)
        parsed = parse_json_response(pass2_response)

        return AnalysisResult(
            dimensional_analysis=parsed.get('dimensional_analysis', {}),
            overall_grade=parsed.get('overall_grade', 'N/A'),
            mode_used=self.name,
            advisor_id=advisor_id,
            metadata={
                'similar_images': [img['image_path'] for img in similar_images],
                'user_profile': user_profile
            }
        )

    def is_available(self, advisor_id: str) -> bool:
        """Available if advisor has indexed dimensional profiles."""
        return _has_dimensional_profiles(advisor_id)

    def get_fallback(self) -> Optional[AnalysisStrategy]:
        """Fall back to baseline if no profiles available."""
        return BaselineStrategy()

    def _get_model(self):
        if self._model is None:
            self._model, self._processor = get_mlx_model()
        return self._model, self._processor
```

```python
# mondrian/strategies/lora.py

class LoRAStrategy(AnalysisStrategy):
    """
    Single-pass analysis with fine-tuned LoRA adapter.
    Advisor style is embedded in model weights.
    """

    def __init__(self, adapter_dir: str = None):
        self._adapter_dir = adapter_dir or LORA_ADAPTER_DIR
        self._models = {}  # Cache: advisor_id -> (model, processor)

    @property
    def name(self) -> str:
        return "lora"

    def analyze(
        self,
        image_path: str,
        advisor_id: str,
        config: 'Config'
    ) -> AnalysisResult:
        # Get model with LoRA adapter applied
        model, processor = self._get_model_with_adapter(advisor_id)
        advisor = get_advisor_from_db(config.db_path, advisor_id)

        # Build prompt (style is in weights, no RAG needed)
        prompt = build_analysis_prompt(
            config.system_prompt,
            advisor['prompt']
        )

        # Single inference pass with fine-tuned model
        response = run_model_mlx(model, processor, image_path, prompt)
        parsed = parse_json_response(response)

        return AnalysisResult(
            dimensional_analysis=parsed.get('dimensional_analysis', {}),
            overall_grade=parsed.get('overall_grade', 'N/A'),
            mode_used=self.name,
            advisor_id=advisor_id,
            metadata={
                'adapter_path': self._get_adapter_path(advisor_id)
            }
        )

    def is_available(self, advisor_id: str) -> bool:
        """Available if LoRA adapter exists for advisor."""
        adapter_path = self._get_adapter_path(advisor_id)
        return (adapter_path / "adapter_config.json").exists()

    def get_fallback(self) -> Optional[AnalysisStrategy]:
        """Fall back to RAG if no adapter available."""
        return RAGStrategy()

    def _get_adapter_path(self, advisor_id: str) -> Path:
        return Path(self._adapter_dir) / advisor_id

    def _get_model_with_adapter(self, advisor_id: str):
        if advisor_id not in self._models:
            base_model, processor = get_mlx_model()
            adapter_path = self._get_adapter_path(advisor_id)
            model = apply_lora_layers(base_model, str(adapter_path))
            self._models[advisor_id] = (model, processor)
        return self._models[advisor_id]
```

#### Context Class (Strategy Selector)

```python
# mondrian/strategies/context.py

class AnalysisContext:
    """
    Context class that manages strategy selection and execution.
    Handles fallback chain and mode resolution.
    """

    STRATEGIES = {
        'baseline': BaselineStrategy,
        'rag': RAGStrategy,
        'lora': LoRAStrategy
    }

    def __init__(self, config: 'Config'):
        self.config = config
        self._strategy: AnalysisStrategy = None
        self._effective_mode: str = None

    def set_strategy(self, mode: str, advisor_id: str) -> 'AnalysisContext':
        """
        Set analysis strategy with automatic fallback.

        Args:
            mode: Requested mode ("baseline" | "rag" | "lora")
            advisor_id: Advisor to check availability for

        Returns:
            self for chaining
        """
        if mode not in self.STRATEGIES:
            raise ValueError(f"Unknown mode: {mode}. Use: {list(self.STRATEGIES.keys())}")

        # Instantiate requested strategy
        strategy = self.STRATEGIES[mode]()

        # Apply fallback chain if not available
        while strategy and not strategy.is_available(advisor_id):
            logger.info(f"{strategy.name} unavailable for {advisor_id}, trying fallback")
            strategy = strategy.get_fallback()

        if strategy is None:
            raise RuntimeError(f"No available strategy for advisor {advisor_id}")

        self._strategy = strategy
        self._effective_mode = strategy.name

        if self._effective_mode != mode:
            logger.warning(f"Fell back from {mode} to {self._effective_mode}")

        return self

    def analyze(self, image_path: str, advisor_id: str) -> AnalysisResult:
        """Execute analysis using current strategy."""
        if self._strategy is None:
            raise RuntimeError("Strategy not set. Call set_strategy() first.")

        return self._strategy.analyze(image_path, advisor_id, self.config)

    @property
    def effective_mode(self) -> str:
        """Return the actual mode being used (after fallbacks)."""
        return self._effective_mode

    @property
    def strategy_name(self) -> str:
        """Return current strategy name."""
        return self._strategy.name if self._strategy else None
```

#### Usage in Flask API

```python
# mondrian/ai_advisor_service.py

from strategies import AnalysisContext, AnalysisResult

# Initialize context at startup
analysis_context = AnalysisContext(config)

@app.route('/analyze', methods=['POST'])
def analyze():
    image_path = save_uploaded_image(request.files['image'])
    advisor_id = request.form.get('advisor', 'ansel')
    mode = request.form.get('mode', config.ANALYSIS_MODE)

    # Set strategy with automatic fallback
    context = analysis_context.set_strategy(mode, advisor_id)

    # Execute analysis
    result: AnalysisResult = context.analyze(image_path, advisor_id)

    # Build response with headers
    response = make_response(jsonify(result.__dict__))
    response.headers['X-Analysis-Mode'] = context.effective_mode
    response.headers['X-Requested-Mode'] = mode
    response.headers['X-Advisor-ID'] = advisor_id

    return response
```

#### Strategy Pattern Benefits

| Benefit | Description |
|---------|-------------|
| **Encapsulation** | Each mode's logic is isolated in its own class |
| **Testability** | Strategies can be unit tested independently |
| **Extensibility** | Add new modes without modifying existing code |
| **Fallback Chain** | Each strategy defines its own fallback behavior |
| **Runtime Swapping** | Change strategy per-request without restart |
| **Single Responsibility** | Each class does one thing well |

#### File Structure

```
mondrian/
├── strategies/
│   ├── __init__.py          # Exports: AnalysisStrategy, AnalysisResult, AnalysisContext
│   ├── base.py              # Abstract AnalysisStrategy class
│   ├── baseline.py          # BaselineStrategy
│   ├── rag.py               # RAGStrategy
│   ├── lora.py              # LoRAStrategy
│   └── context.py           # AnalysisContext (strategy selector)
│
├── ai_advisor_service.py    # Uses AnalysisContext
└── config.py                # ANALYSIS_MODE setting
```

### API Response Headers

Include mode information in response for debugging:

```python
response.headers['X-Analysis-Mode'] = context.effective_mode  # Actual mode used
response.headers['X-Requested-Mode'] = mode                   # Originally requested
response.headers['X-Advisor-ID'] = advisor_id
response.headers['X-Strategy-Available'] = str(context.strategy_name is not None)
```

### Mode Fallback Chain

Each strategy defines its fallback via `get_fallback()`:

```
LoRAStrategy.get_fallback() → RAGStrategy
RAGStrategy.get_fallback()  → BaselineStrategy
BaselineStrategy.get_fallback() → None (terminal)
```

Resulting chain:
```
lora (requested) → rag (if no adapter) → baseline (if no profiles)
```

### Environment Variable Quick Reference

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `ANALYSIS_MODE` | `baseline` \| `rag` \| `lora` | `rag` | Default analysis mode |
| `EMBEDDINGS_ENABLED` | `true` \| `false` | `false` | Enable visual similarity (hybrid with any mode) |

### Testing Modes

```bash
# Test baseline mode
curl -X POST http://localhost:5100/analyze \
  -F "image=@test.jpg" -F "advisor=ansel" -F "mode=baseline"

# Test RAG mode
curl -X POST http://localhost:5100/analyze \
  -F "image=@test.jpg" -F "advisor=ansel" -F "mode=rag"

# Test LoRA mode (requires trained adapter)
curl -X POST http://localhost:5100/analyze \
  -F "image=@test.jpg" -F "advisor=ansel" -F "mode=lora"

# Compare all modes
for mode in baseline rag lora; do
  echo "=== $mode ==="
  curl -s -X POST http://localhost:5100/analyze \
    -F "image=@test.jpg" -F "advisor=ansel" -F "mode=$mode" | jq '.dimensional_analysis'
done
```

---

## MLX-VLM LoRA API - Complete Documentation

### Package Structure (Verified)

```
mlx_vlm/
├── lora.py              # Main training entry point (CLI)
├── trainer/
│   ├── __init__.py      # Exports: Dataset, Trainer, save_adapter
│   ├── lora.py          # LoRaLayer implementation
│   ├── trainer.py       # Training loop & Dataset class
│   └── utils.py         # apply_lora_layers, get_peft_model, find_all_linear_names
└── utils.py             # load(), prepare_inputs()
```

### Core Components

#### 1. LoRaLayer Class (`trainer/lora.py`)

```python
class LoRaLayer(nn.Module):
    """
    Low-Rank Adaptation layer that wraps a Linear layer.

    Formula: y = original_layer(x) + alpha * (dropout(x) @ A) @ B
    """
    def __init__(
        self,
        linear: Union[nn.Linear, nn.QuantizedLinear],
        rank: int,           # LoRA rank (r)
        alpha: float = 0.1,  # Scaling factor
        dropout: float = 0.0
    ):
        # A: (input_dims, rank) - initialized with uniform distribution
        # B: (rank, output_dims) - initialized with zeros

    def __call__(self, x):
        y = self.original_layer(x)
        lora_update = (self.dropout(x) @ self.A) @ self.B
        return y + (self.alpha * lora_update).astype(x.dtype)
```

#### 2. Model Setup (`trainer/utils.py`)

```python
# Find all linear layers eligible for LoRA
def find_all_linear_names(model) -> list:
    """
    Returns names of all Linear/QuantizedLinear layers,
    excluding multimodal components (mm_projector, vision_tower, aligner).
    Also excludes 'lm_head'.
    """

# Apply LoRA to model
def get_peft_model(
    model,
    linear_layers: list,      # From find_all_linear_names()
    rank: int = 10,
    alpha: float = 0.1,
    dropout: float = 0.1,
    freeze: bool = True,      # Freeze base model weights
    verbose: bool = True
) -> nn.Module:
    """
    Freezes model and replaces Linear layers with LoRaLayer wrappers.
    Saves config to model.config.lora for serialization.
    """

# Load existing adapter
def apply_lora_layers(model: nn.Module, adapter_path: str) -> nn.Module:
    """
    Load adapter_config.json and adapters.safetensors from adapter_path.
    Apply LoRA layers with saved configuration.
    """
```

#### 3. Dataset Class (`trainer/trainer.py`)

```python
class Dataset:
    """
    HuggingFace-compatible dataset wrapper for vision-language training.

    Required columns:
    - 'messages': List of conversation turns (chat format)
    - 'images': PIL Image or image path
    """
    def __init__(
        self,
        hf_dataset,
        config,                  # Model config dict
        processor,               # Model processor/tokenizer
        image_processor=None,
        image_resize_shape=None  # Optional (height, width)
    ):

    def __getitem__(self, idx):
        # Returns dict with:
        # - pixel_values: Processed image tensor
        # - input_ids: Tokenized text
        # - attention_mask: Attention mask
        # - (additional model-specific kwargs)
```

#### 4. Trainer Class (`trainer/trainer.py`)

```python
class Trainer:
    def __init__(
        self,
        model,
        optimizer,
        train_on_completions: bool = False,  # Mask loss on prompts
        assistant_id: int = 77091,           # Token ID for assistant
        clip_gradients: float = None         # Optional gradient clipping
    ):

    def loss_fn(self, model, batch):
        """Cross-entropy loss with optional completion masking."""

    def train_step(self, batch) -> mx.array:
        """Single training step with gradient computation."""
        loss_and_grad_fn = nn.value_and_grad(self.model, self.loss_fn)
        loss, grads = loss_and_grad_fn(self.model, batch)
        if self.clip_gradients:
            grads = tree_map(lambda g: mx.clip(g, -clip, clip), grads)
        self.optimizer.update(self.model, grads)
        return loss
```

#### 5. Saving Adapters (`trainer/trainer.py`)

```python
def save_adapter(model: nn.Module, adapter_file: str):
    """
    Saves:
    - adapter_config.json: {rank, alpha, dropout}
    - adapters.safetensors: Trainable LoRA weights (A and B matrices)
    """
```

### CLI Training Interface (`lora.py`)

The `mlx_vlm.lora` module provides a complete CLI:

```bash
python -m mlx_vlm.lora \
    --model-path "mlx-community/Qwen2-VL-2B-Instruct-bf16" \
    --dataset "path/to/hf_dataset" \
    --split "train" \
    --learning-rate 1e-4 \
    --batch-size 1 \
    --epochs 3 \
    --lora-rank 10 \
    --lora-alpha 0.1 \
    --lora-dropout 0.1 \
    --output-path "adapters/ansel" \
    --save-after-epoch
```

### Required Dataset Format

HuggingFace dataset with columns:

```python
{
    "messages": [
        {"role": "user", "content": "<image>\nAnalyze this photograph..."},
        {"role": "assistant", "content": '{"dimensional_analysis": {...}}'}
    ],
    "images": [PIL.Image]  # or image paths
}
```

---

## Phase 1: Data Preparation (Updated Plan)

### Training Data Source

For Ansel Adams (initial implementation):

| Source | Count | Purpose |
|--------|-------|---------|
| Reference images from `source/advisor/photographer/ansel/` | < 20 | High-quality portfolio exemplars |
| Existing dimensional profiles from `dimensional_profiles` table | All analyzed | Consistent scoring examples |

### Data Augmentation Strategy (for < 20 images)

Since we have limited training data, we'll use:

1. **Image Augmentations**:
   - Random crops (90-100% of image)
   - Horizontal flips (where appropriate for composition)
   - Minor exposure adjustments (±0.2 stops)
   - Minor rotation (±5°)

2. **Response Variations**:
   - Generate multiple valid JSON responses per image
   - Vary comment phrasing while maintaining scores
   - Include different improvement suggestions

3. **Synthetic Examples**:
   - Use base model to generate analysis of similar photographs
   - Manually correct/adjust to match Ansel Adams' style

### Dataset Preparation Script

```python
# training/prepare_ansel_dataset.py

from datasets import Dataset
from PIL import Image
import json
from mondrian.sqlite_helper import get_dimensional_profiles

def prepare_training_data(advisor_id: str = "ansel"):
    """
    Convert dimensional_profiles + reference images to HuggingFace format.
    """
    profiles = get_dimensional_profiles(advisor_id)

    examples = []
    for profile in profiles:
        # Load image
        image = Image.open(profile['image_path'])

        # Format as conversation
        messages = [
            {
                "role": "user",
                "content": f"<image>\nAs {advisor_id}, analyze this photograph across all 8 dimensions."
            },
            {
                "role": "assistant",
                "content": json.dumps({
                    "dimensional_analysis": {
                        "composition": {
                            "score": profile['composition_score'],
                            "comment": profile['composition_comment']
                        },
                        # ... all 8 dimensions
                    }
                })
            }
        ]

        examples.append({
            "messages": messages,
            "images": [image]
        })

    return Dataset.from_list(examples)
```

---

## Phase 2: Training Infrastructure

### Training Script

```python
# training/train_advisor_lora.py

import mlx.optimizers as optim
from mlx_vlm import load
from mlx_vlm.trainer import Dataset, Trainer, save_adapter
from mlx_vlm.trainer.utils import get_peft_model, find_all_linear_names

def train_advisor_lora(
    advisor_id: str,
    dataset_path: str,
    output_path: str,
    config: dict
):
    # Load base model
    model, processor = load("mlx-community/Qwen2-VL-2B-Instruct-bf16")

    # Setup LoRA
    linear_layers = find_all_linear_names(model.language_model)
    model = get_peft_model(
        model,
        linear_layers,
        rank=config.get('rank', 8),        # Lower rank for small dataset
        alpha=config.get('alpha', 0.1),
        dropout=config.get('dropout', 0.05)
    )

    # Load dataset
    dataset = Dataset(
        load_from_disk(dataset_path),
        model.config.__dict__,
        processor
    )

    # Setup optimizer
    optimizer = optim.Adam(learning_rate=config.get('lr', 1e-4))

    # Setup trainer
    trainer = Trainer(
        model,
        optimizer,
        train_on_completions=True  # Only train on response tokens
    )

    # Training loop
    model.train()
    for epoch in range(config.get('epochs', 5)):
        for i in range(len(dataset)):
            loss = trainer.train_step(dataset[i:i+1])
            if i % 10 == 0:
                print(f"Epoch {epoch}, Step {i}, Loss: {loss.item():.4f}")

    # Save adapter
    save_adapter(model, output_path)
```

### Recommended Hyperparameters (Small Dataset)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `rank` | 4-8 | Lower rank prevents overfitting with < 20 images |
| `alpha` | 0.1 | Conservative scaling |
| `dropout` | 0.1 | Regularization for small dataset |
| `learning_rate` | 5e-5 | Lower LR for stability |
| `epochs` | 5-10 | More epochs with small dataset |
| `batch_size` | 1 | Memory efficient |

---

## Phase 3: Integration with Mondrian

### Modified `ai_advisor_service.py`

```python
# At module level
LORA_ADAPTERS = {}  # Cache loaded adapters

def get_mlx_model(advisor_id: str = None):
    """
    Load MLX model with optional advisor-specific LoRA adapter.
    Adapters are cached at startup for fast inference.
    """
    global _MLX_MODEL, _MLX_PROCESSOR, LORA_ADAPTERS

    if _MLX_MODEL is None:
        _MLX_MODEL, _MLX_PROCESSOR = mlx_vlm.load(MLX_MODEL)

    # Apply LoRA adapter if available
    if advisor_id and advisor_id in LORA_ADAPTERS:
        from mlx_vlm.trainer.utils import apply_lora_layers
        model = apply_lora_layers(_MLX_MODEL, LORA_ADAPTERS[advisor_id])
        return model, _MLX_PROCESSOR

    return _MLX_MODEL, _MLX_PROCESSOR

def load_lora_adapters():
    """Load all available LoRA adapters at startup."""
    global LORA_ADAPTERS
    adapter_dir = Path("adapters")

    for adapter_path in adapter_dir.iterdir():
        if adapter_path.is_dir() and (adapter_path / "adapter_config.json").exists():
            advisor_id = adapter_path.name
            LORA_ADAPTERS[advisor_id] = str(adapter_path)
            logger.info(f"Loaded LoRA adapter for {advisor_id}")

# Call at startup
load_lora_adapters()
```

### Adapter Storage Structure

```
mondrian-macos/
├── adapters/
│   ├── ansel/
│   │   ├── adapter_config.json    # {rank, alpha, dropout}
│   │   └── adapters.safetensors   # LoRA weights (~10-50MB)
│   ├── fan_ho/
│   │   ├── adapter_config.json
│   │   └── adapters.safetensors
│   └── ...
```

---

## Phase 4: Evaluation

### Evaluation Metrics

1. **Scoring Consistency**
   - Compare fine-tuned model scores vs reference image scores
   - Measure score distribution alignment with advisor portfolio

2. **Dimensional Accuracy**
   - Evaluate per-dimension prediction accuracy
   - Compare to baseline model on held-out images

3. **Qualitative Assessment**
   - Expert review of generated recommendations
   - Alignment with advisor's known principles

### Evaluation Script

```python
# training/evaluate_lora.py

def evaluate_advisor_lora(advisor_id: str, test_images: list):
    """
    Compare base model vs fine-tuned model on test images.
    """
    base_model, processor = load(BASE_MODEL)
    lora_model = apply_lora_layers(base_model, f"adapters/{advisor_id}")

    results = []
    for image_path in test_images:
        base_response = generate(base_model, processor, image_path, prompt)
        lora_response = generate(lora_model, processor, image_path, prompt)

        results.append({
            "image": image_path,
            "base_scores": extract_scores(base_response),
            "lora_scores": extract_scores(lora_response),
            "reference_scores": get_reference_scores(image_path)
        })

    # Calculate metrics
    base_mse = calculate_mse(results, "base_scores")
    lora_mse = calculate_mse(results, "lora_scores")

    print(f"Base Model MSE: {base_mse:.4f}")
    print(f"LoRA Model MSE: {lora_mse:.4f}")
    print(f"Improvement: {(1 - lora_mse/base_mse) * 100:.1f}%")
```

---

## File Structure (Updated)

```
mondrian-macos/
├── docs/LoRA/
│   ├── tuning-roadmap.md           # This file
│   ├── investigation_summary.md    # Initial findings
│   └── investigation_report.txt    # Raw investigation output
│
├── training/                        # NEW: Training module
│   ├── __init__.py
│   ├── prepare_dataset.py          # Convert DB profiles to HF dataset
│   ├── train_advisor_lora.py       # Main training script
│   ├── evaluate_lora.py            # Evaluation utilities
│   ├── augment.py                  # Data augmentation
│   └── config.py                   # Training hyperparameters
│
├── adapters/                        # NEW: Saved LoRA weights
│   └── ansel/
│       ├── adapter_config.json
│       └── adapters.safetensors
│
├── mondrian/
│   ├── ai_advisor_service.py       # MODIFIED: Add LoRA loading
│   └── ...
│
└── tools/
    └── rag/
        └── index_with_metadata.py  # Existing indexing script
```

---

## Implementation Checklist

### Phase 1: Data Preparation
- [ ] Create `training/prepare_dataset.py`
- [ ] Extract Ansel Adams profiles from database
- [ ] Implement data augmentation utilities
- [ ] Generate HuggingFace-compatible dataset
- [ ] Validate dataset format with mlx_vlm.Dataset

### Phase 2: Training
- [ ] Create `training/train_advisor_lora.py`
- [ ] Test with small subset (2-3 images)
- [ ] Run full training on Ansel Adams data
- [ ] Monitor loss curves
- [ ] Save checkpoints after each epoch

### Phase 3: Integration
- [ ] Modify `ai_advisor_service.py` for adapter loading
- [ ] Create `adapters/` directory structure
- [ ] Test inference with loaded adapter
- [ ] Verify backward compatibility (no adapter = base model)
- [ ] Add adapter caching at startup

### Phase 4: Evaluation
- [ ] Create `training/evaluate_lora.py`
- [ ] Hold out 2-3 images for testing
- [ ] Compare base vs fine-tuned scores
- [ ] Qualitative review of recommendations
- [ ] Document findings

---

## Risk Mitigation Updates

| Risk | Status | Mitigation |
|------|--------|------------|
| MLX-VLM lacks LoRA support | ✅ RESOLVED | Built-in support confirmed |
| Small training dataset (< 20 images) | ⚠️ ACTIVE | Use low rank, augmentation, regularization |
| Overfitting on reference images | ⚠️ ACTIVE | Hold-out validation, dropout, early stopping |
| Memory constraints | ✅ LOW RISK | Batch size 1, gradient checkpointing available |
| Integration complexity | ✅ LOW RISK | Clear API, adapter loading is straightforward |

---

## Project Decisions (User Confirmed)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Initial advisor | **Ansel Adams only** | Validate approach before expanding |
| Training data size | **< 20 images** | Requires low rank + augmentation |
| Adapter loading | **Cached at startup** | Faster inference, acceptable memory |
| Priority | Dimensional scoring alignment | Train model to score like advisor |

---

## Training Strategy: Dimensional Alignment

The goal is not just to memorize advisor images, but to teach the model:

1. **Score like the advisor** - Learn their dimensional preferences from portfolio
2. **Recommend like the advisor** - Generate feedback in their voice/style
3. **Reference their techniques** - Zone system, tonal range, composition principles

### Why This Matters

With < 20 images, we can't teach the model to recognize "all Ansel Adams photos." Instead, we teach it:
- What scores Ansel Adams would give across the 8 dimensions
- How to phrase feedback in his analytical style
- Which techniques to emphasize (zone system, previsualization, etc.)

---

## Advanced: Merging LoRA into Base Weights

For production deployment, LoRA weights can be merged into the base model:

```python
# trainer/lora.py - replace_lora_with_linear()
def replace_lora_with_linear(model):
    """
    Merge LoRA adapters into base model weights.

    Final weight = original_weight + alpha * (A @ B)

    Benefits:
    - No inference overhead
    - Single model file
    - Same speed as base model

    Trade-off:
    - Cannot easily swap adapters
    - Requires saving full model
    """
    for i, layer in enumerate(model.layers):
        if isinstance(layer, LoRaLayer):
            lora_update = layer.alpha * (layer.A @ layer.B)
            updated_weight = layer.original_layer.weight + lora_update
            # Create new Linear with merged weights
            new_linear = nn.Linear(...)
            new_linear.weight = updated_weight
            model.layers[i] = new_linear
```

---

## Mondrian Codebase Context

### Key Files for Integration

| File | Purpose | LoRA Changes Needed |
|------|---------|---------------------|
| [ai_advisor_service.py](../../mondrian/ai_advisor_service.py) | Flask API, MLX inference | Add `get_mlx_model(advisor_id)` |
| [sqlite_helper.py](../../mondrian/sqlite_helper.py) | DB queries for dimensional profiles | Use existing `get_dimensional_profiles()` |
| [json_to_html_converter.py](../../mondrian/json_to_html_converter.py) | Extract dimensional scores | Use `extract_dimensional_profile()` |

### Current MLX Model Loading (lines 154-190)

```python
def get_mlx_model():
    """Current implementation - no LoRA support"""
    global _MLX_MODEL, _MLX_PROCESSOR
    if _MLX_MODEL is None:
        _MLX_MODEL, _MLX_PROCESSOR = load(MLX_MODEL)
    return _MLX_MODEL, _MLX_PROCESSOR
```

### Dimensional Profiles Table Schema

```sql
-- Used for training data extraction
CREATE TABLE dimensional_profiles (
    id TEXT PRIMARY KEY,
    advisor_id TEXT NOT NULL,
    image_path TEXT NOT NULL,

    -- 8 Dimensional Scores (training targets)
    composition_score REAL,
    lighting_score REAL,
    focus_sharpness_score REAL,
    color_harmony_score REAL,
    subject_isolation_score REAL,
    depth_perspective_score REAL,
    visual_balance_score REAL,
    emotional_impact_score REAL,

    -- 8 Dimensional Comments (training targets)
    composition_comment TEXT,
    lighting_comment TEXT,
    ...
);
```

---

## Step-by-Step Implementation Guide

This is the complete, actionable guide to implement LoRA fine-tuning for Mondrian advisors.

---

### Step 1: Create Feature Branch

```bash
cd /Users/shaydu/dev/mondrian-macos
git checkout -b feature/lora-fine-tuning
```

---

### Step 2: Create Directory Structure

```bash
# Create training module
mkdir -p training
touch training/__init__.py

# Create adapters directory
mkdir -p adapters/ansel

# Create strategies module
mkdir -p mondrian/strategies
touch mondrian/strategies/__init__.py
```

---

### Step 3: Verify Ansel Adams Reference Images

```bash
# Check what reference images exist
ls -la source/advisor/photographer/ansel/

# Count images
find source/advisor/photographer/ansel -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) | wc -l
```

**Expected**: You should see the reference portfolio images for Ansel Adams.

---

### Step 4: Check Existing Dimensional Profiles

```bash
# Query the database for existing Ansel profiles
sqlite3 mondrian/mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id = 'ansel';"

# View sample profile
sqlite3 mondrian/mondrian.db "SELECT image_path, composition_score, lighting_score FROM dimensional_profiles WHERE advisor_id = 'ansel' LIMIT 3;"
```

**If no profiles exist**, you need to index the reference images first:
```bash
python tools/rag/index_with_metadata.py --advisor ansel
```

---

### Step 5: Create Dataset Preparation Script

Create `training/prepare_dataset.py`:

```python
#!/usr/bin/env python3
"""
Prepare training dataset from dimensional_profiles for LoRA fine-tuning.
"""

import json
import sqlite3
from pathlib import Path
from PIL import Image
from datasets import Dataset as HFDataset

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "mondrian" / "mondrian.db"
OUTPUT_DIR = PROJECT_ROOT / "training" / "datasets"


def get_dimensional_profiles(advisor_id: str) -> list:
    """Fetch all dimensional profiles for an advisor."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM dimensional_profiles
        WHERE advisor_id = ?
        AND image_path NOT LIKE '%temp%'
        AND image_path NOT LIKE '%analyze_image%'
    """, (advisor_id,))

    profiles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return profiles


def format_as_training_example(profile: dict, advisor_id: str) -> dict:
    """Convert a dimensional profile to training format."""

    # Build the expected JSON response
    response = {
        "dimensional_analysis": {
            "composition": {
                "score": int(profile['composition_score'] or 0),
                "comment": profile['composition_comment'] or ""
            },
            "lighting": {
                "score": int(profile['lighting_score'] or 0),
                "comment": profile['lighting_comment'] or ""
            },
            "focus_sharpness": {
                "score": int(profile['focus_sharpness_score'] or 0),
                "comment": profile['focus_sharpness_comment'] or ""
            },
            "color_harmony": {
                "score": int(profile['color_harmony_score'] or 0),
                "comment": profile['color_harmony_comment'] or ""
            },
            "subject_isolation": {
                "score": int(profile['subject_isolation_score'] or 0),
                "comment": profile['subject_isolation_comment'] or ""
            },
            "depth_perspective": {
                "score": int(profile['depth_perspective_score'] or 0),
                "comment": profile['depth_perspective_comment'] or ""
            },
            "visual_balance": {
                "score": int(profile['visual_balance_score'] or 0),
                "comment": profile['visual_balance_comment'] or ""
            },
            "emotional_impact": {
                "score": int(profile['emotional_impact_score'] or 0),
                "comment": profile['emotional_impact_comment'] or ""
            }
        },
        "overall_grade": profile.get('overall_grade', 'A')
    }

    # Format as conversation
    messages = [
        {
            "role": "user",
            "content": "<image>\nAnalyze this photograph across all 8 dimensions."
        },
        {
            "role": "assistant",
            "content": json.dumps(response, indent=2)
        }
    ]

    return {
        "messages": messages,
        "images": [profile['image_path']]
    }


def prepare_dataset(advisor_id: str = "ansel", output_name: str = None):
    """Main function to prepare training dataset."""
    print(f"Preparing dataset for advisor: {advisor_id}")

    # Fetch profiles
    profiles = get_dimensional_profiles(advisor_id)
    print(f"Found {len(profiles)} profiles")

    if len(profiles) == 0:
        print("ERROR: No profiles found. Run indexing first:")
        print(f"  python tools/rag/index_with_metadata.py --advisor {advisor_id}")
        return

    # Convert to training format
    examples = []
    for profile in profiles:
        image_path = profile['image_path']

        # Verify image exists
        if not Path(image_path).exists():
            print(f"  SKIP: Image not found: {image_path}")
            continue

        example = format_as_training_example(profile, advisor_id)
        examples.append(example)
        print(f"  Added: {Path(image_path).name}")

    print(f"\nTotal examples: {len(examples)}")

    # Create HuggingFace dataset
    dataset = HFDataset.from_list(examples)

    # Save dataset
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_name = output_name or f"{advisor_id}_dataset"
    output_path = OUTPUT_DIR / output_name
    dataset.save_to_disk(str(output_path))
    print(f"\nDataset saved to: {output_path}")

    return dataset


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--advisor", default="ansel", help="Advisor ID")
    parser.add_argument("--output", default=None, help="Output dataset name")
    args = parser.parse_args()

    prepare_dataset(args.advisor, args.output)
```

**Run it:**
```bash
python training/prepare_dataset.py --advisor ansel
```

---

### Step 6: Create Training Script

Create `training/train_lora.py`:

```python
#!/usr/bin/env python3
"""
Train LoRA adapter for an advisor using mlx_vlm.
"""

import argparse
import os
from pathlib import Path

import mlx.optimizers as optim
from datasets import load_from_disk
from tqdm import tqdm

from mlx_vlm import load
from mlx_vlm.trainer import Dataset, Trainer, save_adapter
from mlx_vlm.trainer.utils import get_peft_model, find_all_linear_names
from mlx_vlm.utils import load_image_processor

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATASETS_DIR = PROJECT_ROOT / "training" / "datasets"
ADAPTERS_DIR = PROJECT_ROOT / "adapters"


def train_lora(
    advisor_id: str,
    model_path: str = "mlx-community/Qwen2-VL-2B-Instruct-bf16",
    rank: int = 8,
    alpha: float = 0.1,
    dropout: float = 0.1,
    learning_rate: float = 5e-5,
    epochs: int = 5,
    batch_size: int = 1
):
    """Train LoRA adapter for an advisor."""

    print(f"=" * 60)
    print(f"LoRA Training for: {advisor_id}")
    print(f"=" * 60)

    # Load dataset
    dataset_path = DATASETS_DIR / f"{advisor_id}_dataset"
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found at {dataset_path}")
        print(f"Run: python training/prepare_dataset.py --advisor {advisor_id}")
        return

    print(f"\n1. Loading dataset from {dataset_path}")
    hf_dataset = load_from_disk(str(dataset_path))
    print(f"   Examples: {len(hf_dataset)}")

    # Load model
    print(f"\n2. Loading model: {model_path}")
    model, processor = load(model_path, processor_config={"trust_remote_code": True})
    config = model.config.__dict__
    image_processor = load_image_processor(model_path)

    # Setup LoRA
    print(f"\n3. Setting up LoRA (rank={rank}, alpha={alpha}, dropout={dropout})")
    linear_layers = find_all_linear_names(model.language_model)
    print(f"   Target layers: {linear_layers}")

    model = get_peft_model(
        model,
        linear_layers,
        rank=rank,
        alpha=alpha,
        dropout=dropout
    )

    # Create training dataset
    print(f"\n4. Creating training dataset")
    train_dataset = Dataset(
        hf_dataset,
        config,
        processor,
        image_processor=image_processor
    )

    # Setup optimizer
    print(f"\n5. Setting up optimizer (lr={learning_rate})")
    optimizer = optim.Adam(learning_rate=learning_rate)

    # Setup trainer
    trainer = Trainer(
        model,
        optimizer,
        train_on_completions=True,
        clip_gradients=1.0
    )

    # Training loop
    print(f"\n6. Training for {epochs} epochs")
    model.train()

    for epoch in range(epochs):
        epoch_loss = 0.0
        progress = tqdm(range(len(train_dataset)), desc=f"Epoch {epoch+1}/{epochs}")

        for i in progress:
            batch = train_dataset[i:i+batch_size]
            loss = trainer.train_step(batch)
            epoch_loss += loss.item()

            progress.set_postfix({"loss": f"{loss.item():.4f}"})

        avg_loss = epoch_loss / len(train_dataset)
        print(f"   Epoch {epoch+1} - Average Loss: {avg_loss:.4f}")

    # Save adapter
    print(f"\n7. Saving adapter")
    output_path = ADAPTERS_DIR / advisor_id
    output_path.mkdir(parents=True, exist_ok=True)
    save_adapter(model, str(output_path / "adapters.safetensors"))
    print(f"   Saved to: {output_path}")

    print(f"\n{'=' * 60}")
    print(f"Training complete!")
    print(f"Adapter saved to: {output_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train LoRA adapter")
    parser.add_argument("--advisor", required=True, help="Advisor ID (e.g., ansel)")
    parser.add_argument("--model", default="mlx-community/Qwen2-VL-2B-Instruct-bf16")
    parser.add_argument("--rank", type=int, default=8, help="LoRA rank")
    parser.add_argument("--alpha", type=float, default=0.1, help="LoRA alpha")
    parser.add_argument("--dropout", type=float, default=0.1, help="LoRA dropout")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--epochs", type=int, default=5, help="Number of epochs")

    args = parser.parse_args()

    train_lora(
        advisor_id=args.advisor,
        model_path=args.model,
        rank=args.rank,
        alpha=args.alpha,
        dropout=args.dropout,
        learning_rate=args.lr,
        epochs=args.epochs
    )
```

**Run training:**
```bash
python training/train_lora.py --advisor ansel --epochs 5 --rank 8
```

---

### Step 7: Verify Adapter Was Created

```bash
ls -la adapters/ansel/
# Should show:
# - adapter_config.json
# - adapters.safetensors
```

---

### Step 8: Create Strategy Pattern Files

Create `mondrian/strategies/base.py`:

```python
"""Abstract base class for analysis strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class AnalysisResult:
    """Unified result from any analysis strategy."""
    dimensional_analysis: Dict[str, Any]
    overall_grade: str
    mode_used: str
    advisor_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnalysisStrategy(ABC):
    """Abstract base for analysis strategies."""

    @abstractmethod
    def analyze(self, image_path: str, advisor_id: str, config) -> AnalysisResult:
        pass

    @abstractmethod
    def is_available(self, advisor_id: str) -> bool:
        pass

    @abstractmethod
    def get_fallback(self) -> Optional['AnalysisStrategy']:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
```

Create `mondrian/strategies/baseline.py`, `mondrian/strategies/rag.py`, `mondrian/strategies/lora.py`, and `mondrian/strategies/context.py` (use the code from the Strategy Pattern section above).

---

### Step 9: Update Config

Edit `mondrian/config.py`:

```python
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(_BASE_DIR, "mondrian.db")

# Analysis mode: "baseline" | "rag" | "lora"
ANALYSIS_MODE = os.environ.get("ANALYSIS_MODE", "rag")

# LoRA adapter directory
LORA_ADAPTER_DIR = os.path.join(_BASE_DIR, "..", "adapters")

# Legacy toggles (for backward compatibility)
RAG_ENABLED = ANALYSIS_MODE == "rag"
LORA_ENABLED = ANALYSIS_MODE == "lora"
EMBEDDINGS_ENABLED = os.environ.get("EMBEDDINGS_ENABLED", "false").lower() == "true"
```

---

### Step 10: Test LoRA Inference

Create `training/test_lora.py`:

```python
#!/usr/bin/env python3
"""Test LoRA adapter inference."""

from pathlib import Path
from mlx_vlm import load, generate
from mlx_vlm.trainer.utils import apply_lora_layers
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_image

PROJECT_ROOT = Path(__file__).parent.parent
ADAPTERS_DIR = PROJECT_ROOT / "adapters"


def test_lora_inference(advisor_id: str, image_path: str):
    """Compare base model vs LoRA model on same image."""

    print(f"Testing LoRA for {advisor_id} on {image_path}")

    # Load base model
    print("\n1. Loading base model...")
    base_model, processor = load("mlx-community/Qwen2-VL-2B-Instruct-bf16")
    config = base_model.config.__dict__

    # Load LoRA adapter
    adapter_path = ADAPTERS_DIR / advisor_id
    if not (adapter_path / "adapter_config.json").exists():
        print(f"ERROR: No adapter found at {adapter_path}")
        return

    print(f"2. Applying LoRA adapter from {adapter_path}")
    lora_model = apply_lora_layers(base_model, str(adapter_path))

    # Load image
    image = load_image(image_path)

    # Create prompt
    prompt = "Analyze this photograph across all 8 dimensions."

    # Generate with base model
    print("\n3. Generating with BASE model...")
    formatted_prompt = apply_chat_template(processor, config, prompt, num_images=1)
    base_response = generate(
        base_model, processor, image, formatted_prompt,
        max_tokens=1000, verbose=False
    )
    print(f"Base response:\n{base_response[:500]}...")

    # Generate with LoRA model
    print("\n4. Generating with LoRA model...")
    lora_response = generate(
        lora_model, processor, image, formatted_prompt,
        max_tokens=1000, verbose=False
    )
    print(f"LoRA response:\n{lora_response[:500]}...")


if __name__ == "__main__":
    import sys
    advisor = sys.argv[1] if len(sys.argv) > 1 else "ansel"
    image = sys.argv[2] if len(sys.argv) > 2 else "test_image.jpg"
    test_lora_inference(advisor, image)
```

**Run test:**
```bash
python training/test_lora.py ansel /path/to/test/image.jpg
```

---

### Step 11: Test via API

Start the service with LoRA mode:
```bash
ANALYSIS_MODE=lora python mondrian/ai_advisor_service.py
```

Test API:
```bash
curl -X POST http://localhost:5100/analyze \
  -F "image=@test_photo.jpg" \
  -F "advisor=ansel" \
  -F "mode=lora"
```

---

### Step 12: Commit Changes

```bash
git add training/ adapters/ mondrian/strategies/ mondrian/config.py
git commit -m "Add LoRA fine-tuning for advisor recommendations

- Add training module with dataset preparation and training scripts
- Implement Strategy Pattern for baseline/rag/lora modes
- Create Ansel Adams LoRA adapter
- Add mode selection via ANALYSIS_MODE env var or per-request

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

## Quick Reference: Commands

| Task | Command |
|------|---------|
| Prepare dataset | `python training/prepare_dataset.py --advisor ansel` |
| Train LoRA | `python training/train_lora.py --advisor ansel --epochs 5` |
| Test inference | `python training/test_lora.py ansel test.jpg` |
| Start with LoRA | `ANALYSIS_MODE=lora python mondrian/ai_advisor_service.py` |
| API test | `curl -X POST localhost:5100/analyze -F image=@x.jpg -F advisor=ansel -F mode=lora` |

---

## Troubleshooting

### No profiles found
```bash
# Index reference images first
python tools/rag/index_with_metadata.py --advisor ansel
```

### Out of memory during training
```bash
# Reduce batch size and rank
python training/train_lora.py --advisor ansel --rank 4 --epochs 3
```

### Adapter not loading
```bash
# Check adapter files exist
ls adapters/ansel/
# Should have: adapter_config.json, adapters.safetensors
```

### Mode fallback occurring
Check the response headers:
```bash
curl -v -X POST localhost:5100/analyze -F image=@x.jpg -F mode=lora 2>&1 | grep X-Analysis
# X-Analysis-Mode should show the actual mode used
```

---

**Status**: Ready for Implementation
**Last Updated**: 2026-01-13
**Author**: Claude Code
