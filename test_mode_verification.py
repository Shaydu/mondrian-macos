#!/usr/bin/env python3
"""
Mode Verification Test: Baseline vs RAG vs LORA
Tests the same image with all three modes to verify which flow is being executed.
Shows clear debug markers and flow confirmation in output.

Usage:
    python3 test_mode_verification.py
    
To see debug output:
    - Watch the terminal output (./mondrian.sh --restart)
    - Check iOS debug logs for flow markers
    - Grep for [BASELINE], [RAG], [STRATEGY] markers in logs
"""

import requests
import json
import time
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
AI_ADVISOR_URL = "http://127.0.0.1:5100"

# Test image
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
NC = '\033[0m'

def print_header(text):
    """Print section header"""
    print(f"\n{CYAN}{'='*100}{NC}")
    print(f"{CYAN}{BOLD}{text}{NC}")
    print(f"{CYAN}{'='*100}{NC}\n")

def print_step(step_num, text):
    """Print step number"""
    print(f"{BLUE}[STEP {step_num}]{NC} {text}")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓{NC} {text}")

def print_error(text):
    """Print error message"""
    print(f"{RED}✗{NC} {text}")

def print_info(text):
    """Print info message"""
    print(f"{YELLOW}ℹ{NC} {text}")

def print_marker(marker_type, text):
    """Print flow marker"""
    markers = {
        "baseline": f"{BLUE}[BASELINE]{NC}",
        "rag": f"{MAGENTA}[RAG]{NC}",
        "lora": f"{GREEN}[LORA]{NC}",
        "strategy": f"{CYAN}[STRATEGY]{NC}"
    }
    marker = markers.get(marker_type, f"[{marker_type}]")
    print(f"{marker} {text}")

def check_services():
    """Check if services are running"""
    print_header("Checking Services")
    
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/health", timeout=2)
        if resp.status_code == 200:
            print_success(f"Job Service is running on {JOB_SERVICE_URL}")
        else:
            print_error(f"Job Service returned {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"Job Service not reachable: {e}")
        return False
    
    try:
        resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=2)
        if resp.status_code == 200:
            print_success(f"AI Advisor Service is running on {AI_ADVISOR_URL}")
        else:
            print_error(f"AI Advisor Service returned {resp.status_code}")
            return False
    except Exception as e:
        print_error(f"AI Advisor Service not reachable: {e}")
        return False
    
    return True

def upload_image(mode, enable_rag=False):
    """Upload image and return job_id"""
    print_marker(mode, f"Uploading image for {mode.upper()} mode...")
    
    try:
        with open(TEST_IMAGE, 'rb') as f:
            files = {'file': f}
            data = {
                'advisor': ADVISOR,
                'auto_analyze': 'true',
                'mode': mode,
                'enable_rag': 'true' if enable_rag else 'false'
            }
            
            response = requests.post(
                f"{JOB_SERVICE_URL}/upload",
                files=files,
                data=data,
                timeout=10
            )
        
        if response.status_code != 201:
            print_error(f"Upload failed with {response.status_code}: {response.text}")
            return None
        
        result = response.json()
        job_id = result.get('job_id')
        print_success(f"Upload successful - Job ID: {job_id}")
        return job_id
    
    except Exception as e:
        print_error(f"Upload failed: {e}")
        return None

