#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Fine-tuned LoRA Model
Quick script to test inference with a fine-tuned model

Usage:
    python test_lora_model.py \
        --base_model Qwen/Qwen3-VL-4B-Instruct \
        --lora_path ./models/qwen3-vl-4b-lora \
        --image_path ./test_image.jpg \
        --prompt "Analyze this photograph..."
"""

import argparse
import torch
from transformers import AutoModelForCausalLM, AutoProcessor
from peft import PeftModel
from PIL import Image
import os


def load_finetuned_model(base_model_path, lora_path, use_4bit=True):
    """Load base model and LoRA adapter"""
    print(f"Loading base model: {base_model_path}")
    
    if use_4bit:
        from transformers import BitsAndBytesConfig
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
    else:
        bnb_config = None
    
    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16 if use_4bit else torch.float32
    )
    
    # Load processor
    processor = AutoProcessor.from_pretrained(
        base_model_path,
        trust_remote_code=True
    )
    
    # Load LoRA adapter
    if os.path.exists(lora_path):
        print(f"Loading LoRA adapter: {lora_path}")
        model = PeftModel.from_pretrained(base_model, lora_path)
    else:
        print(f"Warning: LoRA path not found, using base model only")
        model = base_model
    
    return model, processor


def generate_response(model, processor, image_path, prompt, max_tokens=512):
    """Generate response from model"""
    # Load image
    image = Image.open(image_path).convert('RGB')
    
    # Format messages
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt}
            ]
        }
    ]
    
    # Apply chat template
    text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False
    )
    
    # Process inputs
    inputs = processor(
        text=[text],
        images=[image],
        return_tensors="pt"
    ).to(model.device)
    
    # Generate
    print("Generating response...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
    
    # Decode
    response = processor.batch_decode(
        outputs,
        skip_special_tokens=True
    )[0]
    
    # Extract only the assistant's response
    if "assistant" in response.lower():
        # Try to extract response after assistant marker
        parts = response.split("assistant", 1)
        if len(parts) > 1:
            response = parts[1].strip()
    
    return response


def main():
    parser = argparse.ArgumentParser(description="Test fine-tuned LoRA model")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen3-VL-4B-Instruct",
                        help="Base model path")
    parser.add_argument("--lora_path", type=str, required=True,
                        help="Path to LoRA adapter")
    parser.add_argument("--image_path", type=str, required=True,
                        help="Path to test image")
    parser.add_argument("--prompt", type=str,
                        default="Analyze this photograph and provide detailed feedback on composition, lighting, and artistic merit.",
                        help="Test prompt")
    parser.add_argument("--max_tokens", type=int, default=512,
                        help="Maximum tokens to generate")
    parser.add_argument("--no_4bit", action="store_true",
                        help="Disable 4-bit quantization")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.image_path):
        print(f"Error: Image not found: {args.image_path}")
        return
    
    # Load model
    model, processor = load_finetuned_model(
        args.base_model,
        args.lora_path,
        use_4bit=not args.no_4bit
    )
    
    # Generate response
    response = generate_response(
        model,
        processor,
        args.image_path,
        args.prompt,
        max_tokens=args.max_tokens
    )
    
    # Print results
    print("\n" + "="*80)
    print("PROMPT:")
    print("="*80)
    print(args.prompt)
    print("\n" + "="*80)
    print("RESPONSE:")
    print("="*80)
    print(response)
    print("="*80)


if __name__ == "__main__":
    main()

