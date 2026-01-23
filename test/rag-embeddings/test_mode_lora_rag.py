#!/usr/bin/env python3
"""
LoRA+RAG Mode Test - Minimal, Standalone Test

Tests the LoRA-adapted model with RAG enabled.
This is the most memory-intensive mode: base model + LoRA adapter + RAG embeddings.

Usage:
    python3 test_mode_lora_rag.py
    python3 test_mode_lora_rag.py --verbose
"""

import sys
import os
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime

# Configuration
AI_SERVICE_URL = "http://localhost:5100"
DEFAULT_IMAGE_PATH = Path("source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg")
TEST_IMAGE_PATH = Path(os.environ.get("TEST_IMAGE_PATH", str(DEFAULT_IMAGE_PATH)))
ADVISOR = "ansel"
MODE = "rag_lora"
TIMEOUT = 300  # 300 second timeout for inference (match service model timeout)

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
NC = '\033[0m'


def print_header(text):
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}{text:^70}{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")


def print_success(text):
    print(f"{GREEN}✓ SUCCESS{NC}: {text}")


def print_fail(text):
    print(f"{RED}✗ FAILED{NC}: {text}")


def print_info(text):
    print(f"{YELLOW}ℹ{NC} {text}")


def check_prerequisites():
    """Check if everything needed is available."""
    print_header("Checking Prerequisites")
    
    # Check test image
    if not TEST_IMAGE_PATH.exists():
        print_fail(f"Test image not found: {TEST_IMAGE_PATH}")
        return False
    
    print_success(f"Test image exists: {TEST_IMAGE_PATH}")
    
    # Check LoRA adapter
    lora_path = Path("./adapters/ansel")
    if not lora_path.exists():
        print_fail(f"LoRA adapter not found: {lora_path}")
        return False
    
    print_success(f"LoRA adapter exists: {lora_path}")
    
    # Check service connectivity
    try:
        response = requests.get(f"{AI_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success(f"AI Advisor Service is running at {AI_SERVICE_URL}")
            data = response.json()
            print_info(f"Service info: {data.get('version', 'unknown')} on device {data.get('device', 'unknown')}")
            
            # Check if LoRA is loaded
            if data.get('fine_tuned'):
                print_info(f"LoRA adapter loaded: {data.get('lora_path', 'unknown')}")
            else:
                print_fail("LoRA adapter not loaded in service")
                print_info("Make sure service is running: ./mondrian.sh --restart --mode=lora+rag --lora-path=./adapters/ansel")
                return False
            
            return True
        else:
            print_fail(f"Service returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_fail(f"Cannot connect to AI Advisor at {AI_SERVICE_URL}")
        print_info("Make sure service is running: ./mondrian.sh --restart --mode=lora+rag --lora-path=./adapters/ansel")
        return False
    except Exception as e:
        print_fail(f"Error checking service: {e}")
        return False


def run_lora_rag_test(verbose=False):
    """Run single LoRA+RAG analysis."""
    print_header("Running LoRA+RAG Analysis Test")

    print_info(f"Mode: {MODE}")
    print_info(f"Advisor: {ADVISOR}")
    print_info(f"Timeout: {TIMEOUT}s")
    print_info(f"Sending analysis request with LoRA adapter and RAG enabled...")

    start_time = time.time()

    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': ADVISOR,
                'mode': MODE,
                'enable_rag': 'true',
                'response_format': 'json'
            }

            response = requests.post(
                f"{AI_SERVICE_URL}/analyze",
                files=files,
                data=data,
                timeout=TIMEOUT
            )

        duration = time.time() - start_time

        # Check response status
        if response.status_code != 200:
            print_fail(f"HTTP {response.status_code}")
            if verbose:
                print(f"Response: {response.text[:500]}")
            return False

        # Parse response
        try:
            result = response.json()
        except json.JSONDecodeError:
            print_fail("Response is not valid JSON")
            if verbose:
                print(f"Response: {response.text[:500]}")
            return False

        # Validate response has analysis results
        # Be flexible about field names since API may vary
        required_fields = ['analysis', 'summary', 'advisor']
        missing = [f for f in required_fields if f not in result]

        if missing:
            print_fail(f"Missing required fields: {missing}")
            if verbose:
                print(f"Response keys: {list(result.keys())}")
            return False

        # Extract and display results
        grade = result.get('overall_grade') or result.get('overall_score', 'N/A')
        dims_count = len(result.get('dimensional_analysis', {}))
        mode_used = result.get('mode_used', result.get('mode', MODE))
        fine_tuned = result.get('fine_tuned')

        # Check for RAG-specific fields
        similar_images = result.get('similar_images')
        rag_context = result.get('rag_context')

        # Parse analysis JSON to check dimensions
        analysis_json = result.get('analysis_json', '{}')
        try:
            analysis_data = json.loads(analysis_json) if isinstance(analysis_json, str) else analysis_json
            dimensions = analysis_data.get('dimensions', [])
            num_dimensions = len(dimensions)
            dimension_names = [d.get('name', 'Unknown') for d in dimensions]

            # Check for citations in dimensions
            cited_images = sum(1 for d in dimensions if d.get('_cited_image'))
            cited_quotes = sum(1 for d in dimensions if d.get('_cited_quote'))
        except:
            num_dimensions = 0
            dimension_names = []
            cited_images = 0
            cited_quotes = 0

        print_success(f"Analysis completed in {duration:.2f}s")
        print_info(f"Mode used: {mode_used}")
        print_info(f"Fine-tuned model: {fine_tuned}")
        print_info(f"Overall grade: {grade}")
        print_info(f"Dimensional analysis: {dims_count} dimensions")
        print_info(f"✓ Detailed dimensions: {num_dimensions}/6")

        if num_dimensions != 6:
            print_fail(f"Expected 6 dimensions, got {num_dimensions}")
            if verbose:
                print(f"Dimension names: {dimension_names}")
            return False

        print_info(f"  Dimensions: {', '.join(dimension_names)}")

        if similar_images:
            print_info(f"Similar images found: {len(similar_images)}")

        if rag_context:
            print_info(f"RAG context generated: {len(str(rag_context))} chars")

        print_info(f"✓ Citations in detailed view: {cited_images} images, {cited_quotes} quotes")

        if verbose:
            print("\nDetailed Results:")
            print(json.dumps(result, indent=2)[:2000])

        return True

    except requests.exceptions.Timeout:
        print_fail(f"Request timeout after {TIMEOUT}s")
        print_info("Service may have run out of memory or is stuck")
        return False

    except requests.exceptions.ConnectionError as e:
        print_fail(f"Connection error: {e}")
        print_info("Service may have crashed during inference")
        return False

    except Exception as e:
        print_fail(f"Unexpected error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="LoRA+RAG Mode Test - Tests LoRA adapter with RAG enabled"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output with full response details")
    
    args = parser.parse_args()
    
    print_header("LoRA+RAG MODE TEST")
    
    # Check prerequisites
    if not check_prerequisites():
        return 1
    
    # Run test
    if run_lora_rag_test(verbose=args.verbose):
        print_header("TEST PASSED ✓")
        print(f"{GREEN}LoRA+RAG mode is working correctly!{NC}\n")
        return 0
    else:
        print_header("TEST FAILED ✗")
        print(f"{RED}LoRA+RAG mode failed. Check logs/ai_advisor_service_*.log{NC}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
