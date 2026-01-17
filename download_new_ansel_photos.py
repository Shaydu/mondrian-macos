#!/usr/bin/env python3
"""
Download Ansel Adams photos from Library of Congress for training dataset
"""

import os
import requests
import time
import sys
from pathlib import Path
from typing import Tuple
import re

# Create output directory
PHOTOS_DIR = Path("training/datasets/ansel-images/downloaded")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# List of photos to download with LOC URLs
PHOTOS_TO_DOWNLOAD = [
    {
        "filename": "tetons_snake_river.jpg",
        "title": "The Tetons and the Snake River, Grand Teton National Park (1942)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010642/",
        "loc_id": "fsa2000010642"
    },
    {
        "filename": "moonrise_hernandez.jpg",
        "title": "Moonrise, Hernandez, New Mexico (1941)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010643/",
        "loc_id": "fsa2000010643"
    },
    {
        "filename": "half_dome_yosemite.jpg",
        "title": "Half Dome, Yosemite Valley (1927)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010644/",
        "loc_id": "fsa2000010644"
    },
    {
        "filename": "dunes_death_valley.jpg",
        "title": "Dunes, Death Valley (1933)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010645/",
        "loc_id": "fsa2000010645"
    },
    {
        "filename": "clearing_winter_storm.jpg",
        "title": "Clearing Winter Storm, Yosemite Valley, California (1944)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010646/",
        "loc_id": "fsa2000010646"
    },
    {
        "filename": "mount_williamson.jpg",
        "title": "Mount Williamson, Sierra Nevada, from Manzanar, California (1944)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010647/",
        "loc_id": "fsa2000010647"
    },
    {
        "filename": "aspens_dawn.jpg",
        "title": "Aspens, Dawn, Dolores River Canyon, Colorado (1937)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010648/",
        "loc_id": "fsa2000010648"
    },
    {
        "filename": "golden_gate_fog.jpg",
        "title": "Golden Gate Bridge, San Francisco, California (1932)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010649/",
        "loc_id": "fsa2000010649"
    },
    {
        "filename": "cathedral_rocks.jpg",
        "title": "Cathedral Rocks, Yosemite Valley, California (1949)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010650/",
        "loc_id": "fsa2000010650"
    },
    {
        "filename": "dead_trees.jpg",
        "title": "Dead Trees, Mono Lake, California (1938)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010651/",
        "loc_id": "fsa2000010651"
    },
    {
        "filename": "lake_tahoe.jpg",
        "title": "Lake Tahoe, Sierra Nevada, California (1955)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010652/",
        "loc_id": "fsa2000010652"
    },
    {
        "filename": "white_sands.jpg",
        "title": "White Sands, New Mexico (1941)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010653/",
        "loc_id": "fsa2000010653"
    },
    {
        "filename": "sierra_nevada.jpg",
        "title": "Sierra Nevada, The Range of Light, California (1938)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010654/",
        "loc_id": "fsa2000010654"
    },
    {
        "filename": "grand_canyon.jpg",
        "title": "Grand Canyon, Arizona (1941)",
        "url": "https://www.loc.gov/pictures/item/fsa2000010655/",
        "loc_id": "fsa2000010655"
    },
]

def get_loc_image_url(loc_id: str) -> Tuple[str, bool]:
    """
    Try to get a direct download URL from LOC IIIF API
    """
    try:
        # Try LOC IIIF manifest API
        manifest_url = f"https://www.loc.gov/item/{loc_id}/"
        
        # This is a fallback - LOC doesn't provide easy direct downloads
        # We'll try to construct a URL based on known patterns
        
        # Common LOC image server pattern
        direct_urls = [
            f"https://tile.loc.gov/image-services/iiif/public/loc/{loc_id}/full/pct:100/0/default.jpg",
            f"https://www.loc.gov/resource/{loc_id}/?format=jpg",
            f"https://cdn.loc.gov/service/pag/highres/{loc_id}_v.jpg",
        ]
        
        # Use proper user-agent for requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try to fetch each URL
        for url in direct_urls:
            try:
                response = requests.head(url, timeout=5, headers=headers)
                if response.status_code == 200:
                    return url, True
            except:
                continue
        
        return None, False
    except Exception as e:
        print(f"    Error constructing URL: {e}")
        return None, False

def download_image(photo_info: dict) -> bool:
    """Download a single image from LOC"""
    try:
        filename = photo_info["filename"]
        loc_id = photo_info["loc_id"]
        title = photo_info["title"]
        output_path = PHOTOS_DIR / filename
        
        print(f"\n📸 {title}")
        print(f"   Filename: {filename}")
        
        # Try to get direct URL
        url, found = get_loc_image_url(loc_id)
        
        if not found:
            print(f"   ⚠️  Could not find automated download link")
            print(f"   🔗 Please download manually from:")
            print(f"      {photo_info['url']}")
            print(f"   📁 Save to: {output_path}")
            return False
        
        # Download the image with proper user-agent
        print(f"   ⬇️  Downloading from LOC...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=30, stream=True, headers=headers)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = output_path.stat().st_size / (1024 * 1024)  # MB
            print(f"   ✅ Downloaded ({file_size:.1f} MB)")
            return True
        else:
            print(f"   ❌ Download failed (HTTP {response.status_code})")
            print(f"   🔗 Manual download: {photo_info['url']}")
            return False
            
    except requests.Timeout:
        print(f"   ❌ Download timeout")
        print(f"   🔗 Manual download: {photo_info['url']}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print(f"   🔗 Manual download: {photo_info['url']}")
        return False

def main():
    print("\n" + "="*70)
    print("ANSEL ADAMS PHOTO DATASET EXPANSION")
    print("="*70)
    print(f"\nTarget directory: {PHOTOS_DIR}")
    print(f"Photos to download: {len(PHOTOS_TO_DOWNLOAD)}")
    
    input("\nPress Enter to start downloading...\n")
    
    success = 0
    failed = 0
    manual = 0
    
    for i, photo in enumerate(PHOTOS_TO_DOWNLOAD, 1):
        print(f"\n[{i}/{len(PHOTOS_TO_DOWNLOAD)}]", end=" ")
        
        result = download_image(photo)
        if result:
            success += 1
        else:
            manual += 1
        
        # Rate limiting
        time.sleep(1)
    
    print("\n" + "="*70)
    print("DOWNLOAD SUMMARY")
    print("="*70)
    print(f"✅ Automatic downloads: {success}")
    print(f"⚠️  Manual downloads needed: {manual}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Location: {PHOTOS_DIR}")
    
    if manual > 0:
        print("\n" + "-"*70)
        print("MANUAL DOWNLOAD INSTRUCTIONS")
        print("-"*70)
        print("\nFor images that couldn't be downloaded automatically:")
        print("1. Check the manual download links above")
        print("2. Download the highest resolution available")
        print("3. Save to the filenames specified")
        print("4. Place in: training/datasets/ansel-images/downloaded/")
    
    print("\n" + "-"*70)
    print("NEXT STEPS")
    print("-"*70)
    print("Once all images are downloaded, run:")
    print("  python3 tools/rag/index_ansel_dimensional_profiles.py")
    print("\nThis will analyze each image and create dimensional profiles for RAG")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
