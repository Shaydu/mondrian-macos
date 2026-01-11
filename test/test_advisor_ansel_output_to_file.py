#!/usr/bin/env python3
"""
Test: Run Ansel advisor on a sample image and write both summary and full advisor output to files for review.
"""
import os
import requests
import time
import json

JOB_SERVICE_URL = "http://localhost:5005"
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR_ID = "ansel"
OUTPUT_DIR = "advisor_output_review"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def upload_image_and_get_job_id(image_path, advisor_id, enable_rag=False):
    with open(image_path, 'rb') as f:
        files = {'image': (os.path.basename(image_path), f, 'image/jpeg')}
        data = {
            'advisor': advisor_id,
            'auto_analyze': 'true',
            'enable_rag': 'true' if enable_rag else 'false'
        }
        resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=30)
        resp.raise_for_status()
        job_id = resp.json().get('job_id')
        return job_id

def wait_for_job_done(job_id, poll_interval=2, timeout=180):
    status_url = f"{JOB_SERVICE_URL}/status/{job_id}"
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(status_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get('status') == 'done':
            return True
        elif data.get('status') == 'error':
            print(f"Job failed: {data.get('current_step')}")
            return False
        time.sleep(poll_interval)
    print("Timeout waiting for job to complete.")
    return False

def fetch_and_write_analysis(job_id, suffix=""):
    analysis_url = f"{JOB_SERVICE_URL}/analysis/{job_id}"
    resp = requests.get(analysis_url, timeout=20)
    if resp.status_code == 200:
        html = resp.text
        filename = f"{job_id}_{suffix}_full.html" if suffix else f"{job_id}_full.html"
        with open(os.path.join(OUTPUT_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[OK] Wrote full advisor output to {OUTPUT_DIR}/{filename}")
        return filename
    else:
        print(f"[ERROR] Could not fetch analysis: {resp.text}")
        return None

def fetch_and_write_summary(job_id):
    # Try to fetch summary from job status (if available)
    status_url = f"{JOB_SERVICE_URL}/status/{job_id}"
    resp = requests.get(status_url, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        summary = data.get('current_step', '')
        with open(os.path.join(OUTPUT_DIR, f"{job_id}_summary.txt"), 'w', encoding='utf-8') as f:
            f.write(summary)
        print(f"[OK] Wrote summary to {OUTPUT_DIR}/{job_id}_summary.txt")
    else:
        print(f"[WARN] Could not fetch summary: {resp.text}")

def main():
    print("=" * 60)
    print("RAG vs Non-RAG Comparison Test")
    print("=" * 60)

    # Run with RAG context
    print(f"\n[1/2] Running Ansel advisor WITH RAG context...")
    print(f"Uploading image {TEST_IMAGE} for advisor '{ADVISOR_ID}' (enable_rag=True)...")
    rag_job_id = upload_image_and_get_job_id(TEST_IMAGE, ADVISOR_ID, enable_rag=True)
    print(f"RAG Job ID: {rag_job_id}")
    print("Waiting for RAG job to complete...")
    rag_filename = None
    if wait_for_job_done(rag_job_id):
        rag_filename = fetch_and_write_analysis(rag_job_id, suffix="rag")
        fetch_and_write_summary(rag_job_id)
    else:
        print("[ERROR] RAG job did not complete successfully.")

    # Run without RAG context (baseline)
    print(f"\n[2/2] Running Ansel advisor WITHOUT RAG context (baseline)...")
    print(f"Uploading image {TEST_IMAGE} for advisor '{ADVISOR_ID}' (enable_rag=False)...")
    baseline_job_id = upload_image_and_get_job_id(TEST_IMAGE, ADVISOR_ID, enable_rag=False)
    print(f"Baseline Job ID: {baseline_job_id}")
    print("Waiting for baseline job to complete...")
    baseline_filename = None
    if wait_for_job_done(baseline_job_id):
        baseline_filename = fetch_and_write_analysis(baseline_job_id, suffix="baseline")
        fetch_and_write_summary(baseline_job_id)
    else:
        print("[ERROR] Baseline job did not complete successfully.")

    # Generate comparison HTML
    if rag_filename and baseline_filename:
        print(f"\n[3/3] Generating comparison HTML...")
        comparison_cmd = (
            f"python3 compare_advisor_outputs.py "
            f"--image {TEST_IMAGE} "
            f"--rag {OUTPUT_DIR}/{rag_filename} "
            f"--baseline {OUTPUT_DIR}/{baseline_filename} "
            f"--compare"
        )
        print(f"Running: {comparison_cmd}")
        result = os.system(comparison_cmd)
        if result == 0:
            print(f"\n{'=' * 60}")
            print(f"SUCCESS! Comparison HTML generated at:")
            print(f"  {OUTPUT_DIR}/comparison.html")
            print(f"{'=' * 60}")
        else:
            print(f"[ERROR] Failed to generate comparison HTML (exit code: {result})")
    else:
        print(f"\n[ERROR] Could not generate comparison - missing output files")
        print(f"  RAG file: {rag_filename}")
        print(f"  Baseline file: {baseline_filename}")

if __name__ == "__main__":
    main()
