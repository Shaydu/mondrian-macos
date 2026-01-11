#!/usr/bin/env python3
"""
iOS End-to-End Test: RAG vs Baseline Comparison
Simulates the complete iOS workflow with both RAG-enabled and baseline analysis
Saves summary HTML, detailed HTML, and SSE/status updates

Usage:
    # Activate venv first
    source mondrian/venv/bin/activate

    # Run the test
    python3 test/test_ios_e2e_rag_comparison.py

    # Or run directly (will try to use venv if available)
    ./test/test_ios_e2e_rag_comparison.py
"""

import requests
import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime
import re

# Try to activate venv if not already active
if 'VIRTUAL_ENV' not in os.environ:
    venv_path = Path(__file__).parent.parent / 'mondrian' / 'venv'
    if venv_path.exists():
        # Add venv packages to path
        site_packages = venv_path / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
        if site_packages.exists():
            sys.path.insert(0, str(site_packages))

# Import sseclient (requires: pip install sseclient-py)
try:
    import sseclient
except ImportError:
    sseclient = None  # Will be handled in main()

# Configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
AI_ADVISOR_URL = "http://127.0.0.1:5100"
RAG_SERVICE_URL = "http://127.0.0.1:5400"

# Test image
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"

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
    """Check that all required services are running"""
    print_step(1, "Checking Services")

    services = [
        ("Job Service", f"{JOB_SERVICE_URL}/health", 5005),
        ("AI Advisor Service", f"{AI_ADVISOR_URL}/health", 5100),
        ("RAG Service", f"{RAG_SERVICE_URL}/health", 5400),
    ]

    all_up = True
    down_services = []

    for name, url, port in services:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print_success(f"{name} (port {port}) - UP")
            else:
                print_error(f"{name} (port {port}) - DOWN (status {resp.status_code})")
                all_up = False
                down_services.append(f"{name} (port {port})")
        except Exception as e:
            print_error(f"{name} (port {port}) - DOWN ({e})")
            all_up = False
            down_services.append(f"{name} (port {port})")

    if not all_up:
        print()
        print_error("Not all services are running. Please start them first.")
        print()
        print(f"{YELLOW}Services that are DOWN:{NC}")
        for service in down_services:
            print(f"  ✗ {service}")
        print()
        print(f"{BLUE}To start all services, run:{NC}")
        print(f"  ./mondrian.sh --restart")
        print()
        sys.exit(1)

    print()

def upload_image(enable_rag=False):
    """Upload image and start analysis (simulates iOS upload)"""
    mode = "RAG-ENABLED" if enable_rag else "BASELINE"
    print_step(2, f"Uploading Image ({mode})")

    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print_error(f"Test image not found: {TEST_IMAGE}")
        sys.exit(1)

    print_info(f"Image: {TEST_IMAGE}")
    print_info(f"Advisor: {ADVISOR}")
    print_info(f"RAG Enabled: {enable_rag}")

    with open(image_path, 'rb') as f:
        files = {'image': (image_path.name, f, 'image/jpeg')}
        data = {
            'advisor': ADVISOR,
            'enable_rag': 'true' if enable_rag else 'false'
        }

        try:
            resp = requests.post(f"{JOB_SERVICE_URL}/upload", files=files, data=data, timeout=30)

            if resp.status_code in [200, 201]:
                result = resp.json()
                job_id = result['job_id']
                stream_url = result['stream_url']
                print_success(f"Upload successful - Job ID: {job_id}")
                print_info(f"Stream URL: {stream_url}")
                return job_id, stream_url
            else:
                print_error(f"Upload failed: {resp.status_code}")
                print_error(f"Response: {resp.text[:500]}")
                sys.exit(1)

        except Exception as e:
            print_error(f"Upload exception: {e}")
            sys.exit(1)

