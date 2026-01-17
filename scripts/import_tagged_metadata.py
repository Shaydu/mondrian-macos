#!/usr/bin/env python3
"""
Import curated metadata from YAML file and generate dimensional scores from tags.
Maps tags to dimensional scores for Ansel Adams reference images.

Usage:
    python scripts/import_tagged_metadata.py
"""

import yaml
import sqlite3
import os
from pathlib import Path

# Configuration
WORKSPACE_ROOT = Path(__file__).parent.parent
DB_PATH = WORKSPACE_ROOT / "mondrian.db"
METADATA_FILE = WORKSPACE_ROOT / "mondrian/source/advisor/photographer/ansel/metadata.yaml"
ANSEL_DIR = WORKSPACE_ROOT / "mondrian/source/advisor/photographer/ansel"

# Tag to dimensional score mapping
# Each tag contributes to one or more dimensions
TAG_SCORE_MAP = {
    # Composition-related tags
    "composition": {"composition_score": 10.0},
    "layered_depth": {"composition_score": 9.5, "depth_perspective_score": 9.5},
    "rule_of_thirds": {"composition_score": 9.0, "visual_balance_score": 9.0},
    "leading_lines": {"composition_score": 9.5, "depth_perspective_score": 9.0},
    "foreground_interest": {"composition_score": 9.0, "depth_perspective_score": 9.0},
    "pattern": {"composition_score": 9.0, "visual_balance_score": 8.5},
    "symmetry": {"visual_balance_score": 10.0, "composition_score": 9.0},
    "geometric": {"composition_score": 8.5, "visual_balance_score": 8.5},
    
    # Lighting-related tags
    "zone_system": {"lighting_score": 10.0, "color_harmony_score": 9.0},
    "dramatic_lighting": {"lighting_score": 10.0, "emotional_impact_score": 9.5},
    "high_contrast": {"lighting_score": 9.5, "color_harmony_score": 8.5},
    "tonal_range": {"lighting_score": 9.5, "color_harmony_score": 9.0},
    "soft_light": {"lighting_score": 8.5, "emotional_impact_score": 8.5},
    "shadows": {"lighting_score": 9.0, "composition_score": 8.5},
    "atmospheric": {"lighting_score": 8.5, "emotional_impact_score": 9.0},
    
    # Depth & Perspective tags
    "depth": {"depth_perspective_score": 9.5},
    "layers": {"depth_perspective_score": 9.5, "composition_score": 9.0},
    "perspective": {"depth_perspective_score": 9.0, "composition_score": 8.5},
    "reflection": {"visual_balance_score": 9.0, "composition_score": 8.5},
    
    # Focus & Sharpness tags
    "texture": {"focus_sharpness_score": 9.5, "composition_score": 8.0},
    "motion": {"focus_sharpness_score": 9.0},
    "long_exposure": {"focus_sharpness_score": 8.5},
    
    # Subject Isolation tags
    "isolation": {"subject_isolation_score": 10.0, "visual_balance_score": 9.0},
    "negative_space": {"subject_isolation_score": 9.5, "visual_balance_score": 9.0},
    "minimalist": {"subject_isolation_score": 9.0, "composition_score": 8.5},
    
    # Emotional Impact tags
    "emotional": {"emotional_impact_score": 10.0},
    "timing": {"emotional_impact_score": 9.0, "composition_score": 8.5},
    "mood": {"emotional_impact_score": 9.5},
    "dramatic": {"emotional_impact_score": 9.5, "lighting_score": 9.0},
    
    # Other tags with dimensional impacts
    "landscape": {"composition_score": 8.5, "depth_perspective_score": 8.5},
    "architecture": {"composition_score": 9.0, "visual_balance_score": 8.5},
    "abstract": {"composition_score": 8.5, "visual_balance_score": 8.0},
    "documentary": {"emotional_impact_score": 8.5, "composition_score": 8.0},
    "curves": {"composition_score": 9.0, "visual_balance_score": 8.5},
    "vertical_lines": {"composition_score": 8.5, "visual_balance_score": 8.5},
    "scale": {"depth_perspective_score": 8.5, "composition_score": 8.0},
    "human_element": {"emotional_impact_score": 8.5, "composition_score": 8.0},
    "clouds": {"composition_score": 8.5, "emotional_impact_score": 8.0},
    "sky": {"composition_score": 8.0, "lighting_score": 8.5},
    "water": {"composition_score": 8.0, "visual_balance_score": 8.0},
    "winter": {"lighting_score": 8.5, "color_harmony_score": 8.5},
    "forest": {"depth_perspective_score": 8.5, "emotional_impact_score": 8.0},
}

