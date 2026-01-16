#!/usr/bin/env python3
"""
Test script to capture thinking/reasoning updates from active Mondrian job inference.
Monitors job status and tries to extract model thinking/reasoning from outputs.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
AI_SERVICE_URL = "http://localhost:5100"

def get_active_jobs():
    """Get list of active jobs"""
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/jobs")
        response.raise_for_status()
        data = response.json()
        
        # Find analyzing jobs
        analyzing = [job for job in data.get('jobs', []) if job.get('status') == 'analyzing']
        return analyzing
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        return []

def get_job_details(job_id):
    """Get detailed job info"""
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get job details: {e}")
        return None

def monitor_job_inference(job_id, poll_interval=2, max_duration=120):
    """
    Monitor job inference and capture any thinking/reasoning updates
    """
    logger.info(f"Monitoring job: {job_id}")
    start_time = time.time()
    last_status = None
    outputs_captured = []
    
    print("\n" + "="*70)
    print(f"MONITORING ACTIVE JOB INFERENCE: {job_id}")
    print("="*70)
    
    while time.time() - start_time < max_duration:
        details = get_job_details(job_id)
        
        if not details:
            logger.warning("Could not fetch job details")
            time.sleep(poll_interval)
            continue
        
        current_status = details.get('status')
        
        # Log status changes
        if current_status != last_status:
            logger.info(f"Job status changed: {last_status} → {current_status}")
            print(f"\n[Status Update] {current_status}")
            last_status = current_status
        
        # Try to extract thinking/reasoning from output
        if 'output' in details and details['output']:
            output = details['output']
            
            # Check if output contains thinking indicators
            thinking_indicators = ['think', 'reason', 'consider', 'analyze', 'observe', 'step', 'therefore', 'because']
            has_thinking = any(indicator in str(output).lower() for indicator in thinking_indicators)
            
            if output not in outputs_captured:
                outputs_captured.append(output)
                
                print("\n" + "-"*70)
                print("OUTPUT CAPTURED:")
                print("-"*70)
                
                if isinstance(output, dict):
                    print(json.dumps(output, indent=2)[:500])
                    if has_thinking:
                        print("\n✓ THINKING INDICATORS DETECTED")
                else:
                    print(str(output)[:500])
                    if has_thinking:
                        print("\n✓ THINKING INDICATORS DETECTED")
        
        # Check for intermediate results or progress
        if 'intermediate' in details and details['intermediate']:
            print(f"\n[Intermediate Data] {details['intermediate'][:100]}")
        
        # Exit if job completed
        if current_status in ['completed', 'failed', 'error']:
            logger.info(f"Job finished with status: {current_status}")
            print(f"\n[FINAL STATUS] {current_status}")
            
            # Get final output
            if 'output' in details:
                final_output = details['output']
                print("\n" + "="*70)
                print("FINAL OUTPUT:")
                print("="*70)
                if isinstance(final_output, dict):
                    print(json.dumps(final_output, indent=2))
                else:
                    print(final_output)
            
            break
        
        time.sleep(poll_interval)
    
    elapsed = time.time() - start_time
    print(f"\n[Monitoring Complete] Elapsed: {elapsed:.1f}s, Outputs captured: {len(outputs_captured)}")
    
    return {
        'job_id': job_id,
        'elapsed': elapsed,
        'outputs_captured': len(outputs_captured),
        'final_status': last_status
    }

def test_thinking_retrieval_from_service():
    """
    Test if we can retrieve thinking updates by making an inference request directly
    with specific parameters to encourage reasoning display.
    """
    
    print("\n" + "="*70)
    print("TEST: Direct Thinking Retrieval from AI Service")
    print("="*70)
    
    # Use a test image
    test_image_path = "./source/mike-shrub-01004b68.jpg"
    if not os.path.exists(test_image_path):
        logger.warning(f"Test image not found: {test_image_path}")
        return False
    
    try:
        # Create thinking-encouraging prompt in request
        with open(test_image_path, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': 'ansel',
                'enable_rag': False,
                'thinking_mode': 'detailed',  # Try custom parameter
            }
            
            logger.info("Sending request with thinking prompt...")
            response = requests.post(f"{AI_SERVICE_URL}/analyze", files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            
            print("\nResponse received:")
            print(json.dumps(result, indent=2)[:1000])
            
            # Look for thinking indicators
            thinking_indicators = ['think', 'reason', 'consider', 'step', 'because']
            result_str = json.dumps(result).lower()
            
            thinking_found = any(term in result_str for term in thinking_indicators)
            if thinking_found:
                print("\n✓ Thinking/reasoning content detected in response!")
            
            return True
            
    except Exception as e:
        logger.error(f"Direct service test failed: {e}")
        return False

def main():
    """Main test execution"""
    print("Testing LLM thinking retrieval from active inference job...\n")
    
    # First, try to capture from active job
    print("\nPhase 1: Monitoring Active Job Inference")
    print("-" * 70)
    
    active_jobs = get_active_jobs()
    
    if active_jobs:
        logger.info(f"Found {len(active_jobs)} active job(s)")
        job = active_jobs[0]
        logger.info(f"Monitoring: {job['id']}")
        
        result = monitor_job_inference(job['id'], poll_interval=1, max_duration=60)
        
        print("\n" + "="*70)
        print("PHASE 1 RESULTS:")
        print("="*70)
        print(json.dumps(result, indent=2))
    else:
        logger.info("No active analyzing jobs found")
        print("\nTo test with active job:")
        print("1. Make an inference request to the AI service")
        print("2. Run this script to monitor the job")
    
    # Try direct service test as well
    print("\n\nPhase 2: Direct Service Test")
    print("-" * 70)
    
    if os.path.exists("./source/mike-shrub-01004b68.jpg"):
        test_thinking_retrieval_from_service()
    else:
        logger.warning("Skipping direct service test (test image not found)")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY: Testing LLM Thinking Retrieval")
    print("="*70)
    print("""
Findings:
- Can we capture model outputs? YES/PARTIAL/NO
- Does output contain reasoning steps? YES/NO
- Are there special thinking tokens? YES/NO
- Can we stream/monitor in real-time? YES/NO

Recommendations:
1. Use chain-of-thought prompting to encourage reasoning display
2. Enable streaming if available for real-time token capture
3. Look for 'think', 'reason', 'step' patterns in outputs
4. Consider custom model fine-tuning for explicit thinking tokens
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
