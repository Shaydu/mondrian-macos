#!/usr/bin/env python3
"""
Populate image_title column in dimensional_profiles from metadata.yaml files.

Usage:
    python3 populate_image_titles.py --advisor ansel
    python3 populate_image_titles.py --advisor all
"""

import sqlite3
import yaml
import argparse
from pathlib import Path

DB_PATH = "mondrian.db"

ADVISOR_METADATA = {
    "ansel": "training/datasets/ansel-images/metadata.yaml",
    "okeefe": "training/datasets/okeefe-images/metadata.yaml",
    "mondrian": "training/datasets/mondrian-images/metadata.yaml",
}

ADVISOR_IMAGE_DIRS = {
    "ansel": "mondrian/source/advisor/photographer/ansel",
    "okeefe": "mondrian/source/advisor/painter/okeefe",
    "mondrian": "mondrian/source/advisor/painter/mondrian",
}


def load_metadata(metadata_path):
    """Load metadata from YAML file"""
    try:
        with open(metadata_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Build filename -> title mapping
        filename_to_title = {}
        if data and 'images' in data:
            for img in data['images']:
                filename = img.get('filename', '')
                title = img.get('title', '')
                if filename and title:
                    filename_to_title[filename] = title
        
        return filename_to_title
    except Exception as e:
        print(f"Error loading metadata from {metadata_path}: {e}")
        return {}


def populate_titles_for_advisor(advisor_id, metadata_path, image_dir):
    """Populate image_title for an advisor"""
    
    # Load metadata
    filename_to_title = load_metadata(metadata_path)
    
    if not filename_to_title:
        print(f"⚠️  No metadata found for {advisor_id}")
        return 0
    
    print(f"\n📖 {advisor_id.title()}: Found {len(filename_to_title)} metadata entries")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updated_count = 0
    not_found = []
    
    # For each metadata entry, find and update the corresponding database row
    for filename, title in filename_to_title.items():
        # Search for any path ending with this filename (handles absolute vs relative paths)
        cursor.execute(
            "SELECT id, image_path FROM dimensional_profiles WHERE image_path LIKE ? AND advisor_id = ?",
            (f"%{filename}", advisor_id)
        )
        row = cursor.fetchone()
        
        if row:
            profile_id = row[0]
            image_path = row[1]
            cursor.execute(
                "UPDATE dimensional_profiles SET image_title = ? WHERE id = ?",
                (title, profile_id)
            )
            conn.commit()
            updated_count += 1
            print(f"  ✓ {filename:40} → {title}")
        else:
            not_found.append(filename)
    
    conn.close()
    
    print(f"\n  Updated: {updated_count}/{len(filename_to_title)} entries")
    
    if not_found:
        print(f"  ⚠️  Not found in database: {len(not_found)}")
        for f in not_found[:5]:
            print(f"     - {f}")
        if len(not_found) > 5:
            print(f"     ... and {len(not_found) - 5} more")
    
    return updated_count


def main():
    parser = argparse.ArgumentParser(description="Populate image_title from metadata.yaml")
    parser.add_argument('--advisor', type=str, default='ansel', 
                       help='Advisor ID (ansel, okeefe, mondrian, or all)')
    args = parser.parse_args()
    
    advisor = args.advisor.lower()
    
    print("=" * 70)
    print("Populating image_title from metadata.yaml")
    print("=" * 70)
    
    if advisor == 'all':
        total_updated = 0
        for adv_id in ADVISOR_METADATA.keys():
            metadata_path = ADVISOR_METADATA[adv_id]
            image_dir = ADVISOR_IMAGE_DIRS[adv_id]
            if Path(metadata_path).exists():
                updated = populate_titles_for_advisor(adv_id, metadata_path, image_dir)
                total_updated += updated
            else:
                print(f"\n⚠️  {adv_id}: metadata.yaml not found at {metadata_path}")
        
        print(f"\n" + "=" * 70)
        print(f"✅ Total updated: {total_updated} image titles")
        print("=" * 70)
    else:
        if advisor not in ADVISOR_METADATA:
            print(f"❌ Unknown advisor: {advisor}")
            print(f"Available: {', '.join(ADVISOR_METADATA.keys())}")
            return
        
        metadata_path = ADVISOR_METADATA[advisor]
        image_dir = ADVISOR_IMAGE_DIRS[advisor]
        
        if not Path(metadata_path).exists():
            print(f"❌ Metadata file not found: {metadata_path}")
            return
        
        updated = populate_titles_for_advisor(advisor, metadata_path, image_dir)
        
        print(f"\n" + "=" * 70)
        print(f"✅ Updated {updated} image titles for {advisor.title()}")
        print("=" * 70)


if __name__ == "__main__":
    main()