def stream_sse_updates(stream_url, output_dir):
    """Stream SSE updates and save to file (simulates iOS SSE listener)"""
    print_step(3, "Streaming SSE Updates")

    sse_log_file = output_dir / "sse_stream.log"
    sse_events_file = output_dir / "sse_events.json"

    events = []

    try:
        response = requests.get(stream_url, stream=True, headers={'Accept': 'text/event-stream'}, timeout=600)
        client = sseclient.SSEClient(response)

        with open(sse_log_file, 'w') as log:
            log.write(f"SSE Stream Started: {datetime.now()}\n")
            log.write(f"Stream URL: {stream_url}\n")
            log.write("="*80 + "\n\n")

            for event in client.events():
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                # Parse event data
                try:
                    event_data = json.loads(event.data) if event.data else {}
                    event_type = event_data.get('type', 'unknown')

                    # Log to console
                    if event_type == 'connected':
                        print_success(f"[{timestamp}] SSE Connected - Job: {event_data.get('job_id', 'N/A')}")
                    elif event_type == 'status_update':
                        job_data = event_data.get('job_data', {})
                        status = job_data.get('status', 'unknown')
                        progress = job_data.get('progress_percentage', 0)
                        step = job_data.get('current_step', '')
                        thinking = job_data.get('llm_thinking', '')
                        print_info(f"[{timestamp}] Status: {status} ({progress}%) - {step}")
                        if thinking:
                            print_info(f"[{timestamp}]   Thinking: {thinking}")
                    elif event_type == 'thinking_update':
                        thinking = event_data.get('thinking', '')
                        print_info(f"[{timestamp}] Thinking: {thinking}")
                    elif event_type == 'analysis_complete':
                        print_success(f"[{timestamp}] Analysis Complete!")
                    elif event_type == 'done':
                        print_success(f"[{timestamp}] Stream Done")
                        # Log and break
                        log.write(f"[{timestamp}] {event_type}: {json.dumps(event_data, indent=2)}\n\n")
                        events.append({'timestamp': timestamp, 'type': event_type, 'data': event_data})
                        break
                    elif event_type == 'heartbeat':
                        pass  # Don't log heartbeats to console
                    else:
                        print_info(f"[{timestamp}] Event: {event_type}")

                    # Log to file
                    log.write(f"[{timestamp}] {event_type}: {json.dumps(event_data, indent=2)}\n\n")
                    log.flush()

                    # Store event
                    events.append({'timestamp': timestamp, 'type': event_type, 'data': event_data})

                except json.JSONDecodeError:
                    log.write(f"[{timestamp}] RAW: {event.data}\n\n")

        print_success(f"SSE stream log saved to: {sse_log_file}")

        # Save events as JSON
        with open(sse_events_file, 'w') as f:
            json.dump(events, f, indent=2)
        print_success(f"SSE events saved to: {sse_events_file}")

        return True

    except Exception as e:
        print_error(f"SSE streaming failed: {e}")
        return False

def monitor_status_polling(job_id, output_dir):
    """Monitor via status polling as fallback (simulates iOS polling)"""
    print_step(3, "Monitoring Progress (Polling)")

    status_log_file = output_dir / "status_polling.log"

    max_retries = 1800  # 30 minutes timeout
    retry = 0

    with open(status_log_file, 'w') as log:
        log.write(f"Status Polling Started: {datetime.now()}\n")
        log.write(f"Job ID: {job_id}\n")
        log.write("="*80 + "\n\n")

        while retry < max_retries:
            try:
                resp = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=5)

                if resp.status_code == 200:
                    status = resp.json()
                    state = status.get('status', 'unknown')
                    progress = status.get('progress_percentage', 0)
                    step = status.get('current_step', '')

                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_line = f"[{timestamp}] Status: {state} | Progress: {progress}% | Step: {step}\n"
                    log.write(log_line)
                    log.flush()

                    if state == 'completed' or state == 'done':
                        print_success(f"Analysis complete (100%)")
                        log.write(f"\n[{timestamp}] COMPLETED\n")
                        return True
                    elif state == 'failed':
                        error = status.get('error', 'Unknown error')
                        print_error(f"Analysis failed: {error}")
                        log.write(f"\n[{timestamp}] FAILED: {error}\n")
                        return False
                    else:
                        print_info(f"Progress: {progress}% - {state} - {step}")

                time.sleep(2)
                retry += 1

            except Exception as e:
                print_error(f"Status check failed: {e}")
                time.sleep(2)
                retry += 1

        print_error("Timeout waiting for analysis to complete")
        log.write(f"\nTIMEOUT after {max_retries} retries\n")
        return False

def get_analysis_html(job_id):
    """Get analysis HTML output (simulates iOS fetching results)"""
    print_step(4, "Fetching Analysis Results")

    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=10)

        if resp.status_code == 200:
            html = resp.text
            print_success(f"Retrieved HTML output ({len(html)} bytes)")
            return html
        else:
            print_error(f"Failed to get analysis: {resp.status_code}")
            return None

    except Exception as e:
        print_error(f"Exception getting analysis: {e}")
        return None

