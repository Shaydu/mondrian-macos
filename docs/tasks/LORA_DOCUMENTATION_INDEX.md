# LoRA Fine-tuning Documentation Index

**Status**: ✅ Planning Complete - All Documentation Ready

**Last Updated**: January 13, 2025

---

## 📋 Documentation Map

### Core Planning Documents

1. **[LORA_IMPLEMENTATION_PLAN.md](LORA_IMPLEMENTATION_PLAN.md)** ⭐ START HERE
   - Executive summary of entire plan
   - 6-phase implementation roadmap
   - Risk mitigation and quality gates
   - Quick reference commands
   - **Best for**: Understanding the big picture

2. **[mondrian/docs/LORA_FINETUNING_GUIDE.md](mondrian/docs/LORA_FINETUNING_GUIDE.md)** - Comprehensive Reference
   - Detailed breakdown of all 6 phases
   - Data schemas and formats
   - Hyperparameter reference
   - Troubleshooting guide
   - Quick reference workflows
   - **Best for**: Step-by-step execution guidance

### Implementation Scripts

3. **[link_training_data.py](link_training_data.py)** - Data Linking (Phase 0-1)
   - Maps analysis files to source images via database
   - Validates JSON format
   - Creates training manifest
   - **Usage**: 
     ```bash
     python link_training_data.py --advisor ansel
     ```

4. **[train_mlx_lora.py](train_mlx_lora.py)** - Fine-tuning Trainer (Phase 2-3)
   - MLX-native training with LoRA adapters
   - Handles batching and loss computation
   - Checkpoint saving
   - **Note**: Contains TODO for LoRA adapter application
   - **Usage**:
     ```bash
     python train_mlx_lora.py --train_data training_data_ansel_train.json
     ```

5. **[evaluate_lora.py](evaluate_lora.py)** - Evaluation Framework (Phase 4)
   - Compares base vs fine-tuned models
   - Format compliance metrics
   - Performance benchmarking
   - Generates comparison report
   - **Usage**:
     ```bash
     python evaluate_lora.py --lora_path ./models/qwen3-vl-4b-lora-ansel
     ```

### Integration Guides

6. **[LORA_SERVICE_INTEGRATION.md](LORA_SERVICE_INTEGRATION.md)** - Service Integration (Phase 5)
   - Required changes to `ai_advisor_service.py`
   - A/B testing setup
   - Rollback strategy
   - Monitoring and metrics
   - **Best for**: Deployment and production integration

---

## 🚀 Quick Start

### For Managers/Decision Makers

1. Read: [LORA_IMPLEMENTATION_PLAN.md](LORA_IMPLEMENTATION_PLAN.md)
2. Review: 6-phase roadmap and timeline (8-10 days)
3. Approve: Risk mitigations and quality gates

### For Developers

1. Read: [LORA_IMPLEMENTATION_PLAN.md](LORA_IMPLEMENTATION_PLAN.md) (overview)
2. Read: [mondrian/docs/LORA_FINETUNING_GUIDE.md](mondrian/docs/LORA_FINETUNING_GUIDE.md) (detailed)
3. Execute Phase 0-1:
   ```bash
   python link_training_data.py --advisor ansel
   python prepare_training_data.py --manifest training_data_manifest.json
   ```
4. Implement Phase 2: Review [train_mlx_lora.py](train_mlx_lora.py) and fill in TODOs
5. Execute Phase 3: Run fine-tuning
6. Execute Phase 4: Run evaluation
7. Implement Phase 5: Integrate with service using [LORA_SERVICE_INTEGRATION.md](LORA_SERVICE_INTEGRATION.md)

---

## 📊 Implementation Timeline

```
Week 1
├─ Mon: Phase 0 - Data linking (1 day)
├─ Tue: Phase 1 - Data preparation (1 day)
├─ Wed-Thu: Phase 2 - MLX setup & Phase 3 - Training (3 days)
└─ Fri: Phase 4 - Evaluation (1 day)

Week 2
├─ Mon: Phase 5 - Integration (1 day)
├─ Tue-Fri: Phase 6 - Testing, docs, iteration (4 days)
```

**Total**: 8-10 days

---

## 🎯 Key Concepts

### What is LoRA Fine-tuning?

LoRA (Low-Rank Adaptation) is a technique to adapt large models to specific domains:

- **Memory Efficient**: Only ~1-5% of parameters trained
- **Fast**: Hours instead of days/weeks
- **Portable**: Small adapter files (~150MB)
- **Flexible**: Can combine multiple adapters

### Why Fine-tune Qwen3-VL-4B?

Your photography analysis data contains patterns the base model hasn't seen:
- Improves consistency with your analysis style
- Enhances photography-specific terminology
- Maintains JSON output format
- Preserves advisor guidance (Ansel style)

---

## 📁 File Organization

