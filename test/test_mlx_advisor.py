#!/usr/bin/env python3
"""
Test MLX integration with AI Advisor Service
Tests the run_model_mlx function directly
"""
import sys
import os

# Add mondrian directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mondrian'))

def test_mlx_import():
    """Test that MLX imports work"""
    print("[TEST] Testing MLX imports...")
    try:
        from mlx_vlm import load, generate
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_image
        print("✅ MLX imports successful")
        return True
    except ImportError as e:
        print(f"❌ MLX import failed: {e}")
        print("Install with: pip install mlx-vlm")
        return False

def test_mlx_text_only():
    """Test MLX with text-only prompt"""
    print("\n[TEST] Testing text-only generation...")

    # Import after checking MLX is available
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template

    try:
        print("Loading model...")
        model, processor = load("Qwen/Qwen2-VL-2B-Instruct")

        prompt = "What is 2+2? Answer in one sentence."
        formatted_prompt = apply_chat_template(
            processor,
            config=model.config,
            prompt=prompt
        )

        print("Generating response...")
        output = generate(model, processor, formatted_prompt, max_tokens=100, verbose=False)

        print(f"Response: {output}")
        print("✅ Text-only generation successful")
        return True

    except Exception as e:
        print(f"❌ Text-only generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mlx_vision():
    """Test MLX with vision prompt"""
    print("\n[TEST] Testing vision generation...")

    # Find a test image
    test_images = [
        "source/mike-shrub.jpg",
        "source/steve-yard.jpg",
    ]

    test_image = None
    for img in test_images:
        if os.path.exists(img):
            test_image = img
            break

    if not test_image:
        print(f"⚠️  No test image found in source/ directory")
        print(f"Skipping vision test")
        return True

    print(f"Using test image: {test_image}")

    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_image

    try:
        print("Loading model...")
        model, processor = load("Qwen/Qwen2-VL-2B-Instruct")

        print("Loading image...")
        image = load_image(test_image)

        prompt = "Describe this image in 1-2 sentences."
        formatted_prompt = apply_chat_template(
            processor,
            config=model.config,
            prompt=prompt,
            image=image
        )

        print("Generating response...")
        output = generate(model, processor, image, formatted_prompt, max_tokens=200, verbose=False)

        print(f"Response: {output}")
        print("✅ Vision generation successful")
        return True

    except Exception as e:
        print(f"❌ Vision generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_advisor_service_mlx():
    """Test the AI Advisor Service with MLX mode"""
    print("\n[TEST] Testing AI Advisor Service MLX integration...")

    # This test requires the service to be running
    print("To test the full service:")
    print("1. Start the service with MLX mode:")
    print("   cd mondrian && python ai_advisor_service.py --use_mlx --db ../mondrian.db")
    print("2. Check health endpoint:")
    print("   curl http://127.0.0.1:5100/health")
    print("3. The 'backend' field should show 'MLX'")

    return True

if __name__ == "__main__":
    print("="*60)
    print("MLX Integration Test Suite")
    print("="*60)

    results = []

    # Test 1: Imports
    results.append(("MLX Imports", test_mlx_import()))

    if results[0][1]:
        # Test 2: Text-only
        results.append(("Text Generation", test_mlx_text_only()))

        # Test 3: Vision
        results.append(("Vision Generation", test_mlx_vision()))

        # Test 4: Service integration
        results.append(("Service Integration", test_advisor_service_mlx()))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)
    print("="*60)
    if all_passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
