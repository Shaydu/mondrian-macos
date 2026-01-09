# MLX-Native LoRA Fine-tuning Roadmap for Qwen3-VL-4B

## Executive Summary

This roadmap outlines a **pure MLX approach** for LoRA fine-tuning of Qwen3-VL-4B, with **no PyTorch dependencies**. The plan is structured in phases, starting with investigation and moving through implementation to integration.

## Current Status

✅ **Planning Phase Complete**
- Architecture plan documented
- Investigation script created
- Roadmap defined

✅ **Investigation Phase Complete**
- Investigation report generated
- **Key Finding: MLX-VLM has built-in LoRA support!**
  - `lora.py` module exists
  - `trainer` package exists
  - LoRA utilities confirmed in source code

⏳ **Next: Phase 1 - LoRA Implementation**
- Examine `mlx_vlm.lora` module
- Review `mlx_vlm.trainer` package
- Test LoRA API usage

## Current System Analysis

### Existing Setup
- **Framework**: MLX (Apple Silicon optimized)
- **Model Package**: `mlx-vlm` (version 0.0.11+)
- **Model**: Qwen3-VL-4B-Instruct (MLX format)
- **Current Usage**: Inference via `mlx_vlm.load()` and `mlx_vlm.generate()`
- **Hardware**: Apple Silicon with Metal GPU

### Key Constraints
1. Must use MLX framework exclusively (no PyTorch)
2. Must work with `mlx-vlm` package structure
3. Must maintain compatibility with existing inference pipeline
4. Must leverage Metal GPU acceleration

## Phase Breakdown

### Phase 0: Investigation & Research (Current)

**Goal**: Understand MLX-VLM capabilities and structure

**Tasks**:
1. ✅ Create investigation script (`investigate_mlx_vlm.py`)
2. ⏳ Run investigation to discover:
   - LoRA support in mlx-vlm
   - Training utilities available
   - Model architecture details
   - Example code patterns
3. ⏳ Review MLX-VLM GitHub repository
4. ⏳ Check for training examples
5. ⏳ Examine model parameter structure

**Deliverables**:
- Investigation report
- Capability assessment
- Architecture understanding

**Timeline**: 1-2 days

---

### Phase 1: LoRA Implementation

**Goal**: Implement or integrate LoRA adapters for MLX

**Tasks**:
1. **If Built-in Support Exists:**
   - Learn API usage
   - Test with small example
   - Document usage patterns

2. **If Custom Implementation Needed:**
   - Design LoRA layer class
   - Implement low-rank decomposition
   - Add parameter freezing logic
   - Create adapter application utilities

**Key Components**:
```python
# LoRA Layer Structure
class LoRALayer(nn.Module):
    def __init__(self, base_layer, rank, alpha):
        # Initialize A and B matrices
        # Store base layer reference
        
    def __call__(self, x):
        # Compute: base(x) + (B @ A) @ x
        # Apply scaling factor
```

**Deliverables**:
- LoRA implementation module
- Unit tests
- Small working example

**Timeline**: 3-5 days

---

### Phase 2: Training Infrastructure

**Goal**: Build complete training pipeline

**Tasks**:
1. **Data Pipeline**
   - Convert existing analyses to training format
   - Create MLX-compatible data loader
   - Implement batching with padding
   - Add data validation

2. **Training Loop**
   - Forward pass implementation
   - Loss computation (causal LM)
   - Backward pass (automatic via MLX)
   - Optimizer integration
   - Gradient accumulation

3. **Checkpointing**
   - Save LoRA adapter weights
   - Save optimizer state
   - Save training metadata
   - Implement resume capability

4. **Monitoring**
   - Loss logging
   - Progress tracking
   - Validation loop
   - Basic metrics

**Key Components**:
```python
# Training Loop Structure
def train_epoch(model, dataloader, optimizer):
    for batch in dataloader:
        loss_fn = lambda m, b: compute_loss(m, b)
        loss_and_grad_fn = mx.value_and_grad(loss_fn)
        
        loss, grads = loss_and_grad_fn(model, batch)
        optimizer.update(model, grads)
        mx.eval(model.parameters())
        
        log_metrics(loss)
```

**Deliverables**:
- Training script
- Data preparation utilities
- Checkpointing system
- Basic monitoring

**Timeline**: 5-7 days

---

### Phase 3: Integration & Testing

**Goal**: Integrate fine-tuned model with existing system

**Tasks**:
1. **Model Loading**
   - Modify `get_mlx_model()` to support LoRA
   - Add adapter loading logic
   - Test inference with adapters
   - Verify backward compatibility

2. **Service Updates**
   - Add LoRA configuration option
   - Update service initialization
   - Add adapter path parameter
   - Test end-to-end flow

