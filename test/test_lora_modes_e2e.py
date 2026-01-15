#!/usr/bin/env python3
"""
LoRA Modes End-to-End Tests - Isolated testing for LoRA flows

Tests LoRA-based analysis modes independently:
  - Pure LoRA mode (mode=lora)
  - RAG+LoRA mode (mode=rag+lora)
  - LoRA with embeddings
  - RAG+LoRA with embeddings

Each test can be run in isolation, allowing you to compare output/timing
across different LoRA configurations without running baseline/RAG tests.

Usage:
    # Run pure LoRA test
    python3 test/test_lora_modes_e2e.py --mode=lora

    # Run RAG+LoRA test
    python3 test/test_lora_modes_e2e.py --mode=rag+lora

    # Run LoRA with embeddings
    python3 test/test_lora_modes_e2e.py --mode=lora --embeddings

    # Run all LoRA tests
    python3 test/test_lora_modes_e2e.py --all

    # Compare all LoRA modes side by side
    python3 test/test_lora_modes_e2e.py --compare

    # Verbose output
    python3 test/test_lora_modes_e2e.py --mode=lora --verbose

    # With timing
    python3 test/test_lora_modes_e2e.py --mode=rag+lora --timing
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
AI_SERVICE_URL = "http://127.0.0.1:5100"
AI_SERVICE_HEALTH = f"{AI_SERVICE_URL}/health"
JOB_SERVICE_HEALTH = f"{JOB_SERVICE_URL}/health"
TEST_IMAGE_PATH = PROJECT_ROOT / "source" / "mike-shrub.jpg"
ADVISOR = "ansel"

# Color codes
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
MAGENTA = '\033[0;35m'
NC = '\033[0m'

# Test results
test_results = {
    "passed": [],
    "failed": [],
    "skipped": []
}

# Timing data
timing_data = {}


def print_header(text):
    """Print section header."""
    print(f"\n{BLUE}{'='*80}{NC}")
    print(f"{BLUE}{text:^80}{NC}")
    print(f"{BLUE}{'='*80}{NC}\n")


def print_subheader(text):
    """Print subsection header."""
    print(f"\n{CYAN}{text}{NC}")
    print(f"{CYAN}{'-' * len(text)}{NC}\n")


def print_test(name):
    """Print test name."""
    print(f"{YELLOW}[TEST]{NC} {name}...", end=" ", flush=True)


def print_pass(msg=""):
    """Print pass result."""
    print(f"{GREEN}✓ PASS{NC} {msg}")


def print_fail(msg=""):
    """Print fail result."""
    print(f"{RED}✗ FAIL{NC} {msg}")


def print_skip(msg=""):
    """Print skip result."""
    print(f"{YELLOW}⊘ SKIP{NC} {msg}")


def print_info(msg):
    """Print info message."""
    print(f"{CYAN}ℹ{NC} {msg}")


def check_services():
    """Check if both services are running. Fail immediately if not."""
    print_header("Service Health Check")

    services_ok = True
    down_services = []

    # Check Job Service
    print_test("Job Service")
    try:
        response = requests.get(JOB_SERVICE_HEALTH, timeout=5)
        if response.status_code == 200:
            print_pass(f"Running at {JOB_SERVICE_URL}")
        else:
            print_fail(f"Status {response.status_code}")
            services_ok = False
            down_services.append("Job Service")
    except Exception as e:
        print_fail(f"Cannot connect: {e}")
        services_ok = False
        down_services.append("Job Service")

    # Check AI Advisor Service
    print_test("AI Advisor Service")
    try:
        response = requests.get(AI_SERVICE_HEALTH, timeout=5)
        if response.status_code == 200:
            print_pass(f"Running at {AI_SERVICE_URL}")
        else:
            print_fail(f"Status {response.status_code}")
            services_ok = False
            down_services.append("AI Advisor Service")
    except Exception as e:
        print_fail(f"Cannot connect: {e}")
        services_ok = False
        down_services.append("AI Advisor Service")

    if not services_ok:
        print()
        print(f"{RED}ERROR: Required services are not running:{NC}")
        for service in down_services:
            print(f"  ✗ {service}")
        print()
        print(f"To start services, run:")
        print(f"  cd {PROJECT_ROOT}")
        print(f"  ./start_services.sh")
        print()
        sys.exit(1)

    print()
    print_pass("All services ready")
    print()


def check_test_image():
    """Check if test image exists."""
    if not TEST_IMAGE_PATH.exists():
        print(f"{RED}ERROR: Test image not found at {TEST_IMAGE_PATH}{NC}")
        print(f"Please ensure the image exists or update TEST_IMAGE_PATH")
        sys.exit(1)


def upload_image_for_mode(mode, enable_embeddings=False):
    """Upload image for analysis in specified mode."""
    print_test(f"Uploading image for mode={mode}")

    with open(TEST_IMAGE_PATH, 'rb') as f:
        files = {'image': (TEST_IMAGE_PATH.name, f, 'image/jpeg')}
        data = {
            'advisor': ADVISOR,
            'mode': mode
        }
        if enable_embeddings:
            data['enable_embeddings'] = 'true'

        try:
            resp = requests.post(
                f"{JOB_SERVICE_URL}/upload",
                files=files,
                data=data,
                timeout=30
            )

            if resp.status_code in [200, 201]:
                result = resp.json()
                job_id = result.get('job_id')
                print_pass(f"Job ID: {job_id}")
                return job_id
            else:
                print_fail(f"HTTP {resp.status_code}")
                return None

        except Exception as e:
            print_fail(f"Error: {e}")
            return None


def poll_job_status(job_id, timeout_seconds=600):
    """Poll job status until completion or timeout."""
    print_test("Polling job status")

    start_time = time.time()
    last_status = None

    while time.time() - start_time < timeout_seconds:
        try:
            resp = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=5)

            if resp.status_code == 200:
                status = resp.json()
                current_status = status.get('status', 'unknown')

                # Only log state changes
                if current_status != last_status:
                    last_status = current_status
                    progress = status.get('progress_percentage', 0)
                    thinking = status.get('llm_thinking', '')
                    
                    if thinking:
                        print_info(f"Status: {current_status} ({progress}%) - {thinking[:80]}")
                    else:
                        print_info(f"Status: {current_status} ({progress}%)")

                if current_status in ['completed', 'done']:
                    print_pass("Analysis complete")
                    return True
                elif current_status == 'failed':
                    error = status.get('error', 'Unknown error')
                    print_fail(f"Analysis failed: {error}")
                    return False

            time.sleep(2)

        except Exception as e:
            print_fail(f"Status check failed: {e}")
            return False

    print_fail(f"Timeout waiting for analysis (>{timeout_seconds}s)")
    return False


def fetch_analysis_result(job_id):
    """Fetch analysis result HTML."""
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=10)

        if resp.status_code == 200:
            return resp.text
        else:
            return None

    except Exception as e:
        print_info(f"Could not fetch HTML: {e}")
        return None


def fetch_analysis_json(job_id):
    """Fetch analysis as JSON."""
    try:
        resp = requests.get(
            f"{JOB_SERVICE_URL}/analysis/{job_id}",
            headers={'Accept': 'application/json'},
            timeout=10
        )

        if resp.status_code == 200:
            return resp.json()
        else:
            return None

    except Exception as e:
        print_info(f"Could not fetch JSON: {e}")
        return None


def validate_analysis_output(result, mode):
    """Validate analysis output structure and content."""
    print_subheader("Output Validation")

    required_fields = ['dimensional_analysis', 'overall_grade']
    
    # Check required fields
    print_test("Required fields")
    missing = [f for f in required_fields if f not in result]
    if missing:
        print_fail(f"Missing: {', '.join(missing)}")
        return False
    print_pass("All fields present")

    # Check dimensional analysis
    print_test("Dimensional analysis")
    dims = result.get('dimensional_analysis', {})
    if len(dims) >= 8:
        print_pass(f"Has {len(dims)} dimensions")
    else:
        print_fail(f"Only {len(dims)} dimensions (expected ≥8)")
        return False

    # Check overall grade
    print_test("Overall grade")
    grade = result.get('overall_grade')
    valid_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F', 'N/A']
    if grade in valid_grades:
        print_pass(f"Grade: {grade}")
    else:
        print_fail(f"Invalid grade: {grade}")
        return False

    # Mode-specific validation
    print_test("Mode-specific validation")
    mode_used = result.get('mode_used', 'unknown')
    expected_modes = {'lora': 'lora', 'rag+lora': 'rag_lora'}
    expected = expected_modes.get(mode, mode)
    
    if mode_used == expected:
        print_pass(f"Mode: {mode_used}")
    else:
        print_fail(f"Expected '{expected}', got '{mode_used}'")
        return False

    # For RAG+LoRA, check metadata
    if mode == 'rag+lora':
        print_test("RAG+LoRA metadata")
        metadata = result.get('metadata', {})
        timing_fields = ['pass1_duration', 'pass2_duration', 'query_duration']
        found = [f for f in timing_fields if f in metadata]
        if found:
            print_pass(f"Found timing: {', '.join(found)}")
        else:
            print_skip("No timing metadata")

    return True


def test_lora_pure(verbose=False, timing=False):
    """Test pure LoRA mode (single-pass fine-tuned analysis)."""
    print_header("Test 1: Pure LoRA Mode")

    if not TEST_IMAGE_PATH.exists():
        print_skip("Test image not found")
        test_results["skipped"].append("LoRA Pure")
        return False

    start_time = time.time()

    # Upload
    job_id = upload_image_for_mode('lora')
    if not job_id:
        test_results["failed"].append("LoRA Pure")
        return False

    # Wait for completion
    success = poll_job_status(job_id)
    if not success:
        test_results["failed"].append("LoRA Pure")
        return False

    # Fetch results
    print_test("Fetching results")
    result = fetch_analysis_json(job_id)
    if not result:
        print_fail("Could not fetch results")
        test_results["failed"].append("LoRA Pure")
        return False
    print_pass()

    # Validate
    if not validate_analysis_output(result, 'lora'):
        test_results["failed"].append("LoRA Pure")
        return False

    duration = time.time() - start_time
    timing_data['lora_pure'] = duration

    if timing:
        print_subheader("Timing")
        print(f"Total duration: {duration:.2f}s")

    test_results["passed"].append("LoRA Pure")
    print_pass("Test passed")
    return True


def test_rag_lora(verbose=False, timing=False):
    """Test RAG+LoRA mode (two-pass with retrieval)."""
    print_header("Test 2: RAG+LoRA Mode")

    if not TEST_IMAGE_PATH.exists():
        print_skip("Test image not found")
        test_results["skipped"].append("RAG+LoRA")
        return False

    start_time = time.time()

    # Upload
    job_id = upload_image_for_mode('rag+lora')
    if not job_id:
        test_results["failed"].append("RAG+LoRA")
        return False

    # Wait for completion
    success = poll_job_status(job_id, timeout_seconds=900)  # Longer timeout for two-pass
    if not success:
        test_results["failed"].append("RAG+LoRA")
        return False

    # Fetch results
    print_test("Fetching results")
    result = fetch_analysis_json(job_id)
    if not result:
        print_fail("Could not fetch results")
        test_results["failed"].append("RAG+LoRA")
        return False
    print_pass()

    # Validate
    if not validate_analysis_output(result, 'rag+lora'):
        test_results["failed"].append("RAG+LoRA")
        return False

    duration = time.time() - start_time
    timing_data['rag_lora'] = duration

    if timing:
        print_subheader("Timing")
        print(f"Total duration: {duration:.2f}s")
        metadata = result.get('metadata', {})
        if 'pass1_duration' in metadata:
            print(f"  Pass 1: {metadata['pass1_duration']:.2f}s")
        if 'query_duration' in metadata:
            print(f"  Query:  {metadata['query_duration']:.2f}s")
        if 'pass2_duration' in metadata:
            print(f"  Pass 2: {metadata['pass2_duration']:.2f}s")

    test_results["passed"].append("RAG+LoRA")
    print_pass("Test passed")
    return True


def test_lora_with_embeddings(verbose=False, timing=False):
    """Test LoRA with CLIP embeddings enabled."""
    print_header("Test 3: LoRA with Embeddings")

    if not TEST_IMAGE_PATH.exists():
        print_skip("Test image not found")
        test_results["skipped"].append("LoRA with Embeddings")
        return False

    start_time = time.time()

    # Upload with embeddings enabled
    job_id = upload_image_for_mode('lora', enable_embeddings=True)
    if not job_id:
        test_results["failed"].append("LoRA with Embeddings")
        return False

    # Wait for completion
    success = poll_job_status(job_id)
    if not success:
        test_results["failed"].append("LoRA with Embeddings")
        return False

    # Fetch results
    print_test("Fetching results")
    result = fetch_analysis_json(job_id)
    if not result:
        print_fail("Could not fetch results")
        test_results["failed"].append("LoRA with Embeddings")
        return False
    print_pass()

    # Validate
    if not validate_analysis_output(result, 'lora'):
        test_results["failed"].append("LoRA with Embeddings")
        return False

    # Check for embeddings
    print_test("Embeddings support")
    similar_images = result.get('similar_images')
    if similar_images and isinstance(similar_images, list):
        print_pass(f"Found {len(similar_images)} similar images")
    else:
        print_skip("similar_images not populated (embeddings may not be enabled)")

    duration = time.time() - start_time
    timing_data['lora_embeddings'] = duration

    if timing:
        print_subheader("Timing")
        print(f"Total duration: {duration:.2f}s")

    test_results["passed"].append("LoRA with Embeddings")
    print_pass("Test passed")
    return True


def test_rag_lora_with_embeddings(verbose=False, timing=False):
    """Test RAG+LoRA with embeddings enabled."""
    print_header("Test 4: RAG+LoRA with Embeddings")

    if not TEST_IMAGE_PATH.exists():
        print_skip("Test image not found")
        test_results["skipped"].append("RAG+LoRA with Embeddings")
        return False

    start_time = time.time()

    # Upload with embeddings enabled
    job_id = upload_image_for_mode('rag+lora', enable_embeddings=True)
    if not job_id:
        test_results["failed"].append("RAG+LoRA with Embeddings")
        return False

    # Wait for completion
    success = poll_job_status(job_id, timeout_seconds=900)
    if not success:
        test_results["failed"].append("RAG+LoRA with Embeddings")
        return False

    # Fetch results
    print_test("Fetching results")
    result = fetch_analysis_json(job_id)
    if not result:
        print_fail("Could not fetch results")
        test_results["failed"].append("RAG+LoRA with Embeddings")
        return False
    print_pass()

    # Validate
    if not validate_analysis_output(result, 'rag+lora'):
        test_results["failed"].append("RAG+LoRA with Embeddings")
        return False

    # Check for embeddings
    print_test("Embeddings support")
    similar_images = result.get('similar_images')
    if similar_images and isinstance(similar_images, list):
        print_pass(f"Found {len(similar_images)} similar images")
    else:
        print_skip("similar_images not populated (embeddings may not be enabled)")

    duration = time.time() - start_time
    timing_data['rag_lora_embeddings'] = duration

    if timing:
        print_subheader("Timing")
        print(f"Total duration: {duration:.2f}s")
        metadata = result.get('metadata', {})
        if 'pass1_duration' in metadata:
            print(f"  Pass 1: {metadata['pass1_duration']:.2f}s")
        if 'query_duration' in metadata:
            print(f"  Query:  {metadata['query_duration']:.2f}s")
        if 'pass2_duration' in metadata:
            print(f"  Pass 2: {metadata['pass2_duration']:.2f}s")

    test_results["passed"].append("RAG+LoRA with Embeddings")
    print_pass("Test passed")
    return True


def print_summary():
    """Print test summary."""
    print_header("Test Summary")

    total_passed = len(test_results["passed"])
    total_failed = len(test_results["failed"])
    total_skipped = len(test_results["skipped"])
    total_tests = total_passed + total_failed + total_skipped

    if total_passed > 0:
        print(f"{GREEN}Passed:{NC}  {total_passed}")
        for test in test_results["passed"]:
            print(f"  {GREEN}✓{NC} {test}")

    if total_failed > 0:
        print(f"\n{RED}Failed:{NC}  {total_failed}")
        for test in test_results["failed"]:
            print(f"  {RED}✗{NC} {test}")

    if total_skipped > 0:
        print(f"\n{YELLOW}Skipped:{NC} {total_skipped}")
        for test in test_results["skipped"]:
            print(f"  {YELLOW}⊘{NC} {test}")

    print(f"\n{BLUE}{'='*80}{NC}")

    if total_failed == 0 and total_passed > 0:
        print(f"{GREEN}All tests passed! ({total_passed}/{total_tests}){NC}")
        return 0
    elif total_failed > 0:
        print(f"{RED}Some tests failed ({total_failed}/{total_tests}){NC}")
        return 1
    else:
        print(f"{YELLOW}No tests passed ({total_skipped} skipped){NC}")
        return 2


def print_timing_summary():
    """Print timing comparison."""
    if not timing_data:
        return

    print_header("Timing Comparison")

    max_name_len = max(len(name) for name in timing_data.keys())
    for test_name in sorted(timing_data.keys()):
        duration = timing_data[test_name]
        print(f"{test_name:<{max_name_len}} : {duration:>8.2f}s")

    # Calculate comparison
    if 'lora_pure' in timing_data and 'rag_lora' in timing_data:
        pure_time = timing_data['lora_pure']
        rag_lora_time = timing_data['rag_lora']
        ratio = rag_lora_time / pure_time
        print()
        print(f"RAG+LoRA vs LoRA: {ratio:.2f}x slower")


def main():
    """Run LoRA E2E tests."""
    parser = argparse.ArgumentParser(
        description="LoRA Modes End-to-End Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run pure LoRA test
  %(prog)s --mode=lora

  # Run RAG+LoRA test
  %(prog)s --mode=rag+lora

  # Run LoRA with embeddings
  %(prog)s --mode=lora --embeddings

  # Run all LoRA tests
  %(prog)s --all

  # Compare all modes with timing
  %(prog)s --compare --timing
        """
    )
    parser.add_argument('--mode', choices=['lora', 'rag+lora'],
                        help='Specific LoRA mode to test')
    parser.add_argument('--embeddings', action='store_true',
                        help='Enable CLIP embeddings for visual similarity')
    parser.add_argument('--all', action='store_true',
                        help='Run all LoRA mode tests')
    parser.add_argument('--compare', action='store_true',
                        help='Run all tests for comparison (equivalent to --all)')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('--timing', action='store_true',
                        help='Include timing measurements')

    args = parser.parse_args()

    print_header("LoRA Modes End-to-End Tests")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Job Service: {JOB_SERVICE_URL}")
    print(f"AI Service: {AI_SERVICE_URL}")
    print(f"Test Image: {TEST_IMAGE_PATH}")
    print()

    # Pre-flight checks
    check_services()
    check_test_image()

    # Determine which tests to run
    if args.compare or args.all:
        run_tests = ['lora', 'rag+lora']
        if args.embeddings:
            run_tests.extend(['lora_embeddings', 'rag+lora_embeddings'])
    elif args.mode:
        if args.mode == 'lora':
            run_tests = ['lora']
            if args.embeddings:
                run_tests = ['lora_embeddings']
        elif args.mode == 'rag+lora':
            run_tests = ['rag+lora']
            if args.embeddings:
                run_tests = ['rag+lora_embeddings']
    else:
        # Default: run lora
        run_tests = ['lora']

    # Run tests
    print_header("Running Tests")
    try:
        if 'lora' in run_tests:
            test_lora_pure(verbose=args.verbose, timing=args.timing)
            if len(run_tests) > 1:
                time.sleep(2)

        if 'lora_embeddings' in run_tests:
            test_lora_with_embeddings(verbose=args.verbose, timing=args.timing)
            if len(run_tests) > 1:
                time.sleep(2)

        if 'rag+lora' in run_tests:
            test_rag_lora(verbose=args.verbose, timing=args.timing)
            if len(run_tests) > 1:
                time.sleep(2)

        if 'rag+lora_embeddings' in run_tests:
            test_rag_lora_with_embeddings(verbose=args.verbose, timing=args.timing)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{NC}")
        test_results["failed"].append("Interrupted")
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{NC}")
        import traceback
        traceback.print_exc()
        test_results["failed"].append("Unexpected error")

    # Print summaries
    if args.timing:
        print_timing_summary()

    exit_code = print_summary()
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
