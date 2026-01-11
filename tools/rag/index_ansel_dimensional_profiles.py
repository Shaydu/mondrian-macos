#!/usr/bin/env python3
"""
Index Historical Ansel Adams Images with Dimensional Profiles

This script:
1. Finds all Ansel Adams images in the advisor directory
2. Analyzes each image using the AI Advisor Service
3. Extracts dimensional profiles automatically (now built into the service)
4. Stores profiles in the dimensional_profiles table

Usage:
    python3 index_ansel_dimensional_profiles.py
"""

import os
import sys
import requests
import time
from pathlib import Path

# Configuration
AI_ADVISOR_URL = "http://localhost:5100/analyze"
ANSEL_DIR = "/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel"
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

    except requests.exceptions.Timeout:
        print(f"  [✗] Timeout analyzing {os.path.basename(image_path)}")
        return False
    except Exception as e:
        print(f"  [✗] Error analyzing {os.path.basename(image_path)}: {e}")
        return False


def main():
    print("=" * 70)
    print("Indexing Ansel Adams Historical Images with Dimensional Profiles")
    print("=" * 70)
    print(f"Directory: {ANSEL_DIR}")
    print(f"Advisor: {ADVISOR_ID}")
    print(f"AI Service: {AI_ADVISOR_URL}")
    print()

    # Check if AI Advisor Service is running
    try:
        health_resp = requests.get("http://localhost:5100/health", timeout=5)
        if health_resp.status_code == 200:
            health_data = health_resp.json()
            print(f"[✓] AI Advisor Service is running")
            print(f"    Backend: {health_data.get('backend', 'Unknown')}")
            print(f"    Model: {health_data.get('model', health_data.get('mlx_model', 'Unknown'))}")
            print(f"    Script: {health_data.get('script', 'Unknown')}")
            print()
        else:
            print(f"[✗] AI Advisor Service health check failed: {health_resp.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[✗] Cannot connect to AI Advisor Service: {e}")
        print(f"    Make sure the service is running on port 5100")
        sys.exit(1)

    # Find all images
    if not os.path.exists(ANSEL_DIR):
        print(f"[✗] Directory not found: {ANSEL_DIR}")
        sys.exit(1)

    image_files = []
    for root, dirs, files in os.walk(ANSEL_DIR):
        for filename in files:
            if Path(filename).suffix in IMG_EXTENSIONS:
                filepath = Path(root) / filename
                image_files.append(filepath)

    print(f"Found {len(image_files)} images to index")
    print()

    # Process each image
    success_count = 0
    fail_count = 0

    for i, image_path in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] Processing: {image_path.name}")

        if analyze_image(image_path, ADVISOR_ID):
            success_count += 1
        else:
            fail_count += 1

        # Small delay to avoid overwhelming the service
        if i < len(image_files):
            time.sleep(2)

        print()

    # Summary
    print("=" * 70)
    print("Indexing Complete")
    print("=" * 70)
    print(f"Total images: {len(image_files)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print()

    if success_count > 0:
        print(f"[✓] {success_count} dimensional profiles saved to database")
        print(f"    You can now use dimensional RAG with enable_rag=true")
    else:
        print(f"[✗] No images were successfully indexed")


if __name__ == "__main__":
    main()
