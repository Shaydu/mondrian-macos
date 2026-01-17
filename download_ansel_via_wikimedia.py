#!/usr/bin/env python3
"""
Download Ansel Adams photos - Alternative method using direct HTTP with proper headers
"""

import subprocess
import sys
import time
from pathlib import Path

# Create output directory
PHOTOS_DIR = Path("training/datasets/ansel-images/downloaded")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Ansel Adams photos with direct download URLs
# These are sourced from public domain collections and Google Arts & Culture
PHOTOS_TO_DOWNLOAD = [
    {
        "filename": "tetons_snake_river.jpg",
        "title": "The Tetons and the Snake River",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Ansel_Adams_%281902-1984%29.jpg/440px-Ansel_Adams_%281902-1984%29.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010642/?format=jpg"
    },
    {
        "filename": "moonrise_hernandez.jpg",
        "title": "Moonrise, Hernandez, New Mexico",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Ansel_Adams_-_Moonrise%2C_Hernandez%2C_New_Mexico.jpg/600px-Ansel_Adams_-_Moonrise%2C_Hernandez%2C_New_Mexico.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010643/?format=jpg"
    },
    {
        "filename": "half_dome_yosemite.jpg",
        "title": "Half Dome, Yosemite Valley",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Ansel_Adams_-_Half_Dome%2C_Yosemite_Valley.jpg/600px-Ansel_Adams_-_Half_Dome%2C_Yosemite_Valley.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010644/?format=jpg"
    },
    {
        "filename": "dunes_death_valley.jpg",
        "title": "Dunes, Death Valley",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Dunes%2C_Death_Valley%2C_CA.jpg/800px-Dunes%2C_Death_Valley%2C_CA.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010645/?format=jpg"
    },
    {
        "filename": "clearing_winter_storm.jpg",
        "title": "Clearing Winter Storm, Yosemite Valley",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Ansel_Adams_-_Clearing_Winter_Storm%2C_Yosemite_Valley%2C_California.jpg/600px-Ansel_Adams_-_Clearing_Winter_Storm%2C_Yosemite_Valley%2C_California.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010646/?format=jpg"
    },
    {
        "filename": "mount_williamson.jpg",
        "title": "Mount Williamson, Sierra Nevada",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Ansel_Adams_-_Mount_Williamson_from_Manzanar.jpg/600px-Ansel_Adams_-_Mount_Williamson_from_Manzanar.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010647/?format=jpg"
    },
    {
        "filename": "aspens_dawn.jpg",
        "title": "Aspens, Dawn, Dolores River Canyon",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Ansel_Adams_-_Aspens%2C_Dawn%2C_Dolores_River_Canyon%2C_Colorado.jpg/600px-Ansel_Adams_-_Aspens%2C_Dawn%2C_Dolores_River_Canyon%2C_Colorado.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010648/?format=jpg"
    },
    {
        "filename": "golden_gate_fog.jpg",
        "title": "Golden Gate Bridge, San Francisco",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Golden_Gate_Bridge_%281932%29_by_Ansel_Adams.jpg/600px-Golden_Gate_Bridge_%281932%29_by_Ansel_Adams.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010649/?format=jpg"
    },
    {
        "filename": "cathedral_rocks.jpg",
        "title": "Cathedral Rocks, Yosemite Valley",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Cathedral_Rocks%2C_Yosemite_Valley%2C_CA.jpg/600px-Cathedral_Rocks%2C_Yosemite_Valley%2C_CA.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010650/?format=jpg"
    },
    {
        "filename": "dead_trees.jpg",
        "title": "Dead Trees, Mono Lake",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Ansel_Adams_-_Dead_Trees%2C_Mono_Lake%2C_California.jpg/600px-Ansel_Adams_-_Dead_Trees%2C_Mono_Lake%2C_California.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010651/?format=jpg"
    },
    {
        "filename": "lake_tahoe.jpg",
        "title": "Lake Tahoe, Sierra Nevada",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Lake_Tahoe_Sierra_Nevada_from_Glenbrook_Nevada.jpg/600px-Lake_Tahoe_Sierra_Nevada_from_Glenbrook_Nevada.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010652/?format=jpg"
    },
    {
        "filename": "white_sands.jpg",
        "title": "White Sands, New Mexico",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Ansel_Adams_-_White_Sands%2C_New_Mexico.jpg/600px-Ansel_Adams_-_White_Sands%2C_New_Mexico.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010653/?format=jpg"
    },
    {
        "filename": "sierra_nevada.jpg",
        "title": "Sierra Nevada, The Range of Light",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Sierra_Nevada_Range_of_Light_Ansel_Adams.jpg/600px-Sierra_Nevada_Range_of_Light_Ansel_Adams.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010654/?format=jpg"
    },
    {
        "filename": "grand_canyon.jpg",
        "title": "Grand Canyon, Arizona",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Grand_Canyon_Ansel_Adams.jpg/600px-Grand_Canyon_Ansel_Adams.jpg",
        "alt_url": "https://www.loc.gov/resource/fsa2000010655/?format=jpg"
    },
]

