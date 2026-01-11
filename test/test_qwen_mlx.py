#!/usr/bin/env python3
"""Test script for Qwen3-VL-4B via MLX"""

import sys
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_image

def test_qwen_text(prompt: str):
    """Test with text-only prompt"""
    print(f"Loading Qwen2.5-VL model...")
    model, processor = load("Qwen/Qwen2.5-VL-7B-Instruct")

    print(f"\nPrompt: {prompt}")
    print(f"\nGenerating response...")

    formatted_prompt = apply_chat_template(
        processor,
        config=model.config,
        prompt=prompt
    )

    output = generate(model, processor, formatted_prompt, max_tokens=200, verbose=False)
    print(f"\nResponse: {output}")
    return output

def test_qwen_vision(image_path: str, prompt: str):
    """Test with image + text prompt"""
    print(f"Loading Qwen2.5-VL model...")
    model, processor = load("Qwen/Qwen2.5-VL-7B-Instruct")

    print(f"\nImage: {image_path}")
    print(f"Prompt: {prompt}")
    print(f"\nGenerating response...")

    image = load_image(image_path)

    formatted_prompt = apply_chat_template(
        processor,
        config=model.config,
        prompt=prompt,
        image=image
    )

    output = generate(model, processor, image, formatted_prompt, max_tokens=200, verbose=False)
    print(f"\nResponse: {output}")
    return output

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Text only: python3 test_qwen_mlx.py 'What is 2+2?'")
        print("  With image: python3 test_qwen_mlx.py /path/to/image.jpg 'Describe this image'")
        sys.exit(1)

    if len(sys.argv) == 2:
        # Text-only mode
        test_qwen_text(sys.argv[1])
    else:
        # Image + text mode
        test_qwen_vision(sys.argv[1], sys.argv[2])
