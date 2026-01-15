# LoRA Fine-tuning Implementation Plan - Complete Summary

**Status**: ✅ Planning Complete - Ready for Implementation

**Date**: January 13, 2025

**Duration Estimate**: 8-10 days

---

## Executive Summary

A comprehensive, actionable end-to-end plan has been created for fine-tuning Qwen3-VL-4B on photography analysis data using MLX on Apple Silicon.

**Key Deliverables**:
- ✅ Comprehensive training guide
- ✅ Data linking script
- ✅ MLX-native training script
- ✅ Evaluation framework
- ✅ Service integration guide

**What This Achieves**:
- Fine-tune a large vision-language model to your specific photography analysis domain
- Maintain existing architecture (MLX-based, Apple Silicon)
- Keep model adapters small (~150MB) and portable
- Enable A/B testing and gradual rollout
- Maintain backward compatibility with base model

---

## Files Created

| File | Purpose | Status |
|------|---------|--------|
| [`mondrian/docs/LORA_FINETUNING_GUIDE.md`](mondrian/docs/LORA_FINETUNING_GUIDE.md) | Main training guide | ✅ Complete |
| [`link_training_data.py`](link_training_data.py) | Data pipeline (Phase 0-1) | ✅ Complete |
| [`train_mlx_lora.py`](train_mlx_lora.py) | Training script (Phase 2-3) | ✅ Complete |
| [`evaluate_lora.py`](evaluate_lora.py) | Evaluation framework (Phase 4) | ✅ Complete |
| [`LORA_SERVICE_INTEGRATION.md`](LORA_SERVICE_INTEGRATION.md) | Integration guide (Phase 5) | ✅ Complete |

---

## 6-Phase Implementation Roadmap

### Phase 0: Data Audit & Linking (1 day)

**Goal**: Map analysis files to source images using database

**Execute**:
```bash
python link_training_data.py \
    --db_path ./mondrian/mondrian.db \
    --advisor ansel \
    --output_dir ./training_data
```

**Output**: `training_data_manifest.json` - Mapping all image-analysis pairs

**Success**: 60-80+ valid examples for Ansel advisor

---

### Phase 1: Training Data Preparation (1 day)

**Goal**: Convert analysis markdown to clean training format

**Execute**:
```bash
python prepare_training_data.py \
    --manifest training_data_manifest.json \
    --advisor ansel \
    --output_dir ./training_data
```

**Output**: 
- `training_data_ansel_train.json` (80%)
- `training_data_ansel_val.json` (20%)

**Success**: Valid JSON files with prompt-response pairs

---

### Phase 2: MLX Training Setup (2-3 days)

**Goal**: Build MLX-native fine-tuning infrastructure

**Key Tasks**:
- Review `mlx_vlm.lora` module API
- Implement LoRA adapter application
- Build training loop with loss computation
- Add checkpoint saving

**Note**: `train_mlx_lora.py` is a template with TODO sections for LoRA adapter application

---

### Phase 3: First Fine-tuning Run (1 day)

**Goal**: Execute complete fine-tuning

**Execute**:
```bash
python train_mlx_lora.py \
    --train_data ./training_data/training_data_ansel_train.json \
    --val_data ./training_data/training_data_ansel_val.json \
    --output_dir ./models/qwen3-vl-4b-lora-ansel \
    --epochs 3
```

**Duration**: ~6-12 hours (depending on data size and epochs)

**Outputs**: 
- `adapter_config.json` - LoRA settings
- `adapter_model.safetensors` - Trained weights (~150MB)
- `training_log.jsonl` - Loss history

---

### Phase 4: Evaluation (1-2 days)

**Goal**: Compare base vs fine-tuned model

**Execute**:
```bash
python evaluate_lora.py \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --val_data ./training_data/training_data_ansel_val.json \
    --output_report ./evaluation/comparison_report.json
```

**Metrics**:
- Format compliance (JSON validity)
- Inference performance
- Score consistency
- Qualitative improvements

**Success Criteria**: 
- Format compliance ≥95%
- Inference time <10% overhead
- Qualitative improvements visible

---

### Phase 5: Service Integration (1 day)

**Goal**: Integrate fine-tuned model with AI advisor service

**Changes to `ai_advisor_service.py`**:
```python
# Add arguments
parser.add_argument("--lora_path", ...)
parser.add_argument("--model_mode", choices=["base", "fine_tuned", "ab_test"])

# Update model loading
MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(
    lora_path=args.lora_path,
    use_lora=(args.model_mode != "base")
)
```

**Usage**:
```bash
# Use fine-tuned model
python mondrian/ai_advisor_service.py \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode fine_tuned

# A/B test 50/50
python mondrian/ai_advisor_service.py \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode ab_test \
    --ab_test_split 0.5
```

---

### Phase 6: Iteration Workflow (Ongoing)

**Goal**: Establish continuous improvement cycle

**Workflow**:
1. Collect new analyses
2. Re-link data
3. Prepare updated training data
4. Fine-tune with new data (v2, v3, etc.)
5. Evaluate new version
6. Gradually shift traffic if metrics improve

