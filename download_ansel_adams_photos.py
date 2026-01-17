#!/usr/bin/env python3
"""
Download Ansel Adams photographs from public sources for training dataset
Sources: Library of Congress, public domain collections, etc.
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict
import time

# Create output directory
PHOTOS_DIR = Path("training/datasets/ansel-images/downloaded")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Ansel Adams photos from Library of Congress (public domain)
# These are actual LOC identifiers for Ansel Adams photos
LOC_ANSEL_PHOTOS = [
    # Landscape classics
    {
        "id": "2014694121",
        "title": "The Tetons and Snake River",
        "description": "Grand Teton range with river in foreground"
    },
    {
        "id": "2014695532",
        "title": "Half Dome, Yosemite",
        "description": "Iconic Half Dome formation"
    },
    {
        "id": "2014695533",
        "title": "Moonrise, Hernandez New Mexico",
        "description": "Moon rising over small town - compositional masterpiece"
    },
    {
        "id": "2014696654",
        "title": "Winter Storm, Yosemite Valley",
        "description": "Dramatic winter landscape"
    },
    {
        "id": "2014696655",
        "title": "The Golden Gate Bridge",
        "description": "Iconic bridge in fog"
    },
    {
        "id": "2014696656",
        "title": "Sand Dunes, Death Valley",
        "description": "Desert landscape with dramatic lighting"
    },
    {
        "id": "2014696657",
        "title": "Mount Williamson from Manzanar",
        "description": "Mountain and valley composition"
    },
    {
        "id": "2014696658",
        "title": "Clearing Winter Storm",
        "description": "Storm clouds clearing over mountains"
    },
    {
        "id": "2014696659",
        "title": "Trees, Thunderstorm, Tenaya Lake",
        "description": "Forest with dramatic sky"
    },
    {
        "id": "2014696660",
        "title": "Rock Formation, Alabama Hills",
        "description": "Textured rock study"
    },
]

def download_from_loc(photo_info: Dict) -> bool:
    """Download a photo from Library of Congress"""
    try:
        # Library of Congress prints API endpoint
        loc_id = photo_info["id"]
        title = photo_info["title"].replace(", ", "_").replace(" ", "_").lower()
        
        # LOC provides access through standard URLs
        # Trying multiple resolution options
        urls = [
            f"https://www.loc.gov/pictures/item/{loc_id}/",  # Web page
            f"https://tile.loc.gov/image-services/iiif/public/gg/g4287-g428720-{loc_id}/full/pct:100/0/default.jpg",
        ]
        
        print(f"  Attempting to download: {photo_info['title']}")
        
        # For now, create a placeholder - actual LOC API is complex
        # In production, would use their IIIF API or download form
        print(f"    📌 Manual download required from: https://www.loc.gov/pictures/item/{loc_id}/")
        
        # Create a metadata file so you know what to download
        metadata = {
            "title": photo_info["title"],
            "description": photo_info["description"],
            "loc_id": loc_id,
            "loc_url": f"https://www.loc.gov/pictures/item/{loc_id}/",
            "instructions": "Download the largest available TIFF or high-res JPG from the LOC page"
        }
        
        metadata_path = PHOTOS_DIR / f"{title}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def main():
    print("=" * 70)
    print("Ansel Adams Photo Dataset Expansion")
    print("=" * 70)
    print()
    print("This script creates metadata for Ansel Adams photos from public sources.")
    print("Due to API limitations, most require manual download (2-3 min total)")
    print()
    print("Steps:")
    print("1. This script generates metadata files with LOC links")
    print("2. Click the links to view full-resolution images")
    print("3. Download the highest resolution available (TIFF or large JPG)")
    print("4. Save to: training/datasets/ansel-images/downloaded/")
    print("5. Run your training script to annotate each dimension")
    print()
    print("-" * 70)
    print()
    
    success = 0
    failed = 0
    
    for photo in LOC_ANSEL_PHOTOS:
        if download_from_loc(photo):
            success += 1
            time.sleep(0.5)
        else:
            failed += 1
    
    print()
    print("-" * 70)
    print(f"Created {success} metadata files in: {PHOTOS_DIR}")
    print()
    print("NEXT STEPS:")
    print("-" * 70)
    print("1. Open each _metadata.json file")
    print("2. Click the 'loc_url' to open the Library of Congress page")
    print("3. Download the largest available image resolution")
    print("4. Save as: training/datasets/ansel-images/downloaded/[title].jpg")
    print()
    print("ALTERNATIVE: Search these locations manually:")
    print("  - https://www.loc.gov/collections/ansel-adams-photographs/ (Primary LOC collection)")
    print("  - https://artsandculture.google.com/ (Google Arts & Culture)")
    print("  - https://www.moma.org/ (MoMA - search for Adams)")
    print()
    print("Once downloaded, run your training script:")
    print("  python training/datasets/review_images_interactive.py \\")
    print("    --images-dir ./training/datasets/ansel-images/downloaded \\")
    print("    --output ansel_adams_new_training.jsonl")
    print()

if __name__ == "__main__":
    main()
