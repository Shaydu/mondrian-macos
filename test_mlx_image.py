#!/usr/bin/env python3
"""
Quick test script to submit an image to the MLX Qwen3-VL-4B model
and get a description.
"""

import sys
import os
import requests
import time
import json

SERVICE_URL = "http://localhost:5100"

def test_image_description(image_path, prompt="Describe what you see in this image in detail."):
    """
    Submit an image to the MLX model and get a description.

    Args:
        image_path: Path to the image file
        prompt: Custom prompt (default: asks for description)
    """

    if not os.path.exists(image_path):
        print(f"❌ Error: Image not found: {image_path}")
        return None

    print("=" * 80)
    print("MLX Qwen3-VL-4B Image Description Test")
    print("=" * 80)
    print(f"\n📷 Image: {image_path}")
    print(f"💬 Prompt: {prompt}")
    print(f"\n⏳ Sending request to {SERVICE_URL}...")

    job_id = f"test_{int(time.time())}"

    try:
        start_time = time.time()

        # Open and send the image
        with open(image_path, 'rb') as f:
            response = requests.post(
                f"{SERVICE_URL}/analyze",
                files={'image': ('image.jpg', f, 'image/jpeg')},
                data={
                    'advisor': prompt,  # Use the prompt as the advisor parameter
                    'job_id': job_id
                },
                timeout=180  # 3 minute timeout
            )

        elapsed = time.time() - start_time

        print(f"✅ Response received in {elapsed:.2f} seconds")
        print("=" * 80)

        if response.status_code == 200:
            result = response.json()

            # Display the analysis
            print("\n📝 Model Response:\n")
            print(result.get('analysis', 'No analysis returned'))
            print("\n" + "=" * 80)

            # Show metadata
            print("\n📊 Metadata:")
            print(f"  Job ID: {result.get('job_id', 'N/A')}")
            print(f"  Analysis ID: {result.get('analysis_id', 'N/A')}")
            print(f"  Response length: {len(result.get('analysis', ''))} characters")
            print(f"  Total time: {elapsed:.2f} seconds")

            return result

        else:
            print(f"\n❌ Error: Server returned status {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        print(f"\n❌ Error: Request timed out after 180 seconds")
        print("The model may be loading for the first time or processing a complex image.")
        return None

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test MLX image description")
    parser.add_argument('image', help='Path to image file')
    parser.add_argument('--prompt', default='Describe what you see in this image in detail.',
                        help='Custom prompt for the model')

    args = parser.parse_args()

    # Test the service health first
    try:
        health = requests.get(f"{SERVICE_URL}/health", timeout=5).json()
        print(f"✅ Service is UP")
        print(f"   Model: {health.get('model', 'Unknown')}")
        print()
    except Exception as e:
        print(f"❌ Service health check failed: {e}")
        print(f"   Make sure the AI Advisor Service is running on port 5100")
        sys.exit(1)

    # Run the test
    result = test_image_description(args.image, args.prompt)

    if result:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)