3. **Evaluation**
   - Compare fine-tuned vs base model
   - Test on validation set
   - Measure performance impact
   - Check output quality

**Integration Points**:
```python
# In ai_advisor_service.py
def get_mlx_model(lora_path=None):
    model, processor = mlx_vlm.load(BASE_MODEL)
    
    if lora_path:
        lora_weights = mx.load(lora_path)
        apply_lora_adapters(model, lora_weights)
    
    return model, processor
```

**Deliverables**:
- Integrated service
- Test suite
- Performance benchmarks
- Documentation

**Timeline**: 3-4 days

---

### Phase 4: Optimization & Production

**Goal**: Optimize and prepare for production use

**Tasks**:
1. **Performance Optimization**
   - Profile training speed
   - Optimize data loading
   - Tune batch sizes
   - Memory optimization

2. **Hyperparameter Tuning**
   - LoRA rank experiments
   - Learning rate search
   - Batch size optimization
   - Epoch count determination

3. **Production Readiness**
   - Error handling
   - Logging improvements
   - Configuration management
   - Deployment guide

**Deliverables**:
- Optimized training pipeline
- Hyperparameter recommendations
- Production deployment guide
- Monitoring setup

**Timeline**: 5-7 days

---

## Architecture Details

### MLX Training Infrastructure

**Core MLX Components Needed:**
```python
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
```

**Key Capabilities:**
- `mx.value_and_grad()` - Automatic differentiation
- `optim.Adam` / `optim.SGD` - Optimizers
- `nn.Module` - Model base class
- `mx.eval()` - Lazy evaluation control

### Model Architecture Understanding

**Qwen3-VL-4B Structure:**
- Vision encoder (image processing)
- Language model backbone (text generation)
- Cross-modal attention layers
- Output projection layers

**LoRA Target Modules:**
- Attention layers: `q_proj`, `k_proj`, `v_proj`, `o_proj`
- MLP layers: `gate_proj`, `up_proj`, `down_proj`
- Cross-attention layers (vision-language interaction)

### Training Data Pipeline

**Data Format:**
```python
{
    "image": PIL.Image or np.array,
    "prompt": str,
    "response": str  # Target output
}
```

**Processing Steps:**
1. Load image with `mlx_vlm.utils.load_image()`
2. Tokenize text with model's tokenizer
3. Format as conversation with `apply_chat_template()`
4. Create input tensors in MLX format

### Loss Function

**Causal Language Modeling Loss:**
- Cross-entropy loss on next-token prediction
- Mask padding tokens
- Apply only to response tokens (not prompt)

**Implementation:**
```python
def compute_loss(logits, labels, mask):
    # Shift for next-token prediction
    shift_logits = logits[..., :-1, :]
    shift_labels = labels[..., 1:]
    shift_mask = mask[..., 1:]
    
    # Compute cross-entropy
    loss = mx.mean(
        mx.sum(
            mx.softmax_cross_entropy(shift_logits, shift_labels) * shift_mask,
            axis=-1
        ) / mx.sum(shift_mask, axis=-1)
    )
    return loss
```

### Checkpointing Strategy

**Save Components:**
- LoRA adapter weights (A and B matrices)
- Optimizer state
- Training metadata (epoch, step, loss history)

**Format:**
- Use MLX's native serialization (`mx.save()` / `mx.load()`)
- Save as `.safetensors` or `.npz` format
- Maintain compatibility with `mlx-vlm` loading

---

## File Structure

```
mondrian-macos/
├── docs/
│   └── LoRA/
│       └── tuning-roadmap.md      # This file
├── investigate_mlx_vlm.py        # Investigation script
│
├── training/                      # Training module (to be created)
│   ├── __init__.py
│   ├── lora.py                   # LoRA implementation
│   ├── dataset.py                # Data loading
│   ├── trainer.py                # Training loop
│   ├── loss.py                   # Loss functions
│   └── utils.py                  # Utilities
│
├── train_mlx_lora.py             # Main training script (to be created)
├── prepare_training_data.py      # Data preparation (exists)
└── test_mlx_lora.py              # Testing script (to be created)
```

## Dependencies

### Required
```python
mlx>=0.15.0              # Core MLX framework
mlx-vlm>=0.0.11          # Vision-language models
numpy>=1.24.0            # Array operations
pillow>=10.0.0           # Image processing
```

### Optional (for utilities)
```python
tqdm>=4.65.0             # Progress bars
safetensors>=0.4.0      # Safe model serialization
```

## Technical Specifications

### LoRA Hyperparameters
- **Rank (r)**: 8-32 (start with 16)
- **Alpha**: 2× rank (typically 32 for r=16)
- **Dropout**: 0.05-0.1
- **Target Modules**: All attention + MLP layers

