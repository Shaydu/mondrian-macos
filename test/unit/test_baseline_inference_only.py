#!/usr/bin/env python3
"""
Phase 0: Baseline Inference Unit Test
======================================

Minimal unit test to verify baseline model can generate responses without hanging.

Purpose:
- Test baseline inference in complete isolation (no LoRA, no RAG, no embeddings)
- Compare baseline output quality with LoRA output
- Verify image, advisor, and system prompt are correctly processed
- Detect inference hangs/timeouts before running more complex tests

Success Criteria:
- Request completes within 90 seconds
- Returns valid JSON structure
- mode_used field equals "baseline"
- No timeout, no hang, no crash

Usage:
    # Ensure services are running in baseline mode first:
    ./mondrian.sh --restart --mode=baseline

    # Then run this test:
    python3 test/unit/test_baseline_inference_only.py

Comparison:
    Run both this test and test_lora_inference_only.py to compare outputs:
    - Check test_results/unit_tests/baseline_inference_*/rendered_analysis.html
    - Check test_results/unit_tests/lora_inference_*/rendered_analysis.html
"""

import requests
import json
import time
import sys
import os
import sqlite3
import base64
from pathlib import Path
from datetime import datetime

# Configuration
AI_ADVISOR_URL = "http://127.0.0.1:5100"
JOB_SERVICE_URL = "http://127.0.0.1:5005"
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"
MODE = "base"
TIMEOUT = 90  # seconds

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


def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓{NC} {text}")


def print_error(text):
    """Print error message"""
    print(f"{RED}✗{NC} {text}")


def print_info(text):
    """Print info message"""
    print(f"{YELLOW}ℹ{NC} {text}")


def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠{NC} {text}")


def make_json_serializable(obj):
    """Convert non-JSON-serializable types (like bytes) to serializable types"""
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    return obj


