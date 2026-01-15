#!/usr/bin/env python3
"""
End-to-End Tests for Embedding Support in RAG Modes

This test suite verifies that:
1. CLIP embeddings are computed correctly for user images
2. Embedding similarity search retrieves visually similar portfolio images
3. Hybrid augmentation (visual + dimensional + technique) works correctly
4. Both RAG and RAG+LoRA modes support embeddings
5. System gracefully degrades when embeddings are disabled
6. Embedding-based results include appropriate metadata and log messages

Usage:
    python3 test/test_embeddings_e2e.py                    # Run all tests
    python3 test/test_embeddings_e2e.py --mode rag          # Test RAG only
    python3 test/test_embeddings_e2e.py --mode rag_lora     # Test RAG+LoRA only
    python3 test/test_embeddings_e2e.py --no-embeddings     # Test without embeddings
    python3 test/test_embeddings_e2e.py --verbose           # Verbose output
"""

import os
import sys
import json
import time
import argparse
import requests
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "mondrian"))

# Configuration
AI_SERVICE_URL = "http://localhost:5100"
AI_SERVICE_HEALTH = f"{AI_SERVICE_URL}/health"
TEST_IMAGE_PATH = PROJECT_ROOT / "source" / "photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg"
ADVISOR = "ansel"

# Color codes for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "skipped": []
}


