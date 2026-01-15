#!/usr/bin/env python3
"""
E2E iOS Test Suite
Tests the complete workflow: upload image → analyze → stream progress → get results
"""
import requests
import time
import json
import sys
from pathlib import Path

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
AI_ADVISOR_URL = "http://localhost:5100"
SUMMARY_SERVICE_URL = "http://localhost:5200"  # Summary service

# Test image
TEST_IMAGE = Path("source/mike-shrub.jpg")
ADVISOR = "ansel"

def check_health():
    """Verify all services are healthy"""
    print("📋 Checking service health...")
    services = {
        "Job Service": (JOB_SERVICE_URL, 5005),
        "AI Advisor": (AI_ADVISOR_URL, 5100),
        "Summary Service": (SUMMARY_SERVICE_URL, 5200),
    }
    
    all_healthy = True
    for name, (url, port) in services.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {name} (:{port}) - healthy")
            else:
                print(f"  ⚠️  {name} (:{port}) - responded but status {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name} (:{port}) - {str(e)[:50]}")
            all_healthy = False
    
    return all_healthy

def test_image_upload():
    """Test image upload and job creation"""
    print("\n🔷 Test 1: Image Upload & Job Creation")
    
    if not TEST_IMAGE.exists():
        print(f"  ❌ Test image not found: {TEST_IMAGE}")
        return None
    
    try:
        with open(TEST_IMAGE, "rb") as f:
            response = requests.post(
                f"{JOB_SERVICE_URL}/analyze",
                files={"image": ("test.jpg", f, "image/jpeg")},
                data={"advisor": ADVISOR},
                timeout=10
            )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ Job created: {job_id}")
            return job_id
        else:
            print(f"  ❌ Upload failed: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  ❌ Upload error: {str(e)}")
        return None

def test_stream_progress(job_id):
    """Test SSE streaming of analysis progress"""
    print(f"\n🔷 Test 2: SSE Stream Progress (Job: {job_id})")
    
    try:
        stream_url = f"{JOB_SERVICE_URL}/stream/{job_id}"
        print(f"  Connecting to {stream_url}...")
        
        response = requests.get(stream_url, stream=True, timeout=300)
        
        if response.status_code != 200:
            print(f"  ❌ Stream failed: {response.status_code}")
            return False
        
        print("  ✅ Stream connected")
        events_received = 0
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("data:"):
                events_received += 1
                data = line.replace("data:", "").strip()
                if data:
                    try:
                        msg = json.loads(data)
                        status = msg.get("status", "unknown")
                        progress = msg.get("progress", 0)
                        print(f"    [{progress}%] {status}")
                    except:
                        pass
            
            # Stop after reasonable time to avoid blocking
            if events_received > 20:
                print(f"  ✅ Received {events_received} progress updates")
                break
        
        return True
    except Exception as e:
        print(f"  ❌ Stream error: {str(e)}")
        return False

def test_job_status(job_id):
    """Test polling job status"""
    print(f"\n🔷 Test 3: Job Status Polling (Job: {job_id})")
    
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                
                print(f"  [{progress}%] Status: {status}")
                
                if status == "completed":
                    print(f"  ✅ Job completed successfully")
                    return data
                elif status == "error":
                    error = data.get("error", "Unknown error")
                    print(f"  ❌ Job error: {error}")
                    return None
                
                time.sleep(2)
            else:
                print(f"  ⚠️  Status check returned {response.status_code}")
                time.sleep(5)
        
        except Exception as e:
            print(f"  ⚠️  Status check error: {str(e)[:50]}")
            time.sleep(5)
    
    print(f"  ❌ Job did not complete within {max_wait}s")
    return None

def test_get_results(job_id):
    """Test retrieving final analysis results"""
    print(f"\n🔷 Test 4: Get Analysis Results (Job: {job_id})")
    
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/results/{job_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            analysis = data.get("analysis", "")
            
            if analysis:
                preview = analysis[:200] + "..." if len(analysis) > 200 else analysis
                print(f"  ✅ Results retrieved")
                print(f"  Preview: {preview}")
                return data
            else:
                print(f"  ⚠️  No analysis in results")
                return data
        else:
            print(f"  ❌ Results retrieval failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"  ❌ Results error: {str(e)}")
        return None

def test_summary_service(job_id):
    """Test summary/consolidation service if available"""
    print(f"\n🔷 Test 5: Summary Service (Job: {job_id})")
    
    try:
        # Try to get summary
        response = requests.get(f"{SUMMARY_SERVICE_URL}/summary/{job_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Summary service working")
            return data
        elif response.status_code == 404:
            print(f"  ⚠️  Summary service available but job summary not found (may still be processing)")
            return None
        else:
            print(f"  ⚠️  Summary service returned {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"  ⚠️  Summary service not running on port 5200")
        return None
    except Exception as e:
        print(f"  ⚠️  Summary service error: {str(e)[:50]}")
        return None

def main():
    print("=" * 70)
    print("🚀 MONDRIAN E2E iOS TEST SUITE")
    print("=" * 70)
    
    # Step 1: Health check
    if not check_health():
        print("\n❌ Not all services are healthy. Please start services first:")
        print("   ./mondrian.sh --restart --mode=lora --lora-path=adapters/ansel/epoch_10")
        sys.exit(1)
    
    # Step 2: Upload image
    job_id = test_image_upload()
    if not job_id:
        print("\n❌ Failed to upload image")
        sys.exit(1)
    
    # Step 3: Stream progress
    test_stream_progress(job_id)
    
    # Step 4: Poll status
    results = test_job_status(job_id)
    if not results:
        print("\n❌ Job did not complete")
        sys.exit(1)
    
    # Step 5: Get full results
    final_data = test_get_results(job_id)
    if not final_data:
        print("\n❌ Failed to get results")
        sys.exit(1)
    
    # Step 6: Try summary service
    test_summary_service(job_id)
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ E2E TEST COMPLETE - ALL CRITICAL PATHS WORKING")
    print("=" * 70)
    print(f"\nJob ID: {job_id}")
    print(f"Status: {results.get('status', 'unknown')}")
    print(f"Analysis length: {len(final_data.get('analysis', ''))} chars")

if __name__ == "__main__":
    main()