### Training Hyperparameters
- **Learning Rate**: 1e-4 to 5e-4
- **Batch Size**: 1-4 (depending on memory)
- **Gradient Accumulation**: 4-8 steps
- **Epochs**: 3-5
- **Warmup Steps**: 100-200
- **Weight Decay**: 0.01

### Memory Management
- Use gradient checkpointing if available
- Implement gradient accumulation
- Process images at appropriate resolution
- Monitor Metal GPU memory usage

## Key Design Decisions

### 1. Pure MLX Approach
- **Decision**: Use only MLX, no PyTorch
- **Rationale**: Maintains consistency with existing system, leverages Apple Silicon
- **Trade-off**: May need custom implementations if utilities don't exist

### 2. LoRA-Only Fine-tuning
- **Decision**: Use LoRA adapters, not full fine-tuning
- **Rationale**: Memory efficient, faster training, easier to manage
- **Trade-off**: Slightly less capacity than full fine-tuning

### 3. Integration with Existing Service
- **Decision**: Extend current service, maintain compatibility
- **Rationale**: Minimal disruption, backward compatible
- **Trade-off**: Some complexity in conditional loading

### 4. Checkpoint Format
- **Decision**: Use MLX native format (`.safetensors` or `.npz`)
- **Rationale**: Compatible with MLX ecosystem
- **Trade-off**: May need conversion if sharing with other frameworks

## Success Metrics

### Functional
- ✅ Can train LoRA adapters using MLX
- ✅ Can save/load adapters in MLX format
- ✅ Can use fine-tuned model for inference
- ✅ Integrates with existing service

### Performance
- Training time: < 2 hours for 100 examples (on M-series Mac)
- Memory usage: < 16GB GPU memory
- Inference speed: < 10% slower than base model
- Model size: < 100MB for LoRA adapters

### Quality
- Improved performance on photography analysis domain
- Maintains general vision-language capabilities
- Consistent output format

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| MLX-VLM lacks LoRA support | High | Medium | Implement custom LoRA |
| Training too slow | Medium | Low | Optimize batch processing |
| Memory issues | High | Medium | Use gradient accumulation |
| Integration complexity | Medium | Low | Design clean interfaces |
| Model quality issues | Medium | Medium | Careful hyperparameter tuning |

## Timeline Estimate

- **Phase 0 (Investigation)**: 1-2 days
- **Phase 1 (LoRA)**: 3-5 days
- **Phase 2 (Training)**: 5-7 days
- **Phase 3 (Integration)**: 3-4 days
- **Phase 4 (Optimization)**: 5-7 days

**Total**: ~3-4 weeks for complete implementation

## Investigation Results

### Key Findings

✅ **MLX-VLM has built-in LoRA support!**
- `mlx_vlm.lora` module exists
- `mlx_vlm.trainer` package exists
- LoRA keywords found in source code (lora, adapter, train, optimizer)

### Package Structure Discovered

```
mlx_vlm/
├── lora.py              # LoRA implementation ✓
├── trainer/             # Training package ✓
├── utils.py             # Utilities (contains LoRA references)
├── models/              # Model definitions
├── prompt_utils.py     # Prompt handling
└── __init__.py          # Exports: load, generate
```

### Remaining Questions

1. ✅ Does mlx-vlm have built-in LoRA support? **YES - `lora.py` module exists**
2. ✅ What training utilities are available? **`trainer` package exists**
3. ⏳ What is the exact API for LoRA training?
4. ⏳ How are vision tokens handled in training?
5. ⏳ What's the best batching strategy?

**Next Action**: Examine `mlx_vlm.lora` and `mlx_vlm.trainer` source code to understand API.

## Next Immediate Steps

1. **Run Investigation** (Today)
   ```bash
   python investigate_mlx_vlm.py > docs/LoRA/investigation_report.txt
   ```

2. **Review MLX-VLM Source** (Today)
   - Check GitHub: https://github.com/Blaizzy/mlx-vlm
   - Look for training examples
   - Review API documentation

3. **Plan Implementation** (Tomorrow)
   - Based on investigation results
   - Choose implementation approach
   - Design interfaces

4. **Start Phase 1** (Day 3)
   - Begin LoRA implementation
   - Create basic structure
   - Test with small example

## Resources

- **MLX Documentation**: https://ml-explore.github.io/mlx/
- **MLX-VLM GitHub**: https://github.com/Blaizzy/mlx-vlm
- **MLX-LM-LoRA** (reference): https://github.com/ml-explore/mlx-lm-lora
- **LoRA Paper**: https://arxiv.org/abs/2106.09685

---

**Status**: Ready for Phase 0 (Investigation)
**Last Updated**: 2025-01-09

