# LoRA Adapter Strategy for Linux CUDA RTX 3060

**Date:** January 15, 2026  
**Branch:** `linux-cuda-backend`  
**Hardware:** RTX 3060 with 12GB VRAM

## Current Adapter Status

### Existing Adapters Found
✓ Located in `adapters/` directory:
- `adapters/ansel/` - Base ansel adapter
- `adapters/ansel_original/` - Original ansel with epochs
- `adapters/ansel_image/` - Image-based ansel

### Adapter Format Analysis
The existing adapters appear to be **minimal MLX-format adapters** with simple config:
```json
{"rank": 8, "alpha": 0.1, "dropout": 0.1}
```

**Issue:** These are likely from macOS MLX training, not PEFT format needed for PyTorch/CUDA

## Recommendation: RETRAIN for Linux

### Why Retrain:
1. **Format Incompatibility**
   - Existing: MLX format (macOS Metal backend)
   - Needed: PEFT format (PyTorch/CUDA backend)
   - Direct conversion is complex and may not preserve quality

2. **Hardware Optimization**
   - RTX 3060 with 4-bit quantization has different memory/performance characteristics than MLX
   - Retraining on actual hardware ensures optimization for GPU

3. **Quality Assurance**
   - Retraining validates adapter quality on target hardware
   - Can fine-tune hyperparameters for RTX 3060 specifically

### Training Resources Available

#### Option A: Quick LoRA Training (Recommended)
**File:** `train_lora_qwen3vl.py` (344 lines)

**Features:**
- PyTorch with PEFT
- 4-bit quantization support
- Designed for Qwen models
- Training on RTX 3060

**Time Estimate:**
- 3 epochs with 100 examples: 15-30 minutes
- 5 epochs with 500 examples: 1-2 hours

**Usage:**
```bash
source venv/bin/activate

# Prepare training data (if needed)
python prepare_training_data.py --advisor ansel

# Train LoRA adapter
python train_lora_qwen3vl.py \
    --base_model "Qwen/Qwen2-VL-7B-Instruct" \
    --data_dir ./training_data \
    --output_dir ./adapters/ansel_pytorch \
    --epochs 3 \
    --batch_size 2 \
    --learning_rate 2e-4 \
    --load_in_4bit \
    --use_gradient_checkpointing
```

#### Option B: Use Training Script
**File:** `retrain_lora_fix.py` (available)

Can orchestrate the full retraining pipeline with validation

#### Option C: Quick Test Mode (No Retraining)
**Trade-off:** Use baseline mode (no LoRA) while training

```bash
# Run baseline (model only, no adapter)
curl -X POST -F "image=@source/photo.jpg" \
  -F "advisor=ansel" -F "enable_rag=false" \
  http://localhost:5100/analyze
```

## Implementation Plan

### Phase 1: Quick Validation (No Changes)
```bash
# 1. Start services in baseline mode
python mondrian/ai_advisor_service_linux.py --port 5100 --load_in_4bit

# 2. Test without LoRA
curl -X POST -F "image=@source/mike-shrub-01004b68.jpg" \
  -F "advisor=ansel" -F "enable_rag=false" \
  http://localhost:5100/analyze

# 3. Verify performance is acceptable
# If baseline is sufficient, can skip LoRA training
```

### Phase 2: Optional LoRA Training
If you want adapter benefits:

```bash
# 1. Prepare training data
python prepare_training_data.py --advisor ansel

# 2. Train PEFT adapter for Qwen2-VL
python train_lora_qwen3vl.py \
    --base_model "Qwen/Qwen2-VL-7B-Instruct" \
    --data_dir ./training/ansel \
    --output_dir ./adapters/ansel_pytorch \
    --epochs 3 \
    --batch_size 2 \
    --load_in_4bit

# 3. Update service to use adapter
python mondrian/ai_advisor_service_linux.py \
    --port 5100 \
    --load_in_4bit \
    --lora_path ./adapters/ansel_pytorch
```

### Phase 3: Validation & Testing
```bash
# Test with LoRA adapter
curl -X POST -F "image=@source/mike-shrub-01004b68.jpg" \
  -F "advisor=ansel" -F "enable_rag=false" \
  http://localhost:5100/analyze

# Compare baseline vs LoRA outputs
```

## Baseline vs LoRA Comparison

| Aspect | Baseline | LoRA Adapter |
|--------|----------|-------------|
| Speed | ⚡ Fastest (15-25s) | ⚡ Fast (18-28s) |
| Quality | ✓ Good | ✓✓ Better (fine-tuned) |
| VRAM | ~4-5 GB | ~4-6 GB |
| Training Time | N/A | 15-30 min (3 epochs) |
| Setup Complexity | Simple | Medium |

## Decision Matrix

### ✓ Use Existing Adapters IF:
- Baseline mode performance is insufficient
- You have PEFT-format adapters for Qwen2-VL
- Training data hasn't changed

### ❌ DO NOT Use Existing Adapters IF:
- They're in MLX format (likely)
- You need optimal quality on RTX 3060
- You want to validate on actual hardware

### ✓ RETRAIN Adapters IF:
- You have training data available
- Quality/optimization matters
- You have 30 minutes to 1 hour for training

### ⚪ SKIP Adapter Training IF:
- Baseline mode performance is acceptable
- Time is critical
- You just want to validate setup

## Quick Start: Choose Your Path

### Path 1: Baseline Only (5 minutes)
```bash
# Fast, no retraining needed
source venv/bin/activate
python mondrian/ai_advisor_service_linux.py --port 5100 --load_in_4bit
# Test with curl above
```

### Path 2: Quick LoRA Training (45 minutes)
```bash
# Retrain PEFT adapter on RTX 3060
python train_lora_qwen3vl.py \
    --base_model "Qwen/Qwen2-VL-7B-Instruct" \
    --data_dir ./training/ansel \
    --output_dir ./adapters/ansel_pytorch \
    --epochs 3 --batch_size 2 --load_in_4bit
```

### Path 3: Hybrid (Recommended)
```bash
# 1. Test baseline first (5 min)
# 2. If satisfied, done
# 3. If not, retrain adapter (45 min)
# 4. Compare results
```

## Performance on RTX 3060

### Baseline (No LoRA)
- Model size: 7B parameters (4-bit ≈ 2.5GB)
- VRAM: 4-5GB
- Inference: 15-25 seconds per image
- Quality: Good for general photography analysis

### LoRA Fine-tuned (PEFT)
- Additional params: ~100K (0.01% of base)
- VRAM: +0.5-1GB (total 4.5-6GB)
- Inference: 18-28 seconds per image (negligible slowdown)
- Quality: Better for specific advisor styles

## Recommendation Summary

**FOR THIS PROJECT:**
1. ✓ Start with **baseline mode** (fastest validation)
2. ✓ If baseline quality is acceptable, **skip LoRA training**
3. ✓ If you need better advisor-specific responses, **retrain PEFT adapter** using `train_lora_qwen3vl.py`
4. ✓ Don't try to use old MLX adapters - they won't work with PyTorch

**Expected Timeline:**
- Baseline setup & test: 5-10 minutes
- LoRA training (if needed): 30-60 minutes
- Total: 35-70 minutes to production

---

**Recommendation:** Test baseline first. If performance is sufficient, you're done in 5 minutes. If you want better quality, retrain adapters in parallel with other work.
