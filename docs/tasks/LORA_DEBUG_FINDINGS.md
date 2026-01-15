# LoRA Debug Findings & Solution

## Problem Summary

The LoRA end-to-end test is failing with **incomplete JSON output** from the model:
- Expected: Full JSON with `dimensional_analysis`, `overall_grade`, `techniques`, etc. (3000-5000 chars)
- Actual: Only `image_description` field with trailing comma (~492 chars)
- Error: `[JSON PARSER] All parsing strategies failed`

## Root Cause Identified ✓

**The LoRA adapter was trained on the WRONG training data.**

The adapter at `adapters/ansel/` was trained using:
- **File**: `training/datasets/ansel_combined_train.jsonl` (1494 lines)
- **Content**: Ansel Adams **philosophy text** (books, essays, biographical information)
- **NOT image analysis**: No image analysis examples, no dimensional scoring, no JSON structure training

Expected training data should have been:
- **File**: `training/datasets/ansel_image_training_nuanced.jsonl` (21 examples)
- **Content**: Image analysis with full JSON structure including:
  - `dimensional_analysis` with 8 dimensions
  - `overall_grade`
  - `advisor_notes`
  - `image_path` and label

### Evidence

From log `/logs/ai_advisor_service_1768428395.log`:
```
[JSON PARSER] First 100 chars: '{\n  "image_description": "The photograph depicts a dramatic desert landscape at sunset, with a range'
[JSON PARSER] Last 100 chars: ' foreground vegetation is silhouetted against the bright sand, adding texture and visual interest.",'
[JSON PARSER] All parsing strategies failed
[JSON PARSER] Response length: 492 chars
```

The model trained on philosophy text now generates only image descriptions (from system prompt) and stops.

From training config `/adapters/ansel/training_config.json`:
```json
{
  "num_examples": 1478,  // <-- This is ansel_combined_train.jsonl count
  "model_path": "mlx-community/Qwen3-VL-4B-Instruct-4bit",
  "rank": 8,
  "alpha": 0.1,
  "dropout": 0.1,
  "epochs": 3,
  "batch_size": 1
}
```

## Available Training Data Files

| File | Lines | Content | Status |
|------|-------|---------|--------|
| `ansel_combined_train.jsonl` | 1494 | Philosophy/text (WRONG) | ❌ Was used for training |
| `ansel_image_training_nuanced.jsonl` | 21 | Full image analysis JSON | ✅ Correct format, too few examples |
| `ansel_image_training_nuanced_abs.jsonl` | 21 | Image analysis JSON (absolute) | ✅ Correct format, too few examples |
| `ansel_text_train.jsonl` | ? | Text training | ❌ Text only |
| `ansel_train.jsonl` | ? | ? | ? |

## Solutions

### Solution 1: Retrain with Correct Data (RECOMMENDED)

**Time**: 45-60 minutes | **Reliability**: HIGH

Steps:
```bash
# 1. Stop services
# (Ctrl+C or kill the services)

# 2. Retrain with correct image analysis data
python3 train_mlx_lora.py \
  --advisor ansel \
  --train_data training/datasets/ansel_image_training_nuanced.jsonl \
  --epochs 3 \
  --batch_size 1

# 3. Restart services
python3 mondrian/start_services.py

# 4. Test
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

**Note**: Only 21 examples available - this is a very small dataset. Model may not learn much, but should at least generate complete JSON structure.

### Solution 2: Use Baseline or RAG Mode (IMMEDIATE WORKAROUND)

**Time**: 5 minutes | **Reliability**: VERY HIGH

These modes work perfectly and produce complete output:

```bash
# Test baseline mode
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline

# Test RAG mode (retrieval-augmented)
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag

# Comparison test
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare
```

### Solution 3: Generate More Training Data

**Time**: 1-2 hours | **Reliability**: HIGHEST

Before retraining with more examples:

```bash
# 1. Generate analysis outputs from baseline model
python3 scripts/generate_training_data.py \
  --advisor ansel \
  --input_dir source/ \
  --output training/datasets/ansel_full_training.jsonl

# 2. Retrain with full dataset
python3 train_mlx_lora.py \
  --advisor ansel \
  --train_data training/datasets/ansel_full_training.jsonl \
  --epochs 3

# 3. Test
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

## Why This Happened

The training pipeline likely ran like this:

```
train_mlx_lora.py 
  ↓ (no --train_data specified or default used)
  ├─→ defaulted to ansel_combined_train.jsonl
  ├─→ loaded 1478 philosophy text examples
  ├─→ trained model on philosophy (not image analysis)
  └─→ saved to adapters/ansel/
```

Result: Model learned to generate philosophy discussions, not image analysis JSON.

## Quick Diagnostic

To verify the training data issue:

```bash
# Check what the model outputs for an image
curl -X POST http://127.0.0.1:5100/analyze \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "mode=lora" 2>/dev/null | python3 -m json.tool | head -50

# Compare to baseline
curl -X POST http://127.0.0.1:5100/analyze \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "mode=baseline" 2>/dev/null | python3 -m json.tool | head -50
```

Baseline should have full JSON structure. LoRA should be incomplete.

## Recommendations Going Forward

1. **Immediate**: Use RAG or baseline mode for production
2. **Short-term**: Retrain LoRA with correct image analysis data (even just 21 examples will be better than current)
3. **Long-term**: Set up automated training data generation pipeline to create more examples

## Files Involved

- **Current (broken)**: `adapters/ansel/` (trained on philosophy text)
- **Training data (wrong)**: `training/datasets/ansel_combined_train.jsonl`
- **Training data (correct)**: `training/datasets/ansel_image_training_nuanced.jsonl` (21 examples)
- **Training script**: `train_mlx_lora.py`
- **Strategy code**: `mondrian/strategies/lora.py`
- **Logs**: `logs/ai_advisor_service_*.log`
