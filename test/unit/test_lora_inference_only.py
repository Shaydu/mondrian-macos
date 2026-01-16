#!/usr/bin/env python3
"""
Phase 0: LoRA Inference Unit Test
==================================

Minimal unit test to verify LoRA-adapted model can generate responses without hanging.

Purpose:
- Test LoRA inference in complete isolation (no RAG, no embeddings)
- Verify image, advisor, and system prompt are correctly processed
- Detect inference hangs/timeouts before running more complex tests

Success Criteria:
- Request completes within 90 seconds
- Returns valid JSON structure
- mode_used field equals "lora"
- No timeout, no hang, no crash

Usage:
    # Ensure services are running in LoRA mode first:
    ./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

    # Then run this test:
    python3 test/unit/test_lora_inference_only.py
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
MODE = "lora"
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
    output_dir = Path("test_results") / "unit_tests" / f"lora_inference_{timestamp}"
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

            # Check if LoRA is enabled
            lora_enabled = health.get('lora_enabled', False)
            model_mode = health.get('model_mode', 'unknown')

            if not lora_enabled:
                print_warning(f"LoRA not enabled (model_mode={model_mode})")
                print_warning("Service should be started with: ./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel")
                services_ok = False
            else:
                lora_path = health.get('lora_path', 'unknown')
                print_success(f"LoRA enabled: {lora_path}")

            return services_ok, health
        else:
            print_error(f"AI Advisor Service returned status {resp.status_code}")
            return False, None
    except Exception as e:
        print_error(f"AI Advisor Service not reachable: {e}")
        return False, None


def fetch_advisor_metadata():
    """Fetch advisor metadata and system prompt from database"""
    print_info("Fetching advisor metadata from database...")

    try:
        # Import config to get database path
        sys.path.insert(0, str(Path.cwd() / "mondrian"))
        from config import DATABASE_PATH

        conn = sqlite3.connect(DATABASE_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Fetch advisor metadata
        cursor.execute("""
            SELECT id, name, bio, prompt, years, focus_areas
            FROM advisors
            WHERE id = ?
        """, (ADVISOR,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            print_error(f"Advisor '{ADVISOR}' not found in database")
            return None

        metadata = {
            'id': row['id'],
            'name': row['name'],
            'bio': row['bio'],
            'advisor_prompt': row['prompt'],
            'years': row['years'],
            'focus_areas': row['focus_areas']
        }

        # Fetch system prompt from config table
        cursor.execute("""
            SELECT value FROM config WHERE key = 'system_prompt'
        """)

        system_prompt_row = cursor.fetchone()
        if system_prompt_row:
            metadata['system_prompt'] = system_prompt_row['value']
            print_success(f"System prompt loaded ({len(system_prompt_row['value'])} chars)")
        else:
            print_warning("System prompt not found in config")

        conn.close()

        print_success(f"Advisor metadata loaded: {metadata['name']}")
        return metadata

    except Exception as e:
        print_error(f"Failed to fetch advisor metadata: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_lora_inference(output_dir, advisor_metadata):
    """Run LoRA inference test"""
    print_header(f"Phase 0: LoRA Inference Unit Test")

    # Verify test image exists
    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print_error(f"Test image not found: {TEST_IMAGE}")
        return False, None, None

    print_info(f"Test image: {TEST_IMAGE}")
    print_info(f"Advisor: {ADVISOR}")
    print_info(f"Mode: {MODE}")
    print_info(f"Timeout: {TIMEOUT} seconds")

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

                    return True, elapsed_time, result

                except json.JSONDecodeError as e:
                    print_error(f"Response is not valid JSON: {e}")

                    # Save raw response
                    with open(output_dir / "response_raw.txt", 'w') as f:
                        f.write(response.text)

                    return False, elapsed_time, None
            else:
                print_error(f"Request failed with status {response.status_code}")
                print_error(f"Response: {response.text[:500]}")

                # Save error response
                with open(output_dir / "error_response.txt", 'w') as f:
                    f.write(f"Status: {response.status_code}\n")
                    f.write(f"Response: {response.text}\n")

                return False, elapsed_time, None

        except requests.exceptions.Timeout:
            elapsed_time = time.time() - start_time
            print_error(f"✗ REQUEST TIMEOUT after {elapsed_time:.2f} seconds")
            print_error("This indicates the inference is hanging")

            # Save timeout info
            timing = {
                'start_time': datetime.fromtimestamp(start_time).isoformat(),
                'timeout_at': datetime.now().isoformat(),
                'elapsed_seconds': elapsed_time,
                'timeout_limit': TIMEOUT,
                'error': 'TIMEOUT'
            }

            with open(output_dir / "timing.json", 'w') as f:
                json.dump(timing, f, indent=2)

            with open(output_dir / "error_debug.log", 'w') as f:
                f.write(f"ERROR: Request timeout after {elapsed_time:.2f} seconds\n")
                f.write(f"Timeout limit: {TIMEOUT} seconds\n")
                f.write(f"This indicates the MLX model inference is hanging\n")
                f.write(f"\nSee: docs/tasks/MLX_STATUS.md for known issues\n")

            return False, elapsed_time, None

        except Exception as e:
            elapsed_time = time.time() - start_time
            print_error(f"Request exception: {e}")

            # Save error info
            with open(output_dir / "error_debug.log", 'w') as f:
                f.write(f"ERROR: {str(e)}\n")
                f.write(f"Exception type: {type(e).__name__}\n")
                f.write(f"Elapsed time: {elapsed_time:.2f} seconds\n")

            return False, elapsed_time, None


def main():
    """Main test execution"""
    print_header("Phase 0: LoRA Inference Unit Test - START")

    print_info(f"Test configuration:")
    print_info(f"  Image: {TEST_IMAGE}")
    print_info(f"  Advisor: {ADVISOR}")
    print_info(f"  Mode: {MODE}")
    print_info(f"  Timeout: {TIMEOUT}s")

    # Setup output directory
    output_dir = setup_output_directory()
    print_info(f"Output directory: {output_dir}")

    # Open test log
    log_file = output_dir / "test.log"

    with open(log_file, 'w') as log:
        log.write(f"Phase 0: LoRA Inference Unit Test\n")
        log.write(f"Start time: {datetime.now().isoformat()}\n")
        log.write(f"="*80 + "\n\n")

        # Step 1: Check services
        print_info("\nStep 1: Checking services...")
        log.write("Step 1: Checking services\n")

        services_ok, health_data = check_services()

        if not services_ok:
            print_error("\n✗ TEST FAILED: Services not ready")
            log.write("\nResult: FAILED - Services not ready\n")
            sys.exit(1)

        # Step 2: Fetch advisor metadata
        print_info("\nStep 2: Fetching advisor metadata...")
        log.write("\nStep 2: Fetching advisor metadata\n")

        advisor_metadata = fetch_advisor_metadata()

        if not advisor_metadata:
            print_error("\n✗ TEST FAILED: Could not load advisor metadata")
            log.write("\nResult: FAILED - Advisor metadata not found\n")
            sys.exit(1)

        # Step 3: Run inference test
        print_info("\nStep 3: Running LoRA inference...")
        log.write("\nStep 3: Running LoRA inference\n")

        success, elapsed_time, result = run_lora_inference(output_dir, advisor_metadata)

        # Final result
        print_header("TEST RESULT")

        if success:
            print_success(f"✓ TEST PASSED")
            print_success(f"  Response time: {elapsed_time:.2f}s")
            print_success(f"  Mode verified: {MODE}")
            print_success(f"  Valid JSON structure: Yes")

            log.write(f"\n{'='*80}\n")
            log.write(f"Result: PASSED\n")
            log.write(f"Response time: {elapsed_time:.2f}s\n")
            log.write(f"End time: {datetime.now().isoformat()}\n")

            print_info(f"\nTest results saved to: {output_dir}")
            sys.exit(0)
        else:
            print_error(f"✗ TEST FAILED")
            if elapsed_time:
                print_error(f"  Response time: {elapsed_time:.2f}s")

            log.write(f"\n{'='*80}\n")
            log.write(f"Result: FAILED\n")
            if elapsed_time:
                log.write(f"Response time: {elapsed_time:.2f}s\n")
            log.write(f"End time: {datetime.now().isoformat()}\n")

            print_info(f"\nTest results and debug info saved to: {output_dir}")

            print_warning("\n" + "="*80)
            print_warning("NEXT STEPS:")
            print_warning("1. Check error_debug.log in output directory")
            print_warning("2. Review service logs in logs/")
            print_warning("3. See docs/tasks/MLX_STATUS.md for known issues")
            print_warning("="*80)

            sys.exit(1)


if __name__ == "__main__":
    main()
