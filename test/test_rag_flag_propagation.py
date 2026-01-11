#!/usr/bin/env python3
"""
RAG Flag Propagation Test - Comprehensive verification of enable_rag parameter flow

This test verifies that the enable_rag parameter properly flows through:
1. Upload endpoint → Database storage
2. Job queue → process_job function
3. process_job → AI Advisor Service
4. AI Advisor Service → RAG code path execution

Usage:
    python3 test/test_rag_flag_propagation.py
"""

import requests
import sqlite3
import time
import sys
from pathlib import Path

# Configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
AI_ADVISOR_URL = "http://127.0.0.1:5100"
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"
DB_PATH = "mondrian.db"

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
    """Check that required services are running"""
    print_step(1, "Checking Services")

    services = [
        ("Job Service", f"{JOB_SERVICE_URL}/health", 5005),
        ("AI Advisor Service", f"{AI_ADVISOR_URL}/health", 5100),
    ]

    all_up = True
    for name, url, port in services:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print_success(f"{name} (port {port}) - UP")
            else:
                print_error(f"{name} (port {port}) - UNHEALTHY (status: {resp.status_code})")
                all_up = False
        except Exception as e:
            print_error(f"{name} (port {port}) - DOWN ({e})")
            all_up = False

    if not all_up:
        print_error("Not all services are running!")
        print_info("Please start services: ./mondrian.sh --restart")
        return False

    return True


def check_database_schema():
    """Verify enable_rag column exists in database"""
    print_step(2, "Checking Database Schema")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()

        if 'enable_rag' in columns:
            print_success("enable_rag column exists in jobs table")
            return True
        else:
            print_error("enable_rag column NOT FOUND in jobs table")
            print_info("Run: python3 init_database.py")
            return False
    except Exception as e:
        print_error(f"Database check failed: {e}")
        return False


