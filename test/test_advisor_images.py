#!/usr/bin/env python3
"""Test that advisor images are properly accessible via the API."""
import os
import requests

BASE_URL = "http://127.0.0.1:5005"
ADVISOR_IDS = ["watkins", "weston", "cunningham", "gilpin", "ansel", "mondrian", "okeefe", "vangogh", "gehry"]

def test_advisor_images():
    """Test that all advisor headshots are accessible."""
    print("Testing advisor image endpoints...\n")

    for advisor_id in ADVISOR_IDS:
        url = f"{BASE_URL}/advisor_image/{advisor_id}.jpg"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                size = len(response.content)
                print(f"✓ {advisor_id:12} - {size:,} bytes")
            else:
                print(f"✗ {advisor_id:12} - HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ {advisor_id:12} - Error: {e}")

def test_advisor_detail_pages():
    """Test that advisor detail pages include image URLs."""
    print("\nTesting advisor detail pages for image URLs...\n")

    for advisor_id in ADVISOR_IDS:
        url = f"{BASE_URL}/advisor/{advisor_id}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                has_image = f"/advisor_image/{advisor_id}.jpg" in response.text
                status = "✓" if has_image else "✗"
                print(f"{status} {advisor_id:12} - Image {'included' if has_image else 'missing'}")
            else:
                print(f"✗ {advisor_id:12} - HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ {advisor_id:12} - Error: {e}")

if __name__ == "__main__":
    test_advisor_images()
    test_advisor_detail_pages()