```
mondrian-macos/
├── mondrian/
│   ├── docs/
│   │   └── LORA_FINETUNING_GUIDE.md        ← Main reference
│   ├── source/                              ← Source images (~80)
│   ├── analysis_md/                         ← Analysis files (~89)
│   └── mondrian.db                          ← Job records
├── link_training_data.py                    ← Phase 0-1 script
├── prepare_training_data.py                 ← Existing, will update
├── train_mlx_lora.py                        ← Phase 2-3 script
├── evaluate_lora.py                         ← Phase 4 script
├── LORA_SERVICE_INTEGRATION.md              ← Phase 5 guide
├── LORA_IMPLEMENTATION_PLAN.md              ← This summary
└── training_data/                           ← Output (to be created)
    ├── training_data_manifest.json
    ├── training_data_ansel_train.json
    └── training_data_ansel_val.json

models/                                      ← Output (to be created)
└── qwen3-vl-4b-lora-ansel/
    ├── adapter_config.json
    ├── adapter_model.safetensors
    └── training_args.json
```

---

## ✅ Quality Checklist

### Phase 1: Data Preparation
- [ ] `link_training_data.py` runs without errors
- [ ] `training_data_manifest.json` created
- [ ] 60-80+ examples for Ansel advisor
- [ ] Train/val split is 80/20

### Phase 2-3: Training
- [ ] `train_mlx_lora.py` training loop works
- [ ] Loss decreases over epochs
- [ ] Checkpoints save successfully
- [ ] Model loads for inference

### Phase 4: Evaluation
- [ ] Base model format compliance ≥90%
- [ ] Fine-tuned model format compliance ≥95%
- [ ] Inference time <3 seconds
- [ ] Sample outputs show improvement

### Phase 5: Integration
- [ ] Service starts with `--lora_path`
- [ ] Service starts without `--lora_path` (backward compatible)
- [ ] A/B testing tracks model usage
- [ ] Responses are valid JSON

---

## 🔗 Related Documentation

**Existing Documentation**:
- [MLX_LORA_PLAN.md](MLX_LORA_PLAN.md) - Original MLX architecture plan
- [MLX_LORA_ROADMAP.md](MLX_LORA_ROADMAP.md) - Original roadmap
- [docs/LoRA/tuning-roadmap.md](docs/LoRA/tuning-roadmap.md) - Technical specs
- [LORA_SETUP_SUMMARY.md](LORA_SETUP_SUMMARY.md) - Setup reference

**System Documentation**:
- [docs/architecture/data-flow.md](docs/architecture/data-flow.md) - System architecture
- [mondrian/sqlite_helper.py](mondrian/sqlite_helper.py) - Database schema

---

## 🆘 Troubleshooting

### Common Issues

**"Image file not found"**
- Verify image paths are absolute
- Run `link_training_data.py` to create manifest

**"JSON parse error"**
- Check analysis files contain valid JSON
- Run validation in `link_training_data.py`

**Out of Memory**
- Reduce `batch_size` to 1
- Reduce `lora_r` from 16 to 8
- Reduce `max_seq_length` to 1024

**Service won't start with LoRA**
- Verify LoRA directory exists
- Check `adapter_config.json` present
- Verify `adapter_model.safetensors` present

See [mondrian/docs/LORA_FINETUNING_GUIDE.md](mondrian/docs/LORA_FINETUNING_GUIDE.md) troubleshooting section for detailed solutions.

---

## 🔄 Iteration Workflow

Once Phase 1-5 complete, establish continuous improvement:

```
Collect New Data
     ↓
Re-link (link_training_data.py)
     ↓
Prepare Training Data (prepare_training_data.py)
     ↓
Fine-tune v2 (train_mlx_lora.py)
     ↓
Evaluate v2 (evaluate_lora.py)
     ↓
If improved → Deploy v2
If declined → Keep v1
```

---

## 📚 Learning Resources

- **LoRA Paper**: https://arxiv.org/abs/2106.09685
- **MLX Documentation**: https://ml-explore.github.io/mlx/
- **MLX-VLM GitHub**: https://github.com/Blaizzy/mlx-vlm
- **Qwen3-VL Model Card**: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct

---

## 💡 Key Takeaways

1. **Complete End-to-End Plan**: From data linking through integration
2. **MLX-Native Approach**: Leverages Apple Silicon, no PyTorch
3. **Small Adapter Files**: ~150MB, easy to store and version
4. **Backward Compatible**: Service works with or without LoRA
5. **A/B Testing Ready**: Can gradually shift traffic to fine-tuned model
6. **Measurable Improvements**: Evaluation framework for metrics comparison
7. **Iteration Ready**: Workflow for continuous model improvement

---

## 📞 Support

For questions about:

- **Overall Plan**: See [LORA_IMPLEMENTATION_PLAN.md](LORA_IMPLEMENTATION_PLAN.md)
- **Detailed Instructions**: See [mondrian/docs/LORA_FINETUNING_GUIDE.md](mondrian/docs/LORA_FINETUNING_GUIDE.md)
- **Data Linking**: See [link_training_data.py](link_training_data.py)
- **Training**: See [train_mlx_lora.py](train_mlx_lora.py)
- **Evaluation**: See [evaluate_lora.py](evaluate_lora.py)
- **Integration**: See [LORA_SERVICE_INTEGRATION.md](LORA_SERVICE_INTEGRATION.md)
- **Troubleshooting**: See [mondrian/docs/LORA_FINETUNING_GUIDE.md](mondrian/docs/LORA_FINETUNING_GUIDE.md#troubleshooting)

---

**Created**: January 13, 2025
**Status**: Ready for Implementation
**Complexity**: Medium (data engineering + MLX training)
**Timeline**: 8-10 days
**Team**: 1-2 ML engineers recommended