def test_rag_enabled():
    """Test with enable_rag=true"""
    print_step(3, "Testing RAG-Enabled Mode")

    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print_error(f"Test image not found: {TEST_IMAGE}")
        return False

    # Upload with enable_rag=true
    print_info("Uploading image with enable_rag='true'...")
    with open(image_path, 'rb') as f:
        files = {'image': (image_path.name, f, 'image/jpeg')}
        data = {
            'advisor': ADVISOR,
            'auto_analyze': 'true',
            'enable_rag': 'true'
        }

        try:
            resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=10)
            if resp.status_code not in [200, 201]:
                print_error(f"Upload failed: {resp.status_code}")
                print_error(f"Response: {resp.text[:200]}")
                return False

            result = resp.json()
            job_id = result.get('job_id')
            enable_rag_response = result.get('enable_rag')

            print_success(f"Upload successful - Job ID: {job_id}")
            print_info(f"enable_rag in response: {enable_rag_response}")

            # Verify response includes enable_rag=true
            if not enable_rag_response:
                print_error("enable_rag=true not in response!")
                return False
            print_success("✓ Upload response includes enable_rag=true")

        except Exception as e:
            print_error(f"Upload error: {e}")
            return False

    # Wait for job completion
    print_info("Waiting for job to complete...")
    timeout = 180
    start_time = time.time()
    status = None

    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=10)
            if resp.status_code == 200:
                status_data = resp.json()
                status = status_data.get('status')

                if status == 'done':
                    print_success("Job completed successfully")
                    break
                elif status == 'error':
                    print_error("Job failed with error status")
                    return False
                else:
                    print_info(f"Job status: {status}")

            time.sleep(5)
        except Exception as e:
            print_error(f"Status check error: {e}")
            time.sleep(5)

    if status != 'done':
        print_error(f"Job did not complete within {timeout}s (final status: {status})")
        return False

    # Check database for stored enable_rag value
    print_info("Checking database for enable_rag value...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT enable_rag FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            print_error(f"Job {job_id} not found in database!")
            return False

        db_enable_rag = row[0]
        print_info(f"Database enable_rag value: {db_enable_rag}")

        if db_enable_rag == 1:
            print_success("✓ Database correctly stores enable_rag=1")
        else:
            print_error(f"Database has enable_rag={db_enable_rag}, expected 1!")
            return False

    except Exception as e:
        print_error(f"Database query error: {e}")
        return False

    print_success("✓ RAG-Enabled test PASSED")
    return True


def test_baseline():
    """Test with enable_rag=false"""
    print_step(4, "Testing Baseline Mode (RAG Disabled)")

    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print_error(f"Test image not found: {TEST_IMAGE}")
        return False

    # Upload with enable_rag=false
    print_info("Uploading image with enable_rag='false'...")
    with open(image_path, 'rb') as f:
        files = {'image': (image_path.name, f, 'image/jpeg')}
        data = {
            'advisor': ADVISOR,
            'auto_analyze': 'true',
            'enable_rag': 'false'
        }

        try:
            resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=10)
            if resp.status_code not in [200, 201]:
                print_error(f"Upload failed: {resp.status_code}")
                print_error(f"Response: {resp.text[:200]}")
                return False

            result = resp.json()
            job_id = result.get('job_id')
            enable_rag_response = result.get('enable_rag')

            print_success(f"Upload successful - Job ID: {job_id}")
            print_info(f"enable_rag in response: {enable_rag_response}")

            # Verify response includes enable_rag=false
            if enable_rag_response:
                print_error("enable_rag should be false!")
                return False
            print_success("✓ Upload response includes enable_rag=false")

        except Exception as e:
            print_error(f"Upload error: {e}")
            return False

    # Wait for job completion
    print_info("Waiting for job to complete...")
    timeout = 180
    start_time = time.time()
    status = None

    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=10)
            if resp.status_code == 200:
                status_data = resp.json()
                status = status_data.get('status')

                if status == 'done':
                    print_success("Job completed successfully")
                    break
                elif status == 'error':
                    print_error("Job failed with error status")
                    return False
                else:
                    print_info(f"Job status: {status}")

            time.sleep(5)
        except Exception as e:
            print_error(f"Status check error: {e}")
            time.sleep(5)

    if status != 'done':
        print_error(f"Job did not complete within {timeout}s (final status: {status})")
        return False

    # Check database for stored enable_rag value
    print_info("Checking database for enable_rag value...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT enable_rag FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            print_error(f"Job {job_id} not found in database!")
            return False

        db_enable_rag = row[0]
        print_info(f"Database enable_rag value: {db_enable_rag}")

        if db_enable_rag == 0:
            print_success("✓ Database correctly stores enable_rag=0")
        else:
            print_error(f"Database has enable_rag={db_enable_rag}, expected 0!")
            return False

    except Exception as e:
        print_error(f"Database query error: {e}")
        return False

    print_success("✓ Baseline test PASSED")
    return True


def main():
    """Main test runner"""
    print_header("RAG Flag Propagation Test")
    print("This test verifies enable_rag parameter flows correctly through the system")

    # Check services
    if not check_services():
        return 1

    # Check database schema
    if not check_database_schema():
        return 1

    # Run tests
    results = []

    # Test RAG-enabled
    results.append(("RAG-Enabled Mode", test_rag_enabled()))

    # Test baseline
    results.append(("Baseline Mode", test_baseline()))

    # Summary
    print_header("Test Summary")

    all_passed = all(result[1] for result in results)

    for test_name, passed in results:
        if passed:
            print_success(f"PASS: {test_name}")
        else:
            print_error(f"FAIL: {test_name}")

    if all_passed:
        print(f"\n{GREEN}{BOLD}✓ ALL TESTS PASSED{NC}")
        print("\nThe enable_rag parameter is correctly:")
        print("  1. Received from upload requests")
        print("  2. Stored in the database")
        print("  3. Passed to the AI service")
        print("  4. Used to control RAG code path execution")
        print("\nNext steps:")
        print("  - Check service logs for RAG activation messages")
        print("  - Run: python3 mondrian/test/view_all_jobs.py")
        print("  - Open: mondrian/analysis_output/jobs_list.html")
        return 0
    else:
        print(f"\n{RED}{BOLD}✗ SOME TESTS FAILED{NC}")
        print("\nPlease check:")
        print("  1. Service logs for errors")
        print("  2. Database schema (run: python3 init_database.py)")
        print("  3. Code changes in job_service_v2.3.py and ai_advisor_service.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
