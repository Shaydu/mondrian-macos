#!/usr/bin/env python3
"""
Quick test to generate an analysis with reference images and check the output
"""
import requests
import json
import time
from pathlib import Path

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
TEST_IMAGE = "source/mike-shrub.jpg"  # Using existing test image
OUTPUT_FILE = "test_reference_output.html"

def submit_job():
    """Submit a job for analysis"""
    print("=" * 70)
    print("Submitting analysis job with RAG enabled...")
    print("=" * 70)
    
    # Use multipart form data to submit the job
    files = {
        'file': ('test_image.jpg', open(TEST_IMAGE, 'rb'), 'image/jpeg')
    }
    data = {
        'advisors': 'ansel',
        'enable_rag': 'true'  # Enable RAG to get reference images
    }
    
    try:
        response = requests.post(f"{JOB_SERVICE_URL}/submit", files=files, data=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✓ Job submitted successfully!")
            print(f"  Job ID: {job_id}")
            return job_id
        else:
            print(f"✗ Failed to submit job (Status: {response.status_code})")
            print(f"  Response: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Error submitting job: {e}")
        return None

def wait_for_completion(job_id, timeout=300):
    """Wait for job to complete"""
    print(f"\nWaiting for job {job_id} to complete...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=5)
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status')
                current_step = status_data.get('current_step', '')
                
                if status == 'completed':
                    print(f"✓ Job completed!")
                    return True
                elif status == 'error':
                    print(f"✗ Job failed with error")
                    print(f"  Details: {status_data.get('error', 'Unknown error')}")
                    return False
                else:
                    print(f"  Status: {status} - {current_step}", end='\r')
        except Exception as e:
            print(f"  Error checking status: {e}")
        
        time.sleep(2)
    
    print(f"\n✗ Timeout waiting for job to complete")
    return False

def get_analysis(job_id):
    """Get the HTML analysis output"""
    print(f"\nRetrieving analysis for job {job_id}...")
    
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=10)
        if response.status_code == 200:
            html_content = response.text
            
            # Save to file
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✓ Analysis saved to: {OUTPUT_FILE}")
            
            # Check for reference images section
            if 'Reference Images Gallery' in html_content:
                print(f"✓ Reference Images Gallery section found!")
                
                # Count reference images
                import re
                ref_count = len(re.findall(r'Reference #\d+:', html_content))
                print(f"  Number of reference images: {ref_count}")
                
                # Check for "View full size" links
                view_links = re.findall(r'<a href="([^"]+)"[^>]*>View full size', html_content)
                if view_links:
                    print(f"\n  View full size links found:")
                    for i, link in enumerate(view_links[:3], 1):  # Show first 3
                        print(f"    {i}. {link}")
                else:
                    print(f"  ⚠ No 'View full size' links found!")
                
                # Check for image tags
                img_tags = re.findall(r'<img src="([^"]+)"[^>]*alt="[^"]*Reference', html_content)
                if img_tags:
                    print(f"\n  Reference image src attributes found:")
                    for i, src in enumerate(img_tags[:3], 1):  # Show first 3
                        print(f"    {i}. {src}")
                else:
                    print(f"  ⚠ No reference image tags found!")
            else:
                print(f"✗ Reference Images Gallery section NOT found")
                print(f"  This means RAG might not be working properly")
            
            return True
        else:
            print(f"✗ Failed to get analysis (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ Error getting analysis: {e}")
        return False

def main():
    print("\n" + "=" * 70)
    print("REFERENCE IMAGES TEST")
    print("=" * 70)
    print()
    
    # Check if test image exists
    if not Path(TEST_IMAGE).exists():
        print(f"✗ Test image not found: {TEST_IMAGE}")
        print(f"  Please provide a test image at this path, or use:")
        print(f"  - source/test_image.jpg")
        print(f"  - Any .jpg file in the source directory")
        return
    
    # Step 1: Submit job
    job_id = submit_job()
    if not job_id:
        return
    
    # Step 2: Wait for completion
    if not wait_for_completion(job_id):
        return
    
    # Step 3: Get analysis
    if not get_analysis(job_id):
        return
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print(f"Next steps:")
    print(f"1. Open {OUTPUT_FILE} in your browser")
    print(f"2. Scroll to the bottom to see 'Reference Images Gallery'")
    print(f"3. Check if images are displayed correctly")
    print(f"4. Click 'View full size' links to test if they work")
    print()

if __name__ == "__main__":
    main()
