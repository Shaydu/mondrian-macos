# LoRA Strategy Pattern Implementation Guide

## Executive Summary

Your documentation outlines a comprehensive **strategy pattern** for LoRA fine-tuning integration. The pattern allows the service to dynamically select between multiple model configurations at startup through command-line arguments, enabling:

1. **Base Model Only** (default, backward compatible)
2. **Fine-tuned Model Only** (improved domain-specific performance)
3. **A/B Testing** (gradual rollout with traffic splitting)

---

## Current State of Implementation

### ✅ Completed Work
- **Documentation**: Comprehensive guides for all 6 phases
- **Data Scripts**: `link_training_data.py`, `prepare_training_data.py`
- **Training Script**: `train_mlx_lora.py` (with TODOs for LoRA application)
- **Evaluation Script**: `evaluate_lora.py`
- **Service Integration Guide**: Complete specification with code examples
- **Architectural Design**: Clean separation of concerns with strategy pattern

### ⏳ Outstanding Work

The main gap is **partial implementation** of the service integration. Here's what needs to be done:

---

## What Needs to be Done - The LoRA Strategy Pattern Implementation

### Phase 1: Implement the Strategy Pattern in `ai_advisor_service.py`

The strategy pattern requires three key changes:

#### 1.1 Add New Command-Line Arguments

```python
# Add to parser in ai_advisor_service.py (around line 89)

parser.add_argument(
    "--lora_path",
    type=str,
    default=None,
    help="Path to LoRA adapter directory (optional). If provided, loads fine-tuned model."
)

parser.add_argument(
    "--model_mode",
    type=str,
    choices=["base", "fine_tuned", "ab_test"],
    default="base",
    help="Model selection strategy: base (base model only), fine_tuned (use LoRA), ab_test (A/B test both)"
)

parser.add_argument(
    "--ab_test_split",
    type=float,
    default=0.5,
    help="For A/B testing: fraction of requests to route to fine-tuned model (0.0 to 1.0)"
)
```

**Purpose**: These arguments implement the "strategy selector" - users choose at service startup which strategy to use.

#### 1.2 Implement the `get_mlx_model()` Enhancement

Update the model loading function to support LoRA adapters:

**Requirements**:
- Accept optional `lora_path` and `use_lora` parameters
- Return tuple: `(model, processor, is_fine_tuned_flag)`
- Validate adapter files exist before loading
- Load adapter configuration from JSON
- **TODO**: Implement the actual LoRA adapter application (this is where mlx-vlm's LoRA API is used)
- Gracefully fall back to base model if LoRA loading fails

**Key Implementation Points**:
```python
def get_mlx_model(lora_path=None, use_lora=False):
    # 1. Load base model (existing code)
    # 2. If use_lora and lora_path:
    #    a. Validate adapter_config.json exists
    #    b. Validate adapter_model.safetensors exists
    #    c. Load adapter configuration
    #    d. Load adapter weights (mx.load())
    #    e. Apply LoRA to model (needs mlx-vlm LoRA API)
    # 3. Return (model, processor, is_fine_tuned)
```

#### 1.3 Implement Strategy Initialization

Create an initialization function that applies the selected strategy:

```python
def initialize_service(lora_path=None, model_mode="base", ab_test_split=0.5):
    """Initialize service with selected model strategy."""
    global MODEL, PROCESSOR, IS_FINE_TUNED, MODEL_MODE, AB_TEST_SPLIT
    
    if model_mode == "base":
        # Load base model only
        MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=None, use_lora=False)
    
    elif model_mode == "fine_tuned":
        # Load base + LoRA adapter
        if not lora_path:
            logger.error("--model_mode fine_tuned requires --lora_path")
            sys.exit(1)
        MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=lora_path, use_lora=True)
        if not IS_FINE_TUNED:
            logger.error("Failed to load fine-tuned model")
            sys.exit(1)
    
    elif model_mode == "ab_test":
        # A/B test: randomly route between base and fine-tuned
        if not lora_path:
            logger.warning("A/B test requires --lora_path, falling back to base")
            model_mode = "base"
        MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=lora_path, use_lora=True)
    
    MODEL_MODE = model_mode
    AB_TEST_SPLIT = ab_test_split
    logger.info(f"Service initialized with strategy: {model_mode}, Fine-tuned: {IS_FINE_TUNED}")
```

#### 1.4 Implement Strategy Execution in `/analyze` Endpoint

Update the analysis endpoint to use the correct strategy:

```python
@app.route('/analyze', methods=['POST'])
def analyze():
    global MODEL, PROCESSOR, IS_FINE_TUNED, MODEL_MODE, AB_TEST_SPLIT
    
    # ... existing code to get request data ...
    
    # Determine which model to use based on strategy
    use_fine_tuned = False
    
    if MODEL_MODE == "base":
        use_fine_tuned = False
    elif MODEL_MODE == "fine_tuned":
        use_fine_tuned = True
    elif MODEL_MODE == "ab_test":
        import random
        use_fine_tuned = random.random() < AB_TEST_SPLIT
    
    # Log which model was used (for tracking)
    model_label = "fine_tuned" if use_fine_tuned else "base"
    logger.info(f"Job {job_id}: Using {model_label} model")
    
    # Store model choice in job record (optional, for analytics)
    # update_job_status(job_id, model_used=model_label)
    
    # ... rest of analysis proceeds normally ...
    # The model (base or fine-tuned) is used transparently
```

---

### Phase 2: Implement the LoRA Adapter Application Logic

This is the **critical TODO** in `train_mlx_lora.py` and needs to be completed in `get_mlx_model()`:

**The Challenge**: Apply trained LoRA adapter weights to the base MLX model

**Required Investigation**:
1. Check MLX-VLM's LoRA utilities
2. Understand adapter weight structure
3. Identify which model layers receive LoRA adapters
4. Implement the application logic

**Placeholder Code** (to be replaced):
```python
# TODO: Implement LoRA adapter application
# Expected API (to be confirmed from mlx-vlm):
# from mlx_vlm.lora import apply_lora_adapters
# or similar

# Load LoRA weights
lora_weights = mx.load(adapter_weights)

# Apply to model
# Option A: Direct application
# model = apply_lora_adapters(model, lora_weights, lora_config)

# Option B: Layer-by-layer application
# For each layer in lora_config:
#   inject_lora(model.layer, lora_weights[layer])

# Option C: Manual low-rank decomposition
# For each qualified layer:
#   layer.weight = layer.weight + (B @ A) @ layer.weight
```

---

### Phase 3: Database Tracking (Optional but Recommended)

Add model usage tracking to database:

```sql
ALTER TABLE jobs ADD COLUMN model_used TEXT DEFAULT 'base';
-- Values: 'base', 'fine_tuned', 'ab_test_base', 'ab_test_fine_tuned'
```

This enables analytics and A/B test comparison queries.

---

## Implementation Checklist

### ✅ Phase 1: Strategy Pattern Infrastructure

- [ ] Add `--lora_path`, `--model_mode`, `--ab_test_split` arguments
- [ ] Create global variables: `MODEL_MODE`, `AB_TEST_SPLIT`
- [ ] Implement `initialize_service()` function
- [ ] Update service initialization code (where argparse results are used)
- [ ] Update `/analyze` endpoint to use strategy

### ⏳ Phase 2: LoRA Adapter Application

- [ ] Research MLX-VLM's LoRA API
- [ ] Implement `get_mlx_model()` LoRA loading section
- [ ] Test with dummy LoRA adapter
- [ ] Handle edge cases and errors

### ⏳ Phase 3: Testing & Validation

- [ ] Test base model mode (no changes needed, backward compatible)
- [ ] Test fine-tuned mode with valid LoRA adapter
- [ ] Test A/B test mode (random routing)
- [ ] Verify service starts/stops cleanly
- [ ] Verify API responses are valid

### ⏳ Phase 4: Analytics & Monitoring

- [ ] Add database column for model tracking
- [ ] Implement model usage logging
- [ ] Create comparison query
- [ ] Monitor performance metrics

---

## How the Strategy Pattern Works

```
Command Line Arguments
        |
        v
    parser.parse_args()
        |
        +---> args.model_mode
        +---> args.lora_path
        +---> args.ab_test_split
        |
        v
initialize_service()
        |
        +---> Strategy: BASE
        |     └---> Load base model only
        |     └---> Is_fine_tuned = False
        |
        +---> Strategy: FINE_TUNED
        |     └---> Load base + LoRA
        |     └---> Is_fine_tuned = True
        |     └---> Exit if fails
        |
        +---> Strategy: A/B_TEST
              └---> Load base + LoRA (if available)
              └---> Mark for random routing
        |
        v
    Service Running
        |
        v
   /analyze request
        |
        +---> If BASE: use base model
        +---> If FINE_TUNED: use fine-tuned
        +---> If A/B_TEST: randomly pick (split = probability)
        |
        v
    Analysis Complete
        |
        v
   Log which model was used
```

---

## Usage Examples (Once Implemented)

### Example 1: Default (Base Model)
```bash
python mondrian/ai_advisor_service.py --port 5100
# Uses base Qwen3-VL-4B only
```

### Example 2: Full Fine-tuned
```bash
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode fine_tuned
# Uses base + Ansel LoRA adapter exclusively
```

### Example 3: A/B Test 50/50
```bash
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode ab_test \
    --ab_test_split 0.5
# 50% of requests use base, 50% use fine-tuned
```

### Example 4: Gradual Rollout (10% Fine-tuned)
```bash
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode ab_test \
    --ab_test_split 0.1
# 90% base model, 10% fine-tuned (safe testing)
```

---

## Key Design Benefits

1. **Strategy Pattern**: Clean separation of model selection logic
2. **Backward Compatible**: Default is existing behavior (base model only)
3. **Gradual Rollout**: A/B testing enables safe deployment
4. **Easy Rollback**: Stop service, restart without `--lora_path`
5. **Observable**: Every request logs which model was used
6. **Testable**: Each strategy can be tested independently

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| LoRA adapter loading fails | Graceful fallback to base model with warning |
| Random number generation not seeded | Use Python's built-in `random.random()` |
| Database schema doesn't have model_used | Make optional, log to console instead |
| Service memory increases with LoRA | LoRA adapters are tiny (~150MB, negligible overhead) |
| Inference slows with LoRA | Overhead <10% (acceptable for quality improvement) |

---

## Next Steps

1. **Review** this plan with your team
2. **Ask**: Should I implement phases 1-3 (strategy pattern + LoRA application)?
3. **Investigate**: MLX-VLM's LoRA API if not already done
4. **Implement**: Phase 1 first (safe, doesn't require LoRA working)
5. **Test**: Each strategy independently
6. **Deploy**: Start with A/B testing at 10% fine-tuned

---

## Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `mondrian/ai_advisor_service.py` | Add args, `get_mlx_model()`, `initialize_service()`, `/analyze` logic | ⭐⭐⭐ HIGH |
| `train_mlx_lora.py` | Implement LoRA adapter application TODO | ⭐⭐ MEDIUM |
| `mondrian/mondrian.db` schema | Add `model_used` column (optional) | ⭐ LOW |
| `mondrian/sqlite_helper.py` | Add `update_job_status()` variant (optional) | ⭐ LOW |

---

## Summary

Your LoRA strategy pattern is well-designed and documented. The main work remaining is:

1. ✅ **Phase 1** (Low effort): Add strategy pattern infrastructure to service
2. ⏳ **Phase 2** (Medium effort): Implement LoRA adapter application
3. ⏳ **Phase 3** (Low effort): Test all three strategies
4. ⏳ **Phase 4** (Optional): Add analytics tracking

**Estimated Effort**: 
- Phase 1: 1-2 hours
- Phase 2: 2-4 hours (depends on MLX-VLM API clarity)
- Phase 3: 1-2 hours
- Phase 4: 1 hour

**Total**: 5-9 hours of focused development work

---

**Created**: January 14, 2026
**Status**: Ready for Implementation
**Complexity**: Medium (integrating multiple components)
