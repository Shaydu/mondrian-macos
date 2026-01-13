#!/usr/bin/env python3
"""
Populate Image Metadata from YAML to Database

Reads metadata.yaml files from advisor directories and updates
the dimensional_profiles table with proper metadata (title, year, location, significance).

Usage:
    python scripts/populate_image_metadata.py --advisor ansel
    python scripts/populate_image_metadata.py --advisor all
    python scripts/populate_image_metadata.py --verify-only
"""

import os
import sys
import sqlite3
import yaml
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = "mondrian/mondrian.db"

ADVISOR_DIRS = {
    "ansel": "mondrian/source/advisor/photographer/ansel",
    "okeefe": "mondrian/source/advisor/painter/okeefe",
    "mondrian": "mondrian/source/advisor/painter/mondrian",
    "gehry": "mondrian/source/advisor/architect/gehry",
    "vangogh": "mondrian/source/advisor/painter/vangogh",
    "watkins": "mondrian/source/advisor/photographer/watkins",
    "weston": "mondrian/source/advisor/photographer/weston",
    "cunningham": "mondrian/source/advisor/photographer/cunningham",
    "gilpin": "mondrian/source/advisor/photographer/gilpin"
}

def load_metadata_yaml(yaml_path):
    """Load metadata from YAML file"""
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data.get('images', [])
    except FileNotFoundError:
        print(f"  [WARN] metadata.yaml not found: {yaml_path}")
        return []
    except Exception as e:
        print(f"  [ERROR] Failed to load YAML: {e}")
        return []

def update_profile_metadata(db_path, image_path, metadata):
    """Update dimensional profile with metadata"""
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        # Get title, year, location, significance from metadata
        title = metadata.get('title', '')
        date_taken = str(metadata.get('date_taken', ''))
        location = metadata.get('location', '')
        significance = metadata.get('significance', '')
        description = metadata.get('description', '')
        
        # Clean up location if it's just coordinates
        if location and location.replace('.', '').replace('-', '').isdigit():
            location = ''  # Don't use raw coordinates as location
        
        # Update profile with metadata
        cursor.execute('''
            UPDATE dimensional_profiles
            SET image_title = ?,
                date_taken = ?,
                location = ?,
                image_significance = ?,
                image_description = COALESCE(NULLIF(image_description, ''), ?)
            WHERE image_path = ?
        ''', (title, date_taken, location, significance, description, image_path))
        
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return updated_count > 0
        
    except Exception as e:
        print(f"  [ERROR] Database update failed: {e}")
        return False

def verify_metadata(db_path, image_path):
    """Verify that metadata was populated"""
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT image_title, date_taken, location, image_significance
            FROM dimensional_profiles
            WHERE image_path = ?
        ''', (image_path,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False, "No profile found"
        
        title, date_taken, location, significance = result
        
        if not title or title.strip() == '':
            return False, "No title"
        
        return True, f"✓ Title: {title}, Year: {date_taken or 'N/A'}"
        
    except Exception as e:
        return False, f"Error: {e}"

def process_advisor(advisor_id, verify_only=False):
    """Process metadata for one advisor"""
    advisor_dir = ADVISOR_DIRS.get(advisor_id)
    if not advisor_dir:
        print(f"[ERROR] Unknown advisor: {advisor_id}")
        return False
    
    print(f"\n{'='*60}")
    print(f"Processing: {advisor_id.upper()}")
    print(f"{'='*60}")
    
    # Load metadata.yaml
    metadata_path = Path(advisor_dir) / "metadata.yaml"
    if not metadata_path.exists():
        print(f"[WARN] No metadata.yaml found at {metadata_path}")
        return False
    
    metadata_list = load_metadata_yaml(metadata_path)
    if not metadata_list:
        print(f"[WARN] No metadata entries found")
        return False
    
    print(f"[INFO] Loaded {len(metadata_list)} metadata entries")
    
    updated_count = 0
    verified_count = 0
    missing_count = 0
    
    for metadata in metadata_list:
        filename = metadata.get('filename')
        if not filename:
            continue
        
        # Construct absolute path
        image_path = str((Path(advisor_dir) / filename).resolve())
        
        # Check if file exists
        if not Path(image_path).exists():
            print(f"  [SKIP] File not found: {filename}")
            continue
        
        if verify_only:
            # Just verify
            success, message = verify_metadata(DB_PATH, image_path)
            if success:
                print(f"  [OK] {filename}: {message}")
                verified_count += 1
            else:
                print(f"  [MISSING] {filename}: {message}")
                missing_count += 1
        else:
            # Update metadata
            success = update_profile_metadata(DB_PATH, image_path, metadata)
            if success:
                print(f"  [UPDATED] {filename}: title='{metadata.get('title', 'N/A')}', year={metadata.get('date_taken', 'N/A')}")
                updated_count += 1
            else:
                print(f"  [SKIP] {filename}: No profile in database (run batch_analyze_advisor_images.py first)")
    
    # Summary
    print(f"\n{'='*60}")
    if verify_only:
        print(f"Verification Summary for {advisor_id}:")
        print(f"  ✓ Verified: {verified_count}")
        print(f"  ✗ Missing metadata: {missing_count}")
    else:
        print(f"Update Summary for {advisor_id}:")
        print(f"  Updated: {updated_count} profiles")
    print(f"{'='*60}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Populate image metadata from YAML to database")
    parser.add_argument("--advisor", type=str, default="ansel",
                        help="Advisor ID (ansel, okeefe, mondrian, gehry, vangogh, all)")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only verify metadata, don't update")
    args = parser.parse_args()
    
    print("=" * 60)
    print("IMAGE METADATA POPULATION TOOL")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Mode: {'VERIFY ONLY' if args.verify_only else 'UPDATE'}")
    
    if args.advisor == "all":
        for advisor_id in ADVISOR_DIRS.keys():
            process_advisor(advisor_id, verify_only=args.verify_only)
    else:
        process_advisor(args.advisor, verify_only=args.verify_only)
    
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
