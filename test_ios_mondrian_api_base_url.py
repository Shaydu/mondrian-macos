#!/usr/bin/env python3
"""
Test the iOS MONDRIAN_API_BASE_URL fix
Verifies that passing the parameter results in correct image URLs
"""
import requests
import json
import time
import re

JOB_SERVICE_URL = "http://localhost:5005"
AI_SERVICE_URL = "http://localhost:5100"
TEST_IMAGE = "source/mike-shrub.jpg"

# Simulate what iOS app should send
SIMULATED_IOS_IP = "192.168.1.100"
MONDRIAN_API_BASE_URL = f"http://{SIMULATED_IOS_IP}:5005"

print("=" * 70)
print("iOS REFERENCE IMAGES FIX - TEST")
print("=" * 70)
print(f"\nSimulating iOS device IP: {SIMULATED_IOS_IP}")
print(f"Sending MONDRIAN_API_BASE_URL: {MONDRIAN_API_BASE_URL}")

# Wait for services
print("\nWaiting for services...")
for i in range(10):
    try:
        requests.get(f"{AI_SERVICE_URL}/health", timeout=2)
        requests.get(f"{JOB_SERVICE_URL}/health", timeout=2)
        print("✓ Services ready")
        break
    except:
        time.sleep(1)

# Test 1: Submit analysis WITH MONDRIAN_API_BASE_URL
print("\n[Test 1] Submitting analysis WITH MONDRIAN_API_BASE_URL parameter...")
try:
    with open(TEST_IMAGE, 'rb') as f:
        files = {'image': f}
        data = {
            'advisor': 'ansel',
            'enable_rag': 'true',
            'job_id': 'test-ios-fix-1',
            'MONDRIAN_API_BASE_URL': MONDRIAN_API_BASE_URL  # THIS IS THE KEY!
        }
        
        response = requests.post(
            f"{AI_SERVICE_URL}/analyze",
            files=files,
            data=data,
            timeout=300
        )
    
    if response.status_code == 200:
        result = response.json()
        html_content = result.get('html', '')
        
        # Check if image URLs contain the iOS IP address (not localhost)
        print("✓ Analysis completed")
        
        # Look for the simulated IP in image URLs
        img_urls = re.findall(r'src="([^"]+/api/reference-image/[^"]+)"', html_content)
        link_urls = re.findall(r'href="([^"]+/api/reference-image/[^"]+)"', html_content)
        
        if img_urls:
            print(f"\n✓ Found {len(img_urls)} image URLs:")
            for url in img_urls[:3]:
                print(f"  {url}")
                if SIMULATED_IOS_IP in url:
                    print(f"  ✅ Contains iOS IP {SIMULATED_IOS_IP}")
                elif "localhost" in url:
                    print(f"  ❌ Still has localhost (not fixed!)")
        
        if link_urls:
            print(f"\n✓ Found {len(link_urls)} 'View full size' links:")
            for url in link_urls[:3]:
                print(f"  {url}")
                if SIMULATED_IOS_IP in url:
                    print(f"  ✅ Contains iOS IP {SIMULATED_IOS_IP}")
                elif "localhost" in url:
                    print(f"  ❌ Still has localhost (not fixed!)")
        
        # Check logs
        print("\n[Test 2] Checking backend logs...")
        try:
            with open('/tmp/ai_service_ios_fix.log', 'r') as f:
                logs = f.read()
            
            if 'MONDRIAN_API_BASE_URL' in logs:
                print("✓ Backend received MONDRIAN_API_BASE_URL parameter")
                # Extract and show the relevant log lines
                for line in logs.split('\n'):
                    if 'MONDRIAN_API_BASE_URL' in line or 'iOS DEBUG' in line:
                        print(f"  {line}")
            else:
                print("⚠ Backend didn't log MONDRIAN_API_BASE_URL")
        except Exception as e:
            print(f"Could not read logs: {e}")
        
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        if SIMULATED_IOS_IP in html_content:
            print("✅ SUCCESS: Image URLs now contain iOS IP address!")
            print("   Reference images should now render on iOS devices")
        else:
            print("❌ FAILED: Image URLs still don't have iOS IP")
            print("   Check backend logs for issues")
    
    else:
        print(f"✗ Failed: {response.status_code}")
        print(f"Response: {response.text[:200]}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
