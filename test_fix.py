#!/usr/bin/env python3
"""Test script to verify the reference image link fix"""
import requests
import json
import time
import sys

JOB_SERVICE_URL = "http://localhost:5005"
TEST_IMAGE = "source/mike-shrub.jpg"

print("=" * 70)
print("TESTING REFERENCE IMAGE FIX")
print("=" * 70)

# Wait for service to start
print("\nWaiting for services to be ready...")
for i in range(15):
    try:
        requests.get(f"{JOB_SERVICE_URL}/health", timeout=2)
        print("✓ Services ready!")
        break
    except:
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(1)
else:
    print("\n✗ Services not responding")
    sys.exit(1)

# Submit job
print("\nSubmitting analysis job with RAG enabled...")
try:
    with open(TEST_IMAGE, 'rb') as f:
        response = requests.post(
            f"{JOB_SERVICE_URL}/upload",
            files={'image': f},
            data={
                'advisor': 'ansel',
                'enable_rag': 'true'
            },
            timeout=10
        )
    
    if response.status_code in [200, 201]:
        result = response.json()
        job_id = result.get('job_id')
        print(f"✓ Job submitted: {job_id}")
    else:
        print(f"✗ Failed: {response.status_code}")
        print(response.text)
        sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Wait for job completion
print("\nWaiting for analysis to complete...")
for attempt in range(60):
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=5)
        if response.status_code == 200:
            status_data = response.json()
            status = status_data.get('status')
            
            if status == 'completed':
                print("✓ Analysis completed!")
                break
            elif status == 'error':
                print(f"✗ Job failed: {status_data.get('error')}")
                sys.exit(1)
            else:
                sys.stdout.write(".")
                sys.stdout.flush()
    except:
        pass
    
    time.sleep(2)
else:
    print("\n✗ Timeout waiting for job")
    sys.exit(1)

# Get analysis and check for the fix
print("\nFetching analysis HTML...")
try:
    response = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=10)
    if response.status_code == 200:
        html_content = response.text
        
        # Check for reference gallery
        if 'Reference Images Gallery' in html_content:
            print("✓ Reference Images Gallery found!")
            
            # Check if the fix is applied
            if 'href="/api/reference-image/' in html_content:
                # Count how many "View full size" links use the relative URL
                import re
                view_links = re.findall(r'<a href="(/api/reference-image/[^"]+)"[^>]*>View full size', html_content)
                
                if view_links:
                    print(f"✓ FIX VERIFIED: Found {len(view_links)} 'View full size' links with relative URLs!")
                    print("\n  Sample links:")
                    for link in view_links[:3]:
                        print(f"    {link}")
                    
                    # Open in browser
                    print(f"\n✓ Opening analysis in browser...")
                    import subprocess
                    subprocess.run(['open', f'{JOB_SERVICE_URL}/analysis/{job_id}'], check=False)
                    
                    print("\n" + "=" * 70)
                    print("SUCCESS! The fix is working.")
                    print("=" * 70)
                    print("\nIn your browser, scroll to 'Reference Images Gallery'")
                    print("and try clicking 'View full size →' links to verify they work.")
                else:
                    print("✗ No 'View full size' links found")
            else:
                print("✗ View full size links not using relative URLs")
        else:
            print("✗ Reference Images Gallery not found in output")
    else:
        print(f"✗ Failed to get analysis: {response.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
