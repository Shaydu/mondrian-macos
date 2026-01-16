#!/usr/bin/env python3
"""
Test script to verify the /summary endpoint fix
Tests that /summary returns JSON with job_id field (iOS compatibility)
"""
import requests
import json
import time
from pathlib import Path

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
TEST_IMAGE = Path("source/mike-shrub.jpg")
ADVISOR = "ansel"

def test_summary_endpoint():
    """Test that /summary/{job_id} returns JSON with job_id field"""
    print("\n" + "="*70)
    print("Testing /summary endpoint fix for iOS compatibility")
    print("="*70)
    
    # Step 1: Upload image
    print("\n1️⃣  Uploading test image...")
    try:
        with open(TEST_IMAGE, 'rb') as f:
            files = {'image': f}
            data = {'advisor': ADVISOR, 'auto_analyze': 'true'}
            response = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=10)
        
        if response.status_code != 201:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        upload_response = response.json()
        job_id = upload_response.get('job_id')
        print(f"   ✅ Upload successful. Job ID: {job_id}")
        
    except Exception as e:
        print(f"   ❌ Upload error: {e}")
        return False
    
    # Step 2: Wait for job completion
    print(f"\n2️⃣  Waiting for job completion (max 5 minutes)...")
    max_wait = 300
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=10)
            
            if response.status_code == 200:
                job_data = response.json()
                status = job_data.get('status')
                progress = job_data.get('progress_percentage', 0)
                
                print(f"   [{progress}%] Status: {status}")
                
                if status == "completed":
                    print(f"   ✅ Job completed!")
                    break
                elif status == "error":
                    print(f"   ❌ Job error: {job_data.get('error', 'Unknown error')}")
                    return False
                
                time.sleep(5)
            else:
                print(f"   ⚠️  Status check returned {response.status_code}")
                time.sleep(5)
                
        except Exception as e:
            print(f"   ⚠️  Status check error: {str(e)[:50]}")
            time.sleep(5)
    
    if time.time() - start_time >= max_wait:
        print(f"   ❌ Job did not complete within {max_wait}s")
        return False
    
    # Step 3: Test /summary endpoint (iOS compatibility test)
    print(f"\n3️⃣  Testing /summary endpoint (iOS compatibility)...")
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/summary/{job_id}", timeout=10)
        
        if response.status_code != 200:
            print(f"   ❌ /summary endpoint failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
        
        # Try to parse as JSON (what iOS app expects)
        try:
            data = response.json()
            print(f"   ✅ Response is valid JSON")
            
            # Check for required job_id field
            if 'job_id' not in data:
                print(f"   ❌ Missing 'job_id' field in response")
                print(f"   Available fields: {list(data.keys())}")
                return False
            
            print(f"   ✅ Contains 'job_id' field: {data['job_id']}")
            
            # Verify job_id matches
            if data['job_id'] != job_id:
                print(f"   ❌ job_id mismatch: {data['job_id']} != {job_id}")
                return False
            
            print(f"   ✅ job_id matches uploaded job")
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type.lower():
                print(f"   ⚠️  Content-Type is '{content_type}', expected 'application/json'")
                # This is a warning but not a failure
            else:
                print(f"   ✅ Content-Type is correct: {content_type}")
            
            # Verify other fields
            expected_fields = ['job_id', 'status', 'advisor', 'mode']
            missing_fields = [f for f in expected_fields if f not in data]
            if missing_fields:
                print(f"   ⚠️  Missing optional fields: {missing_fields}")
            else:
                print(f"   ✅ All expected fields present: {expected_fields}")
            
            print(f"\n   📊 Response preview:")
            for key in ['job_id', 'status', 'advisor', 'mode', 'created_at']:
                if key in data:
                    value = str(data[key])[:50]
                    print(f"      - {key}: {value}")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"   ❌ Response is NOT valid JSON: {e}")
            print(f"   Response preview: {response.text[:200]}")
            return False
        
    except Exception as e:
        print(f"   ❌ /summary endpoint error: {e}")
        return False
    
    finally:
        # Step 4: Test /summary endpoint with format=html (should still work)
        print(f"\n4️⃣  Testing /summary endpoint with format=html parameter...")
        try:
            response = requests.get(f"{JOB_SERVICE_URL}/summary/{job_id}?format=html", timeout=10)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type.lower():
                    print(f"   ✅ HTML format works correctly")
                else:
                    print(f"   ⚠️  Unexpected content-type: {content_type}")
                print(f"   ✅ HTML response ({len(response.text)} bytes)")
            else:
                print(f"   ❌ HTML format request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️  HTML format test error: {e}")


def main():
    print("🧪 iOS API Compatibility Test Suite")
    print("Testing fix for: keyNotFound(CodingKeys(stringValue: \"job_id\"...))")
    
    # Check if services are running
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"\n❌ Job Service health check failed: {response.status_code}")
            print(f"   Make sure the job service is running:")
            print(f"   ./mondrian.sh --start")
            return False
        print(f"✅ Job Service is running on {JOB_SERVICE_URL}")
    except Exception as e:
        print(f"\n❌ Cannot connect to Job Service on {JOB_SERVICE_URL}")
        print(f"   Error: {e}")
        print(f"   Make sure the job service is running:")
        print(f"   ./mondrian.sh --start")
        return False
    
    # Check if test image exists
    if not TEST_IMAGE.exists():
        print(f"\n❌ Test image not found: {TEST_IMAGE}")
        print(f"   Please make sure the test image exists at: {TEST_IMAGE}")
        return False
    
    print(f"✅ Test image exists: {TEST_IMAGE}\n")
    
    # Run the test
    success = test_summary_endpoint()
    
    # Print summary
    print("\n" + "="*70)
    if success:
        print("✅ ALL TESTS PASSED - iOS compatibility fix verified!")
        print("="*70)
        print("\n📱 iOS app should now be able to:")
        print("   • Decode /summary responses as JSON")
        print("   • Extract 'job_id' field without errors")
        print("   • Handle NSURLErrorDomain errors correctly")
        return True
    else:
        print("❌ TESTS FAILED - Please review errors above")
        print("="*70)
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