def setup_output_directory():
    """Create timestamped output directory for test results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("test_results") / "unit_tests" / f"baseline_inference_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def check_services():
    """Check that required services are running"""
    print_info("Checking services...")

    services_ok = True

    # Check AI Advisor Service
    try:
        resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
        if resp.status_code == 200:
            health = resp.json()
            print_success(f"AI Advisor Service (port 5100) - UP")
        else:
            print_error(f"AI Advisor Service returned status {resp.status_code}")
            services_ok = False
    except Exception as e:
        print_error(f"AI Advisor Service - UNREACHABLE: {e}")
        services_ok = False

    # Check Job Service
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        if resp.status_code == 200:
            print_success(f"Job Service (port 5005) - UP")
        else:
            print_error(f"Job Service returned status {resp.status_code}")
            services_ok = False
    except Exception as e:
        print_error(f"Job Service - UNREACHABLE: {e}")
        services_ok = False

    return services_ok


def get_advisor_metadata():
    """Fetch advisor metadata from AI Advisor Service"""
    try:
        response = requests.get(f"{AI_ADVISOR_URL}/advisor/{ADVISOR}/metadata", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print_warning(f"Could not fetch advisor metadata: {e}")
    return None


def run_baseline_inference(output_dir, advisor_metadata):
    """Run baseline inference test

    Args:
        output_dir: Path to save test results
        advisor_metadata: Advisor metadata (or None)

    Returns:
        (success, elapsed_time, result)
    """
    image_path = Path(TEST_IMAGE)

    # Save request metadata
    request_metadata = {
        'image_path': str(image_path),
        'advisor': ADVISOR,
        'mode': MODE,
        'timeout': TIMEOUT,
        'timestamp': datetime.now().isoformat()
    }

    with open(output_dir / "request_metadata.json", 'w') as f:
        json.dump(request_metadata, f, indent=2)

    # Save advisor metadata
    if advisor_metadata:
        # Ensure all values are JSON-serializable (convert bytes to base64, etc.)
        serializable_metadata = make_json_serializable(advisor_metadata)
        with open(output_dir / "advisor_metadata.json", 'w') as f:
            json.dump(serializable_metadata, f, indent=2)

        # Save prompts separately
        if advisor_metadata.get('system_prompt'):
            with open(output_dir / "system_prompt.txt", 'w') as f:
                prompt = advisor_metadata['system_prompt']
                if isinstance(prompt, bytes):
                    prompt = prompt.decode('utf-8')
                f.write(prompt)

        if advisor_metadata.get('advisor_prompt'):
            with open(output_dir / "advisor_prompt.txt", 'w') as f:
                prompt = advisor_metadata['advisor_prompt']
                if isinstance(prompt, bytes):
                    prompt = prompt.decode('utf-8')
                f.write(prompt)

    print_info("Sending request to AI Advisor Service...")

    # Prepare multipart form data
    with open(image_path, 'rb') as f:
        files = {'image': (image_path.name, f, 'image/jpeg')}
        data = {
            'advisor': ADVISOR,
            'mode': MODE
        }

        # Start timer
        start_time = time.time()

        try:
            # Call AI Advisor Service directly
            endpoint = f"{AI_ADVISOR_URL}/analyze"
            print_info(f"Endpoint: {endpoint}")

            response = requests.post(
                endpoint,
                files=files,
                data=data,
                timeout=TIMEOUT
            )

            # Calculate response time
            elapsed_time = time.time() - start_time

            # Save timing info
            timing = {
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'end_time': datetime.now().isoformat(),
                'elapsed_seconds': elapsed_time,
                'timeout_limit': TIMEOUT,
                'completed_within_timeout': elapsed_time < TIMEOUT
            }

            with open(output_dir / "timing.json", 'w') as f:
                json.dump(timing, f, indent=2)

            print_success(f"Request completed in {elapsed_time:.2f} seconds")

            # Check response status
            if response.status_code == 200:
                print_success("Response status: 200 OK")

                # Try to parse JSON
                try:
                    result = response.json()

                    # Save response
                    with open(output_dir / "response.json", 'w') as f:
                        json.dump(result, f, indent=2)

                    print_success("Response is valid JSON")

                    # Validate response structure
                    mode_used = result.get('mode_used', 'unknown')
                    dimensional_analysis = result.get('dimensional_analysis', [])
                    overall_grade = result.get('overall_grade', None)

                    print_info(f"mode_used: {mode_used}")
                    print_info(f"dimensional_analysis entries: {len(dimensional_analysis)}")
                    print_info(f"overall_grade: {overall_grade}")

                    # Validate mode
                    if mode_used == MODE:
                        print_success(f"✓ mode_used matches expected mode: {MODE}")
                    else:
                        print_error(f"✗ mode_used mismatch: expected '{MODE}', got '{mode_used}'")
                        return False, elapsed_time, result

                    # Validate dimensional analysis
                    if len(dimensional_analysis) > 0:
                        print_success(f"✓ dimensional_analysis has {len(dimensional_analysis)} entries")
                    else:
                        print_warning("⚠ dimensional_analysis is empty")

                    # Validate overall grade
                    if overall_grade:
                        print_success(f"✓ overall_grade present: {overall_grade}")
                    else:
                        print_warning("⚠ overall_grade is missing")

                    print_success("✓ Response validation complete")
                    return True, elapsed_time, result

                except json.JSONDecodeError as e:
                    print_error(f"✗ Failed to parse JSON response: {e}")
                    print_error(f"Response text: {response.text[:500]}")
                    return False, elapsed_time, None
            else:
                print_error(f"✗ Response status: {response.status_code}")
                print_error(f"Response text: {response.text[:500]}")
                return False, elapsed_time, None

        except requests.exceptions.Timeout:
            elapsed_time = time.time() - start_time
            print_error(f"✗ Request timeout after {elapsed_time:.2f} seconds (limit: {TIMEOUT}s)")
            return False, elapsed_time, None
        except Exception as e:
            elapsed_time = time.time() - start_time
            print_error(f"✗ Request failed: {e}")
            return False, elapsed_time, None


def main():
    """Main test routine"""
    print_header("Baseline Inference Unit Test")

    print_info(f"Test image: {TEST_IMAGE}")
    print_info(f"Advisor: {ADVISOR}")
    print_info(f"Mode: {MODE}")
    print_info(f"Timeout: {TIMEOUT} seconds")

    # Setup output directory
    output_dir = setup_output_directory()
    print_info(f"Test results will be saved to: {output_dir}")

    # Check services
    if not check_services():
        print_error("✗ Required services are not running!")
        print_error("  Start services with: ./mondrian.sh --restart --mode=baseline")
        sys.exit(1)

    # Get advisor metadata
    print_info("Fetching advisor metadata...")
    advisor_metadata = get_advisor_metadata()
    if advisor_metadata:
        print_success("✓ Advisor metadata retrieved")
    else:
        print_warning("⚠ Could not retrieve advisor metadata (will continue anyway)")

    # Run inference test
    print_header("Running Baseline Inference")

    success, elapsed_time, result = run_baseline_inference(output_dir, advisor_metadata)

    # Print results
    print_header("TEST RESULT")

    if success:
        print_success("✓ TEST PASSED")
        print_success(f"  Response time: {elapsed_time:.2f}s")
        print_success(f"  Mode verified: {result.get('mode_used', 'unknown')}")
        print_success(f"  Valid JSON structure: Yes")
        print_info("")
        print_info(f"Test results saved to: {output_dir}")

        # Create rendered HTML
        try:
            html_content = result.get('html', '')
            if html_content:
                full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baseline Analysis - {ADVISOR.title()}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #e0e0e0;
            text-align: center;
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <h1>Baseline Analysis ({ADVISOR.title()})</h1>
    {html_content}
</body>
</html>"""
                with open(output_dir / "rendered_analysis.html", 'w') as f:
                    f.write(full_html)
                print_success("✓ Rendered HTML saved")
        except Exception as e:
            print_warning(f"⚠ Could not create rendered HTML: {e}")

        return 0
    else:
        print_error("✗ TEST FAILED")
        print_error(f"  Response time: {elapsed_time:.2f}s")
        if result:
            print_error(f"  Mode: {result.get('mode_used', 'unknown')}")
        print_info("")
        print_info(f"Test results saved to: {output_dir}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
