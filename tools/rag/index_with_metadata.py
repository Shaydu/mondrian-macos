#!/usr/bin/env python3
"""
Index Advisor Images with Rich Metadata

This script:
1. Loads metadata from metadata.yaml (title, description, significance, techniques)
2. Analyzes each image using the AI Advisor Service  
3. Extracts dimensional profiles from the analysis
4. Stores profiles WITH metadata in the database for RAG queries

The metadata allows the LLM to reference actual artwork titles and significance
instead of meaningless filenames like "2.jpg"

Usage:
    python3 tools/rag/index_with_metadata.py --advisor ansel --metadata-file mondrian/source/advisor/photographer/ansel/metadata.yaml
"""

import os
import sys
import requests
import time
import yaml
from pathlib import Path
import argparse

# Add mondrian to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mondrian'))

from json_to_html_converter import (
    parse_json_response,
    extract_dimensional_profile_from_json,
    save_dimensional_profile,
    get_dimensional_profile
)
import sqlite3

# Configuration
AI_ADVISOR_URL = "http://localhost:5100/analyze"
IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}


def load_metadata(metadata_file):
    """Load metadata from YAML file."""
    with open(metadata_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Index by filename for quick lookup
    metadata_dict = {}
    for img in data.get('images', []):
        filename = img.get('filename')
        if filename:
            metadata_dict[filename] = img
    
    return metadata_dict


def analyze_image_with_metadata(image_path, advisor_id, metadata, db_path):
    """
    Analyze image and save dimensional profile with metadata.
    
    Args:
        image_path: Path to image file
        advisor_id: Advisor ID (e.g., 'ansel')
        metadata: Dict with title, description, significance, etc.
        db_path: Path to database
        
    Returns:
        True if successful, False otherwise
    """
    try:
        abs_path = str(Path(image_path).resolve())
        filename = os.path.basename(image_path)
        
        # Get metadata for this image
        img_metadata = metadata.get(filename, {})
        title = img_metadata.get('title', filename)
        
        print(f"  [→] Analyzing '{title}'...")
        
        # Send to AI service for analysis
        data = {
            "advisor": advisor_id,
            "image_path": abs_path,
            "enable_rag": "false"  # Don't use RAG for reference images
        }
        
        response = requests.post(
            AI_ADVISOR_URL,
            json=data,
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"  [✗] Analysis failed: {response.status_code}")
            print(f"      Response: {response.text[:200]}")
            return False
        
        print(f"  [✓] Analysis complete - waiting for profile to be saved...")
        
        # The AI service automatically saves dimensional profiles when analyzing
        # Wait a moment for the database write to complete, then retrieve and update with metadata
        time.sleep(1)
        
        # Get the saved profile from database
        saved_profile = get_dimensional_profile(
            db_path=db_path,
            image_path=abs_path,
            advisor_id=advisor_id
        )
        
        if not saved_profile:
            print(f"  [✗] Profile not found in database after analysis")
            print(f"      This might mean the analysis didn't save properly")
            return False
        
        print(f"  [✓] Retrieved profile from database")
        
        # Merge metadata from YAML into the saved profile
        # Keep all the dimensional scores and comments from analysis
        # Add/update metadata fields from YAML
        profile_data = dict(saved_profile)  # Start with saved profile
        
        # Update with metadata from YAML (only if not already set or if YAML has better data)
        if img_metadata.get('title'):
            profile_data['image_title'] = img_metadata.get('title')
        if img_metadata.get('date_taken'):
            profile_data['date_taken'] = img_metadata.get('date_taken')
        if img_metadata.get('location'):
            profile_data['location'] = img_metadata.get('location')
        if img_metadata.get('significance'):
            profile_data['image_significance'] = img_metadata.get('significance')
        if img_metadata.get('description'):
            # Use description as image_description if not already set
            if not profile_data.get('image_description'):
                profile_data['image_description'] = img_metadata.get('description')
        
        # Handle techniques - merge if both exist
        yaml_techniques = img_metadata.get('techniques', [])
        if yaml_techniques:
            # If saved profile has techniques, keep them (they're from analysis)
            # Otherwise use YAML techniques
            if not profile_data.get('techniques'):
                profile_data['techniques'] = yaml_techniques
        
        # Update the profile with merged metadata
        profile_id = save_dimensional_profile(
            db_path=db_path,
            advisor_id=advisor_id,
            image_path=abs_path,
            profile_data=profile_data,
            job_id=None
        )
        
        if profile_id:
            print(f"  [✓] Updated with metadata: '{title}' ({img_metadata.get('date_taken', 'no date')})")
            return True
        else:
            print(f"  [✗] Failed to update profile with metadata")
            return False
        
    except requests.exceptions.Timeout:
        print(f"  [✗] Timeout")
        return False
    except Exception as e:
        print(f"  [✗] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Index advisor images with metadata")
    parser.add_argument('--advisor', type=str, required=True, help='Advisor ID (e.g., ansel)')
    parser.add_argument('--metadata-file', type=str, required=True, help='Path to metadata.yaml')
    parser.add_argument('--image-dir', type=str, help='Override image directory')
    parser.add_argument('--db', type=str, help='Database path (default: mondrian/mondrian.db)')
    args = parser.parse_args()
    
    # Determine database path
    if args.db:
        db_path = os.path.abspath(args.db)
    else:
        # Default to mondrian/mondrian.db relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, '..', '..', 'mondrian', 'mondrian.db')
        db_path = os.path.abspath(db_path)
    
    if not os.path.exists(db_path):
        print(f"[✗] Database not found: {db_path}")
        sys.exit(1)
    
    print("=" * 70)
    print(f"Indexing {args.advisor.title()} Images with Metadata")
    print("=" * 70)
    print(f"Database: {db_path}")
    
    # Load metadata
    if not os.path.exists(args.metadata_file):
        print(f"[✗] Metadata file not found: {args.metadata_file}")
        sys.exit(1)
    
    print(f"Loading metadata from: {args.metadata_file}")
    metadata = load_metadata(args.metadata_file)
    print(f"[✓] Loaded metadata for {len(metadata)} images")
    print()
    
    # Determine image directory
    if args.image_dir:
        image_dir = Path(args.image_dir)
    else:
        # Default: same directory as metadata file
        image_dir = Path(args.metadata_file).parent
    
    if not image_dir.exists():
        print(f"[✗] Image directory not found: {image_dir}")
        sys.exit(1)
    
    print(f"Image directory: {image_dir}")
    print()
    
    # Check if AI service is running
    try:
        health_resp = requests.get("http://localhost:5100/health", timeout=5)
        if health_resp.status_code == 200:
            print(f"[✓] AI Advisor Service is running")
        else:
            print(f"[✗] AI service health check failed")
            sys.exit(1)
    except Exception as e:
        print(f"[✗] Cannot connect to AI service: {e}")
        print(f"    Start it with: python3 mondrian/ai_advisor_service.py --port 5100")
        sys.exit(1)
    
    print()
    
    # Find images that have metadata
    images_to_process = []
    for filename in metadata.keys():
        img_path = image_dir / filename
        if img_path.exists():
            images_to_process.append(img_path)
        else:
            print(f"[WARN] Image not found: {filename}")
    
    if not images_to_process:
        print(f"[✗] No images found with metadata")
        print(f"    Images in metadata: {list(metadata.keys())}")
        print(f"    Directory contents: {[f.name for f in image_dir.glob('*') if f.is_file()]}")
        sys.exit(1)
    
    print(f"Found {len(images_to_process)} images to index")
    print()
    
    # Process each image
    success_count = 0
    fail_count = 0
    
    for i, image_path in enumerate(images_to_process, 1):
        print(f"[{i}/{len(images_to_process)}] {image_path.name}")
        
        if analyze_image_with_metadata(image_path, args.advisor, metadata, db_path):
            success_count += 1
        else:
            fail_count += 1
        
        # Small delay
        if i < len(images_to_process):
            time.sleep(2)
        
        print()
    
    # Summary
    print("=" * 70)
    print("Indexing Complete")
    print("=" * 70)
    print(f"Total images: {len(images_to_process)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print()
    
    if success_count > 0:
        print(f"[✓] {success_count} profiles saved with metadata")
        print(f"    Now when RAG retrieves these images, the LLM will see:")
        print(f"    - Artwork title (not filename)")
        print(f"    - Historical significance")
        print(f"    - Location and date")
        print(f"    - Technical techniques used")
        print()
        print(f"    Enable RAG with: enable_rag=true")
    else:
        print(f"[✗] No images were successfully indexed")


if __name__ == "__main__":
    main()




