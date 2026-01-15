# LoRA Fine-tuning Guide for Qwen3-VL-4B

This guide explains how to fine-tune the Qwen3-VL-4B model using LoRA (Low-Rank Adaptation) for your photography analysis use case.

## Overview

LoRA fine-tuning allows you to adapt the model to your specific domain (photography analysis with advisor-specific feedback) without retraining the entire model. This is:
- **Memory efficient**: Only trains a small number of parameters
- **Fast**: Trains much faster than full fine-tuning
- **Flexible**: Can easily switch between different LoRA adapters

## Prerequisites

### Hardware Requirements

- **GPU**: NVIDIA GPU with at least 16GB VRAM (24GB+ recommended)
  - For 4-bit quantization: 12GB+ VRAM
  - For full precision: 24GB+ VRAM
- **RAM**: 32GB+ system RAM recommended
- **Storage**: 20GB+ free space for model and training data

### Software Requirements

1. Python 3.8 or later
2. CUDA-capable PyTorch (if using NVIDIA GPU)
3. Required packages (see `requirements_training.txt`)

## Installation

1. **Install training dependencies:**

```bash
pip install -r requirements_training.txt
```

2. **Verify installation:**

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"
```

## Step 1: Prepare Training Data

The training data should consist of image-prompt-response triplets from your existing analysis outputs.

### Option A: Use Existing Analysis Data

```bash
python prepare_training_data.py \
    --analysis_dir ./analysis_output \
    --source_dir ./source \
    --prompts_dir ./mondrian/prompts \
    --output_dir ./training_data \
    --advisor ansel
```

This script will:
- Scan your analysis HTML files
- Match them with source images
- Extract prompts and responses
- Create JSON training dataset

### Option B: Create Custom Training Data

Create JSON files with the following format:

```json
{
  "image_path": "/path/to/image.jpg",
  "prompt": "Your system prompt and advisor-specific guidance...",
  "response": "The expected model response..."
}
```

For multiple examples, use a JSON array:

```json
[
  {
    "image_path": "/path/to/image1.jpg",
    "prompt": "...",
    "response": "..."
  },
  {
    "image_path": "/path/to/image2.jpg",
    "prompt": "...",
    "response": "..."
  }
]
```

**Tips for good training data:**
- Include 50-200+ examples for meaningful fine-tuning
- Ensure responses match your desired output format (JSON, HTML, etc.)
- Include diverse images and scenarios
- Use actual advisor prompts from your system

## Step 2: Train the Model

### Basic Training

```bash
python train_lora_qwen3vl.py \
    --base_model Qwen/Qwen3-VL-4B-Instruct \
    --data_dir ./training_data/training_data_ansel.json \
    --output_dir ./models/qwen3-vl-4b-lora-ansel \
    --epochs 3 \
    --batch_size 2 \
    --learning_rate 2e-4
```

### Advanced Training Options

```bash
python train_lora_qwen3vl.py \
    --base_model Qwen/Qwen3-VL-4B-Instruct \
    --data_dir ./training_data \
    --output_dir ./models/qwen3-vl-4b-lora \
    --epochs 5 \
    --batch_size 1 \
    --gradient_accumulation_steps 8 \
    --learning_rate 1e-4 \
    --lora_r 32 \
    --lora_alpha 64 \
    --lora_dropout 0.1 \
    --warmup_steps 200 \
    --save_steps 250 \
    --logging_steps 25
