#!/usr/bin/env python3
"""
Database Migration: Add Technique-Based RAG Tables

Creates new tables for storing photographic techniques and their associations
with advisor images and user images.
"""

import sqlite3
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate_technique_schema(db_path="mondrian.db"):
    """
    Create technique-based RAG tables and populate with initial data.
    
    Args:
        db_path: Path to SQLite database
    """
    print(f"[INFO] Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Create photographer_techniques table
    print("[INFO] Creating photographer_techniques table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photographer_techniques (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            detection_criteria TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 2. Create advisor_image_techniques table
    print("[INFO] Creating advisor_image_techniques table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advisor_image_techniques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            advisor_id TEXT NOT NULL,
            image_path TEXT NOT NULL,
            technique_id TEXT NOT NULL,
            strength TEXT NOT NULL CHECK(strength IN ('strong', 'moderate', 'subtle')),
            evidence TEXT,
            example_region TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (advisor_id) REFERENCES advisors(id) ON DELETE CASCADE,
            FOREIGN KEY (technique_id) REFERENCES photographer_techniques(id) ON DELETE CASCADE
        )
    """)
    
    # 3. Create user_image_techniques table
    print("[INFO] Creating user_image_techniques table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_image_techniques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            image_path TEXT NOT NULL,
            technique_id TEXT NOT NULL,
            confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
            evidence TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            FOREIGN KEY (technique_id) REFERENCES photographer_techniques(id) ON DELETE CASCADE
        )
    """)
    
    # 4. Add techniques_json column to dimensional_profiles (if exists)
    print("[INFO] Adding techniques_json column to dimensional_profiles...")
    try:
        cursor.execute("""
            ALTER TABLE dimensional_profiles ADD COLUMN techniques_json TEXT
        """)
        print("[OK] Added techniques_json column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("[INFO] techniques_json column already exists")
        elif "no such table" in str(e).lower():
            print("[INFO] dimensional_profiles table doesn't exist yet (will be created later)")
        else:
            raise
    
    # 5. Create indexes for performance
    print("[INFO] Creating indexes...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_advisor_image_techniques_advisor 
        ON advisor_image_techniques(advisor_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_advisor_image_techniques_technique 
        ON advisor_image_techniques(technique_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_advisor_image_techniques_image 
        ON advisor_image_techniques(image_path)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_image_techniques_job 
        ON user_image_techniques(job_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_image_techniques_technique 
        ON user_image_techniques(technique_id)
    """)
    
    # 6. Populate photographer_techniques with Ansel Adams techniques
    print("[INFO] Populating photographer_techniques...")
    
    ansel_techniques = [
        # Composition Techniques
        {
            "id": "foreground_anchoring",
            "name": "Foreground Anchoring with Natural Elements",
            "category": "Composition",
            "description": "Strong foreground element (rocks, plants, structures) in lower third that establishes scale and depth, leading eye into the scene",
            "detection_criteria": "Look for: prominent element in bottom 30% of frame, sharp focus, creates depth/scale relationship with background"
        },
        {
            "id": "deep_dof_landscape",
            "name": "Deep Depth of Field for Landscape Sharpness",
            "category": "Technical",
            "description": "Front-to-back sharpness throughout the frame, characteristic of f/64 Group approach",
            "detection_criteria": "Look for: sharp focus from foreground to infinity, no selective focus, everything in frame is crisp"
        },
        {
            "id": "rule_of_thirds_horizon",
            "name": "Rule of Thirds Horizon Placement",
            "category": "Composition",
            "description": "Horizon line positioned at upper or lower third rather than center, creating dynamic balance",
            "detection_criteria": "Look for: horizon at ~33% or ~66% height, not centered, emphasizes either sky or land"
        },
        {
            "id": "leading_lines_natural",
            "name": "Leading Lines through Natural Formations",
            "category": "Composition",
            "description": "Rivers, ridges, tree lines, or geological features that guide the eye through the composition",
            "detection_criteria": "Look for: diagonal or curved lines from foreground to background, natural elements creating visual flow"
        },
        {
            "id": "triangular_composition",
            "name": "Triangular Composition",
            "category": "Composition",
            "description": "Arrangement of elements forming triangular shapes, creating stability and visual interest",
            "detection_criteria": "Look for: three main elements forming triangle, mountain peaks, converging lines creating triangular space"
        },
        
        # Lighting Techniques
        {
            "id": "zone_system_tonal_range",
            "name": "Zone System Dramatic Tonal Range",
            "category": "Lighting",
            "description": "Full spectrum from pure black (Zone 0) to pure white (Zone X), with rich midtones throughout",
            "detection_criteria": "Look for: deep blacks, bright whites, rich gradation of grays between, no clipped highlights/shadows"
        },
        {
            "id": "high_contrast_lighting",
            "name": "High Contrast Lighting (Zones II-IX)",
            "category": "Lighting",
            "description": "Strong separation between light and dark areas, dramatic tonal differences",
            "detection_criteria": "Look for: significant brightness differences, dark shadows with detail, bright highlights with detail"
        },
        {
            "id": "sidelight_texture",
            "name": "Sidelight for Texture Enhancement",
            "category": "Lighting",
            "description": "Light from the side revealing surface texture, dimension, and form",
            "detection_criteria": "Look for: visible texture in rocks/bark/surfaces, shadows revealing form, light raking across subject"
        },
        {
            "id": "golden_hour_warmth",
            "name": "Golden Hour Warmth",
            "category": "Lighting",
            "description": "Warm, directional light from sunrise or sunset creating long shadows and warm tones",
            "detection_criteria": "Look for: warm color temperature, long shadows, low angle light, enhanced texture"
        },
        {
            "id": "overcast_diffusion",
            "name": "Overcast Diffusion for Even Tones",
            "category": "Lighting",
            "description": "Soft, even lighting from overcast skies reducing harsh shadows",
            "detection_criteria": "Look for: minimal shadows, even exposure, soft gradations, no harsh highlights"
        },
        
        # Technical Approaches
        {
            "id": "f64_sharpness",
            "name": "f/64 Group Sharpness Throughout Frame",
            "category": "Technical",
            "description": "Maximum sharpness achieved through small aperture (f/64), characteristic of large format photography",
            "detection_criteria": "Look for: extreme depth of field, sharp foreground and background, no bokeh, everything in focus"
        },
        {
            "id": "large_format_precision",
            "name": "Large Format Camera Precision",
            "category": "Technical",
            "description": "Meticulous composition and exposure planning characteristic of large format view cameras",
            "detection_criteria": "Look for: precise alignment, corrected perspective, no distortion, deliberate composition"
        },
        {
            "id": "pre_visualization",
            "name": "Pre-visualization and Exposure Planning",
            "category": "Technical",
            "description": "Careful planning of final image appearance before capture, including tonal relationships",
            "detection_criteria": "Look for: intentional tonal placement, balanced exposure, no accidents, everything serves composition"
        },
        
        # Post-Processing Techniques
        {
            "id": "dodging_burning",
            "name": "Dodging and Burning for Tonal Control",
            "category": "Post-Processing",
            "description": "Selective lightening (dodging) and darkening (burning) to enhance composition and guide attention",
            "detection_criteria": "Look for: selectively brightened areas, darkened edges/corners, enhanced local contrast, guided eye movement"
        },
        {
            "id": "sky_enhancement",
            "name": "Dramatic Sky Enhancement",
            "category": "Post-Processing",
            "description": "Enhanced cloud detail and sky drama through filtration or darkroom techniques",
            "detection_criteria": "Look for: rich cloud detail, dramatic sky tones, separation between sky and land, enhanced contrast in clouds"
        }
    ]
    
    for tech in ansel_techniques:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO photographer_techniques 
                (id, name, category, description, detection_criteria)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tech["id"],
                tech["name"],
                tech["category"],
                tech["description"],
                tech["detection_criteria"]
            ))
            print(f"[OK] Added technique: {tech['name']}")
        except Exception as e:
            print(f"[ERROR] Failed to add technique {tech['id']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n[SUCCESS] Migration complete!")
    print(f"[INFO] Created {len(ansel_techniques)} Ansel Adams techniques")
    print(f"\n[NEXT STEPS]")
    print(f"1. Run: python3 scripts/index_advisor_techniques.py --advisor ansel")
    print(f"2. This will analyze all Ansel Adams images and tag them with techniques")


def verify_migration(db_path="mondrian.db"):
    """Verify migration was successful"""
    print(f"\n[INFO] Verifying migration...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name IN ('photographer_techniques', 'advisor_image_techniques', 'user_image_techniques')
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"[INFO] Tables created: {', '.join(tables)}")
    
    # Count techniques
    cursor.execute("SELECT COUNT(*) FROM photographer_techniques")
    tech_count = cursor.fetchone()[0]
    print(f"[INFO] Techniques populated: {tech_count}")
    
    # Show technique categories
    cursor.execute("""
        SELECT category, COUNT(*) 
        FROM photographer_techniques 
        GROUP BY category
    """)
    categories = cursor.fetchall()
    print(f"[INFO] Technique breakdown:")
    for cat, count in categories:
        print(f"  - {cat}: {count}")
    
    conn.close()
    
    if len(tables) == 3 and tech_count > 0:
        print(f"\n[SUCCESS] Migration verified successfully!")
        return True
    else:
        print(f"\n[ERROR] Migration verification failed")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate database to technique-based RAG schema")
    parser.add_argument("--db", type=str, default="mondrian.db", help="Database path")
    parser.add_argument("--verify-only", action="store_true", help="Only verify migration, don't run it")
    args = parser.parse_args()
    
    if args.verify_only:
        verify_migration(args.db)
    else:
        migrate_technique_schema(args.db)
        verify_migration(args.db)

