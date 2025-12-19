#!/usr/bin/env python3
"""Quick test to verify MLX backend is working"""
import requests
import sys

print("Testing MLX Backend...")
print("=" * 60)

# Test health
try:
    health = requests.get("http://localhost:5100/health", timeout=5).json()
    print(f"✅ Service UP - Model: {health['model']}")
except Exception as e:
    print(f"❌ Service down: {e}")
    sys.exit(1)

# Test with image
print("\n📷 Sending image to MLX model...")
try:
    with open("mondrian/source/mike-shrub.jpg", "rb") as f:
        response = requests.post(
            "http://localhost:5100/analyze",
            files={"image": ("test.jpg", f, "image/jpeg")},
            data={"advisor": "mondrian", "job_id": "quick_test"},
            timeout=180
        )

    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS! MLX Response:")
        print("-" * 60)
        print(result.get("analysis", "No analysis"))
        print("-" * 60)
    else:
        print(f"❌ Error {response.status_code}: {response.text[:200]}")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
