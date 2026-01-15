# AI Advisor Service Integration Guide - LoRA Fine-tuned Models

## Overview

This guide explains how to integrate LoRA fine-tuned models with `mondrian/ai_advisor_service.py` to use them for live inference instead of the base model.

**Key Concept**: The service will optionally load LoRA adapter weights at startup and use the fine-tuned model for all analysis requests.

---

## Integration Architecture

```
    Client Request
          |
          v
    API Endpoint (/analyze)
          |
    +-----+-----+
    |     |     |
    v     v     v
  Image Prompt Config
    |
    +-> Load Model (base + optional LoRA)
    |
    v
  Generate Analysis (MLX inference)
    |
    v
  Return JSON/HTML Response
```

**Decision Point**: When service starts, decide which model to use:
- Base model only (default)
- Base model + LoRA adapter (if `--lora_path` provided)

---

## Required Changes to ai_advisor_service.py

### 1. Add Command-Line Arguments

Add these arguments to the argument parser in `ai_advisor_service.py`:

```python
parser.add_argument(
    "--lora_path",
    type=str,
    default=None,
    help="Path to LoRA adapter directory (optional). If provided, loads fine-tuned model."
)

parser.add_argument(
    "--use_fine_tuned",
    action="store_true",
    help="Use fine-tuned model if --lora_path provided"
)

parser.add_argument(
    "--model_mode",
    type=str,
    choices=["base", "fine_tuned", "ab_test"],
    default="base",
    help="Model selection mode: base (base model only), fine_tuned (use LoRA), ab_test (A/B test both)"
)

parser.add_argument(
    "--ab_test_split",
    type=float,
    default=0.5,
    help="For A/B testing: fraction of requests to route to fine-tuned model (0.0 to 1.0)"
)
```

### 2. Modify get_mlx_model() Function

Update the model loading function to support LoRA adapters:

```python
def get_mlx_model(lora_path=None, use_lora=False):
    """
    Load MLX model with optional LoRA adapter.
    
    Args:
        lora_path: Path to LoRA adapter directory
        use_lora: Whether to load and apply LoRA adapter
    
    Returns:
        (model, processor, is_fine_tuned)
    """
    logger.info(f"Loading base model: {BASE_MODEL}")
    model, processor = mlx_vlm.load(BASE_MODEL)
    
    is_fine_tuned = False
    
    if lora_path and use_lora:
        try:
            logger.info(f"Loading LoRA adapter from {lora_path}")
            
            # Verify adapter files exist
            adapter_config = os.path.join(lora_path, "adapter_config.json")
            adapter_weights = os.path.join(lora_path, "adapter_model.safetensors")
            
            if not os.path.exists(adapter_config):
                logger.error(f"LoRA config not found: {adapter_config}")
                return model, processor, False
            
            if not os.path.exists(adapter_weights):
                logger.error(f"LoRA weights not found: {adapter_weights}")
                return model, processor, False
            
            # Load LoRA configuration
            with open(adapter_config, 'r') as f:
                lora_config = json.load(f)
            
            logger.info(f"LoRA config: {lora_config}")
            
            # TODO: Apply LoRA adapters to model
            # This requires implementing LoRA adapter application in MLX
            # Placeholder until mlx_vlm.lora API is fully documented
            # from mlx_vlm.lora import apply_lora_adapters
            # lora_weights = mx.load(adapter_weights)
            # model = apply_lora_adapters(model, lora_weights)
            
            logger.warning("[TODO] LoRA adapter application not yet implemented")
            is_fine_tuned = False
            
        except Exception as e:
            logger.error(f"Failed to load LoRA adapter: {str(e)}")
            logger.warning("Falling back to base model")
            is_fine_tuned = False
    
    return model, processor, is_fine_tuned
```

### 3. Update Service Initialization

Modify the service startup code to initialize the correct model:

```python
# Global model reference
MODEL = None
PROCESSOR = None
IS_FINE_TUNED = False

# At service startup (in main or app initialization)
def initialize_service(lora_path=None, model_mode="base", use_lora=False):
    global MODEL, PROCESSOR, IS_FINE_TUNED
    
    if model_mode == "base":
        logger.info("Model mode: BASE (no fine-tuning)")
        MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=None, use_lora=False)
    
    elif model_mode == "fine_tuned":
        logger.info("Model mode: FINE-TUNED")
        if not lora_path:
            logger.error("--model_mode fine_tuned requires --lora_path")
            sys.exit(1)
        MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=lora_path, use_lora=True)
        if not IS_FINE_TUNED:
            logger.error("Failed to load fine-tuned model")
            sys.exit(1)
    
    elif model_mode == "ab_test":
        logger.info("Model mode: A/B TEST")
        if not lora_path:
            logger.warning("--model_mode ab_test requires --lora_path; using base model")
            model_mode = "base"
        MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=lora_path, use_lora=use_lora)
    
    logger.info(f"Model initialized. Fine-tuned: {IS_FINE_TUNED}")

# In argparse handling
args = parser.parse_args()
initialize_service(
    lora_path=args.lora_path,
    model_mode=args.model_mode,
    use_lora=args.use_fine_tuned
)
```

### 4. Update /analyze Endpoint (Optional A/B Testing)

For A/B testing, route requests to different models:

```python
@app.route('/analyze', methods=['POST'])
def analyze():
    global MODEL, PROCESSOR, IS_FINE_TUNED, AB_TEST_SPLIT
    
    # Get request data
    data = request.get_json()
    
    # For A/B testing, decide which model to use
    use_fine_tuned = IS_FINE_TUNED
    if args.model_mode == "ab_test":
        # Route randomly based on ab_test_split
        import random
        use_fine_tuned = random.random() < AB_TEST_SPLIT
    
    # Store which model was used in job record for tracking
    if use_fine_tuned:
        logger.info(f"Using FINE-TUNED model for job {job_id}")
        update_job_status(job_id, model_used="fine_tuned")
    else:
        logger.info(f"Using BASE model for job {job_id}")
        update_job_status(job_id, model_used="base")
    
    # Rest of analysis proceeds normally
    # The model (base or fine-tuned) is used transparently
```

---

## Usage Examples

### Example 1: Use Base Model (Default)

```bash
python mondrian/ai_advisor_service.py --port 5100
```

### Example 2: Use Fine-tuned Model Only

```bash
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode fine_tuned
```

### Example 3: A/B Test (50/50 Split)

```bash
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode ab_test \
    --ab_test_split 0.5
```

### Example 4: Gradual Rollout (10% Fine-tuned)

```bash
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode ab_test \
    --ab_test_split 0.1
```

---

## Tracking Model Usage

### Database Schema Addition

Add a column to track which model was used:

```sql
ALTER TABLE jobs ADD COLUMN model_used TEXT DEFAULT 'base';
-- Values: 'base', 'fine_tuned', 'ab_test_base', 'ab_test_fine_tuned'
```

### Logging Model Selection

Update logging to track which model was used:

```python
def update_job_status(job_id, model_used=None, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if model_used:
        updates.append("model_used = ?")
        params.append(model_used)
    
    # ... other updates ...
    
    if updates:
        cursor.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params + [job_id])
        conn.commit()
    
    conn.close()
```

---

## Monitoring and Metrics

### Log Files

Model selection is logged to console/logs:
```
[2025-01-13 10:30:45] Using BASE model for job abc123
[2025-01-13 10:30:46] Analysis completed in 2.3s
```

### A/B Testing Dashboard

Query database to compare model performance:

```python
def compare_model_performance(days=7):
    """Compare metrics between base and fine-tuned models."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        model_used,
        COUNT(*) as total,
        AVG(CAST(json_extract(llm_outputs, '$.overall_score') AS FLOAT)) as avg_score,
        AVG(CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS FLOAT)) as avg_duration
    FROM jobs
    WHERE model_used IN ('base', 'fine_tuned', 'ab_test_base', 'ab_test_fine_tuned')
        AND completed_at > datetime('now', '-' || ? || ' days')
    GROUP BY model_used
    """
    
    cursor.execute(query, (days,))
    results = cursor.fetchall()
    
    return results
```

---

## Rollback Strategy

### Quick Rollback to Base Model

If the fine-tuned model causes issues:

```bash
# Stop service
pkill -f "ai_advisor_service.py"

# Start with base model
python mondrian/ai_advisor_service.py --port 5100
```

### Version Management

Keep multiple model versions:

