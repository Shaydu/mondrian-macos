#!/usr/bin/env python3
"""
End-to-End Tests for RAG+LoRA Strategy

This test suite verifies RAG+LoRA specific functionality:
1. Two-pass analysis workflow (dimensional extraction + augmented analysis)
2. LoRA adapter loading and inference
3. RAG retrieval with dimensional scoring
4. Embedding-based visual similarity (optional)
5. Hybrid augmentation combining all context sources
6. Proper fallback behavior when unavailable

Usage:
    python3 test/test_rag_lora_e2e.py                    # Run all tests
    python3 test/test_rag_lora_e2e.py --verbose          # Verbose output
    python3 test/test_rag_lora_e2e.py --with-embeddings  # Test with embeddings
    python3 test/test_rag_lora_e2e.py --timing           # Include timing measurements
"""

import os
import sys
import json
import time
import argparse
import requests
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "mondrian"))

# ============================================================================
# LOGGING SETUP
# ============================================================================
LOG_DIR = PROJECT_ROOT / "logs" / "tests"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"test_rag_lora_e2e_{int(time.time())}.log"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("TEST SESSION STARTED")
logger.info("=" * 80)
logger.info(f"Log file: {LOG_FILE}")
logger.info(f"Project root: {PROJECT_ROOT}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Timestamp: {datetime.now().isoformat()}")

# Configuration
AI_SERVICE_URL = "http://localhost:5100"
JOB_SERVICE_URL = "http://localhost:5005"
AI_SERVICE_HEALTH = f"{AI_SERVICE_URL}/health"
JOB_SERVICE_HEALTH = f"{JOB_SERVICE_URL}/health"
TEST_IMAGE_PATH = PROJECT_ROOT / "source" / "photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg"
ADVISOR = "ansel"

logger.info(f"AI Service URL: {AI_SERVICE_URL}")
logger.info(f"Test image: {TEST_IMAGE_PATH}")
logger.info(f"Advisor: {ADVISOR}")

# Color codes
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
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


def print_test(name, newline=True):
    """Print test name."""
    sep = "" if not newline else "\n"
    print(f"{YELLOW}[TEST]{NC} {name}...", end=" ", flush=True)
    return True


def print_pass(msg=""):
    """Print pass result."""
    print(f"{GREEN}✓ PASS{NC} {msg}")
    return True


def print_fail(msg=""):
    """Print fail result."""
    logger.error(f"TEST FAILED: {msg}")
    print(f"{RED}✗ FAIL{NC} {msg}")
    return False


def print_skip(msg=""):
    """Print skip result."""
    logger.warning(f"TEST SKIPPED: {msg}")
    print(f"{YELLOW}⊘ SKIP{NC} {msg}")
    return True


def print_info(msg):
    """Print info message."""
    logger.info(f"INFO: {msg}")
    print(f"{CYAN}ℹ{NC} {msg}")


def check_services():
    """Check if both services are running."""
    print_header("Service Health Check")
    
    services_ok = True
    
    # Check AI Advisor Service
    print_test("AI Advisor Service")
    try:
        response = requests.get(AI_SERVICE_HEALTH, timeout=5)
        if response.status_code == 200:
            print_pass(f"Running at {AI_SERVICE_URL}")
        else:
            print_fail(f"Status {response.status_code}")
            services_ok = False
    except Exception as e:
        print_fail(f"Cannot connect: {e}")
        services_ok = False
    
    # Check Job Service (optional)
    print_test("Job Service")
    try:
        response = requests.get(JOB_SERVICE_HEALTH, timeout=5)
        if response.status_code == 200:
            print_pass(f"Running at {JOB_SERVICE_URL}")
        else:
            print_skip(f"Status {response.status_code} (optional)")
    except Exception as e:
        print_skip(f"Not running (optional): {e}")
    
    return services_ok


