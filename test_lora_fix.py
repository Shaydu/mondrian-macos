#!/usr/bin/env python3
"""
Test to verify the repetition fix works in LoRA mode.
"""

import requests
import json
import time
import sys

def test_lora_inference():
    """Test inference with LoRA adapter to verify no repetition issue"""
    
    print("="*70)
    print("Testing LoRA Mode with Fixed Generation Parameters")
    print("="*70)
    
    # Use a test image
    test_image_path = "./source/mike-shrub-01004b68.jpg"
    
    try:
        with open(test_image_path, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': 'ansel',
                'enable_rag': False,
            }
            
            print("\n1️⃣  Sending LoRA inference request...")
            response = requests.post(
                "http://localhost:5100/analyze",
                files=files,
                data=data,
                timeout=120
            )
            response.raise_for_status()
            
            result = response.json()
            
            print("✓ Response received")
            
            # Check for repetition issues in the response
            response_json = json.dumps(result)
            
            # Look for the massive "peace" repetition
            if "**peace**" in response_json:
                print("❌ FAILED: Still seeing **peace** repetition!")
                return False
            
            # Check for dimensions
            if 'dimensions' in result:
                dimensions = result['dimensions']
                print(f"✓ Got {len(dimensions)} dimensions")
                
                for dim in dimensions:
                    name = dim.get('name', '')
                    comment = dim.get('comment', '')
                    
                    # Check for word repetition
                    words = comment.split()
                    if len(words) > 0:
                        unique_count = len(set(words))
                        total_count = len(words)
                        
                        # Flag if any word appears too many times
                        word_freq = {}
                        for word in words:
                            word_freq[word] = word_freq.get(word, 0) + 1
                        
                        max_freq = max(word_freq.values())
                        
                        if max_freq > 50:
                            print(f"  ⚠️  {name}: Repetition detected (word repeated {max_freq}x)")
                            return False
                        else:
                            print(f"  ✓ {name}: OK (uniqueness: {(unique_count/total_count)*100:.1f}%)")
            
            print("\n✅ SUCCESS: No repetition issues detected!")
            print("\nSample output:")
            print(json.dumps(result, indent=2)[:500] + "...")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Waiting for services to be ready...")
    time.sleep(3)
    
    success = test_lora_inference()
    sys.exit(0 if success else 1)
