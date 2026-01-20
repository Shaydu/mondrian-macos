#!/usr/bin/env python3
"""
Add instructive text columns to dimensional_profiles table.

These columns store WHY each reference image is instructive for each dimension,
to be displayed when that image is shown as a case study.
"""

import sqlite3
import sys

DB_PATH = "mondrian.db"

def add_instructive_columns():
    """Add instructive text columns for each dimension"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Dimensions that need instructive text columns
    dimensions = [
        'composition',
        'lighting',
        'focus_sharpness',
        'color_harmony',
        'subject_isolation',
        'depth_perspective',
        'visual_balance',
        'emotional_impact'
    ]
    
    print("Adding instructive text columns to dimensional_profiles table...")
    
    for dim in dimensions:
        column_name = f"{dim}_instructive"
        try:
            cursor.execute(f"ALTER TABLE dimensional_profiles ADD COLUMN {column_name} TEXT")
            print(f"  ✓ Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  - Column already exists: {column_name}")
            else:
                print(f"  ✗ Error adding {column_name}: {e}")
                raise
    
    conn.commit()
    conn.close()
    
    print("\n✓ Migration complete!")
    print("\nNext steps:")
    print("  1. Generate instructive text for each high-scoring dimension of reference images")
    print("  2. Update HTML generator to use these fields instead of image_description")
    print("  3. Example instructive text:")
    print('     "Notice how the S-curve of the river creates a visual path from')
    print('      foreground to background, drawing your eye through zones of depth.')
    print('      This layering technique transforms a flat vista into an immersive')
    print('      scene. Try finding natural leading lines in your landscapes."')

if __name__ == '__main__':
    add_instructive_columns()
