#!/usr/bin/env python3
"""Simple MLX vision test using Qwen2-VL-2B"""

from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_image

# Use source image
image_path = "source/mike-shrub.jpg"
prompt = "Describe this image briefly."

print(f"Loading Qwen2-VL-2B model...")
model, processor = load("Qwen/Qwen2-VL-2B-Instruct")

print(f"Formatting prompt (text-only)...")
# Format the prompt WITHOUT the image - image will be passed to generate()
formatted_prompt = apply_chat_template(
    processor,
    config=model.config,
    prompt=prompt
)

print(f"Generating response with image...")
# Pass the image path as a list (Union[str, List[str]])
output = generate(model, processor, formatted_prompt, image=[image_path], max_tokens=200, verbose=True)

print(f"\n=== RESULT ===")
print(output)
