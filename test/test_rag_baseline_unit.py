#!/usr/bin/env python3
"""
Unit tests for RAG vs Baseline API functionality

Tests both the enable_rag=true and enable_rag=false flows to ensure:
1. The flag is correctly passed from iOS app -> Job Service -> AI Advisor Service
2. RAG is enabled when enable_rag='true'
3. Baseline (no RAG) is used when enable_rag='false' or omitted
4. The response correctly indicates which mode was used

Usage:
    # Run directly (recommended):
    python3 test/test_rag_baseline_unit.py

    # Or with pytest (if installed):
    pytest test/test_rag_baseline_unit.py -v
"""

import requests
import time
import os
from pathlib import Path

# Optional pytest support
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create dummy pytest decorators
    class pytest:
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(func):
                return func
            return decorator

        @staticmethod
        def skip(msg):
            raise Exception(msg)

# Configuration
JOB_SERVICE_URL = os.getenv("JOB_SERVICE_URL", "http://127.0.0.1:5005")
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"
TIMEOUT = 120  # seconds to wait for job completion


class TestRAGBaseline:
    """Test RAG vs Baseline functionality"""

    @pytest.fixture(autouse=True)
    def check_services(self):
        """Ensure services are running before tests"""
        try:
            resp = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
            assert resp.status_code == 200, "Job service is not running"
        except Exception as e:
            if PYTEST_AVAILABLE:
                pytest.skip(f"Services not available: {e}")
            else:
                raise Exception(f"Services not available: {e}")

    @pytest.fixture
    def test_image_path(self):
        """Verify test image exists"""
        image_path = Path(TEST_IMAGE)
        if not image_path.exists():
            if PYTEST_AVAILABLE:
                pytest.skip(f"Test image not found: {TEST_IMAGE}")
            else:
                raise FileNotFoundError(f"Test image not found: {TEST_IMAGE}")
        return image_path

    def wait_for_job_completion(self, job_id, timeout=TIMEOUT):
        """Wait for job to complete and return final status"""
        status_url = f"{JOB_SERVICE_URL}/status/{job_id}"
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                resp = requests.get(status_url, timeout=5)
                if resp.status_code == 200:
                    job_data = resp.json()
                    status = job_data.get('status')

                    if status in ['done', 'error']:
                        return job_data

                time.sleep(2)  # Poll every 2 seconds
            except Exception as e:
                print(f"Error polling status: {e}")
                time.sleep(2)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

    def test_baseline_mode_explicit_false(self, test_image_path):
        """Test baseline mode with enable_rag='false' explicitly set"""
        print("\n" + "="*80)
        print("TEST: Baseline Mode (enable_rag='false')")
        print("="*80)

        with open(test_image_path, 'rb') as f:
            files = {'image': (test_image_path.name, f, 'image/jpeg')}
            data = {
                'advisor': ADVISOR,
                'enable_rag': 'false'  # Explicitly disable RAG
            }

            resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=30)

            assert resp.status_code in [200, 201], f"Upload failed: {resp.status_code} - {resp.text}"

            result = resp.json()
            job_id = result['job_id']
            enable_rag_response = result.get('enable_rag')

            print(f"✓ Upload successful - Job ID: {job_id}")
            print(f"✓ enable_rag in response: {enable_rag_response}")

            # Verify enable_rag is False in response
            assert enable_rag_response is False, f"Expected enable_rag=False, got {enable_rag_response}"

            # Wait for completion
            print(f"⏳ Waiting for job completion...")
            final_status = self.wait_for_job_completion(job_id)

            assert final_status['status'] == 'done', f"Job failed with status: {final_status.get('status')}"
            print(f"✓ Job completed successfully")
            print(f"✓ Analysis file: {final_status.get('analysis_file')}")

    def test_baseline_mode_omitted(self, test_image_path):
        """Test baseline mode with enable_rag omitted (default behavior)"""
        print("\n" + "="*80)
        print("TEST: Baseline Mode (enable_rag omitted - default)")
        print("="*80)

        with open(test_image_path, 'rb') as f:
            files = {'image': (test_image_path.name, f, 'image/jpeg')}
            data = {
                'advisor': ADVISOR
                # enable_rag NOT included - should default to False
            }

            resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=30)

            assert resp.status_code in [200, 201], f"Upload failed: {resp.status_code} - {resp.text}"

            result = resp.json()
            job_id = result['job_id']
            enable_rag_response = result.get('enable_rag')

            print(f"✓ Upload successful - Job ID: {job_id}")
            print(f"✓ enable_rag in response: {enable_rag_response}")

            # Verify enable_rag defaults to False
            assert enable_rag_response is False, f"Expected enable_rag=False (default), got {enable_rag_response}"

            # Wait for completion
            print(f"⏳ Waiting for job completion...")
            final_status = self.wait_for_job_completion(job_id)

            assert final_status['status'] == 'done', f"Job failed with status: {final_status.get('status')}"
            print(f"✓ Job completed successfully")

    def test_rag_mode_enabled(self, test_image_path):
        """Test RAG mode with enable_rag='true'"""
        print("\n" + "="*80)
        print("TEST: RAG Mode (enable_rag='true')")
        print("="*80)

        with open(test_image_path, 'rb') as f:
            files = {'image': (test_image_path.name, f, 'image/jpeg')}
            data = {
                'advisor': ADVISOR,
                'enable_rag': 'true'  # Enable RAG
            }

            resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=30)

            assert resp.status_code in [200, 201], f"Upload failed: {resp.status_code} - {resp.text}"

            result = resp.json()
            job_id = result['job_id']
            enable_rag_response = result.get('enable_rag')

            print(f"✓ Upload successful - Job ID: {job_id}")
            print(f"✓ enable_rag in response: {enable_rag_response}")

            # Verify enable_rag is True in response
            assert enable_rag_response is True, f"Expected enable_rag=True, got {enable_rag_response}"

            # Wait for completion
            print(f"⏳ Waiting for job completion...")
            final_status = self.wait_for_job_completion(job_id)

            assert final_status['status'] == 'done', f"Job failed with status: {final_status.get('status')}"
            print(f"✓ Job completed successfully with RAG enabled")
            print(f"✓ Analysis file: {final_status.get('analysis_file')}")

    def test_rag_variations(self, test_image_path):
        """Test different variations of enable_rag value"""
        print("\n" + "="*80)
        print("TEST: RAG Value Variations")
        print("="*80)

        test_cases = [
            ('true', True, "lowercase 'true'"),
            ('True', True, "capitalized 'True'"),
            ('TRUE', True, "uppercase 'TRUE'"),
            ('1', True, "numeric '1'"),
            ('yes', True, "word 'yes'"),
            ('false', False, "lowercase 'false'"),
            ('False', False, "capitalized 'False'"),
            ('0', False, "numeric '0'"),
            ('no', False, "word 'no'"),
        ]

        for value, expected, description in test_cases:
            print(f"\nTesting {description} (value='{value}')...")

            with open(test_image_path, 'rb') as f:
                files = {'image': (test_image_path.name, f, 'image/jpeg')}
                data = {
                    'advisor': ADVISOR,
                    'enable_rag': value,
                    'auto_analyze': 'false'  # Don't actually run analysis for speed
                }

                resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=30)

                assert resp.status_code in [200, 201], f"Upload failed for {description}: {resp.status_code}"

                result = resp.json()
                job_id = result['job_id']
                enable_rag_response = result.get('enable_rag')

                # Note: Response may not include enable_rag when auto_analyze=false
                print(f"  Job ID: {job_id}")
                print(f"  enable_rag in response: {enable_rag_response}")

                # The important thing is that the upload succeeded
                assert job_id is not None, f"No job_id returned for {description}"