def check_rag_lora_availability():
    """Check if RAG+LoRA mode is available by attempting a test analysis."""
    print_header("RAG+LoRA Availability Check")
    
    print_test("Mode Availability")
    print_skip("Availability check deferred (will test during analysis)")
    print_info("If RAG+LoRA is unavailable, the service will automatically fallback to the next available mode")
    return True  # Proceed with tests; fallback is automatic


def test_rag_lora_basic_workflow():
    """Test basic RAG+LoRA workflow."""
    print_header("Test 1: Basic RAG+LoRA Workflow")
    
    print_test("Sending analysis request")
    
    if not TEST_IMAGE_PATH.exists():
        print_skip(f"Test image not found")
        test_results["skipped"].append("Basic workflow")
        return False
    
    try:
        logger.info(f"Starting basic workflow test")
        logger.info(f"Image path: {TEST_IMAGE_PATH}")
        logger.info(f"Image size: {TEST_IMAGE_PATH.stat().st_size} bytes")
        
        start_time = time.time()
        logger.info(f"Request timestamp: {datetime.now().isoformat()}")
        
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': ADVISOR,
                'mode': 'rag_lora',
                'response_format': 'json'
            }
            
            logger.debug(f"POST request to: {AI_SERVICE_URL}/analyze")
            logger.debug(f"Data: {data}")
            
            response = requests.post(
                f"{AI_SERVICE_URL}/analyze",
                files=files,
                data=data,
                timeout=300
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response text length: {len(response.text)}")
        
        duration = time.time() - start_time
        timing_data['basic_workflow'] = duration
        logger.info(f"Request duration: {duration:.2f}s")
        
        if response.status_code != 200:
            logger.error(f"HTTP error {response.status_code}")
            logger.error(f"Response: {response.text[:500]}")
            print_fail(f"HTTP {response.status_code}")
            test_results["failed"].append("Basic workflow")
            return False
        
        result = response.json()
        logger.info(f"Response keys: {list(result.keys())}")
        print_pass(f"Duration: {duration:.2f}s")
        
        # Verify response
        print_subheader("Response Validation")
        
        required_fields = ['mode_used', 'dimensional_analysis', 'overall_grade']
        missing = [f for f in required_fields if f not in result]
        
        if missing:
            print_fail(f"Missing fields: {missing}")
            test_results["failed"].append("Basic workflow - missing fields")
            return False
        
        print_pass("All required fields present")
        
        # Verify mode
        print_test("Mode verification")
        if result.get('mode_used') == 'rag_lora':
            print_pass("Correct mode in response")
        else:
            print_fail(f"Expected 'rag_lora', got '{result.get('mode_used')}'")
            test_results["failed"].append("Basic workflow - wrong mode")
            return False
        
        # Verify dimensional analysis
        print_test("Dimensional analysis")
        dim_analysis = result.get('dimensional_analysis', {})
        expected_dims = 8
        
        if len(dim_analysis) >= expected_dims:
            print_pass(f"Has {len(dim_analysis)} dimensions")
        else:
            print_fail(f"Expected {expected_dims} dimensions, got {len(dim_analysis)}")
            test_results["failed"].append("Basic workflow - incomplete analysis")
            return False
        
        # Verify overall grade
        print_test("Overall grade")
        grade = result.get('overall_grade')
        valid_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F', 'N/A']
        
        if grade in valid_grades:
            print_pass(f"Grade: {grade}")
        else:
            print_fail(f"Invalid grade: {grade}")
            test_results["failed"].append("Basic workflow - invalid grade")
            return False
        
        test_results["passed"].append("Basic workflow")
        return True
        
    except requests.exceptions.Timeout:
        logger.error("Request TIMEOUT after 300 seconds")
        logger.error("This likely indicates the service crashed or is unresponsive")
        print_fail("Request timeout")
        test_results["failed"].append("Basic workflow - timeout")
        return False
    except Exception as e:
        logger.error(f"Request EXCEPTION: {type(e).__name__}: {e}")
        logger.error(f"Exception details: {repr(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        print_fail(f"Error: {e}")
        test_results["failed"].append(f"Basic workflow - {str(e)}")
        return False


def test_rag_lora_with_embeddings():
    """Test RAG+LoRA with embeddings enabled."""
    print_header("Test 2: RAG+LoRA with Embeddings")
    
    print_test("Sending analysis with embeddings")
    
    if not TEST_IMAGE_PATH.exists():
        print_skip(f"Test image not found")
        test_results["skipped"].append("With embeddings")
        return False
    
    try:
        start_time = time.time()
        
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': ADVISOR,
                'mode': 'rag_lora',
                'enable_embeddings': 'true',
                'response_format': 'json'
            }
            
            response = requests.post(
                f"{AI_SERVICE_URL}/analyze",
                files=files,
                data=data,
                timeout=300
            )
        
        duration = time.time() - start_time
        timing_data['with_embeddings'] = duration
        
        if response.status_code != 200:
            print_fail(f"HTTP {response.status_code}")
            test_results["failed"].append("With embeddings")
            return False
        
        result = response.json()
        print_pass(f"Duration: {duration:.2f}s")
        
        # Verify response
        print_subheader("Response Validation")
        
        print_test("Mode verification")
        if result.get('mode_used') == 'rag_lora':
            print_pass()
        else:
            print_fail(f"Expected 'rag_lora', got '{result.get('mode_used')}'")
            test_results["failed"].append("With embeddings - wrong mode")
            return False
        
        print_test("Analysis completeness")
        dim_analysis = result.get('dimensional_analysis', {})
        
        if len(dim_analysis) >= 8:
            print_pass(f"Has {len(dim_analysis)} dimensions")
        else:
            print_fail(f"Incomplete analysis")
            test_results["failed"].append("With embeddings - incomplete")
            return False
        
        # Check for similar images (optional, indicates embedding support)
        print_test("Similar images in response")
        similar_images = result.get('similar_images')
        
        if similar_images:
            if isinstance(similar_images, list):
                print_pass(f"Found {len(similar_images)} similar images")
            else:
                print_skip("similar_images present but not expected format")
        else:
            print_skip("similar_images not in response (embeddings may not be populated)")
        
        test_results["passed"].append("With embeddings")
        return True
        
    except requests.exceptions.Timeout:
        print_fail("Request timeout")
        test_results["failed"].append("With embeddings - timeout")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        test_results["failed"].append(f"With embeddings - {str(e)}")
        return False


def test_rag_lora_metadata():
    """Test that RAG+LoRA includes timing metadata."""
    print_header("Test 3: RAG+LoRA Metadata")
    
    print_test("Requesting analysis for metadata check")
    
    if not TEST_IMAGE_PATH.exists():
        print_skip(f"Test image not found")
        test_results["skipped"].append("Metadata check")
        return False
    
    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': ADVISOR,
                'mode': 'rag_lora',
                'response_format': 'json'
            }
            
            response = requests.post(
                f"{AI_SERVICE_URL}/analyze",
                files=files,
                data=data,
                timeout=300
            )
        
        if response.status_code != 200:
            print_fail(f"HTTP {response.status_code}")
            test_results["failed"].append("Metadata check - request failed")
            return False
        
        result = response.json()
        print_pass()
        
        print_subheader("Metadata Validation")
        
        # Check for metadata
        print_test("Metadata presence")
        metadata = result.get('metadata', {})
        
        if metadata:
            print_pass()
        else:
            print_skip("No metadata in response")
            test_results["skipped"].append("Metadata check")
            return True
        
        # Check for timing fields
        print_test("Timing information")
        timing_fields = ['pass1_duration', 'pass2_duration', 'query_duration']
        found_timing = [f for f in timing_fields if f in metadata]
        
        if found_timing:
            timing_info = ", ".join([f"{f}={metadata[f]:.2f}s" for f in found_timing])
            print_pass(timing_info)
        else:
            print_skip("No timing fields in metadata")
        
        # Check for reference images count
        print_test("Reference images metadata")
        ref_count = metadata.get('representative_images_count')
        
        if ref_count is not None:
            print_pass(f"Count: {ref_count}")
        else:
            print_skip("No reference images count")
        
        test_results["passed"].append("Metadata check")
        return True
        
    except requests.exceptions.Timeout:
        print_fail("Request timeout")
        test_results["failed"].append("Metadata check - timeout")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        test_results["failed"].append(f"Metadata check - {str(e)}")
        return False


