#!/usr/bin/env python3
"""
Test MLX directly without the service
This bypasses the Flask service to test if MLX itself is working
"""

import sys
print("Testing MLX-VLM directly...")

# Test 1: Can we import MLX?
try:
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    from PIL import Image
    print("✅ MLX-VLM imports successful")
except ImportError as e:
    print(f"❌ Cannot import MLX-VLM: {e}")
    sys.exit(1)

# Test 2: Can we load the model?
MODEL = "lmstudio-community/Qwen3-VL-4B-Instruct-MLX-4bit"
print(f"\n📦 Loading model: {MODEL}")
print("   (This may take 30-60 seconds on first run...)")

try:
    model, processor = load(MODEL)
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    sys.exit(1)

# Test 3: Can we run inference?
print("\n🖼️  Testing inference with sample image...")
image_path = "mondrian/source/mike-shrub.jpg"

try:
    image = Image.open(image_path)
    print(f"✅ Image loaded: {image.size}")

    # Simple prompt
    prompt = "Describe this image in one sentence."

    # Format prompt
    config = load_config(MODEL)
    formatted_prompt = apply_chat_template(
        processor,
        config,
        prompt,
        num_images=1
    )

    print("⏳ Generating response...")
    output = generate(
        model,
        processor,
        formatted_prompt,
        image,
        max_tokens=100,
        temp=0.7,
        verbose=False
    )

    print("\n✅ SUCCESS! MLX is working!")
    print("=" * 60)
    print("Response:")
    print(output)
    print("=" * 60)

except Exception as e:
    print(f"❌ Inference failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 MLX backend is fully functional!")
print("   The issue is with how the service loads the model.")
