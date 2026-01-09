#!/usr/bin/env python3
"""
Quick test to verify enable_rag flag is being passed correctly
"""
import requests

JOB_SERVICE_URL = "http://127.0.0.1:5005"
TEST_IMAGE = "source/mike-shrub.jpg"

# Test with enable_rag=true
print("Testing with enable_rag=true...")
with open(TEST_IMAGE, 'rb') as f:
    files = {'image': (TEST_IMAGE, f, 'image/jpeg')}
    data = {
        'advisor': 'ansel',
        'enable_rag': 'true'  # Explicitly set to true
    }
    resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=30)
    print(f"Response status: {resp.status_code}")
    if resp.status_code in [200, 201]:
        result = resp.json()
        print(f"Job ID: {result['job_id']}")
        print(f"enable_rag in response: {result.get('enable_rag')}")
    else:
        print(f"Error: {resp.text}")
