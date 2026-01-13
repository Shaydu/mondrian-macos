#!/usr/bin/env python3
"""
iOS End-to-End Test: RAG vs Baseline Comparison
Simulates the complete iOS workflow with both RAG-enabled and baseline analysis
Saves summary HTML, detailed HTML, advisor bio HTML, and SSE/status updates

Usage:
    # Activate venv first
    source mondrian/venv/bin/activate

    # Run both baseline and RAG tests (default)
    python3 test/test_ios_e2e_rag_comparison.py
    python3 test/test_ios_e2e_rag_comparison.py --both

    # Run only baseline test
    python3 test/test_ios_e2e_rag_comparison.py --baseline

    # Run only RAG test
    python3 test/test_ios_e2e_rag_comparison.py --rag

    # Or run directly (will try to use venv if available)
    ./test/test_ios_e2e_rag_comparison.py --rag
"""

import requests
import json
import time
import sys
import os
import argparse
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

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠{NC} {text}")

def check_services(require_rag_service=False):
    """Check that all required services are running
    
    Args:
        require_rag_service: DEPRECATED - Always False. RAG Service (port 5400) is not used.
                            Technique-based RAG is integrated into AI Advisor Service.
    """
    print_step(1, "Checking Services")

    # Always required services
    required_services = [
        ("Job Service", f"{JOB_SERVICE_URL}/health", 5005),
        ("AI Advisor Service", f"{AI_ADVISOR_URL}/health", 5100),
    ]
    
    # RAG Service - required if testing RAG, optional otherwise
    if require_rag_service:
        required_services.append(("RAG Service", f"{RAG_SERVICE_URL}/health", 5400))
        optional_services = []
    else:
        optional_services = [
            ("RAG Service (caption-based)", f"{RAG_SERVICE_URL}/health", 5400),
        ]

    all_required_up = True
    down_services = []

    # Check required services
    for name, url, port in required_services:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print_success(f"{name} (port {port}) - UP")
            else:
                print_error(f"{name} (port {port}) - DOWN (status {resp.status_code})")
                all_required_up = False
                down_services.append(f"{name} (port {port})")
        except Exception as e:
            print_error(f"{name} (port {port}) - DOWN ({e})")
            all_required_up = False
            down_services.append(f"{name} (port {port})")

    # Check optional services (warn but don't fail)
    for name, url, port in optional_services:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print_success(f"{name} (port {port}) - UP")
            else:
                print_info(f"{name} (port {port}) - DOWN (optional, not required for dimensional RAG)")
        except Exception as e:
            print_info(f"{name} (port {port}) - DOWN (optional, not required for dimensional RAG)")

    if not all_required_up:
        print()
        print_error("Not all required services are running. Please start them first.")
        print()
        print(f"{YELLOW}Required services that are DOWN:{NC}")
        for service in down_services:
            print(f"  ✗ {service}")
        print()
        print(f"{BLUE}To start all services, run:{NC}")
        print(f"  ./mondrian.sh --restart")
        print()
        if require_rag_service:
            print(f"{YELLOW}Note:{NC} RAG Service (port 5400) is deprecated - not used in current implementation.")
        else:
            print(f"{YELLOW}Note:{NC} RAG Service (port 5400) is deprecated - not used.")
            print(f"       Technique-based RAG (currently used) is integrated into AI Advisor Service.")
        print()
        sys.exit(1)

    print()
    print_success("All required services are running")
    if len(optional_services) > 0:
        print_info("Optional services (caption-based RAG) are not required for dimensional RAG")
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

def get_advisor_bio_html(advisor_id):
    """Fetch advisor bio HTML from the /advisor endpoint"""
    try:
        advisor_url = f"{JOB_SERVICE_URL}/advisor/{advisor_id}"
        print_info(f"Fetching advisor bio from: {advisor_url}")
        
        response = requests.get(advisor_url, timeout=10)
        response.raise_for_status()
        
        advisor_html = response.text
        
        if not advisor_html or len(advisor_html) < 100:
            print_warning(f"Advisor bio HTML too short ({len(advisor_html)} chars)")
            return None
        
        print_success(f"Advisor bio HTML retrieved: {len(advisor_html):,} characters")
        return advisor_html
        
    except requests.exceptions.RequestException as e:
        print_error(f"Failed to fetch advisor bio: {e}")
        return None
    except Exception as e:
        print_error(f"Error getting advisor bio: {e}")
        return None

