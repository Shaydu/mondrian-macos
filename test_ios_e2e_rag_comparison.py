#!/usr/bin/env python3
"""
iOS End-to-End Test: RAG vs Baseline Comparison
Simulates the complete iOS workflow with both RAG-enabled and baseline analysis
"""

import requests
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
AI_ADVISOR_URL = "http://127.0.0.1:5100"
RAG_SERVICE_URL = "http://127.0.0.1:5400"

# Test image
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
NC = '\033[0m'

def print_header(text):
    """Print section header"""
    print(f"\n{CYAN}{'='*80}{NC}")
    print(f"{CYAN}{BOLD}{text}{NC}")
    print(f"{CYAN}{'='*80}{NC}\n")

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

def check_services():
    """Check that all required services are running"""
    print_step(1, "Checking Services")
    
    services = [
        ("Job Service", f"{JOB_SERVICE_URL}/health", 5005),
        ("AI Advisor Service", f"{AI_ADVISOR_URL}/health", 5100),
        ("RAG Service", f"{RAG_SERVICE_URL}/health", 5400),
    ]
    
    all_up = True
    for name, url, port in services:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print_success(f"{name} (port {port}) - UP")
            else:
                print_error(f"{name} (port {port}) - DOWN (status {resp.status_code})")
                all_up = False
        except Exception as e:
            print_error(f"{name} (port {port}) - DOWN ({e})")
            all_up = False
    
    if not all_up:
        print_error("Not all services are running. Please start them first.")
        sys.exit(1)
    
    print()

def upload_image(enable_rag=False):
    """Upload image and start analysis (simulates iOS upload)"""
    mode = "RAG-ENABLED" if enable_rag else "BASELINE"
    print_step(2, f"Uploading Image ({mode})")
    
    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print_error(f"Test image not found: {TEST_IMAGE}")
        sys.exit(1)
    
    print_info(f"Image: {TEST_IMAGE}")
    print_info(f"Advisor: {ADVISOR}")
    print_info(f"RAG Enabled: {enable_rag}")
    
    with open(image_path, 'rb') as f:
        files = {'image': (image_path.name, f, 'image/jpeg')}
        data = {
            'advisor': ADVISOR,
            'enable_rag': 'true' if enable_rag else 'false'
        }
        
        try:
            resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=30)
            
            if resp.status_code in [200, 201]:
                result = resp.json()
                job_id = result['job_id']
                stream_url = result['stream_url']
                print_success(f"Upload successful - Job ID: {job_id}")
                print_info(f"Stream URL: {stream_url}")
                return job_id, stream_url
            else:
                print_error(f"Upload failed: {resp.status_code}")
                print_error(f"Response: {resp.text[:500]}")
                sys.exit(1)
                
        except Exception as e:
            print_error(f"Upload exception: {e}")
            sys.exit(1)

def monitor_progress(job_id):
    """Monitor job progress (simulates iOS SSE monitoring)"""
    print_step(3, "Monitoring Progress")
    
    max_retries = 60  # 60 seconds timeout
    retry = 0
    
    while retry < max_retries:
        try:
            resp = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=5)
            
            if resp.status_code == 200:
                status = resp.json()
                state = status.get('status', 'unknown')
                progress = status.get('progress_percentage', 0)
                
                if state == 'completed' or state == 'done':
                    print_success(f"Analysis complete (100%)")
                    return True
                elif state == 'failed':
                    print_error(f"Analysis failed: {status.get('error', 'Unknown error')}")
                    return False
                else:
                    print_info(f"Progress: {progress}% - {state}")
                    
            time.sleep(1)
            retry += 1
            
        except Exception as e:
            print_error(f"Status check failed: {e}")
            time.sleep(1)
            retry += 1
    
    print_error("Timeout waiting for analysis to complete")
    return False

def get_analysis_html(job_id):
    """Get analysis HTML output (simulates iOS fetching results)"""
    print_step(4, "Fetching Analysis Results")
    
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=10)
        
        if resp.status_code == 200:
            html = resp.text
            print_success(f"Retrieved HTML output ({len(html)} bytes)")
            return html
        else:
            print_error(f"Failed to get analysis: {resp.status_code}")
            return None
            
    except Exception as e:
        print_error(f"Exception getting analysis: {e}")
        return None

