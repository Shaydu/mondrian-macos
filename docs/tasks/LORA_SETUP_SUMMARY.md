# LoRA Fine-tuning Setup Summary

This document summarizes the LoRA fine-tuning setup for Qwen3-VL-4B.

## Files Created

### Core Training Scripts

1. **`train_lora_qwen3vl.py`** - Main training script
   - Handles LoRA fine-tuning with PEFT
   - Supports 4-bit quantization for memory efficiency
   - Includes validation and checkpointing
   - TensorBoard logging

2. **`prepare_training_data.py`** - Data preparation utility
   - Converts existing analysis outputs to training format
   - Matches images with analysis files
   - Extracts prompts and responses
   - Creates JSON training dataset

3. **`test_lora_model.py`** - Model testing script
   - Quick inference testing
   - Loads base model + LoRA adapter
   - Tests on custom images and prompts

4. **`merge_lora_weights.py`** - Weight merging utility
   - Merges LoRA weights into base model
   - Creates standalone model file
   - Useful for deployment or MLX conversion

### Configuration & Documentation

5. **`requirements_training.txt`** - Training dependencies
   - PyTorch, Transformers, PEFT
   - BitsAndBytes for quantization
   - TensorBoard for monitoring

6. **`LORA_FINETUNING_GUIDE.md`** - Comprehensive guide
   - Step-by-step instructions
   - Parameter explanations
   - Troubleshooting tips
   - Best practices

7. **`quick_start_lora.sh`** - Interactive setup script
   - Guides through entire process
   - Prompts for configuration
   - Runs training automatically

## Quick Start

### Option 1: Interactive Script (Recommended)

```bash
./quick_start_lora.sh
```

This will guide you through:
1. Installing dependencies
2. Preparing training data
3. Configuring training
4. Starting training

### Option 2: Manual Steps

1. **Install dependencies:**
   ```bash
   pip install -r requirements_training.txt
   ```

2. **Prepare training data:**
   ```bash
   python prepare_training_data.py \
       --analysis_dir ./analysis_output \
       --source_dir ./source \
       --prompts_dir ./mondrian/prompts \
       --output_dir ./training_data \
       --advisor ansel
   ```

3. **Train model:**
   ```bash
   python train_lora_qwen3vl.py \
       --base_model Qwen/Qwen3-VL-4B-Instruct \
       --data_dir ./training_data/training_data_ansel.json \
       --output_dir ./models/qwen3-vl-4b-lora-ansel \
       --epochs 3 \
       --batch_size 2 \
       --learning_rate 2e-4
   ```

4. **Test model:**
   ```bash
   python test_lora_model.py \
       --lora_path ./models/qwen3-vl-4b-lora-ansel \
       --image_path ./test_image.jpg \
       --prompt "Analyze this photograph..."
   ```

## Training Data Format

Training data should be JSON with the following structure:

```json
{
  "image_path": "/path/to/image.jpg",
  "prompt": "System prompt and advisor guidance...",
  "response": "Expected model response..."
}
```

For multiple examples, use an array:

```json
[
  { "image_path": "...", "prompt": "...", "response": "..." },
  { "image_path": "...", "prompt": "...", "response": "..." }
]
```

## Key Parameters

### LoRA Configuration
- **`lora_r`** (default: 16): Rank of LoRA matrices
  - Higher = more capacity, more parameters
  - Typical range: 8-64
- **`lora_alpha`** (default: 32): Scaling factor
  - Typically 2× the rank
- **`lora_dropout`** (default: 0.05): Dropout rate
  - Prevents overfitting

### Training Configuration
- **`epochs`** (default: 3): Number of training epochs
- **`batch_size`** (default: 2): Batch size per device
- **`learning_rate`** (default: 2e-4): Learning rate
  - Typical range: 1e-4 to 5e-4
- **`gradient_accumulation_steps`** (default: 4): Effective batch size multiplier

## Memory Requirements

- **Minimum**: 12GB VRAM (with 4-bit quantization)
- **Recommended**: 16-24GB VRAM
- **Full precision**: 24GB+ VRAM

If you run out of memory:
- Reduce `batch_size` to 1
- Increase `gradient_accumulation_steps`
- Reduce `lora_r` to 8
- Ensure 4-bit quantization is enabled (default)

## Monitoring Training

View training progress with TensorBoard:

```bash
tensorboard --logdir ./models/qwen3-vl-4b-lora/logs
```

Then open http://localhost:6006 in your browser.

## Using the Fine-tuned Model

### With PyTorch/Transformers

```python
from transformers import AutoModelForCausalLM, AutoProcessor
from peft import PeftModel

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen3-VL-4B-Instruct",
    device_map="auto"
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-4B-Instruct")

# Load LoRA adapter
model = PeftModel.from_pretrained(base_model, "./models/qwen3-vl-4b-lora")

# Use for inference...
```

### Merged Model (Standalone)

If you want a single model file without separate LoRA adapter:

```bash
python merge_lora_weights.py \
    --base_model Qwen/Qwen3-VL-4B-Instruct \
    --lora_path ./models/qwen3-vl-4b-lora \
    --output_path ./models/qwen3-vl-4b-merged
```

Then load normally:

```python
model = AutoModelForCausalLM.from_pretrained("./models/qwen3-vl-4b-merged")
```

## Integration with Existing System

To use the fine-tuned model with your existing MLX-based system:

1. **Option A**: Use PyTorch backend for inference
   - Modify `ai_advisor_service.py` to support PyTorch models
   - Load fine-tuned model instead of MLX model

2. **Option B**: Convert to MLX (if tools available)
   - Merge LoRA weights first
   - Convert merged model to MLX format
   - Use with existing MLX infrastructure

3. **Option C**: Hybrid approach
   - Use PyTorch for fine-tuned model
   - Keep MLX for base model
   - Route requests based on configuration

## Troubleshooting

### Common Issues

1. **Out of Memory**
   - Reduce batch size
   - Enable 4-bit quantization (default)
   - Reduce LoRA rank

2. **Training Loss Not Decreasing**
   - Check learning rate
   - Verify data quality
   - Increase epochs

3. **Poor Model Performance**
   - Need more training data (50+ examples)
   - Try different LoRA configurations
   - Check for overfitting

See `LORA_FINETUNING_GUIDE.md` for detailed troubleshooting.

## Next Steps

1. **Collect more training data** - Aim for 100+ examples
2. **Experiment with hyperparameters** - Try different LoRA ranks, learning rates
3. **Fine-tune per advisor** - Create separate adapters for each advisor
4. **Evaluate systematically** - Test on held-out validation set
5. **Deploy** - Integrate fine-tuned model into production system

## Resources

- [PEFT Documentation](https://huggingface.co/docs/peft)
- [Qwen3-VL Model Card](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- Full guide: `LORA_FINETUNING_GUIDE.md`