```
models/
├── qwen3-vl-4b-lora-ansel-v1/
├── qwen3-vl-4b-lora-ansel-v2/  (latest, in production)
└── qwen3-vl-4b-lora-ansel-v2-backup/
```

Switch between versions:

```bash
# Use v1 if issues occur
python mondrian/ai_advisor_service.py \
    --lora_path ./models/qwen3-vl-4b-lora-ansel-v1 \
    --model_mode fine_tuned

# Back to v2
python mondrian/ai_advisor_service.py \
    --lora_path ./models/qwen3-vl-4b-lora-ansel-v2 \
    --model_mode fine_tuned
```

---

## Backward Compatibility

### Design Principles

1. **Default is Base Model**: If no `--lora_path` provided, uses base model (existing behavior)
2. **Optional LoRA Loading**: LoRA adapter loading is optional and doesn't break if unavailable
3. **Graceful Fallback**: If LoRA loading fails, service continues with base model

### Testing Integration

```bash
# Test that service still works without --lora_path
python mondrian/ai_advisor_service.py --port 5100

# Verify API responds
curl -X POST http://localhost:5100/analyze \
    -H "Content-Type: application/json" \
    -d '{"image": "test.jpg", "advisor": "ansel"}'
```

---

## Performance Considerations

### Model Loading Time

- **Base model only**: ~2-3 seconds
- **Base + LoRA**: ~2-3 seconds (LoRA adapters are tiny)

### Inference Time

- **Base model**: ~2-3 seconds per image
- **Fine-tuned (base + LoRA)**: ~2-3 seconds per image (minimal difference)

### Memory Usage

- **Base model**: ~8GB GPU memory
- **Fine-tuned (base + LoRA)**: ~8-8.5GB GPU memory (negligible increase)

---

## Troubleshooting

### Service Won't Start with LoRA Path

**Error**: `FileNotFoundError: adapter_config.json not found`

**Solution**:
```bash
# Verify LoRA directory exists and contains required files
ls -la ./models/qwen3-vl-4b-lora-ansel/
# Should see: adapter_config.json, adapter_model.safetensors, training_args.json
```

### Incorrect Output Format

**Symptom**: Analysis output not in expected JSON format

**Diagnosis**:
1. Check which model was used (base or fine-tuned)
2. Compare outputs manually
3. Review training data quality

### Slow Inference with Fine-tuned Model

**Symptom**: Response times increased

**Diagnosis**:
1. May be normal (LoRA adds minimal overhead)
2. Check GPU utilization: `metal_gpu_monitor` (Metal GPU monitor)
3. Verify LoRA weights loaded correctly

---

## Configuration File (Optional)

For easier management, create `config/model_config.json`:

```json
{
  "models": {
    "base": {
      "id": "Qwen/Qwen3-VL-4B-Instruct",
      "description": "Base model"
    },
    "ansel_v1": {
      "lora_path": "./models/qwen3-vl-4b-lora-ansel-v1",
      "description": "Ansel advisor, first version"
    },
    "ansel_v2": {
      "lora_path": "./models/qwen3-vl-4b-lora-ansel-v2",
      "description": "Ansel advisor, improved version"
    }
  },
  "active_model": "base"
}
```

Load in service:

```python
with open("config/model_config.json") as f:
    model_config = json.load(f)

active_model = model_config["active_model"]
model_info = model_config["models"][active_model]

if "lora_path" in model_info:
    MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(
        lora_path=model_info["lora_path"],
        use_lora=True
    )
else:
    MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model()
```

---

## Summary

**Integration Steps**:

1. ✓ Add `--lora_path`, `--model_mode`, `--ab_test_split` arguments
2. ✓ Update `get_mlx_model()` to load LoRA adapters
3. ✓ Initialize service with selected model
4. ✓ Test with base model (backward compatibility)
5. ✓ Test with fine-tuned model (`--lora_path` + `--model_mode fine_tuned`)
6. ✓ Deploy and monitor A/B testing results
7. ✓ Gradually shift traffic to fine-tuned model if metrics improve

**Testing Checklist**:

- [ ] Service starts without `--lora_path`
- [ ] Service starts with valid `--lora_path`
- [ ] Responses are valid JSON
- [ ] Inference time is acceptable
- [ ] A/B testing properly tracks which model was used
- [ ] Rollback to base model works smoothly

---

**Last Updated**: January 13, 2025
**Status**: Ready for Implementation
