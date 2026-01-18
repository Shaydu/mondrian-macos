#!/usr/bin/env python3
"""
Test PDF export functionality and file size
Helps verify that exported PDFs are optimized and under 1MB
"""

import requests
import sys
from pathlib import Path
import json

def get_latest_job_id(job_service_url="http://localhost:5005"):
    """Get the most recent completed job ID"""
    try:
        response = requests.get(f"{job_service_url}/jobs", timeout=5)
        if response.status_code == 200:
            jobs = response.json()
            if isinstance(jobs, list):
                for job in jobs:
                    if job.get('status') == 'completed':
                        return job.get('id')
    except Exception as e:
        print(f"Error fetching jobs: {e}")
    return None

def test_export(job_id, export_service_url="http://localhost:5007"):
    """Test HTML export and estimate PDF size"""
    try:
        print(f"\nTesting export for job: {job_id}")
        
        # Get export HTML
        response = requests.get(f"{export_service_url}/export/{job_id}", timeout=10)
        if response.status_code != 200:
            print(f"Error: Export returned {response.status_code}")
            return False
        
        html = response.text
        html_size_kb = len(html.encode('utf-8')) / 1024
        
        print(f"✓ Export HTML size: {html_size_kb:.1f} KB")
        
        # Count images in HTML
        import re
        images = re.findall(r'src="data:image/[^"]+base64,[^"]{100,}"', html)
        print(f"✓ Embedded images: {len(images)}")
        
        # Estimate image compression
        image_bytes = sum(len(img) for img in images)
        image_kb = image_bytes / 1024
        print(f"✓ Total image data: ~{image_kb:.1f} KB")
        
        # Estimate PDF size (typically 30-50% of HTML size with native PDF compression)
        estimated_pdf_kb = html_size_kb * 0.4  # Conservative estimate
        print(f"✓ Estimated PDF size: ~{estimated_pdf_kb:.1f} KB")
        
        if estimated_pdf_kb < 1024:
            print(f"✓ ✓ PASSED: Estimated PDF size under 1MB")
            return True
        else:
            print(f"✗ WARNING: Estimated PDF size may exceed 1MB")
            return False
        
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to export service at {export_service_url}")
        print("Make sure both job service and export service are running:")
        print("  python3 mondrian/job_service_v2.3.py --port 5005")
        print("  python3 mondrian/export_service_linux.py --port 5007")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main test routine"""
    job_service_url = "http://localhost:5005"
    export_service_url = "http://localhost:5007"
    
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        print("Finding latest completed job...")
        job_id = get_latest_job_id(job_service_url)
        if not job_id:
            print("No completed jobs found. Run an analysis first.")
            return 1
        print(f"Found job: {job_id}")
    
    success = test_export(job_id, export_service_url)
    
    print("\nNotes:")
    print("- Images are automatically downsampled to 800x600 max")
    print("- JPEG quality is adjusted (30-75) to fit within 40KB per image")
    print("- CSS is simplified for better PDF rendering")
    print("- Page breaks are optimized to avoid splitting cards")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
