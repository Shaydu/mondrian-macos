#!/usr/bin/env python3
"""
Service Health Verification Script
===================================

Standalone script to verify service health before running tests.
Checks both Job Service and AI Advisor Service.

Exit Codes:
    0 - READY (all services healthy)
    1 - NOT_READY (services down or unhealthy)
    2 - DEGRADED (services up but with warnings)

Usage:
    python3 test/scripts/verify_service_health.py
    python3 test/scripts/verify_service_health.py --mode=lora
"""

import requests
import sys
import argparse
from pathlib import Path

# Configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
AI_ADVISOR_URL = "http://127.0.0.1:5100"

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
NC = '\033[0m'


def print_header(text):
    print(f"\n{CYAN}{'='*70}{NC}")
    print(f"{CYAN}{BOLD}{text}{NC}")
    print(f"{CYAN}{'='*70}{NC}\n")


def print_success(text):
    print(f"{GREEN}✓{NC} {text}")


def print_error(text):
    print(f"{RED}✗{NC} {text}")


def print_warning(text):
    print(f"{YELLOW}⚠{NC} {text}")


def print_info(text):
    print(f"{BLUE}ℹ{NC} {text}")


def check_job_service():
    """Check Job Service health"""
    print_info("Checking Job Service (port 5005)...")

    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)

        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status', 'unknown')

            if status == 'UP':
                print_success(f"Job Service: {status}")
                return True, data
            else:
                print_warning(f"Job Service status: {status}")
                return False, data
        else:
            print_error(f"Job Service returned status {resp.status_code}")
            return False, None

    except requests.exceptions.Timeout:
        print_error("Job Service: Connection timeout")
        return False, None
    except requests.exceptions.ConnectionError:
        print_error("Job Service: Connection refused (not running)")
        return False, None
    except Exception as e:
        print_error(f"Job Service error: {e}")
        return False, None


def check_ai_advisor_service(expected_mode=None):
    """Check AI Advisor Service health"""
    print_info("Checking AI Advisor Service (port 5100)...")

    try:
        resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status', 'unknown')

            if status == 'UP':
                print_success(f"AI Advisor Service: {status}")

                # Extract service info
                model_mode = data.get('model_mode', 'unknown')
                lora_enabled = data.get('lora_enabled', False)
                lora_path = data.get('lora_path', None)
                device = data.get('device', 'unknown')
                using_gpu = data.get('using_gpu', False)

                print_info(f"  Model mode: {model_mode}")
                print_info(f"  LoRA enabled: {lora_enabled}")
                if lora_path:
                    print_info(f"  LoRA path: {lora_path}")
                print_info(f"  Device: {device}")
                print_info(f"  Using GPU: {using_gpu}")

                warnings = []

                # Check GPU status
                if not using_gpu:
                    print_warning("  ⚠ Running in CPU mode (slow performance)")
                    warnings.append("CPU mode")

                # Check mode if expected
                if expected_mode:
                    mode_ok = False

                    if expected_mode == "lora" or expected_mode == "rag_lora":
                        mode_ok = lora_enabled
                    elif expected_mode == "baseline" or expected_mode == "base":
                        mode_ok = (model_mode == "base" and not lora_enabled)
                    elif expected_mode == "rag":
                        mode_ok = (model_mode == "base")

                    if not mode_ok:
                        print_warning(f"  ⚠ Expected mode '{expected_mode}' but got mode={model_mode}, lora={lora_enabled}")
                        warnings.append(f"Mode mismatch (expected {expected_mode})")

                return True, data, warnings
            else:
                print_warning(f"AI Advisor Service status: {status}")
                return False, data, []

        else:
            print_error(f"AI Advisor Service returned status {resp.status_code}")
            return False, None, []

    except requests.exceptions.Timeout:
        print_error("AI Advisor Service: Connection timeout")
        return False, None, []
    except requests.exceptions.ConnectionError:
        print_error("AI Advisor Service: Connection refused (not running)")
        return False, None, []
    except Exception as e:
        print_error(f"AI Advisor Service error: {e}")
        return False, None, []