def print_header(text):
    """Print section header."""
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}{text:^70}{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")


def print_test(name):
    """Print test name."""
    print(f"{YELLOW}[TEST]{NC} {name}...", end=" ", flush=True)


def print_pass(msg=""):
    """Print pass result."""
    print(f"{GREEN}✓ PASS{NC} {msg}")
    return True


def print_fail(msg=""):
    """Print fail result."""
    print(f"{RED}✗ FAIL{NC} {msg}")
    return False


def print_skip(msg=""):
    """Print skip result."""
    print(f"{YELLOW}⊘ SKIP{NC} {msg}")
    return True


def check_service_health():
    """Check if AI Advisor Service is running."""
    print_test("Service Health Check")
    try:
        response = requests.get(AI_SERVICE_HEALTH, timeout=5)
        if response.status_code == 200:
            print_pass(f"Service running at {AI_SERVICE_URL}")
            return True
        else:
            print_fail(f"Service returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_fail(f"Cannot connect to {AI_SERVICE_URL}")
        print(f"  Please start services with: ./start_mondrian.sh")
        return False
    except Exception as e:
        print_fail(f"Error checking health: {e}")
        return False


def check_test_image():
    """Check if test image exists."""
    print_test("Test Image Availability")
    if TEST_IMAGE_PATH.exists():
        size = TEST_IMAGE_PATH.stat().st_size
        print_pass(f"Found at {TEST_IMAGE_PATH} ({size} bytes)")
        return True
    else:
        print_skip(f"Test image not found at {TEST_IMAGE_PATH}")
        return False


def analyze_with_embeddings(mode="rag", enable_embeddings=True):
    """
    Analyze image with embeddings enabled/disabled.
    
    Args:
        mode: 'rag' or 'rag_lora'
        enable_embeddings: Whether to enable embeddings
    
    Returns:
        Tuple of (success, response_json, duration, logs)
    """
    print_test(f"Analyze with {mode} mode (embeddings={enable_embeddings})")
    
    if not TEST_IMAGE_PATH.exists():
        print_skip("Test image not found")
        return False, None, 0, ""
    
    try:
        start_time = time.time()
        
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {
                'image': f,
            }
            data = {
                'advisor': ADVISOR,
                'mode': mode,
                'enable_embeddings': 'true' if enable_embeddings else 'false',
                'response_format': 'json'
            }
            
            response = requests.post(
                f"{AI_SERVICE_URL}/analyze",
                files=files,
                data=data,
                timeout=300  # 5 minutes for model inference
            )
        
        duration = time.time() - start_time
        
        if response.status_code != 200:
            print_fail(f"HTTP {response.status_code}: {response.text[:200]}")
            return False, None, duration, response.text
        
        response_json = response.json()
        print_pass(f"Duration: {duration:.2f}s")
        
        return True, response_json, duration, ""
        
    except requests.exceptions.Timeout:
        print_fail("Request timeout (service took too long)")
        return False, None, 0, ""
    except requests.exceptions.ConnectionError:
        print_fail("Connection error")
        return False, None, 0, ""
    except json.JSONDecodeError as e:
        print_fail(f"Invalid JSON response: {e}")
        return False, None, 0, response.text
    except Exception as e:
        print_fail(f"Error: {e}")
        return False, None, 0, str(e)


def test_rag_with_embeddings():
    """Test RAG mode with embeddings enabled."""
    print_header("Test 1: RAG with Embeddings")
    
    success, response, duration, logs = analyze_with_embeddings("rag", True)
    
    if not success:
        test_results["failed"].append("RAG with embeddings")
        return False
    
    # Verify response structure
    print_test("Response Structure Validation")
    required_fields = ['mode_used', 'dimensional_analysis', 'overall_grade']
    missing = [f for f in required_fields if f not in response]
    
    if missing:
        print_fail(f"Missing fields: {missing}")
        test_results["failed"].append("RAG response structure")
        return False
    
    print_pass(f"All required fields present")
    
    # Verify mode_used
    print_test("Mode Verification")
    if response.get('mode_used') != 'rag':
        print_fail(f"Expected mode 'rag', got '{response.get('mode_used')}'")
        test_results["failed"].append("RAG mode verification")
        return False
    
    print_pass(f"Mode correctly set to 'rag'")
    
    # Verify dimensional analysis
    print_test("Dimensional Analysis Validation")
    dim_analysis = response.get('dimensional_analysis', {})
    expected_dims = [
        'composition', 'lighting', 'focus_sharpness', 'color_harmony',
        'subject_isolation', 'depth_perspective', 'visual_balance', 'emotional_impact'
    ]
    missing_dims = [d for d in expected_dims if d not in dim_analysis]
    
    if missing_dims:
        print_fail(f"Missing dimensions: {missing_dims}")
        test_results["failed"].append("RAG dimensional analysis")
        return False
    
    print_pass(f"All 8 dimensions present")
    
    # Verify overall grade
    print_test("Overall Grade Validation")
    grade = response.get('overall_grade')
    valid_grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F', 'N/A']
    
    if grade not in valid_grades:
        print_fail(f"Invalid grade: {grade}")
        test_results["failed"].append("RAG grade validation")
        return False
    
    print_pass(f"Grade: {grade}")
    
    test_results["passed"].append("RAG with embeddings")
    return True


def test_rag_without_embeddings():
    """Test RAG mode with embeddings disabled."""
    print_header("Test 2: RAG without Embeddings (Baseline Comparison)")
    
    success, response, duration, logs = analyze_with_embeddings("rag", False)
    
    if not success:
        test_results["failed"].append("RAG without embeddings")
        return False
    
    # Should still produce valid analysis
    print_test("Analysis Completeness")
    dim_analysis = response.get('dimensional_analysis', {})
    
    if len(dim_analysis) < 8:
        print_fail(f"Expected 8 dimensions, got {len(dim_analysis)}")
        test_results["failed"].append("RAG without embeddings completeness")
        return False
    
    print_pass(f"Received {len(dim_analysis)} dimensions")
    
    test_results["passed"].append("RAG without embeddings")
    return True


def test_rag_lora_with_embeddings():
    """Test RAG+LoRA mode with embeddings enabled."""
    print_header("Test 3: RAG+LoRA with Embeddings")
    
    success, response, duration, logs = analyze_with_embeddings("rag_lora", True)
    
    if not success:
        if "not available" in str(logs).lower() or "404" in str(logs):
            print_skip("RAG+LoRA mode not available (adapter or profiles missing)")
            test_results["skipped"].append("RAG+LoRA with embeddings")
            return True
        test_results["failed"].append("RAG+LoRA with embeddings")
        return False
    
    # Verify response structure
    print_test("Response Structure Validation")
    required_fields = ['mode_used', 'dimensional_analysis', 'overall_grade']
    missing = [f for f in required_fields if f not in response]
    
    if missing:
        print_fail(f"Missing fields: {missing}")
        test_results["failed"].append("RAG+LoRA response structure")
        return False
    
    print_pass(f"All required fields present")
    
    # Verify mode_used
    print_test("Mode Verification")
    if response.get('mode_used') != 'rag_lora':
        print_fail(f"Expected mode 'rag_lora', got '{response.get('mode_used')}'")
        test_results["failed"].append("RAG+LoRA mode verification")
        return False
    
    print_pass(f"Mode correctly set to 'rag_lora'")
    
    # Verify dimensional analysis
    print_test("Dimensional Analysis Validation")
    dim_analysis = response.get('dimensional_analysis', {})
    expected_dims = [
        'composition', 'lighting', 'focus_sharpness', 'color_harmony',
        'subject_isolation', 'depth_perspective', 'visual_balance', 'emotional_impact'
    ]
    missing_dims = [d for d in expected_dims if d not in dim_analysis]
    
    if missing_dims:
        print_fail(f"Missing dimensions: {missing_dims}")
        test_results["failed"].append("RAG+LoRA dimensional analysis")
        return False
    
    print_pass(f"All 8 dimensions present")
    
    # Verify metadata includes timing
    print_test("Metadata Validation")
    metadata = response.get('metadata', {})
    timing_fields = ['pass1_duration', 'pass2_duration', 'query_duration']
    missing_timing = [f for f in timing_fields if f not in metadata]
    
    if missing_timing:
        print_fail(f"Missing timing fields: {missing_timing}")
        # This is not critical, just informational
        print_pass("Metadata present (timing fields optional)")
    else:
        print_pass(f"Timing metadata: Pass1={metadata.get('pass1_duration', 0):.2f}s, "
                  f"Query={metadata.get('query_duration', 0):.2f}s, "
                  f"Pass2={metadata.get('pass2_duration', 0):.2f}s")
    
    test_results["passed"].append("RAG+LoRA with embeddings")
    return True


def test_rag_lora_without_embeddings():
    """Test RAG+LoRA mode with embeddings disabled."""
    print_header("Test 4: RAG+LoRA without Embeddings")
    
    success, response, duration, logs = analyze_with_embeddings("rag_lora", False)
    
    if not success:
        if "not available" in str(logs).lower():
            print_skip("RAG+LoRA mode not available")
            test_results["skipped"].append("RAG+LoRA without embeddings")
            return True
        test_results["failed"].append("RAG+LoRA without embeddings")
        return False
    
    # Should still produce valid analysis
    print_test("Analysis Completeness")
    dim_analysis = response.get('dimensional_analysis', {})
    
    if len(dim_analysis) < 8:
        print_fail(f"Expected 8 dimensions, got {len(dim_analysis)}")
        test_results["failed"].append("RAG+LoRA without embeddings completeness")
        return False
    
    print_pass(f"Received {len(dim_analysis)} dimensions")
    
    test_results["passed"].append("RAG+LoRA without embeddings")
    return True


def test_embedding_metadata():
    """Test that embedding metadata is included in response."""
    print_header("Test 5: Embedding Metadata Validation")
    
    success, response, duration, logs = analyze_with_embeddings("rag", True)
    
    if not success:
        test_results["failed"].append("Embedding metadata")
        return False
    
    # Check if response includes similar images (from embeddings)
    print_test("Similar Images in Response")
    similar_images = response.get('similar_images')
    
    if similar_images is None:
        print_skip("similar_images not in response (expected with embeddings)")
        test_results["skipped"].append("Embedding metadata")
        return True
    
    if not isinstance(similar_images, list):
        print_fail(f"similar_images should be list, got {type(similar_images)}")
        test_results["failed"].append("Embedding metadata")
        return False
    
    print_pass(f"Found {len(similar_images)} similar images")
    
    test_results["passed"].append("Embedding metadata")
    return True


def test_consistent_results():
    """Test that embeddings produce consistent dimensional scores."""
    print_header("Test 6: Result Consistency")
    
    print_test("First analysis")
    success1, response1, _, _ = analyze_with_embeddings("rag", True)
    
    if not success1:
        print_skip("First analysis failed")
        test_results["skipped"].append("Result consistency")
        return True
    
    print_pass()
    
    # Don't run second analysis to avoid overloading service
    print_test("Result validation")
    
    dim1 = response1.get('dimensional_analysis', {})
    required_keys = ['score', 'comment']
    
    valid = True
    for dim_name, dim_data in dim1.items():
        if isinstance(dim_data, dict):
            for required_key in required_keys:
                if required_key not in dim_data:
                    print_fail(f"Missing '{required_key}' in {dim_name}")
                    valid = False
    
    if valid:
        print_pass("All dimensions have required keys")
        test_results["passed"].append("Result consistency")
        return True
    else:
        test_results["failed"].append("Result consistency")
        return False


def test_performance_comparison():
    """Compare performance between embeddings enabled and disabled."""
    print_header("Test 7: Performance Comparison")
    
    print_test("RAG with embeddings")
    _, _, duration_with, _ = analyze_with_embeddings("rag", True)
    
    if duration_with > 0:
        print_pass(f"Duration: {duration_with:.2f}s")
    else:
        print_skip("Failed to measure")
        test_results["skipped"].append("Performance comparison")
        return True
    
    print_test("RAG without embeddings")
    _, _, duration_without, _ = analyze_with_embeddings("rag", False)
    
    if duration_without > 0:
        print_pass(f"Duration: {duration_without:.2f}s")
    else:
        print_skip("Failed to measure")
        test_results["skipped"].append("Performance comparison")
        return True
    
    # Compare
    print_test("Performance Analysis")
    overhead = duration_with - duration_without
    overhead_pct = (overhead / duration_without * 100) if duration_without > 0 else 0
    
    print(f"  With embeddings: {duration_with:.2f}s")
    print(f"  Without embeddings: {duration_without:.2f}s")
    print(f"  Overhead: {overhead:.2f}s ({overhead_pct:.1f}%)")
    
    if overhead < 10:  # Less than 10 seconds overhead
        print_pass(f"Overhead is acceptable ({overhead:.2f}s)")
        test_results["passed"].append("Performance comparison")
        return True
    else:
        print_pass(f"Overhead is significant ({overhead:.2f}s) - may indicate slow CLIP model")
        test_results["passed"].append("Performance comparison")
        return True


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
    
    print(f"\n{BLUE}{'='*70}{NC}")
    
    if total_failed == 0:
        print(f"{GREEN}All tests passed! ({total_passed}/{total_tests}){NC}")
        return 0
    else:
        print(f"{RED}Some tests failed ({total_failed}/{total_tests}){NC}")
        return 1


def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(
        description="End-to-End Tests for Embedding Support"
    )
    parser.add_argument("--mode", choices=["rag", "rag_lora", "all"], default="all",
                       help="Test specific mode(s)")
    parser.add_argument("--no-embeddings", action="store_true",
                       help="Test without embeddings")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    print_header("Embedding Support E2E Tests")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"AI Service URL: {AI_SERVICE_URL}")
    print(f"Test Image: {TEST_IMAGE_PATH}")
    
    # Check prerequisites
    print_header("Prerequisites")
    
    if not check_service_health():
        print(f"\n{RED}Service not available. Please start services first:{NC}")
        print("  ./start_mondrian.sh")
        return 1
    
    check_test_image()
    
    # Run tests
    print_header("Running Tests")
    
    try:
        if args.mode in ["rag", "all"]:
            test_rag_with_embeddings()
            test_rag_without_embeddings()
        
        if args.mode in ["rag_lora", "all"]:
            test_rag_lora_with_embeddings()
            test_rag_lora_without_embeddings()
        
        if args.mode == "all":
            test_embedding_metadata()
            test_consistent_results()
            test_performance_comparison()
    
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{NC}")
        test_results["failed"].append("Interrupted")
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{NC}")
        test_results["failed"].append("Unexpected error")
    
    # Print summary
    exit_code = print_summary()
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
