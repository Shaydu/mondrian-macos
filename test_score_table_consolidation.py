#!/usr/bin/env python3
"""
Test script to verify that dimensional score tables are shown once 
below all reference images, not repeated for each image.
"""

import sys
import os
import re

# Add mondrian to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mondrian'))

from json_to_html_converter import json_to_html

# Sample JSON analysis data with user's dimensional scores
sample_json = {
    "image_description": "A landscape photograph showing mountains and a river.",
    "dimensions": [
        {
            "name": "Composition",
            "score": 7.5,
            "comment": "Good use of rule of thirds with the river as a leading line.",
            "recommendation": "Consider adding a stronger foreground element for depth."
        },
        {
            "name": "Lighting",
            "score": 8.0,
            "comment": "Nice golden hour light with warm tones.",
            "recommendation": "Expose for highlights to preserve detail in bright areas."
        },
        {
            "name": "Focus & Sharpness",
            "score": 8.5,
            "comment": "Sharp focus throughout the image.",
            "recommendation": "Maintain this level of sharpness."
        },
        {
            "name": "Color Harmony",
            "score": 7.0,
            "comment": "Good color palette.",
            "recommendation": "Enhance color saturation."
        }
    ],
    "overall_score": 7.8,
    "technical_notes": "Well-composed landscape with room for improvement in foreground interest."
}

# Sample similar images from RAG (reference images all scored at 10.0)
sample_similar_images = [
    {
        'dimensional_profile': {
            'image_path': '/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/1.jpg',
            'image_title': 'The Tetons and the Snake River',
            'date_taken': '1942',
            'location': 'Grand Teton National Park, Wyoming',
            'image_significance': 'One of Ansel Adams\' most famous photographs.',
            'composition_score': 10.0,
            'lighting_score': 10.0,
            'focus_sharpness_score': 10.0,
            'color_harmony_score': 10.0,
            'subject_isolation_score': 10.0,
            'depth_perspective_score': 10.0,
            'visual_balance_score': 10.0,
            'emotional_impact_score': 10.0
        },
        'distance': 1.2
    },
    {
        'dimensional_profile': {
            'image_path': '/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/2.jpg',
            'image_title': 'Clearing Winter Storm, Yosemite',
            'date_taken': '1944',
            'location': 'Yosemite National Park, California',
            'image_significance': 'Demonstrates Adams\' mastery of dramatic lighting.',
            'composition_score': 10.0,
            'lighting_score': 10.0,
            'focus_sharpness_score': 10.0,
            'color_harmony_score': 10.0,
            'subject_isolation_score': 10.0,
            'depth_perspective_score': 10.0,
            'visual_balance_score': 10.0,
            'emotional_impact_score': 10.0
        },
        'distance': 1.5
    },
    {
        'dimensional_profile': {
            'image_path': '/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/3.jpg',
            'image_title': 'The Mist, Yosemite Valley',
            'date_taken': '1946',
            'location': 'Yosemite National Park, California',
            'image_significance': 'Classic example of Zone System application.',
            'composition_score': 10.0,
            'lighting_score': 10.0,
            'focus_sharpness_score': 10.0,
            'color_harmony_score': 10.0,
            'subject_isolation_score': 10.0,
            'depth_perspective_score': 10.0,
            'visual_balance_score': 10.0,
            'emotional_impact_score': 10.0
        },
        'distance': 1.8
    }
]

def test_no_per_image_score_tables():
    """Test that dimensional score tables are NOT repeated for each reference image."""
    print("=" * 70)
    print("TEST 1: Verify no per-image score tables")
    print("=" * 70)
    
    base_url = "http://localhost:5100"
    html = json_to_html(sample_json, similar_images=sample_similar_images, base_url=base_url, advisor_name="Ansel Adams")
    
    # Count occurrences of "How your image compares" in the HTML
    # This should NOT appear in the gallery items anymore
    pattern = r'<strong[^>]*>How your image compares:</strong>'
    matches = re.findall(pattern, html)
    
    print(f"Found {len(matches)} occurrences of 'How your image compares'")
    
    # With the fix, it should appear 0 times in the reference gallery section
    # (The advisor analysis section won't have it either)
    if len(matches) == 0:
        print("✓ PASS: 'How your image compares' does not appear in per-image sections")
    else:
        print(f"✗ FAIL: Found {len(matches)} occurrences of 'How your image compares' (expected 0)")
        return False
    
    return True


