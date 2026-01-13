#!/usr/bin/env python3
"""
Test script to verify advisor output view fixes
"""

import requests
import json
import time

# Test configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
TEST_IMAGE_PATH = "/Users/shaydu/dev/mondrian-macos/source/test_image.jpg"

def test_reference_image_endpoint():
    """Test that the new /api/reference-image endpoint works"""
    print("=" * 60)
    print("TEST 1: Reference Image Endpoint")
    print("=" * 60)
    
    # Try to fetch a known reference image
    test_images = [
        "ansel-old-faithful-geyser-1944.png",
        "Adams_The_Tetons_and_the_Snake_River.jpg"
    ]
    
    for filename in test_images:
        url = f"{JOB_SERVICE_URL}/api/reference-image/{filename}"
        print(f"\nTesting: {url}")
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  ✓ SUCCESS - Image served ({len(response.content)} bytes)")
                print(f"  Content-Type: {response.headers.get('Content-Type')}")
            else:
                print(f"  ✗ FAILED - Status {response.status_code}")
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  ✗ ERROR: {e}")

def test_html_output_format():
    """Test that HTML output has the correct format"""
    print("\n" + "=" * 60)
    print("TEST 2: HTML Output Format")
    print("=" * 60)
    
    # This would require analyzing actual job output
    # For now, just check that the converter module loads
    try:
        from mondrian.json_to_html_converter import json_to_html
        print("  ✓ HTML converter module loaded successfully")
    except Exception as e:
        print(f"  ✗ Failed to load converter: {e}")

def main():
    print("Testing Advisor Output View Fixes")
    print("=" * 60)
    
    # Test 1: Reference image endpoint
    test_reference_image_endpoint()
    
    # Test 2: HTML format
    test_html_output_format()
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Submit a new analysis job with RAG enabled")
    print("2. Check the HTML output for:")
    print("   - Reference titles show 'Title Year' format")
    print("   - Reference images load correctly")
    print("   - Dimensional scores show 'X / Y' format")
    print("   - Only one 'Advisor Analysis' section exists")

if __name__ == "__main__":
    main()
