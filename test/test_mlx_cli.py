#!/usr/bin/env python3
"""
Quick CLI test for MLX backend
Tests if we can reach the MLX LLM with a simple text query
"""

import requests
import json
import sys

def test_health():
    """Test service health"""
    print("=" * 60)
    print("Testing MLX Backend Connection")
    print("=" * 60)

    try:
        response = requests.get("http://localhost:5100/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print("\n✅ AI Advisor Service is UP")
            print(f"   Model: {health.get('model', 'Unknown')}")
            print(f"   Backend: MLX (Apple Silicon)")
            print(f"   Status: {health.get('status', 'Unknown')}")
            return True
        else:
            print(f"\n❌ Service returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Cannot connect to service: {e}")
        print("   Make sure services are running: cd mondrian && python3 start_services.py --restart")
        return False

def test_with_image(image_path="mondrian/source/mike-shrub.jpg"):
    """Test with an actual image"""
    import os

    if not os.path.exists(image_path):
        print(f"\n❌ Image not found: {image_path}")
        print("   Available test images:")
        source_dir = "mondrian/source"
        if os.path.exists(source_dir):
            for f in os.listdir(source_dir)[:5]:
                print(f"      {source_dir}/{f}")
        return False

    print(f"\n📷 Testing with image: {image_path}")
    print("⏳ Sending request to MLX model...")

    try:
        with open(image_path, 'rb') as f:
            response = requests.post(
                "http://localhost:5100/analyze",
                files={'image': ('test.jpg', f, 'image/jpeg')},
                data={
                    'advisor': 'mondrian',
                    'job_id': 'cli_test'
                },
                timeout=180
            )

        if response.status_code == 200:
            result = response.json()
            print("\n✅ MLX Model Response:")
            print("-" * 60)
            print(result.get('analysis', 'No analysis returned'))
            print("-" * 60)
            print(f"\n✅ Test successful! MLX backend is working.")
            return True
        else:
            print(f"\n❌ Error: Status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False

    except requests.exceptions.Timeout:
        print("\n❌ Request timed out (first request may take longer)")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    # Test 1: Health check
    if not test_health():
        sys.exit(1)

    # Test 2: Image analysis
    print("\n" + "=" * 60)
    print("Testing MLX Model with Image")
    print("=" * 60)

    if test_with_image():
        print("\n🎉 All tests passed! MLX backend is fully operational.")
        sys.exit(0)
    else:
        print("\n⚠️  Health check passed but image test failed.")
        print("   Check logs: mondrian/logs/ai_advisor_err.log")
        sys.exit(1)

if __name__ == "__main__":
    main()
