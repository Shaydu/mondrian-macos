#!/usr/bin/env python3
"""
Streaming Proof of Concept - Test if thinking model can stream tokens in real-time
Shows tokens as they're generated, not after completion.
"""

import sys
import time
from pathlib import Path
from PIL import Image
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, TextIteratorStreamer
import threading

print("="*70)
print("STREAMING PROOF OF CONCEPT - Qwen3-VL-4B-Thinking")
print("="*70)

# Configuration
MODEL_NAME = "Qwen/Qwen3-VL-4B-Thinking"  # Thinking model with reasoning capabilities
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TEST_IMAGE = "source/mike-shrub.jpg"

print(f"\n[1] Loading model: {MODEL_NAME}")
print(f"    Device: {DEVICE}")

# Load model and processor
processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = Qwen2VLForConditionalGeneration.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32,
    device_map=DEVICE,
    trust_remote_code=True
)

# Load LoRA adapter for thinking model
adapter_path = Path("adapters/ansel_qwen3_4b_thinking/epoch_10")
if adapter_path.exists():
    print(f"[2] Loading LoRA adapter from: {adapter_path}")
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, str(adapter_path))
    print(f"    ✓ Adapter loaded successfully")
else:
    print(f"[2] ⚠️  Adapter not found at {adapter_path}, using base model")
    print("    Available adapters:")
    for p in Path("adapters").glob("*/epoch_*"):
        print(f"      - {p}")

print(f"[3] Loading test image: {TEST_IMAGE}")
image = Image.open(TEST_IMAGE).convert('RGB')

# Create prompt
prompt = """You are a photography analyst. 

If you perform reasoning, wrap it in <thinking></thinking> tags.

Then output valid JSON:
{
  "image_description": "Brief description",
  "score": 8
}"""

messages = [
    {"role": "user", "content": [
        {"type": "image"},
        {"type": "text", "text": prompt}
    ]}
]

# Prepare inputs
text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = processor(text=text, images=[image], padding=True, return_tensors="pt")

if DEVICE == "cuda":
    inputs = {k: v.cuda() if hasattr(v, 'cuda') else v for k, v in inputs.items()}

print("\n" + "="*70)
print("STREAMING OUTPUT (tokens appear as generated):")
print("="*70 + "\n")

# Create streamer
streamer = TextIteratorStreamer(
    processor.tokenizer, 
    skip_special_tokens=True,
    skip_prompt=True
)

# Generation parameters
generation_kwargs = {
    **inputs,
    "streamer": streamer,
    "max_new_tokens": 800,
    "repetition_penalty": 1.5,
    "do_sample": True,
    "temperature": 0.5,
    "top_p": 0.90,
    "eos_token_id": processor.tokenizer.eos_token_id
}

# Start generation in background thread
thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
thread.start()

# Stream tokens as they arrive
full_response = ""
thinking_started = False
thinking_ended = False
json_started = False

start_time = time.time()

try:
    for new_text in streamer:
        full_response += new_text
        
        # Print each token immediately
        print(new_text, end='', flush=True)
        
        # Track state transitions
        if '<thinking>' in full_response and not thinking_started:
            thinking_started = True
            print("\n\n[DETECTED: Thinking started]", flush=True)
        
        if '</thinking>' in full_response and not thinking_ended:
            thinking_ended = True
            print("\n\n[DETECTED: Thinking ended, JSON should follow]", flush=True)
        
        if '{' in new_text and not json_started:
            json_started = True
            print("\n\n[DETECTED: JSON output started]", flush=True)

except KeyboardInterrupt:
    print("\n\n[Interrupted by user]")

thread.join()

elapsed = time.time() - start_time

print("\n\n" + "="*70)
print("STREAMING COMPLETE")
print("="*70)
print(f"Time elapsed: {elapsed:.1f}s")
print(f"Total chars: {len(full_response)}")
print(f"Thinking detected: {thinking_started}")
print(f"JSON detected: {json_started}")

if thinking_started and json_started:
    print("\n✅ SUCCESS: Model supports streaming with thinking separation!")
    print("   Next step: Implement SSE endpoint in ai_advisor_service_linux.py")
else:
    print("\n⚠️  Model output format may need adjustment")

print("\n[Full response saved for analysis]")
with open("streaming_poc_output.txt", "w") as f:
    f.write(full_response)
print("Saved to: streaming_poc_output.txt")
