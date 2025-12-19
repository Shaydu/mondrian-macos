#!/usr/bin/env python3
"""
Simple test to submit an image directly to MLX model via the AI Advisor Service
Uses a simple advisor from the database
"""

import sys
import os
import requests
import time

SERVICE_URL = "http://localhost:5100"

def test_image(image_path, advisor_id="edge-spotter"):
    """Test image description with MLX model"""

    if not os.path.exists(image_path):
        print(f"❌ Error: Image not found: {image_path}")
        return False

    print("=" * 80)
    print("🤖 MLX Qwen3-VL-4B Model Test")
    print("=" * 80)
    print(f"\n📷 Image: {image_path}")
    print(f"🎯 Advisor: {advisor_id}")
    print(f"\n⏳ Sending request to {SERVICE_URL}...")

    job_id = f"test_{int(time.time())}"

    try:
        start_time = time.time()

        # Send image to the service
        with open(image_path, 'rb') as f:
            response = requests.post(
                f"{SERVICE_URL}/analyze",
                files={'image': ('test.jpg', f, 'image/jpeg')},
                data={
                    'advisor': advisor_id,
                    'job_id': job_id
                },
                timeout=180
            )

        elapsed = time.time() - start_time

        print(f"✅ Response received in {elapsed:.2f} seconds")
        print("=" * 80)

        if response.status_code == 200:
            result = response.json()

            print("\n📝 Model Response:\n")
            print(result.get('analysis', 'No analysis returned'))
            print("\n" + "=" * 80)

            print("\n📊 Metadata:")
            print(f"  Job ID: {job_id}")
            print(f"  Analysis ID: {result.get('analysis_id', 'N/A')}")
            print(f"  Response length: {len(result.get('analysis', ''))} characters")
            print(f"  Total time: {elapsed:.2f} seconds")
            print("\n✅ Test completed successfully!")
            return True
        else:
            print(f"\n❌ Error: Server returned status {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"\n❌ Error: Request timed out")
        print("Note: First request may take longer as model loads into memory")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test_mlx_simple.py <image_path> [advisor_id]")
        print("\nExample:")
        print("  python3 test_mlx_simple.py /path/to/image.jpg")
        print("  python3 test_mlx_simple.py /path/to/image.jpg edge-spotter")
        sys.exit(1)

    image_path = sys.argv[1]
    advisor_id = sys.argv[2] if len(sys.argv) > 2 else "edge-spotter"

    # Check service health
    try:
        health = requests.get(f"{SERVICE_URL}/health", timeout=5).json()
        print(f"✅ Service is UP")
        print(f"   Model: {health.get('model', 'Unknown')}")
        print(f"   Backend: MLX (Apple Silicon)\n")
    except Exception as e:
        print(f"❌ Service health check failed: {e}")
        print(f"   Make sure the service is running: cd mondrian && python3 start_services.py")
        sys.exit(1)

    success = test_image(image_path, advisor_id)
    sys.exit(0 if success else 1)
