#!/usr/bin/env python3
"""
Diagnose why case studies are not appearing in output
"""
import sqlite3
import sys
sys.path.insert(0, '/home/doo/dev/mondrian-macos')

from mondrian.rag_retrieval import get_best_image_per_dimension, DB_PATH

print("="*70)
print("CASE STUDY DIAGNOSTIC")
print("="*70)

# 1. Check database has images
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id = 'ansel'")
total_images = cursor.fetchone()[0]
print(f"\n1. Total Ansel images in database: {total_images}")

cursor.execute("""
    SELECT COUNT(*) FROM dimensional_profiles 
    WHERE advisor_id = 'ansel' 
    AND (composition_score >= 8.0 OR lighting_score >= 8.0 OR focus_sharpness_score >= 8.0)
""")
high_scoring = cursor.fetchone()[0]
print(f"2. Images with scores >= 8.0 in any dimension: {high_scoring}")

# Check instructive text
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN composition_instructive IS NOT NULL AND composition_instructive != '' THEN 1 ELSE 0 END) as has_comp_inst,
        SUM(CASE WHEN lighting_instructive IS NOT NULL AND lighting_instructive != '' THEN 1 ELSE 0 END) as has_light_inst
    FROM dimensional_profiles 
    WHERE advisor_id = 'ansel'
""")
row = cursor.fetchone()
print(f"3. Images with instructive text: composition={row[1]}/{row[0]}, lighting={row[2]}/{row[0]}")

conn.close()

# 2. Test get_best_image_per_dimension
print("\n" + "="*70)
print("TESTING get_best_image_per_dimension()")
print("="*70)

result = get_best_image_per_dimension(DB_PATH, 'ansel', as_list=False)
print(f"\n4. Dict result keys: {list(result.keys()) if result else 'None/Empty'}")
if result:
    for dim, img in result.items():
        print(f"   - {dim}: {img.get('image_title', 'Unknown')}")

result_list = get_best_image_per_dimension(DB_PATH, 'ansel', as_list=True)
print(f"\n5. List result: {len(result_list) if result_list else 0} images")
if result_list:
    for i, img in enumerate(result_list, 1):
        title = img.get('image_title', 'Unknown')
        dims = []
        for dim in ['composition', 'lighting', 'focus_sharpness']:
            score = img.get(f'{dim}_score')
            if score and score >= 8.0:
                dims.append(f"{dim}={score:.1f}")
        print(f"   IMG_{i}: {title} - {', '.join(dims)}")

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)