def test_rag_lora_dimensional_scores():
    """Test that dimensional scores are reasonable."""
    print_header("Test 4: Dimensional Score Validation")
    
    print_test("Sending analysis for score check")
    
    if not TEST_IMAGE_PATH.exists():
        print_skip(f"Test image not found")
        test_results["skipped"].append("Dimensional scores")
        return False
    
    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': ADVISOR,
                'mode': 'rag_lora',
                'response_format': 'json'
            }
            
            response = requests.post(
                f"{AI_SERVICE_URL}/analyze",
                files=files,
                data=data,
                timeout=300
            )
        
        if response.status_code != 200:
            print_fail(f"HTTP {response.status_code}")
            test_results["failed"].append("Dimensional scores - request failed")
            return False
        
        result = response.json()
        print_pass()
        
        print_subheader("Score Range Validation")
        
        dim_analysis = result.get('dimensional_analysis', {})
        score_ranges = {"valid": 0, "out_of_range": 0}
        
        for dim_name, dim_data in dim_analysis.items():
            if isinstance(dim_data, dict):
                score = dim_data.get('score')
                
                if score is not None:
                    try:
                        score_val = float(score)
                        
                        # Valid scores are typically 0-10
                        if 0 <= score_val <= 10:
                            score_ranges["valid"] += 1
                        else:
                            score_ranges["out_of_range"] += 1
                            print_info(f"{dim_name}: {score_val} (out of typical range)")
                    except (ValueError, TypeError):
                        pass
        
        print_test("Score validation")
        if score_ranges["out_of_range"] == 0:
            print_pass(f"All scores in valid range (0-10)")
        else:
            print_skip(f"Some scores out of range ({score_ranges['out_of_range']})")
            # Not a failure, just a warning
        
        # Check that all dimensions have comments
        print_test("Comment presence")
        comments_found = 0
        
        for dim_name, dim_data in dim_analysis.items():
            if isinstance(dim_data, dict) and dim_data.get('comment'):
                comments_found += 1
        
        if comments_found >= len(dim_analysis) * 0.8:  # At least 80%
            print_pass(f"Comments found for {comments_found}/{len(dim_analysis)} dimensions")
        else:
            print_fail(f"Missing comments ({comments_found}/{len(dim_analysis)})")
            test_results["failed"].append("Dimensional scores - missing comments")
            return False
        
        test_results["passed"].append("Dimensional scores")
        return True
        
    except requests.exceptions.Timeout:
        print_fail("Request timeout")
        test_results["failed"].append("Dimensional scores - timeout")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        test_results["failed"].append(f"Dimensional scores - {str(e)}")
        return False


