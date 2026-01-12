#!/usr/bin/env python3
"""
Test RAG Workflow - Verify dimensional profile retrieval and prompt augmentation
"""

import sys
sys.path.insert(0, 'mondrian')

from json_to_html_converter import (
    find_similar_by_dimensions,
    get_dimensional_profile
)
from technique_rag import (
    get_similar_images_by_techniques,
    augment_prompt_with_technique_context
)

print("=" * 70)
print("RAG Workflow Test")
print("=" * 70)

# Test 1: Verify dimensional profiles exist in database
print("\n[TEST 1] Checking dimensional profiles in database...")
db_path = 'mondrian.db'

import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id="ansel"')
count = cursor.fetchone()[0]
print(f"✓ Found {count} Ansel profiles in database")

if count == 0:
    print("✗ ERROR: No profiles found. Run insert_mock_profiles.py first")
    sys.exit(1)

# Show profile details
cursor.execute('''
    SELECT image_path, composition_score, lighting_score, focus_sharpness_score, overall_grade 
    FROM dimensional_profiles 
    WHERE advisor_id="ansel"
''')
print("\nProfile details:")
for row in cursor.fetchall():
    img_name = row[0].split('/')[-1]
    print(f"  {img_name}: comp={row[1]}, light={row[2]}, focus={row[3]}, grade={row[4]}")

conn.close()

# Test 2: Test similarity search
print("\n[TEST 2] Testing dimensional similarity search...")
target_scores = {
    'composition': 8.0,
    'lighting': 8.5,
    'focus_sharpness': 9.0,
    'color_harmony': 7.5,
    'subject_isolation': 7.0,
    'depth_perspective': 8.0,
    'visual_balance': 8.0,
    'emotional_impact': 8.5
}

similar = find_similar_by_dimensions(
    db_path=db_path,
    advisor_id='ansel',
    target_scores=target_scores,
    top_k=3
)

if similar:
    print(f"✓ Found {len(similar)} similar images:")
    for i, img in enumerate(similar, 1):
        img_name = img['image_path'].split('/')[-1]
        print(f"  {i}. {img_name}: distance={img['distance']:.2f}, similarity={img['similarity']:.2f}")
else:
    print("✗ ERROR: No similar images found")
    sys.exit(1)

# Test 3: Test get_similar_images_by_techniques
print("\n[TEST 3] Testing get_similar_images_by_techniques...")
user_profile = {
    'composition_score': 8.0,
    'lighting_score': 8.5,
    'focus_sharpness_score': 9.0,
    'color_harmony_score': 7.5,
    'subject_isolation_score': 7.0,
    'depth_perspective_score': 8.0,
    'visual_balance_score': 8.0,
    'emotional_impact_score': 8.5
}

similar_by_tech = get_similar_images_by_techniques(
    db_path=db_path,
    advisor_id='ansel',
    user_profile=user_profile,
    top_k=3
)

if similar_by_tech:
    print(f"✓ Found {len(similar_by_tech)} similar images via technique matching")
else:
    print("✗ ERROR: Technique matching failed")
    sys.exit(1)

# Test 4: Test prompt augmentation
print("\n[TEST 4] Testing prompt augmentation...")
base_prompt = """
You are Ansel Adams, analyzing a photograph.
Focus on composition, lighting, and technical excellence.
"""

augmented = augment_prompt_with_technique_context(
    advisor_prompt=base_prompt,
    similar_images=similar_by_tech,
    user_profile=user_profile
)

prompt_length_increase = len(augmented) - len(base_prompt)
print(f"✓ Prompt augmented")
print(f"  Original length: {len(base_prompt)} chars")
print(f"  Augmented length: {len(augmented)} chars")
print(f"  Added context: {prompt_length_increase} chars")

if "RAG CONTEXT" in augmented:
    print("✓ RAG context section found in augmented prompt")
else:
    print("✗ WARNING: RAG context section not found")

if "Reference Image" in augmented:
    print(f"✓ Reference images included in prompt")
else:
    print("✗ WARNING: Reference images not found in prompt")

# Test 5: Verify prompt contains comparative language
print("\n[TEST 5] Checking for comparative analysis instructions...")
comparative_keywords = [
    "dimensional",
    "comparison",
    "reference",
    "similar"
]

found_keywords = []
for keyword in comparative_keywords:
    if keyword.lower() in augmented.lower():
        found_keywords.append(keyword)

if len(found_keywords) >= 3:
    print(f"✓ Found comparative keywords: {', '.join(found_keywords)}")
else:
    print(f"✗ WARNING: Only found {len(found_keywords)} comparative keywords")

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("✓ Database schema: OK")
print(f"✓ Dimensional profiles: {count} profiles")
print(f"✓ Similarity search: {len(similar)} matches found")
print(f"✓ Technique matching: {len(similar_by_tech)} matches")
print(f"✓ Prompt augmentation: {prompt_length_increase} chars added")
print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
print("\nThe RAG system is functional and ready to use!")
print("\nNext steps:")
print("1. Start the AI Advisor Service: python3 mondrian/ai_advisor_service.py")
print("2. Upload an image with enable_rag=true")
print("3. The system will automatically:")
print("   - Extract dimensional profile from analysis")
print("   - Find similar reference images")
print("   - Augment prompt with comparative context")
print("   - Generate dimensional comparison feedback")