```

### Parameters Explained

- `--base_model`: Base model to fine-tune (Qwen3-VL-4B-Instruct)
- `--data_dir`: Path to training data (file or directory)
- `--output_dir`: Where to save the fine-tuned model
- `--epochs`: Number of training epochs (3-5 recommended)
- `--batch_size`: Batch size per device (1-4 depending on GPU memory)
- `--gradient_accumulation_steps`: Effective batch size = batch_size × gradient_accumulation_steps
- `--learning_rate`: Learning rate (1e-4 to 5e-4 typical)
- `--lora_r`: LoRA rank (8-64, higher = more capacity but more parameters)
- `--lora_alpha`: LoRA alpha (typically 2× rank)
- `--lora_dropout`: Dropout for LoRA layers (0.05-0.1)
- `--no_4bit`: Disable 4-bit quantization (requires more memory)

### Memory Optimization

If you run out of memory:

1. **Reduce batch size:**
   ```bash
   --batch_size 1 --gradient_accumulation_steps 8
   ```

2. **Use 4-bit quantization** (default):
   ```bash
   # Already enabled by default
   ```

3. **Reduce LoRA rank:**
   ```bash
   --lora_r 8 --lora_alpha 16
   ```

## Step 3: Monitor Training

Training logs are saved to TensorBoard:

```bash
tensorboard --logdir ./models/qwen3-vl-4b-lora/logs
```

Open http://localhost:6006 in your browser to view:
- Training loss
- Validation loss
- Learning rate schedule

## Step 4: Evaluate the Fine-tuned Model

After training, test the model:

```python
from transformers import AutoModelForCausalLM, AutoProcessor
from peft import PeftModel
from PIL import Image

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen3-VL-4B-Instruct",
    device_map="auto",
    torch_dtype=torch.float16
)
processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-4B-Instruct")

# Load LoRA weights
model = PeftModel.from_pretrained(base_model, "./models/qwen3-vl-4b-lora")

# Test inference
image = Image.open("test_image.jpg")
prompt = "Your analysis prompt here..."

messages = [
    {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": prompt}
        ]
    }
]

text = processor.apply_chat_template(messages, tokenize=False)
inputs = processor(text=[text], images=[image], return_tensors="pt").to(model.device)

outputs = model.generate(**inputs, max_new_tokens=512)
response = processor.batch_decode(outputs, skip_special_tokens=True)[0]
print(response)
```

## Step 5: Use Fine-tuned Model

### Option A: Use with PyTorch/Transformers

The fine-tuned model can be used directly with the Transformers library (see evaluation example above).

### Option B: Convert to MLX (if supported)

Currently, MLX doesn't have full support for loading LoRA adapters. You may need to:
1. Merge LoRA weights into base model
2. Convert to MLX format (if conversion tools are available)

### Option C: Use with Ollama

You can create a custom Ollama model file that uses the fine-tuned weights:

```bash
# Create Modelfile
cat > Modelfile << EOF
FROM ./models/qwen3-vl-4b-lora
PARAMETER temperature 0.7
PARAMETER top_p 0.9
EOF

# Create Ollama model
ollama create qwen3-vl-4b-mondrian -f Modelfile
```

## Troubleshooting

### Out of Memory Errors

- Reduce `batch_size` to 1
- Increase `gradient_accumulation_steps`
- Use `--no_4bit` if you have enough memory (but this uses more)
- Reduce image resolution in preprocessing

### Training Loss Not Decreasing

- Check learning rate (try 1e-4 or 5e-4)
- Verify training data quality
- Increase number of epochs
- Check if model is actually updating (verify LoRA parameters are trainable)

### Poor Model Performance

- Ensure you have enough training examples (50+ minimum)
- Verify training data matches your use case
- Try different LoRA ranks (r=16, 32, 64)
- Increase training epochs
- Check for overfitting (validation loss increasing while training loss decreases)

## Best Practices

1. **Start small**: Begin with 50-100 examples and 3 epochs
2. **Monitor closely**: Watch TensorBoard during first epoch
3. **Validate early**: Test on held-out examples after each epoch
4. **Iterate**: Adjust hyperparameters based on results
5. **Save checkpoints**: Use `--save_steps` to save intermediate checkpoints

## Next Steps

- Experiment with different LoRA configurations
- Fine-tune separate adapters for different advisors
- Combine multiple LoRA adapters for ensemble approaches
- Evaluate on your test set and compare with baseline

## Resources

- [PEFT Documentation](https://huggingface.co/docs/peft)
- [Qwen3-VL Model Card](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)