def get_job_status(job_id):
    """Get job status"""
    try:
        # Extract UUID from job_id if it has mode suffix
        uuid_only = job_id.split(' (')[0] if ' (' in job_id else job_id
        
        response = requests.get(
            f"{JOB_SERVICE_URL}/status/{uuid_only}",
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print_error(f"Failed to get status: {e}")
        return None

def wait_for_completion(job_id, mode, timeout=300):
    """Wait for job to complete and show progress"""
    print_marker(mode, "Waiting for analysis to complete...")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < timeout:
        status_data = get_job_status(job_id)
        
        if not status_data:
            print_info(f"Job data not found yet...")
            time.sleep(2)
            continue
        
        current_status = status_data.get('status', 'unknown')
        current_step = status_data.get('current_step', '')
        progress = status_data.get('progress_percentage', 0)
        
        if current_status != last_status:
            mode_display = status_data.get('mode', 'unknown')
            print_marker(mode, f"Status: {current_status} | Progress: {progress}% | Mode: {mode_display}")
            if current_step:
                print_marker(mode, f"  Step: {current_step}")
            last_status = current_status
        
        if current_status == 'done':
            print_success(f"Job completed successfully!")
            return True
        elif current_status == 'error':
            print_error(f"Job failed: {status_data.get('current_step', 'Unknown error')}")
            return False
        
        time.sleep(2)
    
    print_error(f"Job did not complete within {timeout}s")
    return False

def get_full_job_data(job_id):
    """Get full job data including mode verification"""
    try:
        # Extract UUID from job_id if it has mode suffix
        uuid_only = job_id.split(' (')[0] if ' (' in job_id else job_id
        
        response = requests.get(
            f"{JOB_SERVICE_URL}/job/{uuid_only}",
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print_error(f"Failed to get full job data: {e}")
        return None

def verify_mode_in_output(job_data, expected_mode):
    """Verify that the mode markers appear in the response"""
    if not job_data:
        return False
    
    # Check mode field
    mode_used = job_data.get('mode', '').lower()
    if mode_used == expected_mode.lower():
        print_success(f"Mode verification: {mode_used} (matches expected: {expected_mode})")
        return True
    else:
        print_error(f"Mode mismatch: got {mode_used}, expected {expected_mode}")
        return False

def run_test_sequence():
    """Run test for all three modes"""
    print_header("MODE VERIFICATION TEST - Three-Mode Comparison")
    
    print_info("This test will:")
    print_info("  1. Upload the same image in BASELINE mode")
    print_info("  2. Upload the same image in RAG mode")
    print_info("  3. Upload the same image in LORA mode (if available)")
    print_info("")
    print_info("Each mode should show distinct flow markers in the output:")
    print_info(f"  - {BLUE}[BASELINE]{NC} = Single-pass baseline analysis")
    print_info(f"  - {MAGENTA}[RAG]{NC} = Two-pass RAG with dimensional comparison")
    print_info(f"  - {GREEN}[LORA]{NC} = Fine-tuned LORA model analysis")
    print_info("")
    print_info("You should see these markers in:")
    print_info("  - Terminal output from ./mondrian.sh --restart")
    print_info("  - iOS debug logs (if connected)")
    print_info("")
    
    input(f"{YELLOW}Press Enter to start the test...{NC}")
    
    # Check services first
    if not check_services():
        print_error("Services not available. Please start them with: ./mondrian.sh --restart")
        return False
    
    results = {}
    
    # Test 1: BASELINE
    print_header("TEST 1: BASELINE MODE")
    baseline_job_id = upload_image("baseline", enable_rag=False)
    if baseline_job_id:
        if wait_for_completion(baseline_job_id, "baseline"):
            baseline_data = get_full_job_data(baseline_job_id)
            results["baseline"] = {
                "job_id": baseline_job_id,
                "success": verify_mode_in_output(baseline_data, "baseline"),
                "data": baseline_data
            }
        else:
            results["baseline"] = {"success": False, "job_id": baseline_job_id}
    else:
        results["baseline"] = {"success": False}
    
    time.sleep(2)
    
    # Test 2: RAG
    print_header("TEST 2: RAG MODE")
    rag_job_id = upload_image("rag", enable_rag=True)
    if rag_job_id:
        if wait_for_completion(rag_job_id, "rag"):
            rag_data = get_full_job_data(rag_job_id)
            results["rag"] = {
                "job_id": rag_job_id,
                "success": verify_mode_in_output(rag_data, "rag"),
                "data": rag_data
            }
        else:
            results["rag"] = {"success": False, "job_id": rag_job_id}
    else:
        results["rag"] = {"success": False}
    
    time.sleep(2)
    
    # Test 3: LORA
    print_header("TEST 3: LORA MODE")
    lora_job_id = upload_image("lora", enable_rag=False)
    if lora_job_id:
        if wait_for_completion(lora_job_id, "lora"):
            lora_data = get_full_job_data(lora_job_id)
            results["lora"] = {
                "job_id": lora_job_id,
                "success": verify_mode_in_output(lora_data, "lora"),
                "data": lora_data
            }
        else:
            results["lora"] = {"success": False, "job_id": lora_job_id}
    else:
        results["lora"] = {"success": False}
    
    # Print summary
    print_header("TEST SUMMARY")
    print_info("Mode Verification Results:")
    print("")
    
    all_passed = True
    for mode in ["baseline", "rag", "lora"]:
        if mode in results:
            result = results[mode]
            status = "PASS" if result.get("success") else "FAIL"
            color = GREEN if result.get("success") else RED
            print(f"{color}  {mode.upper()}: {status}{NC}")
            if result.get("job_id"):
                print(f"    Job ID: {result['job_id']}")
            if not result.get("success"):
                all_passed = False
    
    print("")
    print_info("To verify the modes are working correctly:")
    print_info("  1. Check the terminal output for [BASELINE], [RAG], [STRATEGY] markers")
    print_info("  2. Look for the flow confirmation messages in ./mondrian.sh output")
    print_info("  3. Check iOS debug logs for mode-specific flow markers")
    print("")
    print_info(f"Job IDs for reference:")
    for mode, result in results.items():
        if result.get("job_id"):
            print_info(f"  {mode.upper()}: {result['job_id']}")
    
    if all_passed:
        print_success("All mode verification tests completed!")
    else:
        print_error("Some tests failed. Check the markers in terminal output.")
    
    return all_passed

if __name__ == "__main__":
    try:
        run_test_sequence()
    except KeyboardInterrupt:
        print(f"\n{RED}Test interrupted by user{NC}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