def save_output(html, mode):
    """Save HTML output to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ios_e2e_{mode.lower()}_{timestamp}.html"
    filepath = Path("analysis_output") / filename
    
    # Create directory if needed
    filepath.parent.mkdir(exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print_success(f"Saved to: {filepath}")
    return filepath

def extract_key_feedback(html):
    """Extract key feedback sections from HTML for comparison"""
    import re
    
    # Extract main feedback text
    feedback_match = re.search(r'<div class="feedback-text">(.*?)</div>', html, re.DOTALL)
    if feedback_match:
        feedback = feedback_match.group(1)
        # Remove HTML tags
        feedback = re.sub(r'<[^>]+>', '', feedback)
        # Clean up whitespace
        feedback = ' '.join(feedback.split())
        return feedback[:500]  # First 500 chars
    return "No feedback found"

def compare_outputs(baseline_html, rag_html):
    """Compare baseline and RAG outputs"""
    print_header("COMPARISON: RAG vs BASELINE")
    
    baseline_feedback = extract_key_feedback(baseline_html)
    rag_feedback = extract_key_feedback(rag_html)
    
    print(f"{BOLD}BASELINE OUTPUT (first 500 chars):{NC}")
    print(f"{baseline_feedback}\n")
    
    print(f"{BOLD}RAG-ENABLED OUTPUT (first 500 chars):{NC}")
    print(f"{rag_feedback}\n")
    
    # Check if outputs are different
    if baseline_feedback == rag_feedback:
        print_error("⚠️  WARNING: Outputs are IDENTICAL")
        print_info("RAG may not be working correctly")
    else:
        print_success("✓ Outputs are DIFFERENT")
        print_info("RAG is augmenting the analysis")
    
    # Calculate similarity
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, baseline_feedback, rag_feedback).ratio()
    print(f"\n{BOLD}Similarity:{NC} {similarity*100:.1f}%")
    
    if similarity > 0.9:
        print_error("⚠️  Outputs are >90% similar - RAG may not be working")
    elif similarity > 0.7:
        print_info("Outputs are 70-90% similar - RAG is making subtle changes")
    else:
        print_success("Outputs are <70% similar - RAG is significantly augmenting")

def run_e2e_test(enable_rag=False):
    """Run complete end-to-end test"""
    mode = "RAG-ENABLED" if enable_rag else "BASELINE"
    print_header(f"iOS End-to-End Test: {mode}")
    
    # Upload and analyze
    job_id, stream_url = upload_image(enable_rag=enable_rag)
    
    # Monitor progress
    if not monitor_progress(job_id):
        print_error("Analysis failed")
        return None
    
    # Get results
    html = get_analysis_html(job_id)
    if not html:
        print_error("Failed to get results")
        return None
    
    # Save output
    filepath = save_output(html, mode)
    
    print_success(f"{mode} test complete!")
    print()
    
    return html

def main():
    """Main test flow"""
    print_header("iOS End-to-End Test: RAG vs Baseline Comparison")
    print(f"Test Image: {TEST_IMAGE}")
    print(f"Advisor: {ADVISOR}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check services
    check_services()
    
    # Run baseline test
    print_header("TEST 1: BASELINE (No RAG)")
    baseline_html = run_e2e_test(enable_rag=False)
    
    if not baseline_html:
        print_error("Baseline test failed")
        sys.exit(1)
    
    # Wait between tests
    print_info("Waiting 5 seconds before RAG test...")
    time.sleep(5)
    
    # Run RAG test
    print_header("TEST 2: RAG-ENABLED")
    rag_html = run_e2e_test(enable_rag=True)
    
    if not rag_html:
        print_error("RAG test failed")
        sys.exit(1)
    
    # Compare outputs
    compare_outputs(baseline_html, rag_html)
    
    # Final summary
    print_header("TEST COMPLETE")
    print_success("Both baseline and RAG-enabled tests completed successfully")
    print_info("Check analysis_output/ directory for HTML files")
    print()

if __name__ == "__main__":
    main()

