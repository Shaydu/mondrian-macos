#!/usr/bin/env python3
"""Test that advisor artworks are properly accessible via the API."""
import os
import requests

BASE_URL = "http://127.0.0.1:5005"
ADVISOR_IDS = ["watkins", "weston", "cunningham", "gilpin", "ansel", "mondrian", "okeefe", "vangogh", "gehry"]

def test_advisor_artwork_endpoints():
    """Test that all advisor artworks are accessible."""
    print("Testing advisor artwork endpoints...\n")

    total_artworks = 0
    for advisor_id in ADVISOR_IDS:
        # First check if the advisor has an artworks directory
        artwork_dir = f"/Users/shaydu/dev/mondrian-macos/mondrian/advisor_artworks/{advisor_id}"
        if not os.path.exists(artwork_dir):
            print(f"✗ {advisor_id:12} - No artwork directory")
            continue

        # Get artwork files
        artworks = [f for f in os.listdir(artwork_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not artworks:
            print(f"✗ {advisor_id:12} - Directory exists but no artworks")
            continue

        # Test first artwork URL
        test_file = artworks[0]
        url = f"{BASE_URL}/advisor_artwork/{advisor_id}/{test_file}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                size = len(response.content)
                print(f"✓ {advisor_id:12} - {len(artworks)} artworks ({size:,} bytes for first)")
                total_artworks += len(artworks)
            else:
                print(f"✗ {advisor_id:12} - HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ {advisor_id:12} - Error: {e}")

    print(f"\nTotal artworks available: {total_artworks}")


def test_advisor_detail_pages_have_artworks():
    """Test that advisor detail pages include artwork images."""
    print("\nTesting advisor detail pages for artwork display...\n")

    for advisor_id in ADVISOR_IDS:
        url = f"{BASE_URL}/advisor/{advisor_id}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                has_artworks = "advisor_artwork" in response.text
                has_section = "Representative Works" in response.text
                status = "✓" if (has_artworks or has_section) else "✗"
                detail = "artworks displayed" if has_artworks else ("section present" if has_section else "no artworks")
                print(f"{status} {advisor_id:12} - {detail}")
            else:
                print(f"✗ {advisor_id:12} - HTTP {response.status_code}")
        except Exception as e:
            print(f"✗ {advisor_id:12} - Error: {e}")


def show_artwork_counts():
    """Show count of artworks per advisor."""
    print("\nArtwork inventory:\n")

    for advisor_id in ADVISOR_IDS:
        artwork_dir = f"/Users/shaydu/dev/mondrian-macos/mondrian/advisor_artworks/{advisor_id}"
        if os.path.exists(artwork_dir):
            artworks = [f for f in os.listdir(artwork_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            print(f"  {advisor_id:12} - {len(artworks)} artworks")
            if artworks:
                for artwork in artworks[:3]:  # Show first 3
                    print(f"    • {artwork[:60]}")
                if len(artworks) > 3:
                    print(f"    ... and {len(artworks) - 3} more")
        else:
            print(f"  {advisor_id:12} - No artworks")


if __name__ == "__main__":
    show_artwork_counts()
    test_advisor_artwork_endpoints()
    test_advisor_detail_pages_have_artworks()
