#!/usr/bin/env python3
"""
Quick test to verify image path resolution works
"""
import os
import sqlite3

# Check what image paths are actually stored in the database
db_path = "mondrian.db"

print("=" * 70)
print("Testing Image Path Resolution")
print("=" * 70)

# Get some sample image paths from database
conn = sqlite3.connect(db_path)
cursor = conn.execute("""
    SELECT image_title, image_path, date_taken 
    FROM advisor_images 
    WHERE advisor = 'ansel' 
    LIMIT 5
""")

results = cursor.fetchall()
conn.close()

print(f"\nFound {len(results)} sample images in database:")
print()

for title, path, year in results:
    print(f"Image: {title} ({year})")
    print(f"  DB Path: {path}")
    
    # Test path resolution logic (same as in html_generator.py)
    possible_paths = [
        path,  # Try as-is first
    ]
    
    # If it's a relative path, try common base directories
    if not os.path.isabs(path):
        base_dirs = [
            os.getcwd(),
            '/home/doo/dev/mondrian-macos',
            '/app',  # Docker container path
        ]
        for base_dir in base_dirs:
            possible_paths.append(os.path.join(base_dir, path))
    
    resolved_path = None
    for test_path in possible_paths:
        if os.path.exists(test_path) and os.path.isfile(test_path):
            resolved_path = test_path
            break
    
    if resolved_path:
        size = os.path.getsize(resolved_path)
        print(f"  ✓ FOUND: {resolved_path} ({size:,} bytes)")
    else:
        print(f"  ✗ NOT FOUND - tried {len(possible_paths)} locations:")
        for i, p in enumerate(possible_paths, 1):
            exists = "EXISTS" if os.path.exists(p) else "missing"
            print(f"    {i}. {p} [{exists}]")
    print()

print("=" * 70)
print("Test complete!")
print("=" * 70)