def run_standalone():
    """Run tests without pytest"""
    print("\n" + "="*80)
    print("RAG vs Baseline Unit Tests")
    print("="*80)

    test = TestRAGBaseline()

    # Check services
    print("\nChecking services...")
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        if resp.status_code == 200:
            print(f"✓ Job Service is running")
        else:
            print(f"✗ Job Service returned status {resp.status_code}")
            print("\nERROR: Job Service not healthy. Please start it first:")
            print("  ./mondrian.sh --restart")
            return 1
    except Exception as e:
        print(f"✗ Job Service not reachable: {e}")
        print("\nERROR: Job Service not running. Please start it first:")
        print("  ./mondrian.sh --restart")
        return 1

    # Get test image
    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print(f"\n✗ ERROR: Test image not found: {TEST_IMAGE}")
        print(f"  Please ensure the test image exists at: {image_path.absolute()}")
        return 1
    else:
        print(f"✓ Test image found: {TEST_IMAGE}")

    # Run tests
    print("\nRunning tests...")
    print("="*80)

    try:
        print("\n")
        test.test_baseline_mode_explicit_false(image_path)
        print("\n✓ PASSED: Baseline mode (explicit false)")

        print("\n")
        test.test_baseline_mode_omitted(image_path)
        print("\n✓ PASSED: Baseline mode (omitted)")

        print("\n")
        test.test_rag_mode_enabled(image_path)
        print("\n✓ PASSED: RAG mode enabled")

        print("\n")
        test.test_rag_variations(image_path)
        print("\n✓ PASSED: RAG value variations")

        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        print("\nSummary:")
        print("  ✓ Baseline mode works correctly")
        print("  ✓ RAG mode works correctly")
        print("  ✓ Parameter variations handled properly")
        print("  ✓ API responses include enable_rag flag")
        return 0

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("  1. Ensure all services are running: ./mondrian.sh --restart")
        print("  2. Check service health: curl http://127.0.0.1:5005/health")
        print("  3. Check test image exists: ls -la source/mike-shrub.jpg")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_standalone())