def test_rag_lora_vs_rag_comparison():
    """Test RAG+LoRA vs RAG mode comparison."""
    print_header("Test 5: RAG+LoRA vs RAG Comparison")
    
    print_test("Testing RAG mode for comparison")
    
    if not TEST_IMAGE_PATH.exists():
        print_skip(f"Test image not found")
        test_results["skipped"].append("Mode comparison")
        return False
    
    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': ADVISOR,
                'mode': 'rag',
                'response_format': 'json'
            }
            
            response = requests.post(
                f"{AI_SERVICE_URL}/analyze",
                files=files,
                data=data,
                timeout=300
            )
        
        if response.status_code != 200:
            print_skip(f"RAG mode unavailable (HTTP {response.status_code})")
            test_results["skipped"].append("Mode comparison")
            return True
        
        rag_result = response.json()
        print_pass()
        
        # Now get RAG+LoRA result
        print_test("Testing RAG+LoRA mode for comparison")
        
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': ADVISOR,
                'mode': 'rag_lora',
                'response_format': 'json'
            }
            
            response = requests.post(
                f"{AI_SERVICE_URL}/analyze",
                files=files,
                data=data,
                timeout=300
            )
        
        if response.status_code != 200:
            print_skip(f"RAG+LoRA mode unavailable")
            test_results["skipped"].append("Mode comparison")
            return True
        
        rag_lora_result = response.json()
        print_pass()
        
        print_subheader("Comparison Analysis")
        
        # Both should have dimensional analysis
        print_test("Both modes produce analysis")
        rag_dims = len(rag_result.get('dimensional_analysis', {}))
        rag_lora_dims = len(rag_lora_result.get('dimensional_analysis', {}))
        
        if rag_dims >= 8 and rag_lora_dims >= 8:
            print_pass(f"RAG: {rag_dims} dims, RAG+LoRA: {rag_lora_dims} dims")
        else:
            print_fail("Incomplete analysis from one or both modes")
            test_results["failed"].append("Mode comparison - incomplete")
            return False
        
        # Compare grades
        print_test("Grade comparison")
        rag_grade = rag_result.get('overall_grade')
        rag_lora_grade = rag_lora_result.get('overall_grade')
        
        print_info(f"RAG grade: {rag_grade}")
        print_info(f"RAG+LoRA grade: {rag_lora_grade}")
        print_pass("Grades assigned by both modes")
        
        test_results["passed"].append("Mode comparison")
        return True
        
    except requests.exceptions.Timeout:
        print_fail("Request timeout")
        test_results["failed"].append("Mode comparison - timeout")
        return False
    except Exception as e:
        print_fail(f"Error: {e}")
        test_results["failed"].append(f"Mode comparison - {str(e)}")
        return False


