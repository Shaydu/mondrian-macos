#!/usr/bin/env python3
"""
Test script to verify RAG reference images appear in HTML output.

This tests the new feature that displays actual reference images
(not just filenames) in the HTML analysis output.
"""

import sys
import os

# Add mondrian to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mondrian'))

from json_to_html_converter import json_to_html

# Sample JSON analysis data
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
        }
    ],
    "overall_score": 7.8,
    "technical_notes": "Well-composed landscape with room for improvement in foreground interest."
}

# Sample similar images from RAG (simulating what technique_rag.py returns)
sample_similar_images = [
    {
        'dimensional_profile': {
            'image_path': '/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/1.jpg',
            'image_title': 'The Tetons and the Snake River',
            'date_taken': '1942',
            'location': 'Grand Teton National Park, Wyoming',
            'image_significance': 'One of Ansel Adams\' most famous photographs, selected for the Voyager Golden Record.',
            'composition_score': 9.5,
            'lighting_score': 9.0,
            'focus_sharpness_score': 9.5,
            'emotional_impact_score': 9.0
        },
        'distance': 1.2
    },
    {
        'dimensional_profile': {
            'image_path': '/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/2.jpg',
            'image_title': 'Clearing Winter Storm, Yosemite',
            'date_taken': '1944',
            'location': 'Yosemite National Park, California',
            'image_significance': 'Demonstrates Adams\' mastery of dramatic lighting and the Zone System.',
            'composition_score': 9.0,
            'lighting_score': 9.5,
            'focus_sharpness_score': 9.0,
            'emotional_impact_score': 9.5
        },
        'distance': 1.5
    }
]

def test_html_without_rag():
    """Test HTML generation without RAG references."""
    print("=" * 70)
    print("TEST 1: HTML Output WITHOUT RAG References")
    print("=" * 70)
    
    html = json_to_html(sample_json)
    
    # Check that basic elements are present
    assert '<div class="analysis">' in html
    assert 'Composition' in html
    assert '7.5' in html
    assert 'Lighting' in html
    assert '8.0' in html
    assert 'Overall Grade' in html
    assert '7.8' in html
    
    # Check that RAG section is NOT present
    assert 'Reference Images' not in html
    assert 'Reference #1' not in html
    
    print("✓ Basic HTML structure correct")
    print("✓ No RAG references (as expected)")
    print(f"✓ HTML length: {len(html)} characters")
    print()


def test_html_with_rag():
    """Test HTML generation WITH RAG references."""
    print("=" * 70)
    print("TEST 2: HTML Output WITH RAG References")
    print("=" * 70)
    
    base_url = "http://localhost:5100"
    html = json_to_html(sample_json, similar_images=sample_similar_images, base_url=base_url)
    
    # Check that RAG section is present
    assert 'Reference Images from Master' in html, "RAG section header missing"
    assert 'Reference #1' in html, "Reference #1 missing"
    assert 'Reference #2' in html, "Reference #2 missing"
    
    # Check that image titles are displayed
    assert 'The Tetons and the Snake River' in html, "Image title #1 missing"
    assert 'Clearing Winter Storm' in html, "Image title #2 missing"
    
    # Check that metadata is displayed
    assert '1942' in html, "Date missing"
    assert 'Grand Teton National Park' in html, "Location missing"
    assert 'Voyager Golden Record' in html, "Significance missing"
    
    # Check that similarity scores are displayed
    assert 'Similarity:' in html, "Similarity label missing"
    
    # Check that image URLs are generated
    assert 'http://localhost:5100/advisor_image/ansel/1.jpg' in html, "Image URL #1 missing"
    assert 'http://localhost:5100/advisor_image/ansel/2.jpg' in html, "Image URL #2 missing"
    
    # Check that <img> tags are present
    assert '<img src=' in html, "Image tags missing"
    assert 'alt="The Tetons and the Snake River"' in html, "Image alt text missing"
    
    # Check that dimensional scores are displayed
    assert 'Composition: 9.5/10' in html, "Composition score missing"
    assert 'Lighting: 9.0/10' in html or 'Lighting: 9.5/10' in html, "Lighting score missing"
    
    print("✓ RAG section present")
    print("✓ Reference images included")
    print("✓ Image titles displayed")
    print("✓ Metadata (dates, locations) displayed")
    print("✓ Historical significance displayed")
    print("✓ Similarity scores displayed")
    print("✓ Image URLs generated correctly")
    print("✓ <img> tags with proper src and alt attributes")
    print("✓ Dimensional scores displayed")
    print(f"✓ HTML length: {len(html)} characters")
    print()
    
    # Save sample HTML for visual inspection
    output_path = "test_rag_output.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        # Add basic HTML wrapper for viewing in browser
        f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>RAG HTML Test Output</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }
        h2 { color: #333; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }
        h3 { color: #0066cc; }
        .feedback-card { background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 8px; }
        .dimension-score { color: #0066cc; font-weight: bold; }
        .feedback-recommendation { background: #e3f2fd; padding: 10px; margin-top: 10px; border-radius: 4px; }
    </style>
</head>
<body>
""")
        f.write(html)
        f.write("""
</body>
</html>
""")
    
    print(f"✓ Sample HTML saved to: {output_path}")
    print(f"  Open in browser to visually inspect the output")
    print()


def test_edge_cases():
    """Test edge cases."""
    print("=" * 70)
    print("TEST 3: Edge Cases")
    print("=" * 70)
    
    # Test with empty similar_images list
    html = json_to_html(sample_json, similar_images=[], base_url="http://localhost:5100")
    assert 'Reference Images' not in html
    print("✓ Empty similar_images list handled correctly")
    
    # Test with None similar_images
    html = json_to_html(sample_json, similar_images=None, base_url="http://localhost:5100")
    assert 'Reference Images' not in html
    print("✓ None similar_images handled correctly")
    
    # Test with missing metadata
    minimal_similar = [{
        'dimensional_profile': {
            'image_path': '/path/to/image.jpg',
            'composition_score': 8.0
        },
        'distance': 1.0
    }]
    html = json_to_html(sample_json, similar_images=minimal_similar, base_url="http://localhost:5100")
    assert 'Reference #1' in html
    print("✓ Missing metadata handled gracefully")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RAG HTML Display Test Suite")
    print("=" * 70)
    print()
    
    try:
        test_html_without_rag()
        test_html_with_rag()
        test_edge_cases()
        
        print("=" * 70)
        print("ALL TESTS PASSED! ✓")
        print("=" * 70)
        print()
        print("Summary:")
        print("  - HTML generation works without RAG")
        print("  - HTML generation works with RAG references")
        print("  - Reference images are embedded with <img> tags")
        print("  - Metadata (titles, dates, locations) is displayed")
        print("  - Image URLs are generated correctly")
        print("  - Edge cases handled properly")
        print()
        print("Next steps:")
        print("  1. Open test_rag_output.html in a browser to visually inspect")
        print("  2. Start the AI service: python3 mondrian/ai_advisor_service.py --port 5100")
        print("  3. Test with a real image upload with enable_rag=true")
        print()
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

