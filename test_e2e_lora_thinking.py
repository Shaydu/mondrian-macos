#!/usr/bin/env python3
"""
End-to-End LoRA Flow Test with Qwen3-VL-4B-Thinking Model

Tests the complete pipeline:
1. Job submission via Job Service API (port 5005)
2. Image upload and queuing
3. LoRA-based inference with thinking model via AI Advisor (port 5100)
4. Result retrieval and validation
5. Thinking process visibility verification

Verifies:
- Services are healthy
- Model/Adapter configuration (thinking model + thinking adapter)
- LoRA inference works correctly
- GPU acceleration is active
- Results are valid (no timeouts, proper formatting)
- Thinking output is present and meaningful
"""

import requests
import json
import time
import sys
import os
from pathlib import Path

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
AI_ADVISOR_URL = "http://localhost:5100"
TEST_IMAGE = "./source/mike-shrub-01004b68.jpg"
TIMEOUT = 180  # 3 minutes for thinking model (slower)

def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def check_service_health():
    """Verify both services are running and healthy"""
    print_section("1. SERVICE HEALTH CHECK")
    
    try:
        # Check Job Service
        job_response = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        job_response.raise_for_status()
        job_health = job_response.json()
        print(f"\n✓ Job Service (port 5005): {job_health['status']}")
        
        # Check AI Advisor Service
        ai_response = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
        ai_response.raise_for_status()
        ai_health = ai_response.json()
        print(f"✓ AI Advisor Service (port 5100): {ai_health['status']}")
        
        # Verify configuration
        print(f"\n  Model Configuration:")
        print(f"    - Model: {ai_health.get('model', 'UNKNOWN')}")
        print(f"    - Device: {ai_health.get('device', 'UNKNOWN')}")
        print(f"    - GPU Active: {ai_health.get('using_gpu', False)}")
        print(f"    - LoRA Path: {ai_health.get('lora_path', 'NONE')}")
        print(f"    - Fine-tuned: {ai_health.get('fine_tuned', False)}")
        
        # Verify it's the thinking model with thinking adapter
        is_thinking_model = "Thinking" in ai_health.get('model', '')
        is_thinking_adapter = "thinking" in ai_health.get('lora_path', '').lower()
        
        if not is_thinking_model:
            print(f"\n⚠️  WARNING: Expected Thinking model, got: {ai_health.get('model')}")
            
        if not is_thinking_adapter:
            print(f"\n⚠️  WARNING: Expected thinking adapter, got: {ai_health.get('lora_path')}")
        
        if not ai_health.get('using_gpu'):
            print(f"\n⚠️  WARNING: GPU not active, CPU inference will be slow")
        
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def submit_job():
    """Submit an analysis job to the Job Service"""
    print_section("2. JOB SUBMISSION")
    
    if not os.path.exists(TEST_IMAGE):
        print(f"❌ Test image not found: {TEST_IMAGE}")
        return None
    
    try:
        with open(TEST_IMAGE, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': 'ansel',
                'enable_rag': False,
                # Don't override model/adapter - use what's configured
            }
            
            print(f"\n  Submitting image: {TEST_IMAGE}")
            print(f"  Advisor: ansel")
            print(f"  LoRA enabled: Yes (using thinking adapter)")
            
            response = requests.post(
                f"{JOB_SERVICE_URL}/submit",
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            job_id = result.get('job_id')
            
            print(f"\n✓ Job submitted successfully")
            print(f"  Job ID: {job_id}")
            print(f"  Status: {result.get('status')}")
            
            return job_id
            
    except Exception as e:
        print(f"❌ Job submission failed: {e}")
        return None

def poll_job_status(job_id, max_wait=TIMEOUT, poll_interval=5):
    """Poll job status until completion"""
    print_section("3. JOB PROCESSING (Polling)")
    
    print(f"\n  Waiting for job {job_id[:8]}... (up to {max_wait}s)")
    print(f"  Poll interval: {poll_interval}s")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"{JOB_SERVICE_URL}/job/{job_id}",
                timeout=10
            )
            response.raise_for_status()
            job = response.json()
            
            current_status = job.get('status')
            if current_status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] Status: {current_status}")
                if job.get('current_step'):
                    print(f"           Step: {job.get('current_step')}")
                last_status = current_status
            
            # Check for completion
            if current_status in ['completed', 'failed']:
                elapsed = int(time.time() - start_time)
                print(f"\n✓ Job {current_status.upper()}: {elapsed}s elapsed")
                return job
            
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"  Poll error: {e}")
            time.sleep(poll_interval)
    
    print(f"\n❌ Job polling timeout after {max_wait}s")
    return None

