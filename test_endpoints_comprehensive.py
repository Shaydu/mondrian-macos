#!/usr/bin/env python3
"""
Comprehensive Endpoint Testing Script for Mondrian Services
Tests all API endpoints to verify they return correct status codes and no 500 errors
"""

import requests
import time
import sys
import os
import json
from pathlib import Path

# Service URLs - adjust as needed
JOB_SERVICE_URL = "http://localhost:5005"
AI_ADVISOR_URL = "http://localhost:5100"

class EndpointTester:
    def __init__(self, job_service_url=JOB_SERVICE_URL, ai_service_url=AI_ADVISOR_URL):
        self.job_service_url = job_service_url.rstrip('/')
        self.ai_service_url = ai_service_url.rstrip('/')
        self.test_results = []

    def log(self, message, status="INFO"):
        """Log with status indicator"""
        status_icons = {
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️",
            "INFO": "ℹ️"
        }
        icon = status_icons.get(status, "ℹ️")
        print(f"{icon} {message}")

        self.test_results.append({
            "timestamp": time.time(),
            "message": message,
            "status": status
        })

    def test_endpoint(self, name, url, expected_status=200, method="GET", data=None, files=None, timeout=10):
        """Test a single endpoint"""
        try:
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, data=data, files=files, timeout=timeout)
            else:
                self.log(f"Unsupported method: {method}", "FAIL")
                return False

            if response.status_code == expected_status:
                self.log(f"{name}: {response.status_code} (expected {expected_status})", "PASS")
                return True, response
            else:
                self.log(f"{name}: {response.status_code} (expected {expected_status})", "FAIL")
                if response.status_code >= 500:
                    self.log(f"  500 ERROR: {response.text[:200]}", "FAIL")
                return False, response

        except requests.exceptions.RequestException as e:
            self.log(f"{name}: Connection failed - {e}", "FAIL")
            return False, None
        except Exception as e:
            self.log(f"{name}: Unexpected error - {e}", "FAIL")
            return False, None

    def test_health_endpoints(self):
        """Test health endpoints for both services"""
        self.log("Testing Health Endpoints", "INFO")

        # Test Job Service health
        success, response = self.test_endpoint(
            "Job Service Health",
            f"{self.job_service_url}/health"
        )
        if success and response:
            try:
                health_data = response.json()
                self.log(f"  Job Service version: {health_data.get('version', 'unknown')}", "INFO")
            except:
                pass

        # Test AI Advisor health
        success, response = self.test_endpoint(
            "AI Advisor Health",
            f"{self.ai_service_url}/health"
        )
        if success and response:
            try:
                health_data = response.json()
                self.log(f"  AI Advisor version: {health_data.get('version', 'unknown')}", "INFO")
                self.log(f"  Model: {health_data.get('model', 'unknown')}", "INFO")
            except:
                pass

    def test_advisors_endpoint(self):
        """Test advisors endpoint"""
        self.log("Testing Advisors Endpoint", "INFO")

        success, response = self.test_endpoint(
            "Get Advisors",
            f"{self.job_service_url}/advisors"
        )
        if success and response:
            try:
                advisors_data = response.json()
                if isinstance(advisors_data, dict) and 'advisors' in advisors_data:
                    advisors = advisors_data['advisors']
                    if isinstance(advisors, list):
                        self.log(f"  Found {len(advisors)} advisors", "INFO")
                    elif isinstance(advisors, dict):
                        self.log(f"  Found {len(advisors)} advisors", "INFO")
                else:
                    self.log("  Unexpected advisors response format", "WARN")
            except:
                pass

    def test_jobs_endpoint(self):
        """Test jobs listing endpoint"""
        self.log("Testing Jobs Endpoint", "INFO")

        success, response = self.test_endpoint(
            "List Jobs",
            f"{self.job_service_url}/jobs"
        )
        if success and response:
            try:
                jobs_data = response.json()
                if isinstance(jobs_data, list):
                    self.log(f"  Found {len(jobs_data)} jobs", "INFO")
                else:
                    self.log("  Unexpected jobs response format", "WARN")
            except:
                pass

    def test_upload_endpoint(self):
        """Test image upload endpoint"""
        self.log("Testing Upload Endpoint", "INFO")

        # Find a test image
        test_images = [
            "source/mike-shrub.jpg",
            "mondrian/source/mike-shrub.jpg",
            "mondrian/source/photo-194899EF-81C8-4381-97F7-FAEE99BFDBD7-2645c141.jpg"
        ]

        image_path = None
        for path in test_images:
            if os.path.exists(path):
                image_path = path
                break

        if not image_path:
            self.log("No test image found, skipping upload test", "WARN")
            return

        self.log(f"  Using test image: {image_path}", "INFO")

        try:
            with open(image_path, 'rb') as f:
                files = {'image': ('test.jpg', f, 'image/jpeg')}
                data = {'advisor': 'ansel', 'auto_analyze': 'true'}

                success, response = self.test_endpoint(
                    "Upload Image",
                    f"{self.job_service_url}/upload",
                    method="POST",
                    files=files,
                    data=data,
                    expected_status=201
                )

                if success and response:
                    try:
                        upload_data = response.json()
                        job_id = upload_data.get('job_id')
                        if job_id:
                            self.log(f"  Created job: {job_id}", "INFO")
                            return job_id
                    except:
                        pass

        except Exception as e:
            self.log(f"Upload failed: {e}", "FAIL")

        return None

    def test_status_and_analysis_endpoints(self, job_id):
        """Test status and analysis endpoints for a job"""
        if not job_id:
            return

        self.log(f"Testing Status and Analysis for Job: {job_id}", "INFO")

        # Test status endpoint
        success, response = self.test_endpoint(
            f"Job Status ({job_id[:8]}...)",
            f"{self.job_service_url}/status/{job_id}"
        )

        if success and response:
            try:
                status_data = response.json()
                status = status_data.get('status')
                self.log(f"  Job status: {status}", "INFO")

                if status == 'done':
                    # Test analysis endpoint
                    success, response = self.test_endpoint(
                        f"Job Analysis ({job_id[:8]}...)",
                        f"{self.job_service_url}/analysis/{job_id}"
                    )

                    if success and response:
                        content_length = len(response.text)
                        self.log(f"  Analysis length: {content_length} characters", "INFO")

                        # Check if it contains HTML table
                        if '<table>' in response.text and '<tr>' in response.text:
                            self.log("  Analysis contains HTML table format", "PASS")
                        else:
                            self.log("  Analysis may not be in expected format", "WARN")
                    else:
                        self.log(f"  Analysis endpoint failed for completed job", "FAIL")

                elif status == 'error':
                    self.log(f"  Job failed: {status_data.get('current_step', 'Unknown error')}", "WARN")
                else:
                    self.log(f"  Job still processing: {status}", "INFO")

            except Exception as e:
                self.log(f"Failed to parse status response: {e}", "FAIL")

    def test_nonexistent_job(self):
        """Test endpoints with nonexistent job ID"""
        self.log("Testing Non-existent Job Handling", "INFO")

        fake_job_id = "00000000-0000-0000-0000-000000000000"

        # Test status
        self.test_endpoint(
            "Non-existent Job Status",
            f"{self.job_service_url}/status/{fake_job_id}",
            expected_status=404
        )

        # Test analysis
        self.test_endpoint(
            "Non-existent Job Analysis",
            f"{self.job_service_url}/analysis/{fake_job_id}",
            expected_status=404
        )

    def run_comprehensive_test(self):
        """Run all endpoint tests"""
        print("=" * 80)
        print("🧪 MONDRIAN ENDPOINT COMPREHENSIVE TEST")
        print("=" * 80)
        print(f"Job Service: {self.job_service_url}")
        print(f"AI Advisor:  {self.ai_service_url}")
        print("=" * 80)

        start_time = time.time()

        # Test 1: Health endpoints
        self.test_health_endpoints()
        print()

        # Test 2: Advisors endpoint
        self.test_advisors_endpoint()
        print()

        # Test 3: Jobs listing
        self.test_jobs_endpoint()
        print()

        # Test 4: Upload and job processing
        job_id = self.test_upload_endpoint()
        if job_id:
            print()
            # Wait a bit for processing to start
            self.log("Waiting for job processing to begin...", "INFO")
            time.sleep(3)

            # Test status and analysis
            self.test_status_and_analysis_endpoints(job_id)

            # Wait for completion (up to 30 seconds)
            self.log("Waiting for job completion (max 30s)...", "INFO")
            for i in range(30):
                success, response = self.test_endpoint(
                    "Job Status Check",
                    f"{self.job_service_url}/status/{job_id}",
                    expected_status=200
                )
                if success and response:
                    try:
                        status_data = response.json()
                        if status_data.get('status') == 'done':
                            break
                        elif status_data.get('status') == 'error':
                            break
                    except:
                        pass
                time.sleep(1)

            print()
            self.test_status_and_analysis_endpoints(job_id)
        print()

        # Test 5: Error handling
        self.test_nonexistent_job()
        print()

        # Summary
        end_time = time.time()
        duration = end_time - start_time

        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Duration: {duration:.2f} seconds")

        passes = len([r for r in self.test_results if r['status'] == 'PASS'])
        fails = len([r for r in self.test_results if r['status'] == 'FAIL'])
        warns = len([r for r in self.test_results if r['status'] == 'WARN'])

        print(f"✅ Passed: {passes}")
        print(f"❌ Failed: {fails}")
        print(f"⚠️  Warnings: {warns}")

        if fails == 0:
            print("\n🎉 ALL ENDPOINTS WORKING CORRECTLY!")
            return True
        else:
            print(f"\n⚠️  {fails} endpoint(s) failed. Check logs for details.")
            return False

def main():
    """Main test function"""
    print("Mondrian Endpoint Tester")
    print("Usage: python3 test_endpoints_comprehensive.py [job_service_url] [ai_service_url]")
    print()

    # Allow custom URLs
    job_url = JOB_SERVICE_URL
    ai_url = AI_ADVISOR_URL

    if len(sys.argv) > 1:
        job_url = sys.argv[1]
    if len(sys.argv) > 2:
        ai_url = sys.argv[2]

    tester = EndpointTester(job_url, ai_url)
    success = tester.run_comprehensive_test()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