def get_summary_html(job_id):
    """Fetch summary HTML from the /summary endpoint (what iOS shows first)"""
    try:
        summary_url = f"{JOB_SERVICE_URL}/summary/{job_id}"
        print_info(f"Fetching summary from: {summary_url}")
        
        response = requests.get(summary_url, timeout=30)
        response.raise_for_status()
        
        summary_html = response.text
        
        if not summary_html or len(summary_html) < 100:
            print_error(f"Summary HTML too short ({len(summary_html)} chars)")
            return None
        
        # Verify it contains expected elements
        required_elements = ['Top 3 Recommendations', 'recommendation-item']
        missing = [elem for elem in required_elements if elem not in summary_html]
        if missing:
            print_warning(f"Summary missing expected elements: {missing}")
        
        print_success(f"Summary HTML retrieved: {len(summary_html):,} characters")
        return summary_html
        
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to fetch summary: {e}")
        return None
    except Exception as e:
        print_error(f"Error getting summary: {e}")
        return None

def save_outputs(full_html, job_id, mode, output_dir):
    """Save full HTML, summary HTML, and create metadata"""
    print_step(5, "Saving Output Files")

    # Save full detailed HTML
    full_html_file = output_dir / "analysis_detailed.html"
    with open(full_html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print_success(f"Detailed HTML saved to: {full_html_file}")

    # Fetch summary HTML from /summary endpoint (includes image, top 3, advisor details)
    summary_html = get_summary_html(job_id)
    if summary_html:
        summary_html_file = output_dir / "analysis_summary.html"
        with open(summary_html_file, 'w', encoding='utf-8') as f:
            f.write(summary_html)
        print_success(f"Summary HTML saved to: {summary_html_file}")
    else:
        print_error("Could not fetch summary HTML from endpoint")
        summary_html_file = None

    # Create metadata file
    metadata = {
        'job_id': job_id,
        'mode': mode,
        'advisor': ADVISOR,
        'test_image': TEST_IMAGE,
        'timestamp': datetime.now().isoformat(),
        'files': {
            'detailed_html': str(full_html_file.name),
            'summary_html': str(summary_html_file.name) if summary_html_file else None,
            'sse_stream_log': 'sse_stream.log',
            'sse_events_json': 'sse_events.json',
            'status_polling_log': 'status_polling.log'
        }
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print_success(f"Metadata saved to: {metadata_file}")

    return full_html_file, summary_html_file

def create_comparison_html(baseline_dir, rag_dir):
    """Create side-by-side comparison HTML"""
    print_step(6, "Creating Comparison View")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = Path("analysis_output") / f"ios_e2e_comparison_{timestamp}.html"

    # Convert Path objects to relative paths from analysis_output directory
    # baseline_dir and rag_dir are like "analysis_output/ios_e2e_baseline_..."
    # We need just "ios_e2e_baseline_..." for relative links
    baseline_rel = str(baseline_dir).replace("analysis_output/", "").replace("analysis_output\\", "")
    rag_rel = str(rag_dir).replace("analysis_output/", "").replace("analysis_output\\", "")

    comparison_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iOS E2E Test - RAG vs Baseline Comparison</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #000;
            color: #fff;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .panel {{
            background: #1c1c1e;
            padding: 20px;
            border-radius: 12px;
        }}
        .panel h2 {{
            color: #007AFF;
            margin-bottom: 15px;
        }}
        .file-link {{
            display: block;
            color: #30D158;
            text-decoration: none;
            margin: 8px 0;
        }}
        .file-link:hover {{
            text-decoration: underline;
        }}
        iframe {{
            width: 100%;
            height: 600px;
            border: 1px solid #333;
            border-radius: 8px;
            background: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>iOS End-to-End Test Results</h1>
        <p>RAG vs Baseline Comparison - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="comparison-grid">
        <div class="panel">
            <h2>Baseline (No RAG)</h2>
            <a href="{baseline_rel}/analysis_summary.html" class="file-link">📄 Summary HTML</a>
            <a href="{baseline_rel}/analysis_detailed.html" class="file-link">📄 Detailed HTML</a>
            <a href="{baseline_rel}/sse_stream.log" class="file-link">📝 SSE Stream Log</a>
            <a href="{baseline_rel}/sse_events.json" class="file-link">📝 SSE Events JSON</a>
            <a href="{baseline_rel}/status_polling.log" class="file-link">📝 Status Polling Log</a>
            <a href="{baseline_rel}/metadata.json" class="file-link">ℹ️ Metadata</a>
        </div>

        <div class="panel">
            <h2>RAG-Enabled</h2>
            <a href="{rag_rel}/analysis_summary.html" class="file-link">📄 Summary HTML</a>
            <a href="{rag_rel}/analysis_detailed.html" class="file-link">📄 Detailed HTML</a>
            <a href="{rag_rel}/sse_stream.log" class="file-link">📝 SSE Stream Log</a>
            <a href="{rag_rel}/sse_events.json" class="file-link">📝 SSE Events JSON</a>
            <a href="{rag_rel}/status_polling.log" class="file-link">📝 Status Polling Log</a>
            <a href="{rag_rel}/metadata.json" class="file-link">ℹ️ Metadata</a>
        </div>
    </div>

    <h2 style="margin-top: 40px;">Summary Preview</h2>
    <div class="comparison-grid">
        <iframe src="{baseline_rel}/analysis_summary.html"></iframe>
        <iframe src="{rag_rel}/analysis_summary.html"></iframe>
    </div>
</body>
</html>"""

    with open(comparison_file, 'w') as f:
        f.write(comparison_html)

    print_success(f"Comparison HTML saved to: {comparison_file}")
    return comparison_file

def run_e2e_test(enable_rag=False, use_sse=True):
    """Run complete end-to-end test"""
    mode = "rag-enabled" if enable_rag else "baseline"
    print_header(f"iOS End-to-End Test: {mode.upper()}")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("analysis_output") / f"ios_e2e_{mode}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print_info(f"Output directory: {output_dir}")

    # Upload and analyze
    job_id, stream_url = upload_image(enable_rag=enable_rag)

    # Monitor progress via SSE or polling
    if use_sse:
        success = stream_sse_updates(stream_url, output_dir)
        if not success:
            print_error("SSE streaming failed, falling back to polling")
            success = monitor_status_polling(job_id, output_dir)
    else:
        success = monitor_status_polling(job_id, output_dir)

    if not success:
        print_error("Analysis failed")
        return None, None

    # Get results
    html = get_analysis_html(job_id)
    if not html:
        print_error("Failed to get results")
        return None, None

    # Save outputs
    detailed_file, summary_file = save_outputs(html, job_id, mode, output_dir)

    print_success(f"{mode.upper()} test complete!")
    print()

    return output_dir, html

def main():
    """Main test flow"""
    print_header("iOS End-to-End Test: RAG vs Baseline Comparison")
    print(f"Test Image: {TEST_IMAGE}")
    print(f"Advisor: {ADVISOR}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check SSE client library
    if sseclient is None:
        print_error("sseclient-py not installed.")
        print_info("Install with: source mondrian/venv/bin/activate && pip install sseclient-py")
        print_info("Will use status polling instead of SSE streaming")
        use_sse = False
    else:
        print_success("SSE client available - will stream real-time updates")
        use_sse = True

    # Check services
    check_services()

    # Run baseline test
    print_header("TEST 1: BASELINE (No RAG)")
    baseline_dir, baseline_html = run_e2e_test(enable_rag=False, use_sse=use_sse)

    if not baseline_html:
        print_error("Baseline test failed")
        sys.exit(1)

    # Wait between tests
    print_info("Waiting 5 seconds before RAG test...")
    time.sleep(5)

    # Run RAG test
    print_header("TEST 2: RAG-ENABLED")
    rag_dir, rag_html = run_e2e_test(enable_rag=True, use_sse=use_sse)

    if not rag_html:
        print_error("RAG test failed")
        sys.exit(1)

    # Create comparison view
    comparison_file = create_comparison_html(baseline_dir, rag_dir)

    # Final summary
    print_header("TEST COMPLETE")
    print_success("Both baseline and RAG-enabled tests completed successfully")
    print()
    print(f"{BOLD}Output Files:{NC}")
    print(f"  Baseline:    {baseline_dir}/")
    print(f"  RAG-Enabled: {rag_dir}/")
    print(f"  Comparison:  {comparison_file}")
    print()
    print(f"{BOLD}View in browser:{NC}")
    print(f"  file://{comparison_file.absolute()}")
    print()

if __name__ == "__main__":
    main()
