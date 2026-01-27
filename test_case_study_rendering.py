#!/usr/bin/env python3
"""
E2E Test for Case Study Rendering
Tests that case studies render correctly with:
  - Case study boxes visible
  - Titles and years displayed
  - Images embedded or gracefully omitted
  - Metadata (location, scores, descriptions) visible

Usage:
    python3 test_case_study_rendering.py --url http://10.0.0.227:PORT [--image path/to/image.jpg]
"""
import requests
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
import html.parser

# Test configuration
TEST_IMAGE = Path("source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg")
FALLBACK_IMAGE = Path("source/mike-shrub.jpg")

ADVISOR = "ansel"

def get_test_image(image_path=None):
    """Find a test image to use"""
    if image_path:
        p = Path(image_path)
        if p.exists():
            return p
        print(f"❌ Image not found: {image_path}")
        return None

    if TEST_IMAGE.exists():
        return TEST_IMAGE
    if FALLBACK_IMAGE.exists():
        return FALLBACK_IMAGE

    # Try to find any jpg in source/
    source_dir = Path("source")
    if source_dir.exists():
        jpgs = list(source_dir.glob("*.jpg"))
        if jpgs:
            return jpgs[0]

    print("❌ No test image found. Provide one with --image or place in source/ directory")
    return None

def test_upload_and_analyze(base_url, image_path):
    """Upload image and get analysis with case studies"""
    print(f"\n📸 Uploading image: {image_path.name}")

    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {
                'advisor_id': ADVISOR,
                'auto_analyze': 'true'
            }

            response = requests.post(
                f"{base_url}/upload",
                files=files,
                data=data,
                timeout=60
            )

        if response.status_code not in [200, 201]:
            print(f"  ❌ Upload failed: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return None

        result = response.json()
        job_id = result.get('job_id')
        print(f"  ✅ Upload successful, job_id: {job_id}")

        return job_id

    except Exception as e:
        print(f"  ❌ Error uploading image: {e}")
        return None

def poll_analysis_status(base_url, job_id):
    """Poll until analysis is complete"""
    print(f"\n⏳ Waiting for analysis (job_id: {job_id})...")

    max_attempts = 120  # 2 minutes with 1 second intervals
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                f"{base_url}/status/{job_id}",
                timeout=10
            )

            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status')
                progress = status_data.get('progress', 0)

                if status == 'completed':
                    print(f"  ✅ Analysis completed!")
                    return status_data
                elif status == 'error':
                    print(f"  ❌ Analysis failed: {status_data.get('error')}")
                    return None
                else:
                    if attempt % 10 == 0:
                        print(f"     Progress: {progress}% - Status: {status}")

            import time
            time.sleep(1)

        except Exception as e:
            print(f"  ⚠️  Poll error: {e}")
            continue

    print(f"  ❌ Analysis timed out after {max_attempts} attempts")
    return None

def fetch_full_analysis_html(base_url, job_id):
    """Fetch the full HTML analysis"""
    print(f"\n📄 Fetching full analysis HTML...")

    try:
        response = requests.get(
            f"{base_url}/analysis/{job_id}",
            timeout=30
        )

        if response.status_code == 200:
            html_content = response.text
            print(f"  ✅ Fetched {len(html_content)} characters of HTML")
            return html_content
        else:
            print(f"  ❌ Failed to fetch analysis: {response.status_code}")
            return None

    except Exception as e:
        print(f"  ❌ Error fetching analysis: {e}")
        return None

def check_case_study_elements(html_content):
    """Check if case study elements are present in the HTML"""
    print(f"\n🔍 Analyzing HTML for case study elements...")

    checks = {
        'case-study-box': 'Case study box (container)',
        'case-study-title': 'Case study title',
        'case-study-image': 'Case study image (may fail to load)',
        'case-study-metadata': 'Case study metadata (location, scores, etc)',
        'Case Study:': 'Case study text in content'
    }

    results = {}
    for check_str, description in checks.items():
        found = check_str in html_content
        results[check_str] = found
        status = "✅" if found else "❌"
        print(f"  {status} {description}: {check_str}")

    # Additional checks
    case_study_count = html_content.count('case-study-box')
    print(f"\n  📊 Found {case_study_count} case study boxes")

    # Check for error messages in logs
    if '[RAG] Image path not found' in html_content:
        print(f"  ⚠️  Warning: Found path resolution errors in response")
        # Extract the error lines
        lines = html_content.split('\n')
        for line in lines:
            if '[RAG] Image path not found' in line:
                print(f"     {line.strip()[:100]}")

    return results, case_study_count

def save_html_for_inspection(html_content, filename="test_analysis_output.html"):
    """Save HTML to file for manual inspection"""
    output_path = Path(filename)
    with open(output_path, 'w') as f:
        f.write(html_content)
    print(f"\n💾 HTML saved to: {output_path}")
    print(f"   Open in browser: file://{output_path.absolute()}")

def main():
    parser = argparse.ArgumentParser(description="Test case study rendering")
    parser.add_argument('--url', required=True, help='Base URL of the service (e.g., http://10.0.0.227:5005)')
    parser.add_argument('--image', help='Path to test image')
    parser.add_argument('--save-html', action='store_true', help='Save HTML output to file')

    args = parser.parse_args()

    base_url = args.url.rstrip('/')

    print("=" * 60)
    print("Case Study Rendering E2E Test")
    print("=" * 60)
    print(f"Service URL: {base_url}")
    print(f"Advisor: {ADVISOR}")
    print()

    # Check service health
    print("🏥 Checking service health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ Service is healthy")
        else:
            print(f"  ⚠️  Service returned status {response.status_code}")
    except Exception as e:
        print(f"  ❌ Service is not reachable: {e}")
        print(f"     Check that {base_url} is accessible")
        return 1

    # Get test image
    image_path = get_test_image(args.image)
    if not image_path:
        return 1

    # Upload and analyze
    job_id = test_upload_and_analyze(base_url, image_path)
    if not job_id:
        return 1

    # Wait for completion
    status_data = poll_analysis_status(base_url, job_id)
    if not status_data:
        return 1

    # Fetch analysis
    html_content = fetch_full_analysis_html(base_url, job_id)
    if not html_content:
        return 1

    # Analyze case studies
    results, count = check_case_study_elements(html_content)

    # Save HTML for inspection
    if args.save_html or (count == 0 or not results.get('case-study-box')):
        save_html_for_inspection(html_content)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    if count > 0 and results.get('case-study-box'):
        print(f"✅ SUCCESS: Case studies are rendering!")
        print(f"   Found {count} case study boxes")
        if results.get('case-study-title'):
            print(f"   Titles are present")
        if results.get('case-study-metadata'):
            print(f"   Metadata is present")
        print(f"\n   Check logs for '[RAG] Image path not found' errors")
        return 0
    else:
        print(f"❌ FAILURE: Case studies are NOT rendering properly")
        print(f"   Case study boxes found: {count}")
        print(f"   Results: {json.dumps(results, indent=2)}")
        print(f"\n   → Saved HTML to test_analysis_output.html for inspection")
        return 1

if __name__ == '__main__':
    sys.exit(main())
