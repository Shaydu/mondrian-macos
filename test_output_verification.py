#!/usr/bin/env python3
"""
Quick test to verify LoRA+RAG output includes references and quotes
"""
import requests
import json
import time
from pathlib import Path

JOB_SERVICE_URL = "http://localhost:5005"
TEST_IMAGE = Path("source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg")
FALLBACK_IMAGE = Path("source/mike-shrub.jpg")

def get_test_image():
    if TEST_IMAGE.exists():
        return TEST_IMAGE
    if FALLBACK_IMAGE.exists():
        return FALLBACK_IMAGE
    source_dir = Path("source")
    if source_dir.exists():
        jpgs = list(source_dir.glob("*.jpg"))
        if jpgs:
            return jpgs[0]
    return None

def verify_output():
    # Get test image
    test_image = get_test_image()
    if not test_image:
        print("❌ No test image found")
        return False
    
    print(f"📸 Test image: {test_image}")
    
    # Upload image and create job
    print("\n🔷 Uploading image...")
    with open(test_image, "rb") as f:
        response = requests.post(
            f"{JOB_SERVICE_URL}/upload",
            files={"image": (test_image.name, f, "image/jpeg")},
            data={"advisor": "ansel", "mode": "lora+rag"},
            timeout=30
        )
    
    if response.status_code not in [200, 201]:
        print(f"❌ Upload failed: {response.status_code}")
        return False
    
    job_data = response.json()
    job_id = job_data.get("job_id")
    print(f"✅ Job created: {job_id}")
    
    # Poll for completion
    print("\n🔷 Waiting for analysis to complete...")
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status_response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=10)
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            progress = status_data.get("progress", 0)
            print(f"  Status: {status} ({progress}%)", end="\r")
            
            if status == "completed":
                print(f"\n✅ Job completed!")
                
                # Get the results
                result = status_data.get("result", {})
                
                # Verify references
                print("\n🔍 Checking output structure:")
                
                # Check for reference_images
                ref_images = result.get("reference_images", [])
                print(f"\n  📷 Reference Images: {len(ref_images)} found")
                if ref_images:
                    for i, img in enumerate(ref_images[:3], 1):
                        title = img.get("title", "Unknown")
                        print(f"     {i}. {title}")
                    print(f"     ✅ Reference photos included!")
                else:
                    print(f"     ❌ No reference photos found")
                
                # Check for quotes
                book_passages = result.get("book_passages", [])
                print(f"\n  💬 Book Passages: {len(book_passages)} found")
                if book_passages:
                    for i, passage in enumerate(book_passages[:3], 1):
                        text = passage.get("text", "Unknown")[:80]
                        source = passage.get("source", "Unknown")
                        print(f"     {i}. [{source}] {text}...")
                    print(f"     ✅ Quotes included!")
                else:
                    print(f"     ❌ No book passages found")
                
                # Check dimensions
                dimensions = result.get("dimensions", {})
                print(f"\n  📊 Dimensions: {len(dimensions)} evaluated")
                if dimensions:
                    print(f"     ✅ Dimensional analysis included!")
                
                # Check score
                score = result.get("score")
                if score:
                    print(f"\n  ⭐ Score: {score}")
                
                # Final verdict
                print("\n" + "="*50)
                has_images = len(ref_images) > 0
                has_quotes = len(book_passages) > 0
                has_dims = len(dimensions) > 0
                
                if has_images and has_quotes and has_dims:
                    print("✅ ALL CHECKS PASSED!")
                    print("   - ✅ Reference photos included")
                    print("   - ✅ Quotes/passages included")
                    print("   - ✅ Dimensional analysis included")
                    return True
                else:
                    print("❌ SOME CHECKS FAILED:")
                    print(f"   - {'✅' if has_images else '❌'} Reference photos")
                    print(f"   - {'✅' if has_quotes else '❌'} Quotes/passages")
                    print(f"   - {'✅' if has_dims else '❌'} Dimensional analysis")
                    return False
                
            elif status == "failed":
                print(f"\n❌ Job failed!")
                error = status_data.get("error")
                print(f"   Error: {error}")
                return False
        
        time.sleep(2)
    
    print(f"\n❌ Job timed out after {max_wait} seconds")
    return False

if __name__ == "__main__":
    success = verify_output()
    exit(0 if success else 1)
