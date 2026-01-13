#!/usr/bin/env python3
"""Test the iOS-compatible absolute URL fix for reference images"""
import requests
import json
import time

JOB_SERVICE_URL = "http://localhost:5005"
TEST_IMAGE = "source/mike-shrub.jpg"

print("=" * 70)
print("TESTING iOS-COMPATIBLE REFERENCE IMAGE URLS")
print("=" * 70)

# Wait for service
print("\nWaiting for services...")
for i in range(10):
    try:
        requests.get(f"{JOB_SERVICE_URL}/health", timeout=2)
        print("✓ Services ready")
        break
    except:
        time.sleep(1)

# Submit job
print("\nSubmitting analysis job with RAG enabled...")
try:
    with open(TEST_IMAGE, 'rb') as f:
        response = requests.post(
            f"{JOB_SERVICE_URL}/upload",
            files={'image': f},
            data={'advisor': 'ansel', 'enable_rag': 'true'},
            timeout=10
        )
    
    if response.status_code in [200, 201]:
        job_id = response.json().get('job_id')
        print(f"✓ Job submitted: {job_id}")
    else:
        print(f"✗ Failed: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

# Wait for completion
print("\nWaiting for analysis...")
for attempt in range(120):
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=5)
        if response.status_code == 200:
            status = response.json().get('status')
            if status == 'completed':
                print("✓ Analysis completed")
                break
            elif status == 'error':
                print(f"✗ Error: {response.json().get('error')}")
                exit(1)
    except:
        pass
    time.sleep(2)

# Get analysis
print("\nFetching analysis...")
try:
    response = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=10)
    if response.status_code == 200:
        html = response.text
        
        # Check for absolute URLs
        if 'Reference Images Gallery' in html:
            print("✓ Reference Images Gallery found")
            
            # Check for absolute URLs (should have http://localhost:5005)
            import re
            
            # Look for absolute URLs
            absolute_urls = re.findall(r'href="(http://[^"]+/api/reference-image/[^"]+)"', html)
            if absolute_urls:
                print(f"✓ Found {len(absolute_urls)} absolute URLs:")
                for url in absolute_urls[:2]:
                    print(f"    {url}")
            else:
                # Check for relative URLs (old format)
                relative_urls = re.findall(r'href="(/api/reference-image/[^"]+)"', html)
                if relative_urls:
                    print(f"⚠ Found {len(relative_urls)} RELATIVE URLs (iOS won't work):")
                    for url in relative_urls[:2]:
                        print(f"    {url}")
                else:
                    print("✗ No reference image links found")
            
            # Check image sources
            img_urls = re.findall(r'src="(http://[^"]+/api/reference-image/[^"]+)"', html)
            if img_urls:
                print(f"\n✓ Found {len(img_urls)} absolute image URLs")
            else:
                img_urls = re.findall(r'src="(/api/reference-image/[^"]+)"', html)
                if img_urls:
                    print(f"\n⚠ Found {len(img_urls)} RELATIVE image URLs (iOS won't work)")
                else:
                    print("\n✗ No image URLs found")
        else:
            print("✗ No reference gallery found")
    else:
        print(f"✗ Failed: {response.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

print("\n" + "=" * 70)
print("OPEN BROWSER TO TEST:")
print(f"http://localhost:5005/analysis/{job_id}")
print("=" * 70)