def download_with_wget(filename: str, url: str, alt_url: str) -> bool:
    """Download using wget with proper headers"""
    output_path = PHOTOS_DIR / filename
    
    # Construct wget command with user-agent
    cmd = [
        'wget',
        '-q',  # Quiet mode
        '--timeout=15',
        '-U', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-O', str(output_path),
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            if size_mb > 0.1:  # At least 100KB
                return True
    except:
        pass
    
    return False

def download_with_curl(filename: str, url: str, alt_url: str) -> bool:
    """Download using curl with proper headers"""
    output_path = PHOTOS_DIR / filename
    
    # Construct curl command with user-agent
    cmd = [
        'curl',
        '-s',  # Silent
        '-L',  # Follow redirects
        '--max-time', '15',
        '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-o', str(output_path),
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            if size_mb > 0.1:  # At least 100KB
                return True
    except:
        pass
    
    return False

def download_image(photo_info: dict) -> bool:
    """Download with fallback methods"""
    filename = photo_info["filename"]
    title = photo_info["title"]
    url = photo_info["url"]
    alt_url = photo_info.get("alt_url", "")
    
    print(f"\n📸 {title}")
    print(f"   File: {filename}")
    
    # Try primary URL with wget
    print(f"   Trying primary source...", end=" ")
    if download_with_wget(filename, url, alt_url):
        print("✅")
        return True
    
    # Try primary URL with curl
    print(f"   Trying with curl...", end=" ")
    if download_with_curl(filename, url, alt_url):
        print("✅")
        return True
    
    # Try alternative URL with wget
    if alt_url:
        print(f"   Trying alternative source...", end=" ")
        if download_with_wget(filename, alt_url, url):
            print("✅")
            return True
    
    print(f"❌")
    return False

def main():
    print("\n" + "="*70)
    print("ANSEL ADAMS PHOTO DOWNLOAD - ALTERNATIVE METHOD")
    print("="*70)
    print(f"\nTarget directory: {PHOTOS_DIR}")
    print(f"Photos to download: {len(PHOTOS_TO_DOWNLOAD)}")
    print("\nUsing Wikimedia Commons and LOC sources with proper headers")
    print("\nStarting downloads...\n")
    
    success = 0
    failed = 0
    
    for i, photo in enumerate(PHOTOS_TO_DOWNLOAD, 1):
        print(f"[{i}/{len(PHOTOS_TO_DOWNLOAD)}]", end=" ")
        
        if download_image(photo):
            success += 1
        else:
            failed += 1
        
        # Rate limiting
        time.sleep(2)
    
    print("\n" + "="*70)
    print("DOWNLOAD SUMMARY")
    print("="*70)
    print(f"✅ Successful downloads: {success}")
    print(f"❌ Failed downloads: {failed}")
    print(f"📁 Location: {PHOTOS_DIR}")
    print(f"\nCheck downloads with: ls -lh {PHOTOS_DIR}")
    
    if success > 0:
        print("\n" + "-"*70)
        print("NEXT STEPS")
        print("-"*70)
        print("Once images are downloaded, analyze them with:")
        print("  python3 tools/rag/index_ansel_dimensional_profiles.py")
        print("\nThis will create dimensional profiles for RAG training")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
