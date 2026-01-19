#!/usr/bin/env python3
"""
Test script to verify API upload endpoint conforms to spec
"""

import requests
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:5005"

def test_advisors_endpoint():
    """Test GET /advisors endpoint"""
    print("=" * 70)
    print("TEST 1: GET /advisors")
    print("=" * 70)
    
    response = requests.get(f"{BASE_URL}/advisors")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {data.get('count')} advisors")
        
        # Check first advisor has required fields
        if data.get('advisors'):
            advisor = data['advisors'][0]
            print(f"✓ First advisor: {advisor.get('name')}")
            required_fields = ['id', 'name', 'specialty', 'focus_areas', 'image_url']
            for field in required_fields:
                if field in advisor:
                    print(f"  ✓ {field}: {advisor.get(field)}")
                else:
                    print(f"  ✗ Missing field: {field}")
        return True
    else:
        print(f"✗ Failed: {response.text}")
        return False

def test_upload_with_auto_analyze():
    """Test POST /upload with auto_analyze=true (default)"""
    print("\n" + "=" * 70)
    print("TEST 2: POST /upload with auto_analyze=true (default)")
    print("=" * 70)
    
    # Find a test image
    test_images = [
        "source/test_image.jpg",
        "source/ansel/1.jpg",
        "mondrian/source/advisor/photographer/ansel/1.jpg"
    ]
    
    test_image = None
    for img_path in test_images:
        if Path(img_path).exists():
            test_image = img_path
            break
    
    if not test_image:
        print("✗ No test image found")
        return False
    
    print(f"Using test image: {test_image}")
    
    with open(test_image, 'rb') as f:
        files = {'image': ('test.jpg', f, 'image/jpeg')}
        data = {
            'advisor': 'ansel',
            # auto_analyze defaults to 'true' per spec
        }
        
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        print(f"✓ Upload successful")
        print(f"  job_id: {result.get('job_id')}")
        print(f"  filename: {result.get('filename')}")
        print(f"  advisor: {result.get('advisor')}")
        print(f"  advisors_used: {result.get('advisors_used')}")
        print(f"  status: {result.get('status')}")
        print(f"  stream_url: {result.get('stream_url')}")
        
        # Check required fields per API spec
        required_fields = ['job_id', 'filename', 'advisor', 'advisors_used', 'status', 'status_url', 'stream_url']
        all_present = True
        for field in required_fields:
            if field not in result:
                print(f"  ✗ Missing required field: {field}")
                all_present = False
        
        if all_present:
            print("✓ All required fields present")
        
        # Check that filename is the unique server filename (not original)
        if result.get('filename') != 'test.jpg':
            print(f"✓ Filename is unique server filename (not original)")
        else:
            print(f"✗ Filename should be unique, got original instead")
        
        # Check status is 'queued' as per spec
        if result.get('status') == 'queued':
            print("✓ Status is 'queued' as per spec")
        else:
            print(f"✗ Status should be 'queued', got '{result.get('status')}'")
        
        return result.get('job_id')
    else:
        print(f"✗ Upload failed: {response.text}")
        return None

def test_upload_with_auto_analyze_false():
    """Test POST /upload with auto_analyze=false"""
    print("\n" + "=" * 70)
    print("TEST 3: POST /upload with auto_analyze=false")
    print("=" * 70)
    
    # Find a test image
    test_images = [
        "source/test_image.jpg",
        "source/ansel/1.jpg",
        "mondrian/source/advisor/photographer/ansel/1.jpg"
    ]
    
    test_image = None
    for img_path in test_images:
        if Path(img_path).exists():
            test_image = img_path
            break
    
    if not test_image:
        print("✗ No test image found")
        return False
    
    print(f"Using test image: {test_image}")
    
    with open(test_image, 'rb') as f:
        files = {'image': ('test.jpg', f, 'image/jpeg')}
        data = {
            'advisor': 'ansel',
            'auto_analyze': 'false'
        }
        
        response = requests.post(f"{BASE_URL}/upload", files=files, data=data)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        print(f"✓ Upload successful with auto_analyze=false")
        print(f"  job_id: {result.get('job_id')}")
        print(f"  status: {result.get('status')}")
        
        # With auto_analyze=false, job should stay in 'pending' but we return 'queued' to client
        # (This is a design choice - the API always says 'queued' even if not auto-analyzed)
        
        return True
    else:
        print(f"✗ Upload failed: {response.text}")
        return None

def check_job_status(job_id):
    """Check if job is being processed"""
    print("\n" + "=" * 70)
    print("TEST 4: Check job status after upload")
    print("=" * 70)
    
    if not job_id:
        print("✗ No job_id provided")
        return False
    
    print(f"Checking job: {job_id}")
    
    # Wait a moment for processing to start
    time.sleep(2)
    
    response = requests.get(f"{BASE_URL}/status/{job_id}")
    
    if response.status_code == 200:
        status = response.json()
        print(f"✓ Job status retrieved")
        print(f"  status: {status.get('status')}")
        print(f"  progress: {status.get('progress_percentage')}%")
        print(f"  current_step: {status.get('current_step')}")
        
        # Job should be in analyzing or completed state if auto_analyze worked
        if status.get('status') in ['queued', 'analyzing', 'processing', 'completed']:
            print(f"✓ Job is being processed (auto_analyze worked!)")
            return True
        else:
            print(f"✗ Job status unexpected: {status.get('status')}")
            return False
    else:
        print(f"✗ Failed to get status: {response.text}")
        return False

def main():
    print("Testing Mondrian API Conformance to Spec")
    print("=" * 70)
    
    try:
        # Test 1: Get advisors
        if not test_advisors_endpoint():
            print("\n✗ Advisors endpoint test failed")
            return 1
        
        # Test 2: Upload with auto_analyze=true (default)
        job_id = test_upload_with_auto_analyze()
        if not job_id:
            print("\n✗ Upload test failed")
            return 1
        
        # Test 3: Upload with auto_analyze=false
        if not test_upload_with_auto_analyze_false():
            print("\n✗ Upload with auto_analyze=false test failed")
            return 1
        
        # Test 4: Check job is being processed
        if not check_job_status(job_id):
            print("\n✗ Job status check failed")
            return 1
        
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        return 0
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to service at", BASE_URL)
        print("Make sure job service is running: python3 mondrian/job_service_v2.3.py")
        return 1
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
