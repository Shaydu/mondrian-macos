#!/usr/bin/env python3
"""
Test script to verify streaming token generation and thinking updates.
This script:
1. Starts a job via the job service
2. Monitors SSE stream for thinking updates
3. Prints updates as they arrive every 5 seconds
"""

import requests
import json
import time
import sys
from datetime import datetime

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def test_streaming():
    """Test streaming thinking updates"""
    
    print("=" * 80)
    print("Testing Streaming Token Generation")
    print("=" * 80)
    
    # Configuration
    JOB_SERVICE_URL = "http://127.0.0.1:5000"
    AI_ADVISOR_URL = "http://127.0.0.1:5100"
    
    # Check if services are running
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        print(f"✓ Job Service is running on {JOB_SERVICE_URL}")
    except:
        print(f"✗ Job Service not running on {JOB_SERVICE_URL}")
        print("  Start it with: python mondrian/job_service_v2.3.py")
        return
    
    try:
        resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
        print(f"✓ AI Advisor Service is running on {AI_ADVISOR_URL}")
    except:
        print(f"✗ AI Advisor Service not running on {AI_ADVISOR_URL}")
        print("  Start it with: python mondrian/ai_advisor_service.py")
        return
    
    print("\n" + "=" * 80)
    print("Test Instructions:")
    print("=" * 80)
    print("""
1. Make sure you have a test image in /Users/shaydu/dev/mondrian-macos/source/
2. Run the script: python test_streaming_updates.py
3. The script will submit a job and stream the SSE events
4. You should see "thinking_update" events arriving every 5 seconds
5. Each update shows the token count and generation speed
6. When generation finishes, look for "analysis_complete" event

Expected Output:
- connection
- status_update (initial)
- thinking_update (every ~5 seconds) ← NEW!
- thinking_update (every ~5 seconds) ← NEW!
- ... more thinking updates ...
- analysis_complete
- done
""")
    
    # Get list of available images
    print("\n" + "=" * 80)
    print("Checking for test images...")
    print("=" * 80)
    
    import os
    image_dir = "/Users/shaydu/dev/mondrian-macos/source/"
    if not os.path.exists(image_dir):
        print(f"✗ Image directory not found: {image_dir}")
        return
    
    images = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not images:
        print(f"✗ No images found in {image_dir}")
        return
    
    print(f"✓ Found {len(images)} test image(s)")
    test_image = images[0]
    print(f"  Using: {test_image}")
    
    # Submit a job
    print("\n" + "=" * 80)
    print("Submitting job...")
    print("=" * 80)
    
    try:
        job_resp = requests.post(
            f"{JOB_SERVICE_URL}/submit",
            json={
                "filename": test_image,
                "advisors": ["ansel"],  # Use just one advisor for faster testing
                "enable_rag": False
            },
            timeout=10
        )
        
        if job_resp.status_code != 200:
            print(f"✗ Failed to submit job: {job_resp.status_code}")
            print(f"  Response: {job_resp.text}")
            return
        
        job_data = job_resp.json()
        job_id = job_data.get("job_id")
        print(f"✓ Job submitted: {job_id}")
        
    except Exception as e:
        print(f"✗ Error submitting job: {e}")
        return
    
    # Stream and monitor events
    print("\n" + "=" * 80)
    print("Monitoring SSE stream for thinking updates...")
    print("=" * 80)
    print()
    
    thinking_update_count = 0
    start_time = time.time()
    
    try:
        stream_resp = requests.get(
            f"{JOB_SERVICE_URL}/stream/{job_id}",
            stream=True,
            timeout=600
        )
        
        for line in stream_resp.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            
            # Parse SSE format: "data: {json}"
            if line_str.startswith("data: "):
                try:
                    data = json.loads(line_str[6:])
                    event_type = data.get("type", "unknown")
                    
                    if event_type == "thinking_update":
                        thinking_update_count += 1
                        thinking_text = data.get("thinking", "")
                        elapsed = time.time() - start_time
                        print(f"[{timestamp()}] 💭 THINKING UPDATE #{thinking_update_count}")
                        print(f"   {thinking_text}")
                        print(f"   Elapsed: {elapsed:.1f}s")
                        print()
                    
                    elif event_type == "status_update":
                        job_data = data.get("job_data", {})
                        status = job_data.get("status")
                        current_step = job_data.get("current_step")
                        print(f"[{timestamp()}] 📊 STATUS UPDATE: {status}")
                        if current_step:
                            print(f"   Step: {current_step}")
                    
                    elif event_type == "analysis_complete":
                        print(f"[{timestamp()}] ✓ ANALYSIS COMPLETE")
                    
                    elif event_type == "connection":
                        print(f"[{timestamp()}] 🔗 Connected to stream")
                    
                    elif event_type == "done":
                        print(f"[{timestamp()}] ✓ Job done")
                        break
                    
                except json.JSONDecodeError:
                    pass
        
    except requests.exceptions.Timeout:
        print("✗ Stream timeout (600s)")
    except Exception as e:
        print(f"✗ Error during streaming: {e}")
    
    # Summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Total time: {elapsed:.1f}s")
    print(f"Thinking updates received: {thinking_update_count}")
    
    if thinking_update_count > 0:
        print(f"✓ SUCCESS! Streaming is working!")
        print(f"  Updates arrived every ~{elapsed / thinking_update_count:.1f}s")
    else:
        print(f"✗ No thinking updates received")
        print(f"  Check that:")
        print(f"  1. Job service is running")
        print(f"  2. AI Advisor service is running")
        print(f"  3. Check logs for errors")

if __name__ == "__main__":
    test_streaming()