**Version Management**:
```
models/
├── qwen3-vl-4b-lora-ansel-v1/  (initial)
├── qwen3-vl-4b-lora-ansel-v2/  (improved)
└── qwen3-vl-4b-lora-ansel-v3/  (latest)
```

---

## Data Assets Available

| Asset | Count | Location |
|-------|-------|----------|
| HTML Analysis Files | 60 | `mondrian/analysis/` |
| Markdown Analysis Files (JSON) | 89 | `mondrian/analysis_md/` |
| Source Images | ~80 | `mondrian/source/` |
| Database Records | ~150 | `mondrian/mondrian.db` |

**Recommendation**: Start with 60-80 examples from Ansel advisor

---

## Technical Specifications

### Hardware Requirements

- **GPU**: Apple Silicon (M1/M2/M3 Pro/Max) with 16GB+ unified memory
- **RAM**: 16GB+ (shared with GPU)
- **Storage**: 20GB free (model 8GB, data 2GB, checkpoints 5GB+)

### LoRA Hyperparameters (Recommended)

```python
lora_r = 16              # Rank
lora_alpha = 32          # Scaling (2× rank)
lora_dropout = 0.05      # Regularization
epochs = 3               # Training passes
batch_size = 2           # Images per batch
learning_rate = 2e-4     # Optimizer step size
```

### Model Information

- **Base Model**: Qwen/Qwen3-VL-4B-Instruct
- **Framework**: MLX (Apple-native)
- **LoRA Adapter Size**: ~150MB
- **Training Time**: ~2-4 hours per epoch
- **Inference Overhead**: <10% slower than base

---

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| MLX-VLM LoRA API unclear | Medium | Investigate source code early (Phase 2) |
| Training too slow | Low | Reduce batch size or epochs |
| Memory issues | Medium | Reduce batch size to 1 or LoRA rank to 8 |
| Model quality issues | Medium | Careful hyperparameter tuning, monitor metrics |
| Integration complexity | Low | Keep conditional loading simple, maintain backward compat |

---

## Quality Gates

**Phase 1 Success**:
- [ ] 60-80+ training examples linked
- [ ] Valid JSON in analysis files
- [ ] Train/val split 80/20
- [ ] No data leakage

**Phase 3 Success**:
- [ ] Training completes without errors
- [ ] Loss decreases over epochs
- [ ] Validation loss decreases
- [ ] Checkpoints saved successfully

**Phase 4 Success**:
- [ ] Base model format compliance ≥90%
- [ ] Fine-tuned model format compliance ≥95%
- [ ] Inference time acceptable (<3 seconds)
- [ ] Sample outputs show qualitative improvement

**Phase 5 Success**:
- [ ] Service starts with and without LoRA
- [ ] API responses valid
- [ ] A/B testing tracks model usage
- [ ] Graceful fallback to base model

---

## Quick Start Commands

```bash
# After implementation complete:

# 1. Link data
python link_training_data.py --advisor ansel

# 2. Prepare training data
python prepare_training_data.py \
    --manifest training_data_manifest.json \
    --advisor ansel

# 3. Fine-tune
python train_mlx_lora.py \
    --train_data ./training_data/training_data_ansel_train.json \
    --val_data ./training_data/training_data_ansel_val.json \
    --output_dir ./models/qwen3-vl-4b-lora-ansel \
    --epochs 3

# 4. Evaluate
python evaluate_lora.py \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --val_data ./training_data/training_data_ansel_val.json

# 5. Deploy
python mondrian/ai_advisor_service.py \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode fine_tuned
```

---

## Reference Documentation

- **Main Guide**: [`mondrian/docs/LORA_FINETUNING_GUIDE.md`](mondrian/docs/LORA_FINETUNING_GUIDE.md) - Complete reference with all phases
- **Data Linking**: [`link_training_data.py`](link_training_data.py) - Database-driven image-analysis mapping
- **Training**: [`train_mlx_lora.py`](train_mlx_lora.py) - MLX-native fine-tuning script
- **Evaluation**: [`evaluate_lora.py`](evaluate_lora.py) - Comparison framework
- **Integration**: [`LORA_SERVICE_INTEGRATION.md`](LORA_SERVICE_INTEGRATION.md) - Service changes and deployment

---

## Next Steps

1. **Review** the comprehensive guide: [`mondrian/docs/LORA_FINETUNING_GUIDE.md`](mondrian/docs/LORA_FINETUNING_GUIDE.md)
2. **Investigate** MLX-VLM LoRA API in Phase 2
3. **Implement** `train_mlx_lora.py` LoRA application logic
4. **Test** data pipeline with actual data
5. **Execute** Phase 0-1 data preparation
6. **Run** first fine-tuning
7. **Evaluate** results
8. **Deploy** to service

---

## Success Metrics

**By End of Implementation**:
- ✓ 60-80+ training examples successfully linked
- ✓ Fine-tuned model shows ≥5% improvement in output quality
- ✓ Service runs successfully with fine-tuned model
- ✓ A/B testing infrastructure in place
- ✓ Complete documentation for team

---

**Status**: Ready for implementation
**Plan Created**: January 13, 2025
**Duration**: 8-10 days
**Complexity**: Medium (data engineering + MLX training)
**Impact**: High (domain-specific model improvement)
