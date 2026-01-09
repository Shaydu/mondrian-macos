# MLX-Native LoRA Fine-tuning Plan for Qwen3-VL-4B

## Overview

This document outlines a complete MLX-native approach for LoRA fine-tuning of Qwen3-VL-4B, using only MLX framework components with no PyTorch dependencies.

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

## Architecture Plan

### 1. MLX-VLM LoRA Support Investigation

**Research Required:**
- Check if `mlx-vlm` has built-in LoRA support
- Examine `mlx-vlm` source code for training capabilities
- Verify LoRA adapter loading/saving mechanisms
- Check for training utilities in `mlx-vlm` package

**Expected Components:**
- LoRA adapter creation utilities
- Model parameter freezing/unfreezing
- Training loop integration
- Checkpoint saving/loading

### 2. MLX Training Infrastructure

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

### 3. LoRA Implementation Strategy

#### Option A: Use MLX-VLM Built-in LoRA (Preferred)
If `mlx-vlm` has LoRA support:
- Use existing LoRA utilities
- Follow `mlx-vlm` training patterns
- Leverage existing adapter save/load

#### Option B: Custom LoRA Implementation
If LoRA needs to be implemented:
- Create LoRA layer class extending `nn.Module`
- Implement low-rank decomposition: `W = W_base + BA`
- Add LoRA adapters to target modules
- Handle parameter freezing for base model

### 4. Model Architecture Understanding

**Qwen3-VL-4B Structure:**
- Vision encoder (image processing)
- Language model backbone (text generation)
- Cross-modal attention layers
- Output projection layers

**LoRA Target Modules:**
- Attention layers: `q_proj`, `k_proj`, `v_proj`, `o_proj`
- MLP layers: `gate_proj`, `up_proj`, `down_proj`
- Cross-attention layers (vision-language interaction)

### 5. Training Data Pipeline

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

### 6. Training Loop Design

**Core Training Loop Structure:**
```python
def train_step(model, batch, optimizer):
    # Forward pass
    loss = loss_fn(model, batch)
    
    # Backward pass (automatic via value_and_grad)
    loss_and_grad_fn = mx.value_and_grad(loss_fn)
    loss, grads = loss_and_grad_fn(model, batch)
    
    # Update optimizer
    optimizer.update(model, grads)
    mx.eval(model.parameters())
    
    return loss
```

**Key Considerations:**
- Use MLX's lazy evaluation (`mx.eval()`)
- Batch processing with proper padding
- Gradient accumulation for larger effective batch sizes
- Mixed precision if supported

### 7. Loss Function

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

### 8. Checkpointing Strategy

**Save Components:**
- LoRA adapter weights (A and B matrices)
- Optimizer state
- Training metadata (epoch, step, loss history)

**Format:**
- Use MLX's native serialization (`mx.save()` / `mx.load()`)
- Save as `.safetensors` or `.npz` format
- Maintain compatibility with `mlx-vlm` loading

### 9. Integration with Existing System

**Inference Integration:**
```python
# Load base model
model, processor = mlx_vlm.load("Qwen/Qwen3-VL-4B-Instruct")

# Load LoRA adapter
lora_weights = mx.load("lora_adapters.safetensors")
apply_lora_adapters(model, lora_weights)

# Use for inference (existing code works)
output = mlx_vlm.generate(model, processor, prompt, image)
```

**Service Integration:**
- Modify `get_mlx_model()` to optionally load LoRA adapters
- Add configuration parameter for LoRA path
- Maintain backward compatibility (works without LoRA)

## Implementation Phases

### Phase 1: Research & Discovery
1. **Examine MLX-VLM Source**
   - Check GitHub repository
   - Look for training examples
   - Identify LoRA support level
   - Review API documentation

2. **Test MLX Training Basics**
   - Simple training loop test
   - Verify gradient computation
   - Test optimizer functionality
   - Benchmark performance

### Phase 2: LoRA Implementation
1. **If Built-in Support Exists:**
   - Use existing utilities
   - Follow documentation
   - Test with small dataset

2. **If Custom Implementation Needed:**
   - Implement LoRA layer class
   - Add to target modules
   - Test parameter freezing
   - Verify memory efficiency

### Phase 3: Training Pipeline
1. **Data Preparation**
   - Convert existing analyses to training format
   - Create data loader
   - Implement batching logic
   - Add data augmentation (optional)