# Default scores for dimensions not affected by tags
DEFAULT_SCORES = {
    "composition_score": 8.0,
    "lighting_score": 8.0,
    "focus_sharpness_score": 9.0,  # Ansel's work is generally sharp
    "color_harmony_score": 8.0,
    "subject_isolation_score": 7.5,
    "depth_perspective_score": 8.0,
    "visual_balance_score": 8.0,
    "emotional_impact_score": 8.0
}


def calculate_scores_from_tags(tags):
    """Calculate dimensional scores based on image tags"""
    scores = DEFAULT_SCORES.copy()
    
    for tag in tags:
        if tag in TAG_SCORE_MAP:
            for dimension, score in TAG_SCORE_MAP[tag].items():
                # Take the maximum score for each dimension
                scores[dimension] = max(scores[dimension], score)
    
    return scores


def import_metadata():
    """Import metadata from YAML and populate database"""
    print("=" * 70)
    print("Importing Curated Ansel Adams Metadata")
    print("=" * 70)
    print(f"Metadata file: {METADATA_FILE}")
    print(f"Database: {DB_PATH}")
    print()
    
    # Check files exist
    if not METADATA_FILE.exists():
        print(f"[✗] Metadata file not found: {METADATA_FILE}")
        print("    Please create the metadata.yaml file first")
        return
    
    if not DB_PATH.exists():
        print(f"[✗] Database not found: {DB_PATH}")
        return
    
    # Load metadata
    print("[→] Loading metadata YAML...")
    with open(METADATA_FILE) as f:
        data = yaml.safe_load(f)
    
    images = data.get('images', [])
    print(f"[✓] Loaded {len(images)} image metadata entries")
    print()
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing ansel profiles
    print("[→] Clearing existing Ansel Adams profiles...")
    cursor.execute("DELETE FROM dimensional_profiles WHERE advisor_id = 'ansel'")
    print(f"[✓] Cleared {cursor.rowcount} existing profiles")
    print()
    
    # Import each image
    success_count = 0
    skip_count = 0
    
    for img in images:
        filename = img['filename']
        image_path = ANSEL_DIR / filename
        
        # Check if image file exists
        if not image_path.exists():
            print(f"[SKIP] {filename} - file not found")
            skip_count += 1
            continue
        
        # Calculate scores from tags
        tags = img.get('tags', [])
        scores = calculate_scores_from_tags(tags)
        
        # Insert into database
        cursor.execute("""
            INSERT INTO dimensional_profiles 
            (advisor_id, image_path, image_title, date_taken, image_description,
             composition_score, lighting_score, focus_sharpness_score, 
             color_harmony_score, subject_isolation_score, depth_perspective_score,
             visual_balance_score, emotional_impact_score, overall_grade)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'ansel',
            str(image_path),
            img['title'],
            img.get('year', ''),
            img.get('description', ''),
            scores['composition_score'],
            scores['lighting_score'],
            scores['focus_sharpness_score'],
            scores['color_harmony_score'],
            scores['subject_isolation_score'],
            scores['depth_perspective_score'],
            scores['visual_balance_score'],
            scores['emotional_impact_score'],
            'A+'  # All Ansel images are A+ grade
        ))
        
        print(f"[✓] {img['title']}")
        print(f"    Tags: {', '.join(tags[:3])}{'...' if len(tags) > 3 else ''}")
        print(f"    Scores: Comp={scores['composition_score']:.1f}, Light={scores['lighting_score']:.1f}, Depth={scores['depth_perspective_score']:.1f}")
        success_count += 1
    
    # Commit changes
    conn.commit()
    conn.close()
    
    # Summary
    print()
    print("=" * 70)
    print("Import Complete")
    print("=" * 70)
    print(f"Successfully imported: {success_count}")
    print(f"Skipped (not found): {skip_count}")
    print()
    print("Next steps:")
    print("  1. python scripts/compute_embeddings.py --advisor ansel")
    print("  2. python scripts/compute_embeddings.py --advisor ansel --verify-only")
    print()


if __name__ == "__main__":
    import_metadata()