def save_outputs(full_html, job_id, mode, output_dir, advisor_id=None):
    """Save full HTML, summary HTML, advisor bio HTML, and create metadata"""
    print_step(5, "Saving Output Files")

    # Save full detailed HTML (analysis details)
    full_html_file = output_dir / "analysis_detailed.html"
    with open(full_html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print_success(f"Analysis Details HTML saved to: {full_html_file}")

    # Fetch summary HTML from /summary endpoint (includes image, top 3, advisor details)
    summary_html = get_summary_html(job_id)
    summary_html_file = None
    if summary_html:
        summary_html_file = output_dir / "analysis_summary.html"
        with open(summary_html_file, 'w', encoding='utf-8') as f:
            f.write(summary_html)
        print_success(f"Analysis Summary HTML saved to: {summary_html_file}")
    else:
        print_error("Could not fetch summary HTML from endpoint")

    # Fetch advisor bio HTML
    advisor_bio_html_file = None
    if advisor_id:
        advisor_bio_html = get_advisor_bio_html(advisor_id)
        if advisor_bio_html:
            advisor_bio_html_file = output_dir / "advisor_bio.html"
            with open(advisor_bio_html_file, 'w', encoding='utf-8') as f:
                f.write(advisor_bio_html)
            print_success(f"Advisor Bio HTML saved to: {advisor_bio_html_file}")
        else:
            print_warning("Could not fetch advisor bio HTML from endpoint")
    else:
        print_warning("No advisor ID provided, skipping advisor bio fetch")

    # Create metadata file
    metadata = {
        'job_id': job_id,
        'mode': mode,
        'advisor': advisor_id or ADVISOR,
        'test_image': TEST_IMAGE,
        'timestamp': datetime.now().isoformat(),
        'rag_enabled': mode == 'rag-enabled',
        'files': {
            'advisor_bio_html': str(advisor_bio_html_file.name) if advisor_bio_html_file else None,
            'analysis_summary_html': str(summary_html_file.name) if summary_html_file else None,
            'analysis_detailed_html': str(full_html_file.name),
            'sse_stream_log': 'sse_stream.log',
            'sse_events_json': 'sse_events.json',
            'status_polling_log': 'status_polling.log'
        }
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print_success(f"Metadata saved to: {metadata_file}")

    return full_html_file, summary_html_file, advisor_bio_html_file

def create_comparison_html(baseline_dir, rag_dir):
    """Create side-by-side comparison HTML showing all three outputs"""
    print_step(6, "Creating Comparison View")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = Path("analysis_output") / f"ios_e2e_comparison_{timestamp}.html"

    # Convert Path objects to relative paths from analysis_output directory
    baseline_rel = str(baseline_dir).replace("analysis_output/", "").replace("analysis_output\\", "")
    rag_rel = str(rag_dir).replace("analysis_output/", "").replace("analysis_output\\", "")

    # Check which files exist
    baseline_bio = f"{baseline_rel}/advisor_bio.html" if (baseline_dir / "advisor_bio.html").exists() else None
    baseline_summary = f"{baseline_rel}/analysis_summary.html" if (baseline_dir / "analysis_summary.html").exists() else None
    baseline_detailed = f"{baseline_rel}/analysis_detailed.html" if (baseline_dir / "analysis_detailed.html").exists() else None
    
    rag_bio = f"{rag_rel}/advisor_bio.html" if (rag_dir / "advisor_bio.html").exists() else None
    rag_summary = f"{rag_rel}/analysis_summary.html" if (rag_dir / "analysis_summary.html").exists() else None
    rag_detailed = f"{rag_rel}/analysis_detailed.html" if (rag_dir / "analysis_detailed.html").exists() else None

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
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #007AFF;
            margin-bottom: 20px;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .panel {{
            background: #1c1c1e;
            padding: 20px;
            border-radius: 12px;
        }}
        .panel h3 {{
            color: #30D158;
            margin-bottom: 15px;
        }}
        .file-link {{
            display: block;
            color: #30D158;
            text-decoration: none;
            margin: 8px 0;
            padding: 8px;
            background: #2c2c2e;
            border-radius: 6px;
        }}
        .file-link:hover {{
            background: #3c3c3e;
            text-decoration: underline;
        }}
        iframe {{
            width: 100%;
            height: 600px;
            border: 1px solid #333;
            border-radius: 8px;
            background: white;
        }}
        .missing {{
            color: #ff9500;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>iOS End-to-End Test Results</h1>
        <p>RAG vs Baseline Comparison - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style="color: #999; font-size: 14px;">This shows the HTML output that would be sent to the iOS app</p>
    </div>

    <!-- Advisor Bio Section -->
    <div class="section">
        <h2>1. Advisor Bio HTML</h2>
        <div class="comparison-grid">
            <div class="panel">
                <h3>Baseline (No RAG)</h3>
                {"<iframe src=\"" + baseline_bio + "\"></iframe>" if baseline_bio else "<p class=\"missing\">Advisor bio HTML not available</p>"}
                {"<a href=\"" + baseline_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open Advisor Bio HTML</a>" if baseline_bio else ""}
            </div>
            <div class="panel">
                <h3>RAG-Enabled</h3>
                {"<iframe src=\"" + rag_bio + "\"></iframe>" if rag_bio else "<p class=\"missing\">Advisor bio HTML not available</p>"}
                {"<a href=\"" + rag_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open Advisor Bio HTML</a>" if rag_bio else ""}
            </div>
        </div>
    </div>

    <!-- Analysis Summary Section -->
    <div class="section">
        <h2>2. Analysis Summary HTML (Top 3 Recommendations)</h2>
        <div class="comparison-grid">
            <div class="panel">
                <h3>Baseline (No RAG)</h3>
                {"<iframe src=\"" + baseline_summary + "\"></iframe>" if baseline_summary else "<p class=\"missing\">Summary HTML not available</p>"}
                {"<a href=\"" + baseline_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open Summary HTML</a>" if baseline_summary else ""}
            </div>
            <div class="panel">
                <h3>RAG-Enabled</h3>
                {"<iframe src=\"" + rag_summary + "\"></iframe>" if rag_summary else "<p class=\"missing\">Summary HTML not available</p>"}
                {"<a href=\"" + rag_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open Summary HTML</a>" if rag_summary else ""}
            </div>
        </div>
    </div>

    <!-- Analysis Details Section -->
    <div class="section">
        <h2>3. Analysis Details HTML (Full Analysis)</h2>
        <div class="comparison-grid">
            <div class="panel">
                <h3>Baseline (No RAG)</h3>
                {"<iframe src=\"" + baseline_detailed + "\"></iframe>" if baseline_detailed else "<p class=\"missing\">Detailed HTML not available</p>"}
                {"<a href=\"" + baseline_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open Detailed HTML</a>" if baseline_detailed else ""}
            </div>
            <div class="panel">
                <h3>RAG-Enabled</h3>
                {"<iframe src=\"" + rag_detailed + "\"></iframe>" if rag_detailed else "<p class=\"missing\">Detailed HTML not available</p>"}
                {"<a href=\"" + rag_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open Detailed HTML</a>" if rag_detailed else ""}
            </div>
        </div>
    </div>

    <!-- File Links Section -->
    <div class="section">
        <h2>Additional Files</h2>
        <div class="comparison-grid">
            <div class="panel">
                <h3>Baseline (No RAG)</h3>
                <a href="{baseline_rel}/sse_stream.log" class="file-link" target="_blank">📝 SSE Stream Log</a>
                <a href="{baseline_rel}/sse_events.json" class="file-link" target="_blank">📝 SSE Events JSON</a>
                <a href="{baseline_rel}/status_polling.log" class="file-link" target="_blank">📝 Status Polling Log</a>
                <a href="{baseline_rel}/metadata.json" class="file-link" target="_blank">ℹ️ Metadata</a>
            </div>
            <div class="panel">
                <h3>RAG-Enabled</h3>
                <a href="{rag_rel}/sse_stream.log" class="file-link" target="_blank">📝 SSE Stream Log</a>
                <a href="{rag_rel}/sse_events.json" class="file-link" target="_blank">📝 SSE Events JSON</a>
                <a href="{rag_rel}/status_polling.log" class="file-link" target="_blank">📝 Status Polling Log</a>
                <a href="{rag_rel}/metadata.json" class="file-link" target="_blank">ℹ️ Metadata</a>
            </div>
        </div>
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

    # Save outputs (including advisor bio)
    detailed_file, summary_file, advisor_bio_file = save_outputs(html, job_id, mode, output_dir, advisor_id=ADVISOR)

    print_success(f"{mode.upper()} test complete!")
    print()

    return output_dir, html

def main():
    """Main test flow"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="iOS End-to-End Test: RAG vs Baseline Comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run both baseline and RAG tests (default)
  %(prog)s
  %(prog)s --both

  # Run only baseline test
  %(prog)s --baseline

  # Run only RAG test
  %(prog)s --rag
        """
    )
    parser.add_argument(
        '--baseline', 
        action='store_true',
        help='Run only baseline test (no RAG)'
    )
    parser.add_argument(
        '--rag', 
        action='store_true',
        help='Run only RAG-enabled test'
    )
    parser.add_argument(
        '--both', 
        action='store_true',
        help='Run both baseline and RAG tests (default)'
    )
    args = parser.parse_args()

    # Determine which tests to run
    # Default: run both if no arguments provided
    if args.baseline and args.rag:
        # Both flags set - run both
        run_baseline = True
        run_rag = True
    elif args.baseline:
        # Only baseline flag
        run_baseline = True
        run_rag = False
    elif args.rag:
        # Only RAG flag
        run_baseline = False
        run_rag = True
    else:
        # No flags or --both flag: run both (default behavior)
        run_baseline = True
        run_rag = True

    print_header("iOS End-to-End Test: RAG vs Baseline Comparison")
    print(f"Test Image: {TEST_IMAGE}")
    print(f"Advisor: {ADVISOR}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tests to run: {'Baseline' if run_baseline else ''} {'RAG' if run_rag else ''}".strip())

    # Check SSE client library
    if sseclient is None:
        print_error("sseclient-py not installed.")
        print_info("Install with: source mondrian/venv/bin/activate && pip install sseclient-py")
        print_info("Will use status polling instead of SSE streaming")
        use_sse = False
    else:
        print_success("SSE client available - will stream real-time updates")
        use_sse = True

    # Check services (RAG service not required - technique-based RAG is integrated)
    check_services(require_rag_service=False)

    baseline_dir = None
    rag_dir = None

    # Run baseline test
    if run_baseline:
        print_header("TEST 1: BASELINE (No RAG)")
        baseline_dir, baseline_html = run_e2e_test(enable_rag=False, use_sse=use_sse)

        if not baseline_html:
            print_error("Baseline test failed")
            sys.exit(1)

        # Wait between tests if running both
        if run_rag:
            print_info("Waiting 5 seconds before RAG test...")
            time.sleep(5)

    # Run RAG test
    if run_rag:
        if run_baseline:
            print()
            print_header("Checking Services for RAG Test")
        print_info("Note: Technique-based RAG is integrated into AI Advisor Service - no separate RAG service needed")
        if run_baseline:
            check_services(require_rag_service=False)

        print_header("TEST 2: RAG-ENABLED" if run_baseline else "TEST: RAG-ENABLED")
        rag_dir, rag_html = run_e2e_test(enable_rag=True, use_sse=use_sse)

        if not rag_html:
            print_error("RAG test failed")
            sys.exit(1)

    # Create comparison view if both tests ran
    comparison_file = None
    if baseline_dir and rag_dir:
        comparison_file = create_comparison_html(baseline_dir, rag_dir)

    # Final summary
    print_header("TEST COMPLETE")
    if baseline_dir and rag_dir:
        print_success("Both baseline and RAG-enabled tests completed successfully")
    elif baseline_dir:
        print_success("Baseline test completed successfully")
    elif rag_dir:
        print_success("RAG-enabled test completed successfully")
    print()
    print(f"{BOLD}Output Files:{NC}")
    if baseline_dir:
        print(f"  Baseline:    {baseline_dir}/")
    if rag_dir:
        print(f"  RAG-Enabled: {rag_dir}/")
    if comparison_file:
        print(f"  Comparison:  {comparison_file}")
    print()
    if comparison_file:
        print(f"{BOLD}View in browser:{NC}")
        print(f"  file://{comparison_file.absolute()}")
        print()

if __name__ == "__main__":
    main()