2. **Training Loop**
   - Implement forward pass
   - Add loss computation
   - Integrate optimizer
   - Add checkpointing
   - Implement validation loop

### Phase 4: Integration
1. **Model Loading**
   - Modify model loading to support LoRA
   - Add adapter application logic
   - Test inference with fine-tuned model

2. **Service Updates**
   - Update `ai_advisor_service.py`
   - Add LoRA configuration
   - Maintain backward compatibility

### Phase 5: Evaluation & Optimization
1. **Performance Testing**
   - Compare fine-tuned vs base model
   - Measure training speed
   - Check memory usage
   - Validate output quality

2. **Optimization**
   - Tune hyperparameters
   - Optimize batch size
   - Improve data pipeline
   - Add monitoring/logging

## Technical Specifications

### Dependencies
```python
# Core MLX
mlx>=0.15.0
mlx-vlm>=0.0.11  # Current version

# Training utilities (if needed)
mlx-lm-lora>=0.7.0  # May have utilities we can adapt

# Data handling
numpy>=1.24.0
pillow>=10.0.0

# Utilities
tqdm>=4.65.0  # Progress bars
```

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

## File Structure Plan

```
mondrian/
├── training/
│   ├── __init__.py
│   ├── lora.py              # LoRA implementation
│   ├── dataset.py           # Data loading
│   ├── trainer.py          # Training loop
│   ├── loss.py              # Loss functions
│   └── utils.py             # Training utilities
├── train_mlx_lora.py        # Main training script
├── prepare_training_data.py # Data preparation (reuse)
└── test_mlx_lora.py         # Testing script
```

## Success Criteria

1. **Functional Requirements:**
   - ✅ Train LoRA adapters using MLX only
   - ✅ Save/load LoRA weights in MLX format
   - ✅ Use fine-tuned model for inference
   - ✅ Integrate with existing service

2. **Performance Requirements:**
   - Training speed: Reasonable for dataset size
   - Memory usage: Fits in available GPU memory
   - Inference: No significant slowdown vs base model

3. **Quality Requirements:**
   - Model shows improvement on training domain
   - Maintains general capabilities
   - Produces consistent outputs

## Risks & Mitigations

### Risk 1: MLX-VLM Lacks LoRA Support
**Mitigation**: Implement custom LoRA layers using MLX primitives

### Risk 2: Training Too Slow
**Mitigation**: 
- Optimize batch processing
- Use gradient accumulation
- Consider smaller LoRA rank

### Risk 3: Memory Issues
**Mitigation**:
- Reduce batch size
- Use gradient checkpointing
- Process smaller image resolutions

### Risk 4: Integration Complexity
**Mitigation**:
- Design clean adapter interface
- Maintain backward compatibility
- Add configuration flags

## Next Steps

1. **Immediate Actions:**
   - [ ] Examine `mlx-vlm` source code and documentation
   - [ ] Check for existing training examples
   - [ ] Test basic MLX training loop
   - [ ] Verify MLX-VLM model structure

2. **Short-term (Week 1):**
   - [ ] Implement or identify LoRA utilities
   - [ ] Create data preparation pipeline
   - [ ] Build basic training loop
   - [ ] Test on small dataset

3. **Medium-term (Week 2-3):**
   - [ ] Full training pipeline
   - [ ] Checkpointing system
   - [ ] Integration with service
   - [ ] Evaluation framework

4. **Long-term (Week 4+):**
   - [ ] Hyperparameter tuning
   - [ ] Production deployment
   - [ ] Monitoring and logging
   - [ ] Documentation

## Resources

- [MLX Documentation](https://ml-explore.github.io/mlx/)
- [MLX-VLM GitHub](https://github.com/Blaizzy/mlx-vlm)
- [MLX-LM-LoRA](https://github.com/ml-explore/mlx-lm-lora) (for reference)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)

## Questions to Resolve

1. Does `mlx-vlm` have built-in LoRA support?
2. What is the exact model architecture in MLX format?
3. How are vision tokens handled in training?
4. What's the best way to handle mixed precision in MLX?
5. How to efficiently batch vision-language data?

---

**Status**: Planning Phase
**Last Updated**: 2025-01-09
**Next Review**: After MLX-VLM investigation

