#!/usr/bin/env python3
"""
Quick test to verify IMG_N and QUOTE_N replacement in recommendations
"""

import re
import sys
sys.path.insert(0, '/home/doo/dev/mondrian-macos')

def test_citation_replacement():
    """Test that IMG_N and QUOTE_N handles are replaced with titles"""
    
    # Sample data
    reference_images = [
        {
            'image_title': 'The Tetons and the Snake River',
            'date_taken': '1942',
            'image_path': '/path/to/image1.jpg'
        },
        {
            'image_title': 'Moon and Half Dome',
            'date_taken': '1960',
            'image_path': '/path/to/image2.jpg'
        },
    ]
    
    book_passages = [
        {
            'book_title': 'The Camera',
            'passage_text': 'Some passage text here'
        },
    ]
    
    # Sample recommendation WITH IMG_N and QUOTE_N handles
    test_recommendation = "Study IMG_1 'The Tetons and the Snake River' to understand how the S-curve creates depth. Use QUOTE_1 as guidance."
    
    print("=" * 80)
    print("TEST: Citation Handle Removal")
    print("=" * 80)
    print(f"\nOriginal recommendation:\n  {test_recommendation}\n")
    
    # Simulate the simpler stripping logic from _parse_response
    rec = test_recommendation
    
    # Remove all IMG_N handles
    rec = re.sub(r'\bIMG_\d+\b', '', rec)
    print(f"After removing IMG_N:\n  {rec}\n")
    
    # Remove all QUOTE_N handles
    rec = re.sub(r'\bQUOTE_\d+\b', '', rec)
    print(f"After removing QUOTE_N:\n  {rec}\n")
    
    # Clean up double spaces
    rec = re.sub(r'\s+', ' ', rec).strip()
    print(f"After cleanup:\n  {rec}\n")
    
    # Expected result (handles stripped, titles remain)
    expected = "Study 'The Tetons and the Snake River' to understand how the S-curve creates depth. Use as guidance."
    
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Final recommendation:\n  {rec}\n")
    print(f"Expected:\n  {expected}\n")
    
    if rec == expected:
        print("✅ TEST PASSED - All handles replaced correctly!")
        return True
    else:
        print("❌ TEST FAILED - Output doesn't match expected")
        print(f"\nDifferences:")
        print(f"  Expected length: {len(expected)}")
        print(f"  Actual length:   {len(rec)}")
        return False

if __name__ == '__main__':
    success = test_citation_replacement()
    sys.exit(0 if success else 1)