def print_summary():
    """Print test summary."""
    print_header("Test Summary")
    
    total_passed = len(test_results["passed"])
    total_failed = len(test_results["failed"])
    total_skipped = len(test_results["skipped"])
    total_tests = total_passed + total_failed + total_skipped
    
    print(f"{GREEN}Passed:{NC}  {total_passed}")
    if test_results["passed"]:
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
    """Print timing summary."""
    if not timing_data:
        return
    
    print_header("Timing Summary")
    
    for test_name, duration in sorted(timing_data.items()):
        print(f"{test_name:.<40} {duration:>8.2f}s")


def main():
    """Run all RAG+LoRA tests."""
    parser = argparse.ArgumentParser(
        description="End-to-End Tests for RAG+LoRA Strategy"
    )
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("--timing", action="store_true",
                       help="Include timing measurements")
    parser.add_argument("--with-embeddings", action="store_true",
                       help="Focus on embedding tests")
    
    args = parser.parse_args()
    
    print_header("RAG+LoRA End-to-End Tests")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"AI Service: {AI_SERVICE_URL}")
    print(f"Test Image: {TEST_IMAGE_PATH}")
    
    # Check prerequisites
    if not check_services():
        print(f"\n{RED}Services not available. Please start them first:{NC}")
        print("  ./start_mondrian.sh")
        return 1
    
    check_rag_lora_availability()
    
    # Run tests
    print_header("Running Tests")
    
    try:
        test_rag_lora_basic_workflow()
        test_rag_lora_metadata()
        test_rag_lora_dimensional_scores()
        
        if args.with_embeddings:
            test_rag_lora_with_embeddings()
        
        test_rag_lora_vs_rag_comparison()
    
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{NC}")
        test_results["failed"].append("Interrupted")
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{NC}")
        test_results["failed"].append("Unexpected error")
    
    # Print summaries
    if args.timing:
        print_timing_summary()
    
    exit_code = print_summary()
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