def check_model_loading_status():
    """Check AI Advisor model loading status"""
    print_info("Checking model loading status...")

    try:
        resp = requests.get(f"{AI_ADVISOR_URL}/model-status", timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status', 'unknown')
            progress = data.get('progress', 0)
            message = data.get('message', '')

            print_info(f"  Status: {status}")
            print_info(f"  Progress: {progress}%")
            if message:
                print_info(f"  Message: {message}")

            if status == 'ready':
                print_success("  Model is loaded and ready")
                return True, data
            elif status == 'loading':
                print_warning("  Model is still loading")
                return False, data
            elif status == 'error':
                print_error(f"  Model loading failed: {message}")
                return False, data
            else:
                print_warning(f"  Unknown status: {status}")
                return False, data
        else:
            print_warning(f"Model status endpoint returned {resp.status_code}")
            return False, None

    except requests.exceptions.ConnectionError:
        print_warning("Model status endpoint not available (service may be starting)")
        return False, None
    except Exception as e:
        print_warning(f"Could not check model status: {e}")
        return False, None


def check_lora_adapter(advisor="ansel"):
    """Check if LoRA adapter files exist"""
    print_info(f"Checking LoRA adapter for advisor '{advisor}'...")

    adapter_path = Path(f"adapters/{advisor}")
    adapter_file = adapter_path / "adapters.safetensors"

    if adapter_file.exists():
        print_success(f"  LoRA adapter found: {adapter_path}")
        return True
    else:
        print_warning(f"  LoRA adapter not found: {adapter_path}")
        return False


def main():
    """Main health check"""
    parser = argparse.ArgumentParser(description="Verify service health before testing")
    parser.add_argument('--mode', type=str, choices=['base', 'baseline', 'rag', 'lora', 'rag_lora'],
                        help='Expected service mode')
    parser.add_argument('--advisor', type=str, default='ansel',
                        help='Advisor to check LoRA adapter for (default: ansel)')
    args = parser.parse_args()

    print_header("Service Health Verification")

    all_healthy = True
    warnings_list = []

    # Check Job Service
    print()
    job_ok, job_data = check_job_service()
    if not job_ok:
        all_healthy = False

    # Check AI Advisor Service
    print()
    advisor_ok, advisor_data, advisor_warnings = check_ai_advisor_service(args.mode)
    if not advisor_ok:
        all_healthy = False
    warnings_list.extend(advisor_warnings)

    # Check model loading status
    print()
    model_ok, model_data = check_model_loading_status()
    if not model_ok:
        warnings_list.append("Model not fully loaded")

    # Check LoRA adapter if testing LoRA modes
    if args.mode in ['lora', 'rag_lora']:
        print()
        lora_adapter_ok = check_lora_adapter(args.advisor)
        if not lora_adapter_ok:
            warnings_list.append("LoRA adapter not found")

    # Final verdict
    print()
    print_header("Health Check Result")

    if all_healthy and not warnings_list:
        print_success("✓ STATUS: READY")
        print_success("All services are healthy and ready for testing")
        sys.exit(0)
    elif all_healthy and warnings_list:
        print_warning("⚠ STATUS: DEGRADED")
        print_warning("Services are running but with warnings:")
        for warning in warnings_list:
            print_warning(f"  - {warning}")
        print_warning("\nTests may run but with degraded performance")
        sys.exit(2)
    else:
        print_error("✗ STATUS: NOT READY")
        print_error("One or more services are not healthy")
        print_error("\nPlease start services first:")
        if args.mode:
            if args.mode in ['lora', 'rag_lora']:
                print_error(f"  ./mondrian.sh --restart --mode={args.mode} --lora-path=./adapters/{args.advisor}")
            else:
                print_error(f"  ./mondrian.sh --restart --mode={args.mode}")
        else:
            print_error("  ./mondrian.sh --restart")
        sys.exit(1)


if __name__ == "__main__":
    main()
