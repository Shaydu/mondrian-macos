#!/usr/bin/env python3
"""
Download Ansel Adams photos using cloudscraper to bypass anti-bot protections
"""

import sys
import time
from pathlib import Path
from typing import Tuple

# Create output directory
PHOTOS_DIR = Path("training/datasets/ansel-images/downloaded")
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Import cloudscraper
try:
    import cloudscraper
except ImportError:
    print("Installing cloudscraper...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cloudscraper", "-q"])
    import cloudscraper

# Ansel Adams photos with direct download URLs
PHOTOS_TO_DOWNLOAD = [
    {
        "filename": "tetons_snake_river.jpg",
        "title": "The Tetons and the Snake River",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Ansel_Adams_%281902-1984%29.jpg/440px-Ansel_Adams_%281902-1984%29.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Ansel_Adams_-_Moonrise,_Hernandez,_New_Mexico.jpg"
    },
    {
        "filename": "moonrise_hernandez.jpg",
        "title": "Moonrise, Hernandez, New Mexico",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Ansel_Adams_-_Moonrise%2C_Hernandez%2C_New_Mexico.jpg/600px-Ansel_Adams_-_Moonrise%2C_Hernandez%2C_New_Mexico.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Ansel_Adams_-_Moonrise,_Hernandez,_New_Mexico.jpg"
    },
    {
        "filename": "half_dome_yosemite.jpg",
        "title": "Half Dome, Yosemite Valley",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Ansel_Adams_-_Half_Dome%2C_Yosemite_Valley.jpg/600px-Ansel_Adams_-_Half_Dome%2C_Yosemite_Valley.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Half_Dome,_Yosemite_Valley,_CA.jpg"
    },
    {
        "filename": "dunes_death_valley.jpg",
        "title": "Dunes, Death Valley",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Dunes%2C_Death_Valley%2C_CA.jpg/800px-Dunes%2C_Death_Valley%2C_CA.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Dunes,_Death_Valley,_CA.jpg"
    },
    {
        "filename": "clearing_winter_storm.jpg",
        "title": "Clearing Winter Storm, Yosemite Valley",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Ansel_Adams_-_Clearing_Winter_Storm%2C_Yosemite_Valley%2C_California.jpg/600px-Ansel_Adams_-_Clearing_Winter_Storm%2C_Yosemite_Valley%2C_California.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Clearing_Winter_Storm.jpg"
    },
    {
        "filename": "mount_williamson.jpg",
        "title": "Mount Williamson, Sierra Nevada",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Ansel_Adams_-_Mount_Williamson_from_Manzanar.jpg/600px-Ansel_Adams_-_Mount_Williamson_from_Manzanar.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Mount_Williamson.jpg"
    },
    {
        "filename": "aspens_dawn.jpg",
        "title": "Aspens, Dawn, Dolores River Canyon",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Ansel_Adams_-_Aspens%2C_Dawn%2C_Dolores_River_Canyon%2C_Colorado.jpg/600px-Ansel_Adams_-_Aspens%2C_Dawn%2C_Dolores_River_Canyon%2C_Colorado.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Aspens,_Dolores_River_Canyon.jpg"
    },
    {
        "filename": "golden_gate_fog.jpg",
        "title": "Golden Gate Bridge, San Francisco",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Golden_Gate_Bridge_%281932%29_by_Ansel_Adams.jpg/600px-Golden_Gate_Bridge_%281932%29_by_Ansel_Adams.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Golden_Gate_Bridge_(1932).jpg"
    },
    {
        "filename": "cathedral_rocks.jpg",
        "title": "Cathedral Rocks, Yosemite Valley",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Cathedral_Rocks%2C_Yosemite_Valley%2C_CA.jpg/600px-Cathedral_Rocks%2C_Yosemite_Valley%2C_CA.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Cathedral_Rocks,_Yosemite_Valley.jpg"
    },
    {
        "filename": "dead_trees.jpg",
        "title": "Dead Trees, Mono Lake",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Ansel_Adams_-_Dead_Trees%2C_Mono_Lake%2C_California.jpg/600px-Ansel_Adams_-_Dead_Trees%2C_Mono_Lake%2C_California.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Dead_Trees,_Mono_Lake.jpg"
    },
    {
        "filename": "lake_tahoe.jpg",
        "title": "Lake Tahoe, Sierra Nevada",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Lake_Tahoe_Sierra_Nevada_from_Glenbrook_Nevada.jpg/600px-Lake_Tahoe_Sierra_Nevada_from_Glenbrook_Nevada.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Lake_Tahoe.jpg"
    },
    {
        "filename": "white_sands.jpg",
        "title": "White Sands, New Mexico",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Ansel_Adams_-_White_Sands%2C_New_Mexico.jpg/600px-Ansel_Adams_-_White_Sands%2C_New_Mexico.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:White_Sands,_New_Mexico.jpg"
    },
    {
        "filename": "sierra_nevada.jpg",
        "title": "Sierra Nevada, The Range of Light",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Sierra_Nevada_Range_of_Light_Ansel_Adams.jpg/600px-Sierra_Nevada_Range_of_Light_Ansel_Adams.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Sierra_Nevada.jpg"
    },
    {
        "filename": "grand_canyon.jpg",
        "title": "Grand Canyon, Arizona",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Grand_Canyon_Ansel_Adams.jpg/600px-Grand_Canyon_Ansel_Adams.jpg",
        "alt_url": "https://commons.wikimedia.org/wiki/File:Grand_Canyon.jpg"
    },
]

