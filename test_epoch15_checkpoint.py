#!/usr/bin/env python3
"""
Test the epoch 15 checkpoint with a sample Ansel Adams image
"""

import sys
from pathlib import Path
import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from peft import PeftModel
from PIL import Image

PROJECT_ROOT = Path(__file__).parent

# Paths
checkpoint_path = PROJECT_ROOT / "adapters" / "ansel_qwen3_4b_v2" / "epoch_15"
test_image = PROJECT_ROOT / "training" / "datasets" / "ansel-images" / "ansel-adams-1.jpg"

print("\n" + "=" * 70)
print("Testing Epoch 15 Checkpoint")
print("=" * 70)
print(f"Checkpoint: {checkpoint_path}")
print(f"Test Image: {test_image}")
print()

if not checkpoint_path.exists():
    print(f"ERROR: Checkpoint not found at {checkpoint_path}")
    sys.exit(1)

if not test_image.exists():
    print(f"ERROR: Test image not found at {test_image}")
    # List available images
    image_dir = PROJECT_ROOT / "training" / "datasets" / "ansel-images"
    images = list(image_dir.glob("*.jpg"))
    if images:
        print(f"\nAvailable images in {image_dir}:")
        for img in images[:5]:
            print(f"  - {img.name}")
        test_image = images[0]
        print(f"\nUsing first available image: {test_image.name}")
    else:
        print(f"No images found in {image_dir}")
        sys.exit(1)

# Load model
print("Loading base model with 4-bit quantization...")
from transformers import BitsAndBytesConfig

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

processor = AutoProcessor.from_pretrained(
    "Qwen/Qwen3-VL-4B-Instruct",
    trust_remote_code=True
)

model = Qwen3VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen3-VL-4B-Instruct",
    quantization_config=quantization_config,
    device_map="auto",
    trust_remote_code=True,
)

print("Loading LoRA adapter from checkpoint...")
model = PeftModel.from_pretrained(model, checkpoint_path, device_map="auto")
model.eval()

print("Loading test image...")
image = Image.open(test_image).convert("RGB")

# Create prompt for image analysis
prompt = """Analyze this photograph in English. Describe it across these dimensions:
- Composition: How are elements arranged?
- Lighting: What's the quality of light?
- Focus & Sharpness: What's in focus?
- Color Harmony: Color relationships?
- Depth & Perspective: Sense of depth?
- Visual Balance: Overall balance?
- Emotional Impact: What feeling does it evoke?"""

print("\nPrompt:")
print(prompt)
print("\n" + "-" * 70)
print("Analysis:")
print("-" * 70)

# Prepare input
messages = [{"role": "user", "content": prompt}]
text = processor.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True
)

inputs = processor(
    text=text,
    images=[image],
    padding=True,
    return_tensors="pt"
)

# Move inputs to the same device as the model
device = next(model.parameters()).device
for key in inputs:
    if isinstance(inputs[key], torch.Tensor):
        inputs[key] = inputs[key].to(device)

# Generate response
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=512,
        temperature=0.7,
        top_p=0.9,
    )

response = processor.decode(outputs[0], skip_special_tokens=True)
# Extract just the response part (after the prompt)
if "assistant" in response:
    response = response.split("assistant")[-1].strip()

print(response)
print("\n" + "=" * 70)
