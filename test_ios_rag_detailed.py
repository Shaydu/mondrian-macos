#!/usr/bin/env python3
"""
iOS RAG Test - Detailed logging to see what's happening
"""

import requests
import json
from pathlib import Path

# Configuration
AI_ADVISOR_URL = "http://127.0.0.1:5100"
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"

def test_rag_enabled():
    """Test with RAG enabled and show detailed response"""
    
    image_path = Path(TEST_IMAGE).resolve()
    
    print("=" * 80)
    print("iOS RAG Test - Detailed")
    print("=" * 80)
    print(f"Image: {image_path}")
    print(f"Advisor: {ADVISOR}")
    print(f"RAG: ENABLED")
    print()
    
    payload = {
        "advisor": ADVISOR,
        "image_path": str(image_path),
        "enable_rag": "true"
    }
    
    print("Sending request to AI Advisor Service...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        resp = requests.post(f"{AI_ADVISOR_URL}/analyze", json=payload, timeout=180)
        
        print(f"Response Status: {resp.status_code}")
        print(f"Response Headers: {dict(resp.headers)}")
        print()
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                html = result.get('html', '')
            except:
                html = resp.text
            
            print(f"Response Length: {len(html)} bytes")
            print()
            
            # Check for RAG indicators in the response
            rag_keywords = [
                'reference', 'similar', 'compared to', 'like in',
                'master work', 'historical', 'delta', 'TBD'
            ]
            
            found_keywords = []
            for keyword in rag_keywords:
                if keyword.lower() in html.lower():
                    found_keywords.append(keyword)
            
            if found_keywords:
                print(f"✓ RAG indicators found: {', '.join(found_keywords)}")
            else:
                print("✗ No RAG indicators found in response")
            
            print()
            print("Response sample (first 1000 chars):")
            print("-" * 80)
            print(html[:1000])
            print("-" * 80)
            
            # Save full response
            output_file = Path("analysis_output/rag_detailed_response.html")
            output_file.parent.mkdir(exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"\nFull response saved to: {output_file}")
            
        else:
            print(f"✗ Request failed: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            
    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rag_enabled()

