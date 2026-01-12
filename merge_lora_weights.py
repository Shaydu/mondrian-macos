#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge LoRA Weights into Base Model
Useful for creating a single model file or preparing for MLX conversion

Usage:
    python merge_lora_weights.py \
        --base_model Qwen/Qwen3-VL-4B-Instruct \
        --lora_path ./models/qwen3-vl-4b-lora \
        --output_path ./models/qwen3-vl-4b-merged
"""

import argparse
import torch
from transformers import AutoModelForCausalLM, AutoProcessor
from peft import PeftModel
import os


def merge_lora_weights(base_model_path, lora_path, output_path):
    """Merge LoRA adapter weights into base model"""
    print(f"Loading base model: {base_model_path}")
    
    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16
    )
    
    # Load LoRA adapter
    print(f"Loading LoRA adapter: {lora_path}")
    model = PeftModel.from_pretrained(base_model, lora_path)
    
    # Merge weights
    print("Merging LoRA weights into base model...")
    merged_model = model.merge_and_unload()
    
    # Save merged model
    print(f"Saving merged model to: {output_path}")
    os.makedirs(output_path, exist_ok=True)
    
    merged_model.save_pretrained(
        output_path,
        safe_serialization=True
    )
    
    # Also save processor
    processor = AutoProcessor.from_pretrained(
        base_model_path,
        trust_remote_code=True
    )
    processor.save_pretrained(output_path)
    
    print("✓ Merged model saved successfully!")
    print(f"  Model: {output_path}")
    print(f"  You can now use this model without loading LoRA separately")


def main():
    parser = argparse.ArgumentParser(description="Merge LoRA weights into base model")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen3-VL-4B-Instruct",
                        help="Base model path")
    parser.add_argument("--lora_path", type=str, required=True,
                        help="Path to LoRA adapter")
    parser.add_argument("--output_path", type=str, required=True,
                        help="Output path for merged model")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.lora_path):
        print(f"Error: LoRA path not found: {args.lora_path}")
        return
    
    merge_lora_weights(
        args.base_model,
        args.lora_path,
        args.output_path
    )


if __name__ == "__main__":
    main()