def test_single_score_summary():
    """Test that user's scores appear once in a summary table below all images."""
    print("\n" + "=" * 70)
    print("TEST 2: Verify single score summary exists")
    print("=" * 70)
    
    base_url = "http://localhost:5100"
    html = json_to_html(sample_json, similar_images=sample_similar_images, base_url=base_url, advisor_name="Ansel Adams")
    
    # Look for the "Your Image's Dimensional Scores" section
    if "Your Image's Dimensional Scores" in html:
        print("✓ PASS: Found 'Your Image's Dimensional Scores' section")
    else:
        print("✗ FAIL: 'Your Image's Dimensional Scores' section not found")
        return False
    
    # Verify user scores are displayed in the summary
    if "Composition: 7.5" in html:
        print("✓ PASS: User's Composition score (7.5) appears in summary")
    else:
        print("✗ FAIL: User's Composition score not found")
        return False
    
    if "Lighting: 8.0" in html:
        print("✓ PASS: User's Lighting score (8.0) appears in summary")
    else:
        print("✗ FAIL: User's Lighting score not found")
        return False
    
    if "Focus & Sharpness: 8.5" in html:
        print("✓ PASS: User's Focus & Sharpness score (8.5) appears in summary")
    else:
        print("✗ FAIL: User's Focus & Sharpness score not found")
        return False
    
    return True


def test_reference_images_still_displayed():
    """Test that reference images are still displayed with metadata and techniques."""
    print("\n" + "=" * 70)
    print("TEST 3: Verify reference images are still fully displayed")
    print("=" * 70)
    
    base_url = "http://localhost:5100"
    html = json_to_html(sample_json, similar_images=sample_similar_images, base_url=base_url, advisor_name="Ansel Adams")
    
    # Check for Reference Images Gallery section
    if "Reference Images Gallery" in html:
        print("✓ PASS: Reference Images Gallery section exists")
    else:
        print("✗ FAIL: Reference Images Gallery section not found")
        return False
    
    # Check for reference image titles
    if "The Tetons and the Snake River" in html:
        print("✓ PASS: Reference image #1 title appears")
    else:
        print("✗ FAIL: Reference image #1 title not found")
        return False
    
    if "Clearing Winter Storm" in html:
        print("✓ PASS: Reference image #2 title appears")
    else:
        print("✗ FAIL: Reference image #2 title not found")
        return False
    
    # Check for metadata
    if "1942" in html and "Grand Teton National Park" in html:
        print("✓ PASS: Reference image metadata appears")
    else:
        print("✗ FAIL: Reference image metadata not found")
        return False
    
    # Check for significance
    if "Significance:" in html:
        print("✓ PASS: Reference image significance section exists")
    else:
        print("✗ FAIL: Reference image significance not found")
        return False
    
    return True


def test_output_file():
    """Save HTML to file for manual inspection."""
    print("\n" + "=" * 70)
    print("TEST 4: Save HTML output for manual inspection")
    print("=" * 70)
    
    base_url = "http://localhost:5100"
    html = json_to_html(sample_json, similar_images=sample_similar_images, base_url=base_url, advisor_name="Ansel Adams")
    
    output_path = "test_score_table_consolidation_output.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Score Table Consolidation Test</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; max-width: 900px; margin: 0 auto; background: #1a1a1a; color: #e0e0e0; }
        h1 { color: #4a9eff; border-bottom: 2px solid #4a9eff; padding-bottom: 10px; }
        h2 { color: #66b3ff; margin-top: 30px; }
        h3 { color: #a0d4ff; }
        .note { background: #2a3a4a; padding: 15px; margin: 20px 0; border-left: 4px solid #4a9eff; border-radius: 4px; }
        img { max-width: 100%; height: auto; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
<h1>Score Table Consolidation Test Output</h1>
<div class="note">
    <strong>Test Objective:</strong>
    <p>Verify that dimensional score tables are shown ONCE below all reference images, not repeated for each image.</p>
    <p><strong>Expected:</strong> You should see the reference images displayed, and then a single "Your Image's Dimensional Scores" section showing the user's scores (Composition: 7.5, Lighting: 8.0, etc.)</p>
    <p><strong>Not Expected:</strong> You should NOT see "How your image compares" repeated under each reference image.</p>
</div>
""")
        f.write(html)
        f.write("""
</body>
</html>
""")
    
    print(f"✓ HTML output saved to: {output_path}")
    print(f"  Open in browser to visually inspect the output")
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Score Table Consolidation Test Suite")
    print("=" * 70)
    print()
    
    all_passed = True
    
    try:
        all_passed &= test_no_per_image_score_tables()
        all_passed &= test_single_score_summary()
        all_passed &= test_reference_images_still_displayed()
        all_passed &= test_output_file()
        
        print("\n" + "=" * 70)
        if all_passed:
            print("ALL TESTS PASSED! ✓")
        else:
            print("SOME TESTS FAILED! ✗")
        print("=" * 70)
        print()
        
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
