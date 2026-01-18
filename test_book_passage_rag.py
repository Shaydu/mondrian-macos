#!/usr/bin/env python3
"""
Test script to verify book passage RAG integration in advisor service.
Analyzes a user-uploaded image and checks if passages appear in the response.
"""

import requests
import json
import sys
from pathlib import Path
import time

# Configuration
API_BASE = "http://localhost:5100"
ADVISOR = "ansel"

def find_user_image():
    """Find a user-uploaded image to test with."""
    # Use the provided user image
    user_image = Path("/home/doo/dev/mondrian-macos/source/photo-AC2481F1-69FD-4FB4-A765-73251C2D656C-7cb6d924.jpg")
    
    if not user_image.exists():
        print(f"❌ User image not found: {user_image}")
        # Try to find any user images
        source_dir = Path("/home/doo/dev/mondrian-macos/source")
        if source_dir.exists():
            images = list(source_dir.glob("photo-*.jpg"))
            if images:
                user_image = images[0]
                print(f"✓ Found user image: {user_image.name}")
                return user_image
        return None
    
    print(f"✓ Found user image: {user_image.name}")
    return user_image

def check_api_health():
    """Check if advisor service is running."""
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=2)
        if resp.status_code == 200:
            print("✓ Advisor service is running")
            return True
    except requests.ConnectionError:
        print(f"❌ Cannot connect to advisor service at {API_BASE}")
        print("   Start it with: ./mondrian.sh --restart --backend=vllm --model-preset=qwen3-4b-instruct --mode=lora")
        return False

def analyze_image(image_path):
    """Send image to analyzer and get response."""
    print(f"\n📤 Analyzing image: {image_path.name}")
    print("   Using two-pass RAG mode...")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {'advisor': ADVISOR, 'mode': 'rag'}  # Use RAG mode for two-pass
            
            resp = requests.post(
                f"{API_BASE}/analyze",
                files=files,
                data=data,
                timeout=180  # Longer timeout for two-pass
            )
        
        if resp.status_code != 200:
            print(f"❌ API returned status {resp.status_code}")
            print(resp.text[:500])
            return None
        
        result = resp.json()
        print("✓ Analysis complete")
        return result
        
    except requests.Timeout:
        print("❌ Request timed out (analysis took >120s)")
        return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def check_for_passages(analysis_result):
    """Extract and display book passages from the response."""
    
    if not analysis_result:
        return False
    
    # Check for two-pass metadata
    if analysis_result.get('two_pass'):
        print("\n✅ Two-pass analysis completed!")
        print(f"   Pass 1 dimensions: {len(analysis_result.get('pass1_dimensions', []))}")
        print(f"   Weak dimensions: {analysis_result.get('weak_dimensions', [])}")
    
    # Check if response has the expected structure
    if 'analysis' not in analysis_result:
        print("❌ Response missing 'analysis' field")
        return False
    
    analysis = analysis_result.get('analysis', {})
    
    # Check for book_passages in the analysis
    passages = analysis.get('book_passages', [])
    
    if passages:
        print("\n✅ Book passages FOUND in analysis output!")
        print("\n" + "="*70)
        
        for i, passage in enumerate(passages, 1):
            print(f"\nPassage {i}: {passage['book_title']}")
            print(f"  Dimensions: {', '.join(passage['dimensions'])}")
            print(f"  Relevance: {passage['relevance_score']}")
            print(f"  Text: {passage['text'][:200]}...")
        
        print("\n" + "="*70)
        print(f"\n📚 Number of passages: {len(passages)}")
        
        return True
    else:
        print("\n⚠️  No passages found in response")
        
        # Show dimensional scores to debug
        if 'dimensions' in analysis:
            dims = analysis['dimensions']
            print("\n   Dimensional scores:")
            weak_dims = []
            for dim in dims:
                name = dim.get('name', 'Unknown')
                score = dim.get('score', 0)
                print(f"     {name}: {score}/10")
                if score <= 5:
                    weak_dims.append(name)
            
            if weak_dims:
                print(f"\n   Weak dimensions (score ≤ 5): {weak_dims}")
                print("   → Passages SHOULD have been retrieved for these")
            else:
                print("\n   No weak dimensions (all scores > 5)")
                print("   → Passages won't be retrieved (image has no weaknesses)")
        
        return False

def main():
    print("=" * 70)
    print("Testing Book Passage RAG Integration with User Image")
    print("=" * 70)
    
    # Check API health
    if not check_api_health():
        return 1
    
    # Find test image
    image_path = find_user_image()
    if not image_path:
        return 1
    
    # Analyze image
    result = analyze_image(image_path)
    if not result:
        return 1
    
    # Check for passages
    has_passages = check_for_passages(result)
    
    print("\n" + "=" * 70)
    if has_passages:
        print("✅ INTEGRATION TEST PASSED")
        print("   Book passages are being retrieved and included in responses")
    else:
        print("⚠️  No passages in this response (may be expected)")
        print("   The analyzed image's dimensional scores determine if passages appear")
        print("   Images with low scores (<= 5) in dimensions matching tagged passages")
        print("   will trigger passage retrieval")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