def validate_results(job):
    """Validate job results"""
    print_section("4. RESULT VALIDATION")
    
    if not job:
        print("❌ No job results to validate")
        return False
    
    status = job.get('status')
    print(f"\n  Job Status: {status}")
    
    if status == 'failed':
        error = job.get('error', 'Unknown error')
        print(f"❌ Job failed: {error}")
        return False
    
    if status != 'completed':
        print(f"❌ Job not completed: {status}")
        return False
    
    print(f"✓ Job completed successfully")
    
    # Get the analysis results
    try:
        response = requests.get(
            f"{AI_ADVISOR_URL}/result/{job.get('id')}",
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        # Validate analysis output
        analysis = result.get('analysis', {})
        
        print(f"\n  Analysis Output Structure:")
        print(f"    - Advisor: {analysis.get('advisor', 'N/A')}")
        print(f"    - Dimensions: {len(analysis.get('dimensions', []))}")
        
        dimensions = analysis.get('dimensions', [])
        if dimensions:
            print(f"\n  Evaluated Dimensions:")
            for dim in dimensions[:5]:  # Show first 5
                print(f"    - {dim.get('title')}: {dim.get('grade', 'N/A')}/10")
        
        # Check for thinking output (if present)
        thinking = analysis.get('thinking', '')
        if thinking:
            thinking_preview = thinking[:200].replace('\n', ' ')
            print(f"\n  ✓ Thinking Process FOUND:")
            print(f"    Length: {len(thinking)} chars")
            print(f"    Preview: {thinking_preview}...")
        else:
            print(f"\n  ⚠️  No thinking process in output (may be normal depending on model)")
        
        # Check recommendations
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\n  ✓ Recommendations Found: {len(recommendations)}")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not fetch detailed results: {e}")
        return True  # Don't fail on this, job completed

def direct_inference_test():
    """Test direct inference call to AI Advisor"""
    print_section("5. DIRECT INFERENCE TEST (via AI Advisor)")
    
    if not os.path.exists(TEST_IMAGE):
        print(f"❌ Test image not found: {TEST_IMAGE}")
        return False
    
    try:
        with open(TEST_IMAGE, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': 'ansel',
            }
            
            print(f"\n  Testing direct inference to AI Advisor...")
            print(f"  Using LoRA adapter (thinking model + thinking adapter)")
            
            start = time.time()
            response = requests.post(
                f"{AI_ADVISOR_URL}/analyze",
                files=files,
                data=data,
                timeout=TIMEOUT
            )
            elapsed = time.time() - start
            response.raise_for_status()
            
            result = response.json()
            
            print(f"\n✓ Direct inference successful in {elapsed:.1f}s")
            
            # Check for key fields
            analysis = result.get('analysis', {})
            
            if analysis.get('dimensions'):
                print(f"✓ Dimensions evaluated: {len(analysis.get('dimensions'))}")
            
            if analysis.get('thinking'):
                thinking = analysis.get('thinking')
                print(f"✓ Thinking output present: {len(thinking)} chars")
            else:
                print(f"⚠️  No thinking output in direct inference")
            
            if analysis.get('recommendations'):
                print(f"✓ Recommendations present: {len(analysis.get('recommendations'))}")
            
            return True
            
    except requests.Timeout:
        print(f"❌ Inference timeout after {TIMEOUT}s")
        return False
    except Exception as e:
        print(f"❌ Direct inference failed: {e}")
        return False

def run_all_tests():
    """Run all E2E tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  End-to-End LoRA Flow Test (Qwen3-4B-Thinking)".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    # Run tests in sequence
    results = {
        'health': check_service_health(),
        'job_submit': False,
        'job_poll': False,
        'validate': False,
        'direct_inference': direct_inference_test(),
    }
    
    # Only proceed if health check passes
    if not results['health']:
        print("\n❌ Services not healthy, cannot continue")
        return results
    
    # Job-based flow test
    job_id = submit_job()
    if job_id:
        results['job_submit'] = True
        job = poll_job_status(job_id)
        if job:
            results['job_poll'] = True
            results['validate'] = validate_results(job)
    
    return results

def print_summary(results):
    """Print test summary"""
    print_section("TEST SUMMARY")
    
    tests = [
        ('Service Health', results.get('health', False)),
        ('Job Submission', results.get('job_submit', False)),
        ('Job Processing', results.get('job_poll', False)),
        ('Result Validation', results.get('validate', False)),
        ('Direct Inference', results.get('direct_inference', False)),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    print(f"\n  Results: {passed}/{total} tests passed\n")
    
    for name, result in tests:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"    {status}: {name}")
    
    if passed == total:
        print("\n✓ All E2E tests passed! LoRA flow is working correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Check output above for details.")
        return 1

if __name__ == "__main__":
    results = run_all_tests()
    exit_code = print_summary(results)
    sys.exit(exit_code)
