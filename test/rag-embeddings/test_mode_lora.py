#!/usr/bin/env python3
"""
LoRA Mode Test - Minimal, Standalone Test

Tests the base model with a LoRA adapter applied (fine-tuned model).
LoRA adds adapter weights on top of the base model, using similar or slightly more memory.

Usage:
    python3 test_mode_lora.py
    python3 test_mode_lora.py --verbose
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
TEST_IMAGE_PATH = Path("source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg")
ADVISOR = "ansel"
MODE = "lora"
TIMEOUT = 60  # 60 second timeout for inference

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
                print_info("Make sure service is running: ./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel")
                return False
            
            return True
        else:
            print_fail(f"Service returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_fail(f"Cannot connect to AI Advisor at {AI_SERVICE_URL}")
        print_info("Make sure service is running: ./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel")
        return False
    except Exception as e:
        print_fail(f"Error checking service: {e}")
        return False


def run_lora_test(verbose=False):
    """Run single LoRA analysis."""
    print_header("Running LoRA Analysis Test")
    
    print_info(f"Mode: {MODE}")
    print_info(f"Advisor: {ADVISOR}")
    print_info(f"Timeout: {TIMEOUT}s")
    print_info(f"Sending analysis request with LoRA adapter...")
    
    start_time = time.time()
    
    try:
        with open(TEST_IMAGE_PATH, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor': ADVISOR,
                'mode': MODE,
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
        
        # Validate required fields
        required_fields = ['overall_grade', 'dimensional_analysis']
        missing = [f for f in required_fields if f not in result]
        
        if missing:
            print_fail(f"Missing required fields: {missing}")
            if verbose:
                print(f"Response keys: {list(result.keys())}")
            return False
        
        # Extract and display results
        grade = result.get('overall_grade', 'N/A')
        dims_count = len(result.get('dimensional_analysis', {}))
        mode_used = result.get('mode_used', MODE)
        fine_tuned = result.get('fine_tuned')
        
        print_success(f"Analysis completed in {duration:.2f}s")
        print_info(f"Mode used: {mode_used}")
        print_info(f"Fine-tuned model: {fine_tuned}")
        print_info(f"Overall grade: {grade}")
        print_info(f"Dimensional analysis: {dims_count} dimensions")
        
        if verbose:
            print("\nDetailed Results:")
            print(json.dumps(result, indent=2)[:1000])
        
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
        description="LoRA Mode Test - Tests base model with LoRA adapter"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output with full response details")
    
    args = parser.parse_args()
    
    print_header("LoRA MODE TEST")
    
    # Check prerequisites
    if not check_prerequisites():
        return 1
    
    # Run test
    if run_lora_test(verbose=args.verbose):
        print_header("TEST PASSED ✓")
        print(f"{GREEN}LoRA mode is working correctly!{NC}\n")
        return 0
    else:
        print_header("TEST FAILED ✗")
        print(f"{RED}LoRA mode failed. Check logs/ai_advisor_service_*.log{NC}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
