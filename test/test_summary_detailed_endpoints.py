#!/usr/bin/env python3
"""
Diagnostic test for summary and detailed recommendations endpoints
Tests both baseline and RAG flows to identify why recommendations are failing

Usage:
    python3 test/test_summary_detailed_endpoints.py
"""

import requests
import json
import sys
import os
from pathlib import Path

# Configuration
JOB_SERVICE_URL = os.getenv("JOB_SERVICE_URL", "http://127.0.0.1:5005")
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"

def check_services():
    """Check if services are running"""
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("✓ Job Service is running")
            return True
        else:
            print(f"✗ Job Service returned {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ Job Service is not running: {e}")
        return False

def test_summary_endpoint(job_id):
    """Test the /summary/{job_id} endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing Summary Endpoint: /summary/{job_id}")
    print(f"{'='*80}")
    
    try:
        url = f"{JOB_SERVICE_URL}/summary/{job_id}"
        print(f"URL: {url}")
        
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code != 200:
            print(f"✗ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        html = response.text
        print(f"Response Length: {len(html)} characters")
        
        # Check for required elements
        required_elements = {
            'Top 3 Recommendations': 'Top 3 Recommendations' in html,
            'recommendation-item': 'recommendation-item' in html,
            'recommendations-list': 'recommendations-list' in html or 'recommendations' in html.lower(),
        }
        
        print("\nRequired Elements Check:")
        all_present = True
        for element, present in required_elements.items():
            status = "✓" if present else "✗"
            print(f"  {status} '{element}': {present}")
            if not present:
                all_present = False
        
        # Check for error messages
        error_indicators = ['error', 'Error', 'not found', 'Not Found', 'processing', 'still being generated']
        found_errors = [ind for ind in error_indicators if ind in html]
        if found_errors:
            print(f"\n⚠ Warning: Found error indicators: {found_errors}")
            # Show context around error
            for err in found_errors[:2]:  # Show first 2 errors
                idx = html.find(err)
                if idx >= 0:
                    context = html[max(0, idx-50):idx+100]
                    print(f"  Context: ...{context}...")
        
        # Check if recommendations are empty
        if 'recommendations-list' in html or 'recommendations' in html.lower():
            # Try to count recommendation items
            rec_count = html.count('recommendation-item') or html.count('rec-number')
            print(f"\nRecommendation Items Found: {rec_count}")
            if rec_count == 0:
                print("⚠ Warning: No recommendation items found in HTML")
        
        return all_present and len(html) > 100
        
    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_detailed_endpoint(job_id):
    """Test the /analysis/{job_id} endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing Detailed Endpoint: /analysis/{job_id}")
    print(f"{'='*80}")
    
    try:
        url = f"{JOB_SERVICE_URL}/analysis/{job_id}"
        print(f"URL: {url}")
        
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code != 200:
            print(f"✗ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
        
        html = response.text
        print(f"Response Length: {len(html)} characters")
        
        # Check for required elements
        required_elements = {
            'feedback-card': 'feedback-card' in html,
            'advisor-section': 'advisor-section' in html or 'analysis' in html.lower(),
            'dimension': 'dimension' in html.lower() or 'composition' in html.lower(),
        }
        
        print("\nRequired Elements Check:")
        all_present = True
        for element, present in required_elements.items():
            status = "✓" if present else "✗"
            print(f"  {status} '{element}': {present}")
            if not present:
                all_present = False
        
        # Check for error messages
        error_indicators = ['error', 'Error', 'not found', 'Not Found', 'processing', 'still being generated']
        found_errors = [ind for ind in error_indicators if ind in html]
        if found_errors:
            print(f"\n⚠ Warning: Found error indicators: {found_errors}")
            # Show context around error
            for err in found_errors[:2]:  # Show first 2 errors
                idx = html.find(err)
                if idx >= 0:
                    context = html[max(0, idx-50):idx+100]
                    print(f"  Context: ...{context}...")
        
        # Check for recommendations in detailed view
        rec_indicators = ['recommendation', 'Recommendation']
        rec_found = any(ind in html for ind in rec_indicators)
        print(f"\nRecommendations in Detailed View: {'✓' if rec_found else '✗'}")
        
        return all_present and len(html) > 100
        
    except Exception as e:
        print(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_latest_job_id():
    """Get the latest completed job from the database"""
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/jobs", timeout=5)
        if resp.status_code == 200:
            jobs = resp.json()
            if jobs:
                # Find a completed job
                for job in jobs:
                    if job.get('status') == 'done':
                        return job.get('id')
                # If no done jobs, return the first one
                if jobs:
                    return jobs[0].get('id')
        return None
    except Exception as e:
        print(f"Error getting jobs list: {e}")
        return None

def main():
    """Main test function"""
    print("="*80)
    print("Summary and Detailed Endpoints Diagnostic Test")
    print("="*80)
    
    # Check services
    if not check_services():
        print("\n✗ Services are not running. Please start them first.")
        print("  Run: ./mondrian.sh --restart")
        sys.exit(1)
    
    # Get a job ID to test
    print("\nFetching latest job...")
    job_id = get_latest_job_id()
    
    if not job_id:
        print("✗ No jobs found. Please upload an image first.")
        print(f"  Upload to: {JOB_SERVICE_URL}/upload")
        sys.exit(1)
    
    print(f"✓ Using job ID: {job_id[:8]}...")
    
    # Test summary endpoint
    summary_ok = test_summary_endpoint(job_id)
    
    # Test detailed endpoint
    detailed_ok = test_detailed_endpoint(job_id)
    
    # Summary
    print(f"\n{'='*80}")
    print("Test Summary")
    print(f"{'='*80}")
    print(f"Summary Endpoint:   {'✓ PASS' if summary_ok else '✗ FAIL'}")
    print(f"Detailed Endpoint:  {'✓ PASS' if detailed_ok else '✗ FAIL'}")
    
    if not summary_ok or not detailed_ok:
        print("\n⚠ Issues found. Check the output above for details.")
        print("\nCommon issues:")
        print("  1. Job not completed yet - wait for status='done'")
        print("  2. No recommendations extracted - check extract_critical_recommendations()")
        print("  3. HTML structure mismatch - check json_to_html() output")
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
