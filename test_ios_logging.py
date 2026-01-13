#!/usr/bin/env python3
"""Test iOS reference image serving with detailed logging"""
import requests
import time

JOB_SERVICE_URL = "http://localhost:5005"

print("=" * 70)
print("iOS REFERENCE IMAGE LOGGING TEST")
print("=" * 70)

# Wait for service
print("\nWaiting for service...")
for i in range(10):
    try:
        requests.get(f"{JOB_SERVICE_URL}/health", timeout=2)
        print("✓ Service ready")
        break
    except:
        time.sleep(1)

# Test 1: Request a reference image that should exist
print("\n[Test 1] Requesting existing reference image...")
test_url = f"{JOB_SERVICE_URL}/api/reference-image/ansel-old-faithful-geyser-1944.png"
print(f"URL: {test_url}")

try:
    response = requests.get(test_url, timeout=5)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✓ Image served successfully")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        print(f"  Content-Length: {response.headers.get('Content-Length')}")
        print(f"  Size: {len(response.content)} bytes")
    else:
        print(f"✗ Request failed: {response.text}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Request a non-existent image
print("\n[Test 2] Requesting non-existent reference image...")
test_url_404 = f"{JOB_SERVICE_URL}/api/reference-image/nonexistent-image-12345.png"
print(f"URL: {test_url_404}")

try:
    response = requests.get(test_url_404, timeout=5)
    print(f"Status: {response.status_code}")
    if response.status_code == 404:
        print(f"✓ Correctly returned 404")
        print(f"  Response: {response.json()}")
    else:
        print(f"? Unexpected status: {response.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Check logs
print("\n[Test 3] Checking debug logs...")
try:
    with open('/Users/shaydu/dev/mondrian-macos/.cursor/debug.log', 'r') as f:
        lines = f.readlines()
    
    # Get last 20 lines
    recent_logs = lines[-20:]
    
    ios_debug_logs = [l for l in recent_logs if 'ios-image-debug' in l.lower()]
    
    print(f"Found {len(ios_debug_logs)} iOS debug logs in last 20 entries")
    
    if ios_debug_logs:
        print("\nRecent iOS debug logs:")
        for log in ios_debug_logs[-5:]:
            import json
            try:
                entry = json.loads(log)
                print(f"  [{entry['message']}]")
                print(f"    Data: {entry.get('data', {})}")
            except:
                print(f"  {log[:100]}...")
    else:
        print("No iOS debug logs found yet")
        print("\nLast 5 log entries:")
        for line in recent_logs[-5:]:
            print(f"  {line[:120]}...")
            
except Exception as e:
    print(f"Error reading logs: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE - Check /tmp/job_service_ios_debug.log and")
print("the debug.log file for iOS image request details")
print("=" * 70)
