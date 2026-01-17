#!/usr/bin/env python3
"""
Index Ansel Adams Images with Dimensional Profiles from existing images

This script:
1. Finds all Ansel Adams images in training/datasets/ansel-images/
2. Analyzes each image using the AI Advisor Service
3. Extracts dimensional profiles
4. Stores profiles in the database

Usage:
    python3 index_existing_ansel_images.py
"""

import os
import sys
import requests
import time
from pathlib import Path

# Configuration
AI_ADVISOR_URL = "http://localhost:5100/analyze"
ANSEL_DIR = Path("training/datasets/ansel-images")
ADVISOR_ID = "ansel"

# Supported image extensions
IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}


def analyze_image(image_path, advisor_id):
    """
    Send image to AI Advisor Service for analysis.
    The service will automatically extract and save the dimensional profile.
    """
    try:
        abs_path = str(Path(image_path).resolve())

        print(f"  [→] Analyzing {os.path.basename(image_path)}...")

        # Send as JSON (using image_path method)
        data = {
            "advisor": advisor_id,
            "image_path": abs_path,
            "enable_rag": "false"  # Don't use RAG for historical images (no comparison needed)
        }

        response = requests.post(
            AI_ADVISOR_URL,
            json=data,
            timeout=180  # 3 minutes timeout for analysis
        )

        if response.status_code == 200:
            # Analysis successful - dimensional profile automatically saved
            print(f"  [✓] Analysis complete for {os.path.basename(image_path)}")
            return True
        else:
            print(f"  [✗] Analysis failed: {response.status_code} - {response.text[:200]}")
            return False

    except requests.ConnectionError:
        print(f"  [✗] Cannot connect to AI Advisor Service at {AI_ADVISOR_URL}")
        print(f"      Make sure the service is running: ./mondrian.sh --start")
        return False
    except Exception as e:
        print(f"  [✗] Error: {e}")
        return False


def main():
    print("=" * 70)
    print("INDEX ANSEL ADAMS IMAGES WITH DIMENSIONAL PROFILES")
    print("=" * 70)
    print()

    # Check directory
    if not ANSEL_DIR.exists():
        print(f"[✗] Directory not found: {ANSEL_DIR}")
        sys.exit(1)

    print(f"[✓] Directory: {ANSEL_DIR}")
    print()

    # Find all images
    image_files = sorted([
        f for f in ANSEL_DIR.iterdir()
        if f.is_file() and f.suffix in IMG_EXTENSIONS
    ])

    if not image_files:
        print(f"[✗] No images found in {ANSEL_DIR}")
        sys.exit(1)

    print(f"[✓] Found {len(image_files)} images")
    print()
    print("Analyzing images...")
    print("-" * 70)
    print()

    success_count = 0
    failed_count = 0

    for image_path in image_files:
        if analyze_image(image_path, ADVISOR_ID):
            success_count += 1
        else:
            failed_count += 1

        # Rate limiting
        time.sleep(3)

    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"✓ Success:  {success_count}/{len(image_files)}")
    print(f"✗ Failed:   {failed_count}/{len(image_files)}")
    print("=" * 70)
    print()
    print("NEXT STEPS:")
    print("1. Check dimensional profiles with:")
    print("   python3 tools/rag/view_dimensional_profiles.py ansel")
    print()
    print("2. Now you can retrain the LoRA adapter:")
    print("   bash train_ansel_lora.sh")
    print()


if __name__ == "__main__":
    main()