def download_image(scraper, photo_info: dict) -> bool:
    """Download with cloudscraper"""
    filename = photo_info["filename"]
    title = photo_info["title"]
    url = photo_info["url"]
    alt_url = photo_info.get("alt_url", "")
    
    output_path = PHOTOS_DIR / filename
    
    print(f"\n📸 {title}")
    print(f"   File: {filename}", end="")
    
    # Try primary URL
    try:
        print(" ... downloading", end="", flush=True)
        response = scraper.get(url, timeout=20)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            size_mb = output_path.stat().st_size / (1024 * 1024)
            if size_mb > 0.05:  # At least 50KB
                print(f" ✅ ({size_mb:.1f}MB)")
                return True
            else:
                output_path.unlink()  # Delete if too small
    except Exception as e:
        print(f" ❌ ({str(e)[:30]})", end="")
    
    # Try alternative URL if primary failed
    if alt_url:
        try:
            print(" ... retrying", end="", flush=True)
            response = scraper.get(alt_url, timeout=20)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                size_mb = output_path.stat().st_size / (1024 * 1024)
                if size_mb > 0.05:
                    print(f" ✅ ({size_mb:.1f}MB)")
                    return True
                else:
                    output_path.unlink()
        except Exception as e:
            print(f" ❌")
    
    print(" ❌")
    return False

def main():
    print("\n" + "="*70)
    print("ANSEL ADAMS PHOTO DOWNLOAD - CLOUDSCRAPER")
    print("="*70)
    print(f"\nTarget directory: {PHOTOS_DIR}")
    print(f"Photos to download: {len(PHOTOS_TO_DOWNLOAD)}")
    print("Using cloudscraper to bypass anti-bot protections")
    
    # Create scraper instance
    print("\nInitializing cloudscraper...", end="", flush=True)
    try:
        scraper = cloudscraper.create_scraper()
        print(" ✅")
    except Exception as e:
        print(f" ❌ Error: {e}")
        sys.exit(1)
    
    print("\nStarting downloads...\n")
    
    success = 0
    failed = 0
    
    for i, photo in enumerate(PHOTOS_TO_DOWNLOAD, 1):
        print(f"[{i:2d}/{len(PHOTOS_TO_DOWNLOAD)}]", end=" ")
        
        if download_image(scraper, photo):
            success += 1
        else:
            failed += 1
        
        # Rate limiting - be respectful to servers
        time.sleep(1.5)
    
    print("\n" + "="*70)
    print("DOWNLOAD SUMMARY")
    print("="*70)
    print(f"✅ Successful downloads: {success}/{len(PHOTOS_TO_DOWNLOAD)}")
    print(f"❌ Failed downloads: {failed}/{len(PHOTOS_TO_DOWNLOAD)}")
    print(f"📁 Location: {PHOTOS_DIR}")
    
    # List downloaded files
    downloaded = list(PHOTOS_DIR.glob("*.jpg")) + list(PHOTOS_DIR.glob("*.png"))
    if downloaded:
        print(f"\nDownloaded {len(downloaded)} files:")
        for f in sorted(downloaded)[:5]:
            size = f.stat().st_size / (1024 * 1024)
            print(f"  ✓ {f.name} ({size:.1f}MB)")
        if len(downloaded) > 5:
            print(f"  ... and {len(downloaded) - 5} more")
    
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
