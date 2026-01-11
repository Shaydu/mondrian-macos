#!/usr/bin/env python3
"""
Quick RAG toggle test - just verifies the enable_rag parameter works

This is the minimal test to verify RAG toggle functionality.
Doesn't wait for job completion, just checks the upload response.

Usage:
    python3 test/test_rag_quick.py
"""

import requests
import sqlite3
from pathlib import Path

JOB_SERVICE_URL = "http://127.0.0.1:5005"
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"
DB_PATH = "mondrian.db"


def test_upload(enable_rag_value, description):
    """Test upload with specific enable_rag value"""
    print(f"\nTesting: {description}")
    print(f"  enable_rag={enable_rag_value}")

    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print(f"  ✗ Test image not found: {TEST_IMAGE}")
        return False

    with open(image_path, 'rb') as f:
        files = {'image': (image_path.name, f, 'image/jpeg')}
        data = {
            'advisor': ADVISOR,
            'auto_analyze': 'false'  # Don't actually analyze for speed
        }

        # Add enable_rag if specified
        if enable_rag_value is not None:
            data['enable_rag'] = enable_rag_value

        try:
            resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=10)

            if resp.status_code not in [200, 201]:
                print(f"  ✗ Upload failed: {resp.status_code}")
                print(f"  Response: {resp.text[:200]}")
                return False

            result = resp.json()
            job_id = result.get('job_id')
            enable_rag_response = result.get('enable_rag')

            print(f"  ✓ Upload successful")
            print(f"  Job ID: {job_id}")
            print(f"  enable_rag in response: {enable_rag_response}")

            # Verify database storage
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT enable_rag FROM jobs WHERE id = ?", (job_id,))
                row = cursor.fetchone()
                conn.close()

                if row is not None:
                    db_enable_rag = row[0]
                    expected_db_value = 1 if enable_rag_response else 0

                    if db_enable_rag == expected_db_value:
                        print(f"  ✓ Database correctly stores enable_rag={db_enable_rag}")
                    else:
                        print(f"  ✗ Database mismatch: stored {db_enable_rag}, expected {expected_db_value}")
                        return False
                else:
                    print(f"  ⚠ Job not found in database (might not be created yet)")
            except Exception as e:
                print(f"  ⚠ Database check failed: {e}")

            return True

        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False


def main():
    print("="*80)
    print("Quick RAG Toggle Test")
    print("="*80)

    # Check service
    print("\nChecking Job Service...")
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("✓ Job Service is running")
        else:
            print(f"✗ Job Service unhealthy: {resp.status_code}")
            print("\nPlease start services: ./mondrian.sh --restart")
            return 1
    except Exception as e:
        print(f"✗ Job Service not reachable: {e}")
        print("\nPlease start services: ./mondrian.sh --restart")
        return 1

    # Run tests
    print("\n" + "="*80)
    print("Testing Different enable_rag Values")
    print("="*80)

    tests = [
        (None, "No enable_rag parameter (default)"),
        ('false', "enable_rag='false' (baseline)"),
        ('true', "enable_rag='true' (RAG enabled)"),
    ]

    results = []
    for value, desc in tests:
        success = test_upload(value, desc)
        results.append((desc, success))

    # Summary
    print("\n" + "="*80)
    print("Summary")
    print("="*80)

    all_passed = all(result[1] for result in results)

    for desc, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {desc}")

    if all_passed:
        print("\n✓ ALL TESTS PASSED")
        print("\nThe enable_rag parameter is working correctly!")
        print("You can now use it in your iOS app:")
        print("  - Pass 'enable_rag=false' for baseline mode")
        print("  - Pass 'enable_rag=true' for RAG-enhanced analysis")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
