#!/usr/bin/env python3
"""
iOS End-to-End Test: Four-Mode Comparison (Baseline vs RAG vs LoRA vs RAG+LoRA)
Simulates the complete iOS workflow with all four analysis modes
Saves detailed outputs, timing metadata, and creates a side-by-side comparison

Usage:
    # Activate venv first
    source mondrian/venv/bin/activate

    # Run all four modes (default)
    python3 test/test_ios_e2e_four_modes.py
    python3 test/test_ios_e2e_four_modes.py --all

    # Run specific modes
    python3 test/test_ios_e2e_four_modes.py --mode=base
    python3 test/test_ios_e2e_four_modes.py --mode=rag
    python3 test/test_ios_e2e_four_modes.py --mode=lora --lora-path=./adapters/ansel
    python3 test/test_ios_e2e_four_modes.py --mode=rag_lora --lora-path=./adapters/ansel
    
    # Run specific tests (legacy)
    python3 test/test_ios_e2e_four_modes.py --baseline
    python3 test/test_ios_e2e_four_modes.py --rag
    python3 test/test_ios_e2e_four_modes.py --lora
    python3 test/test_ios_e2e_four_modes.py --rag-lora
    python3 test/test_ios_e2e_four_modes.py --baseline --rag --lora --rag-lora

Browser Viewing:
    After running tests, view comparison in browser:
    
    1. Start HTTP server:
       cd analysis_output && python3 -m http.server 8080
    
    2. Open in browser:
       http://localhost:8080/ios_e2e_four_mode_TIMESTAMP.html
       http://localhost:8080/mode_diff_TIMESTAMP.html

Output Files (per mode directory):
    - analysis_summary.html     Top 3 recommendations
    - analysis_detailed.html    Full analysis
    - advisor_bio.html          Advisor profile
    - sse_stream.log            SSE event stream
    - sse_events.json           Parsed SSE events
    - api_requests.log          API request/response log
    - metadata.json             Job info + service health snapshot
"""

import requests
import json
import time
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Try to activate venv if not already active
if 'VIRTUAL_ENV' not in os.environ:
    venv_path = Path(__file__).parent.parent / 'mondrian' / 'venv'
    if venv_path.exists():
        site_packages = venv_path / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
        if site_packages.exists():
            sys.path.insert(0, str(site_packages))

# Import sseclient
try:
    import sseclient
except ImportError:
    sseclient = None

# Configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
AI_ADVISOR_URL = "http://127.0.0.1:5100"

# Test image
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
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

def log_api_request(output_dir, endpoint, method, data=None, files=None, response=None):
    """Log API request and response details"""
    api_log_file = output_dir / "api_requests.log"
    
    with open(api_log_file, 'a') as f:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        f.write(f"\n{'='*60}\n")
        f.write(f"[{timestamp}] {method} {endpoint}\n")
        
        if data:
            f.write(f"Request Data: {json.dumps(data, indent=2)}\n")
        if files:
            f.write(f"Files: {list(files.keys())}\n")
        
        if response:
            f.write(f"Status: {response.status_code}\n")
            f.write(f"Headers: {dict(response.headers)}\n")
            try:
                f.write(f"Response: {json.dumps(response.json(), indent=2)}\n")
            except:
                f.write(f"Response: {response.text[:1000]}\n")

def check_services(expected_mode=None, lora_path=None, auto_restart=False):
    """Check that all required services are running"""
    print_step(1, "Checking Services")

    required_services = [
        ("Job Service", f"{JOB_SERVICE_URL}/health", 5005),
        ("AI Advisor Service", f"{AI_ADVISOR_URL}/health", 5100),
    ]

    all_required_up = True
    down_services = []

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

    if not all_required_up:
        print()
        print_error("Not all required services are running. Please start them first.")
        print()
        print(f"{BLUE}To start services with your desired mode, run:{NC}")
        print(f"  ./mondrian.sh --restart --mode=<mode>")
        print()
        sys.exit(1)

    print()
    print_success("All required services are running")
    print()

def verify_service_mode(expected_mode):
    """Verify the AI Advisor service is running in the expected mode"""
    print_step("1b", f"Verifying Service Mode: {expected_mode}")
    
    try:
        resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
        if resp.status_code == 200:
            health = resp.json()
            actual_mode = health.get('model_mode', 'unknown')
            lora_enabled = health.get('lora_enabled', False)
            lora_path = health.get('lora_path', None)
            
            print_info(f"Server model_mode: {actual_mode}")
            print_info(f"LoRA enabled: {lora_enabled}")
            if lora_path:
                print_info(f"LoRA path: {lora_path}")
            
            # Verify mode matches expectation
            mode_ok = False
            if expected_mode == "baseline":
                mode_ok = actual_mode == "base" and not lora_enabled
            elif expected_mode == "rag":
                mode_ok = actual_mode == "base"  # RAG uses base model
            elif expected_mode == "lora":
                mode_ok = lora_enabled
            elif expected_mode == "rag_lora":
                mode_ok = lora_enabled
            
            if mode_ok:
                print_success(f"Mode verified: {expected_mode}")
                return True, health
            else:
                print_warning(f"Mode mismatch! Expected {expected_mode}, got mode={actual_mode}, lora={lora_enabled}")
                return False, health
    except Exception as e:
        print_error(f"Could not verify mode: {e}")
        return False, None

def check_lora_adapter():
    """Check if LoRA adapter is available"""
    adapter_path = Path(f"adapters/{ADVISOR}")
    adapter_file = adapter_path / "adapters.safetensors"

    if adapter_file.exists():
        print_success(f"LoRA adapter found: {adapter_path}")
        return True
    else:
        print_warning(f"LoRA adapter not found at: {adapter_path}")
        return False

def check_dimensional_profiles():
    """Check if dimensional profiles exist for RAG"""
    try:
        import sqlite3
        from mondrian.config import DATABASE_PATH
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM dimensional_profiles
            WHERE advisor_id = ?
            AND image_path NOT LIKE '%temp%'
            AND image_path NOT LIKE '%analyze_image%'
        """, (ADVISOR,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            print_success(f"Found {count} dimensional profiles for {ADVISOR}")
            return True
        else:
            print_warning(f"No dimensional profiles found for {ADVISOR}")
            return False
    except Exception as e:
        print_warning(f"Could not check dimensional profiles: {e}")
        return False

def upload_image(mode="baseline", output_dir=None):
    """Upload image and start analysis (simulates iOS upload)"""
    mode_display = mode.upper()
    print_step(2, f"Uploading Image ({mode_display} mode)")

    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print_error(f"Test image not found: {TEST_IMAGE}")
        sys.exit(1)

    print_info(f"Image: {TEST_IMAGE}")
    print_info(f"Advisor: {ADVISOR}")
    print_info(f"Mode: {mode}")

    with open(image_path, 'rb') as f:
        files = {'image': (image_path.name, f, 'image/jpeg')}
        data = {
            'advisor': ADVISOR,
            'mode': mode
        }

        try:
            endpoint = f"{JOB_SERVICE_URL}/upload"
            resp = requests.post(endpoint, files=files, data=data, timeout=30)

            # Log API request/response if output_dir provided
            if output_dir:
                log_api_request(output_dir, endpoint, "POST", data=data, files=files, response=resp)

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
    """Stream SSE updates and save to file"""
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

                try:
                    event_data = json.loads(event.data) if event.data else {}
                    event_type = event_data.get('type', 'unknown')

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
                            print_info(f"[{timestamp}]   Thinking: {thinking[:100]}...")
                    elif event_type == 'thinking_update':
                        thinking = event_data.get('thinking', '')
                        print_info(f"[{timestamp}] Thinking: {thinking[:100]}...")
                    elif event_type == 'analysis_complete':
                        print_success(f"[{timestamp}] Analysis Complete!")
                    elif event_type == 'done':
                        print_success(f"[{timestamp}] Stream Done")
                        log.write(f"[{timestamp}] {event_type}: {json.dumps(event_data, indent=2)}\n\n")
                        events.append({'timestamp': timestamp, 'type': event_type, 'data': event_data})
                        break
                    elif event_type == 'heartbeat':
                        pass  # Don't log heartbeats to console

                    log.write(f"[{timestamp}] {event_type}: {json.dumps(event_data, indent=2)}\n\n")
                    log.flush()
                    events.append({'timestamp': timestamp, 'type': event_type, 'data': event_data})

                except json.JSONDecodeError:
                    log.write(f"[{timestamp}] RAW: {event.data}\n\n")

        print_success(f"SSE stream log saved to: {sse_log_file}")

        with open(sse_events_file, 'w') as f:
            json.dump(events, f, indent=2)
        print_success(f"SSE events saved to: {sse_events_file}")

        return True

    except Exception as e:
        print_error(f"SSE streaming failed: {e}")
        return False

def monitor_status_polling(job_id, output_dir):
    """Monitor via status polling as fallback"""
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
    """Get analysis HTML output"""
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
    """Fetch summary HTML"""
    try:
        summary_url = f"{JOB_SERVICE_URL}/summary/{job_id}"
        print_info(f"Fetching summary from: {summary_url}")

        response = requests.get(summary_url, timeout=30)
        response.raise_for_status()

        summary_html = response.text
        print_success(f"Summary HTML retrieved: {len(summary_html):,} characters")
        return summary_html

    except Exception as e:
        print_error(f"Failed to fetch summary: {e}")
        return None

def get_advisor_bio_html(advisor_id):
    """Fetch advisor bio HTML"""
    try:
        advisor_url = f"{JOB_SERVICE_URL}/advisor/{advisor_id}"
        print_info(f"Fetching advisor bio from: {advisor_url}")

        response = requests.get(advisor_url, timeout=10)
        response.raise_for_status()

        advisor_html = response.text
        print_success(f"Advisor bio HTML retrieved: {len(advisor_html):,} characters")
        return advisor_html

    except Exception as e:
        print_error(f"Failed to fetch advisor bio: {e}")
        return None

def save_outputs(full_html, job_id, mode, output_dir, advisor_id=None, health_snapshot=None):
    """Save HTML outputs and metadata"""
    print_step(5, "Saving Output Files")

    # Save full detailed HTML
    full_html_file = output_dir / "analysis_detailed.html"
    with open(full_html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print_success(f"Analysis Details HTML saved to: {full_html_file}")

    # Fetch summary HTML
    summary_html = get_summary_html(job_id)
    summary_html_file = None
    if summary_html:
        summary_html_file = output_dir / "analysis_summary.html"
        with open(summary_html_file, 'w', encoding='utf-8') as f:
            f.write(summary_html)
        print_success(f"Analysis Summary HTML saved to: {summary_html_file}")

    # Fetch advisor bio HTML
    advisor_bio_html_file = None
    if advisor_id:
        advisor_bio_html = get_advisor_bio_html(advisor_id)
        if advisor_bio_html:
            advisor_bio_html_file = output_dir / "advisor_bio.html"
            with open(advisor_bio_html_file, 'w', encoding='utf-8') as f:
                f.write(advisor_bio_html)
            print_success(f"Advisor Bio HTML saved to: {advisor_bio_html_file}")

    # Create metadata
    metadata = {
        'job_id': job_id,
        'mode': mode,
        'advisor': advisor_id or ADVISOR,
        'test_image': TEST_IMAGE,
        'timestamp': datetime.now().isoformat(),
        'files': {
            'advisor_bio_html': str(advisor_bio_html_file.name) if advisor_bio_html_file else None,
            'analysis_summary_html': str(summary_html_file.name) if summary_html_file else None,
            'analysis_detailed_html': str(full_html_file.name),
            'sse_stream_log': 'sse_stream.log',
            'sse_events_json': 'sse_events.json',
            'api_requests_log': 'api_requests.log',
            'status_polling_log': 'status_polling.log'
        }
    }
    
    # Add health snapshot if provided
    if health_snapshot:
        metadata['service_health'] = health_snapshot

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print_success(f"Metadata saved to: {metadata_file}")

    return full_html_file, summary_html_file, advisor_bio_html_file

def create_four_mode_comparison_html(baseline_dir, rag_dir, lora_dir, rag_lora_dir):
    """Create four-way comparison HTML"""
    print_step(6, "Creating Four-Mode Comparison View")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = Path("analysis_output") / f"ios_e2e_four_mode_{timestamp}.html"

    # Helper to get relative paths
    def get_rel_path(dir_path):
        if dir_path:
            return str(dir_path).replace("analysis_output/", "").replace("analysis_output\\", "")
        return None

    baseline_rel = get_rel_path(baseline_dir)
    rag_rel = get_rel_path(rag_dir)
    lora_rel = get_rel_path(lora_dir)
    rag_lora_rel = get_rel_path(rag_lora_dir)

    # Check which files exist
    def check_files(dir_path, rel_path):
        if not dir_path:
            return None, None, None
        bio = f"{rel_path}/advisor_bio.html" if (dir_path / "advisor_bio.html").exists() else None
        summary = f"{rel_path}/analysis_summary.html" if (dir_path / "analysis_summary.html").exists() else None
        detailed = f"{rel_path}/analysis_detailed.html" if (dir_path / "analysis_detailed.html").exists() else None
        return bio, summary, detailed

    baseline_bio, baseline_summary, baseline_detailed = check_files(baseline_dir, baseline_rel)
    rag_bio, rag_summary, rag_detailed = check_files(rag_dir, rag_rel)
    lora_bio, lora_summary, lora_detailed = check_files(lora_dir, lora_rel)
    rag_lora_bio, rag_lora_summary, rag_lora_detailed = check_files(rag_lora_dir, rag_lora_rel)

    # Count how many modes we're comparing
    num_modes = sum([baseline_dir is not None, rag_dir is not None, lora_dir is not None, rag_lora_dir is not None])
    grid_cols = num_modes

    comparison_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iOS E2E Test - Four Mode Comparison</title>
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
            grid-template-columns: repeat({grid_cols}, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .panel {{
            background: #1c1c1e;
            padding: 20px;
            border-radius: 12px;
        }}
        .panel h3 {{
            margin-bottom: 15px;
        }}
        .panel.baseline h3 {{ color: #30D158; }}
        .panel.rag h3 {{ color: #FFD60A; }}
        .panel.lora h3 {{ color: #BF5AF2; }}
        .panel.rag_lora h3 {{ color: #FF453A; }}
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
        <h1>iOS End-to-End Test - Four Mode Comparison</h1>
        <p>Baseline vs RAG vs LoRA vs RAG+LoRA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style="color: #999; font-size: 14px;">Comparing HTML outputs across all four analysis modes</p>
    </div>

    <!-- Advisor Bio Section -->
    <div class="section">
        <h2>1. Advisor Bio HTML</h2>
        <div class="comparison-grid">"""

    # Add baseline panel
    if baseline_dir:
        comparison_html += f"""
            <div class="panel baseline">
                <h3>Baseline</h3>
                {"<iframe src=\"" + baseline_bio + "\"></iframe>" if baseline_bio else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + baseline_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if baseline_bio else ""}
            </div>"""

    # Add RAG panel
    if rag_dir:
        comparison_html += f"""
            <div class="panel rag">
                <h3>RAG-Enhanced</h3>
                {"<iframe src=\"" + rag_bio + "\"></iframe>" if rag_bio else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + rag_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if rag_bio else ""}
            </div>"""

    # Add LoRA panel
    if lora_dir:
        comparison_html += f"""
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                {"<iframe src=\"" + lora_bio + "\"></iframe>" if lora_bio else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + lora_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if lora_bio else ""}
            </div>"""

    # Add RAG+LoRA panel
    if rag_lora_dir:
        comparison_html += f"""
            <div class="panel rag_lora">
                <h3>RAG+LoRA (Hybrid)</h3>
                {"<iframe src=\"" + rag_lora_bio + "\"></iframe>" if rag_lora_bio else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + rag_lora_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if rag_lora_bio else ""}
            </div>"""

    comparison_html += """
        </div>
    </div>

    <!-- Analysis Summary Section -->
    <div class="section">
        <h2>2. Analysis Summary HTML (Top 3 Recommendations)</h2>
        <div class="comparison-grid">"""

    # Add baseline panel
    if baseline_dir:
        comparison_html += f"""
            <div class="panel baseline">
                <h3>Baseline</h3>
                {"<iframe src=\"" + baseline_summary + "\"></iframe>" if baseline_summary else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + baseline_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if baseline_summary else ""}
            </div>"""

    # Add RAG panel
    if rag_dir:
        comparison_html += f"""
            <div class="panel rag">
                <h3>RAG-Enhanced</h3>
                {"<iframe src=\"" + rag_summary + "\"></iframe>" if rag_summary else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + rag_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if rag_summary else ""}
            </div>"""

    # Add LoRA panel
    if lora_dir:
        comparison_html += f"""
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                {"<iframe src=\"" + lora_summary + "\"></iframe>" if lora_summary else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + lora_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if lora_summary else ""}
            </div>"""

    # Add RAG+LoRA panel
    if rag_lora_dir:
        comparison_html += f"""
            <div class="panel rag_lora">
                <h3>RAG+LoRA (Hybrid)</h3>
                {"<iframe src=\"" + rag_lora_summary + "\"></iframe>" if rag_lora_summary else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + rag_lora_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if rag_lora_summary else ""}
            </div>"""

    comparison_html += """
        </div>
    </div>

    <!-- Analysis Details Section -->
    <div class="section">
        <h2>3. Analysis Details HTML (Full Analysis)</h2>
        <div class="comparison-grid">"""

    # Add baseline panel
    if baseline_dir:
        comparison_html += f"""
            <div class="panel baseline">
                <h3>Baseline</h3>
                {"<iframe src=\"" + baseline_detailed + "\"></iframe>" if baseline_detailed else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + baseline_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if baseline_detailed else ""}
            </div>"""

    # Add RAG panel
    if rag_dir:
        comparison_html += f"""
            <div class="panel rag">
                <h3>RAG-Enhanced</h3>
                {"<iframe src=\"" + rag_detailed + "\"></iframe>" if rag_detailed else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + rag_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if rag_detailed else ""}
            </div>"""

    # Add LoRA panel
    if lora_dir:
        comparison_html += f"""
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                {"<iframe src=\"" + lora_detailed + "\"></iframe>" if lora_detailed else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + lora_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if lora_detailed else ""}
            </div>"""

    # Add RAG+LoRA panel
    if rag_lora_dir:
        comparison_html += f"""
            <div class="panel rag_lora">
                <h3>RAG+LoRA (Hybrid)</h3>
                {"<iframe src=\"" + rag_lora_detailed + "\"></iframe>" if rag_lora_detailed else "<p class=\"missing\">Not available</p>"}
                {"<a href=\"" + rag_lora_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open</a>" if rag_lora_detailed else ""}
            </div>"""

    comparison_html += """
        </div>
    </div>

    <!-- File Links Section -->
    <div class="section">
        <h2>Additional Files</h2>
        <div class="comparison-grid">"""

    # Add baseline panel
    if baseline_dir:
        comparison_html += f"""
            <div class="panel baseline">
                <h3>Baseline</h3>
                <a href="{baseline_rel}/sse_stream.log" class="file-link" target="_blank">📝 SSE Stream Log</a>
                <a href="{baseline_rel}/sse_events.json" class="file-link" target="_blank">📝 SSE Events JSON</a>
                <a href="{baseline_rel}/metadata.json" class="file-link" target="_blank">ℹ️ Metadata</a>
            </div>"""

    # Add RAG panel
    if rag_dir:
        comparison_html += f"""
            <div class="panel rag">
                <h3>RAG-Enhanced</h3>
                <a href="{rag_rel}/sse_stream.log" class="file-link" target="_blank">📝 SSE Stream Log</a>
                <a href="{rag_rel}/sse_events.json" class="file-link" target="_blank">📝 SSE Events JSON</a>
                <a href="{rag_rel}/metadata.json" class="file-link" target="_blank">ℹ️ Metadata</a>
            </div>"""

    # Add LoRA panel
    if lora_dir:
        comparison_html += f"""
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                <a href="{lora_rel}/sse_stream.log" class="file-link" target="_blank">📝 SSE Stream Log</a>
                <a href="{lora_rel}/sse_events.json" class="file-link" target="_blank">📝 SSE Events JSON</a>
                <a href="{lora_rel}/metadata.json" class="file-link" target="_blank">ℹ️ Metadata</a>
            </div>"""

    # Add RAG+LoRA panel
    if rag_lora_dir:
        comparison_html += f"""
            <div class="panel rag_lora">
                <h3>RAG+LoRA (Hybrid)</h3>
                <a href="{rag_lora_rel}/sse_stream.log" class="file-link" target="_blank">📝 SSE Stream Log</a>
                <a href="{rag_lora_rel}/sse_events.json" class="file-link" target="_blank">📝 SSE Events JSON</a>
                <a href="{rag_lora_rel}/metadata.json" class="file-link" target="_blank">ℹ️ Metadata</a>
            </div>"""

    comparison_html += """
        </div>
    </div>
</body>
</html>"""

    with open(comparison_file, 'w') as f:
        f.write(comparison_html)

    print_success(f"Four-mode comparison HTML saved to: {comparison_file}")
    return comparison_file

def run_e2e_test(mode="baseline", use_sse=True):
    """Run complete end-to-end test for a specific mode"""
    print_header(f"iOS End-to-End Test: {mode.upper()}")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("analysis_output") / f"ios_e2e_{mode}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print_info(f"Output directory: {output_dir}")

    # Verify service mode
    mode_ok, health_snapshot = verify_service_mode(mode)
    if not mode_ok:
        print_warning("Mode verification failed - continuing anyway")

    # Upload and analyze
    job_id, stream_url = upload_image(mode=mode, output_dir=output_dir)

    # Monitor progress
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

    # Save outputs (include health snapshot for debugging)
    detailed_file, summary_file, advisor_bio_file = save_outputs(html, job_id, mode, output_dir, advisor_id=ADVISOR, health_snapshot=health_snapshot)

    print_success(f"{mode.upper()} test complete!")
    print()

    return output_dir, html

def create_text_diff_comparison(mode_dirs):
    """Create text diff comparison between mode outputs"""
    from difflib import unified_diff, HtmlDiff
    import re
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    diff_file = Path("analysis_output") / f"mode_diff_{timestamp}.html"
    
    # Extract text content from each mode's summary HTML
    mode_texts = {}
    for mode, dir_path in mode_dirs.items():
        if dir_path and (dir_path / "analysis_summary.html").exists():
            with open(dir_path / "analysis_summary.html", 'r') as f:
                # Strip HTML tags to get plain text
                html = f.read()
                text = re.sub(r'<[^>]+>', '', html)
                text = re.sub(r'\s+', ' ', text).strip()
                mode_texts[mode] = text
    
    # Generate HTML diff
    html_diff = HtmlDiff()
    diff_html = """<!DOCTYPE html>
<html><head><title>Mode Comparison Diff</title>
<style>
body { font-family: monospace; background: #1c1c1e; color: #fff; padding: 20px; }
.diff_add { background: #1a4d1a; }
.diff_sub { background: #4d1a1a; }
.diff_chg { background: #4d4d1a; }
table { border-collapse: collapse; width: 100%; }
td { padding: 2px 8px; border: 1px solid #333; }
h1, h2 { color: #007AFF; }
</style></head><body>
<h1>Mode Comparison Diff</h1>
"""
    
    # Compare each pair
    modes = list(mode_texts.keys())
    for i, mode1 in enumerate(modes):
        for mode2 in modes[i+1:]:
            diff_html += f"<h2>{mode1.upper()} vs {mode2.upper()}</h2>"
            diff_html += html_diff.make_table(
                mode_texts[mode1].split('. '),
                mode_texts[mode2].split('. '),
                fromdesc=mode1, todesc=mode2
            )
    
    diff_html += "</body></html>"
    
    with open(diff_file, 'w') as f:
        f.write(diff_html)
    
    print_success(f"Diff comparison saved to: {diff_file}")
    return diff_file

def main():
    """Main test flow"""
    parser = argparse.ArgumentParser(
        description="iOS End-to-End Test: Four-Mode Comparison (Baseline vs RAG vs LoRA vs RAG+LoRA)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all four modes (default)
  %(prog)s
  %(prog)s --all

  # Run specific mode
  %(prog)s --mode=base
  %(prog)s --mode=rag
  %(prog)s --mode=lora --lora-path=./adapters/ansel
  %(prog)s --mode=rag_lora --lora-path=./adapters/ansel

  # Run specific tests (legacy)
  %(prog)s --baseline
  %(prog)s --rag
  %(prog)s --lora
  %(prog)s --rag-lora
  %(prog)s --baseline --rag --lora --rag-lora
        """
    )
    parser.add_argument('--baseline', action='store_true', help='Run baseline test')
    parser.add_argument('--rag', action='store_true', help='Run RAG-enhanced test')
    parser.add_argument('--lora', action='store_true', help='Run LoRA fine-tuned test')
    parser.add_argument('--rag-lora', action='store_true', help='Run RAG+LoRA hybrid test')
    parser.add_argument('--all', action='store_true', help='Run all four modes (default)')
    parser.add_argument('--mode', type=str, choices=['base', 'rag', 'lora', 'rag_lora'],
                        help='Service mode to use (will require services to be running in that mode)')
    parser.add_argument('--lora-path', type=str, 
                        help='Path to LoRA adapter (required for lora/rag_lora modes)')
    args = parser.parse_args()

    # Handle --mode flag (new approach)
    if args.mode:
        # Single mode test
        if args.mode in ['lora', 'rag_lora'] and not args.lora_path:
            print_error(f"--lora-path required for mode={args.mode}")
            print()
            print(f"Example: {sys.argv[0]} --mode={args.mode} --lora-path=./adapters/ansel")
            sys.exit(1)
        
        print_header(f"iOS End-to-End Test: {args.mode.upper()} Mode")
        print(f"Test Image: {TEST_IMAGE}")
        print(f"Advisor: {ADVISOR}")
        print(f"Mode: {args.mode}")
        if args.lora_path:
            print(f"LoRA Path: {args.lora_path}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Check SSE client
        if sseclient is None:
            print_warning("sseclient-py not installed. Will use status polling instead")
            print_info("Install with: pip install sseclient-py")
            use_sse = False
        else:
            use_sse = True
        
        # Check services
        check_services()
        
        # Run single test
        output_dir, html = run_e2e_test(mode=args.mode, use_sse=use_sse)
        
        # Final summary
        print_header("TEST COMPLETE")
        print_success(f"{args.mode.upper()} mode test completed successfully")
        print()
        print(f"{BOLD}Output Directory:{NC}")
        print(f"  {output_dir}/")
        print()
        print(f"{BOLD}View outputs:{NC}")
        print(f"  open {output_dir}/analysis_summary.html")
        print(f"  open {output_dir}/analysis_detailed.html")
        if output_dir and (output_dir / "advisor_bio.html").exists():
            print(f"  open {output_dir}/advisor_bio.html")
        print()
        return
    
    # Legacy approach: Determine which tests to run (default: all)
    if not any([args.baseline, args.rag, args.lora, args.rag_lora, args.all]):
        run_baseline = run_rag = run_lora = run_rag_lora = True
    elif args.all:
        run_baseline = run_rag = run_lora = run_rag_lora = True
    else:
        run_baseline = args.baseline
        run_rag = args.rag
        run_lora = args.lora
        run_rag_lora = args.rag_lora

    print_header("iOS End-to-End Test: Four-Mode Comparison")
    print(f"Test Image: {TEST_IMAGE}")
    print(f"Advisor: {ADVISOR}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    modes = []
    if run_baseline:
        modes.append("Baseline")
    if run_rag:
        modes.append("RAG")
    if run_lora:
        modes.append("LoRA")
    if run_rag_lora:
        modes.append("RAG+LoRA")
    print(f"Tests to run: {', '.join(modes)}")

    # Check SSE client
    if sseclient is None:
        print_error("sseclient-py not installed.")
        print_info("Install with: pip install sseclient-py")
        print_info("Will use status polling instead")
        use_sse = False
    else:
        print_success("SSE client available")
        use_sse = True

    # Check services
    check_services()

    # Check LoRA adapter if testing LoRA or RAG+LoRA
    lora_available = False
    if run_lora or run_rag_lora:
        lora_available = check_lora_adapter()
        if not lora_available:
            print_warning("LoRA adapter not found - LoRA tests may fail")

    # Check dimensional profiles if testing RAG or RAG+LoRA
    profiles_available = False
    if run_rag or run_rag_lora:
        profiles_available = check_dimensional_profiles()
        if not profiles_available:
            print_warning("Dimensional profiles not found - RAG tests may fail")

    baseline_dir = rag_dir = lora_dir = rag_lora_dir = None

    # Run tests
    test_num = 1
    if run_baseline:
        print_header(f"TEST {test_num}: BASELINE")
        baseline_dir, _ = run_e2e_test(mode="baseline", use_sse=use_sse)
        if baseline_dir and any([run_rag, run_lora, run_rag_lora]):
            print_info("Waiting 5 seconds before next test...")
            time.sleep(5)
        test_num += 1

    if run_rag:
        print_header(f"TEST {test_num}: RAG-ENHANCED")
        rag_dir, _ = run_e2e_test(mode="rag", use_sse=use_sse)
        if rag_dir and any([run_lora, run_rag_lora]):
            print_info("Waiting 5 seconds before next test...")
            time.sleep(5)
        test_num += 1

    if run_lora and lora_available:
        print_header(f"TEST {test_num}: LORA FINE-TUNED")
        lora_dir, _ = run_e2e_test(mode="lora", use_sse=use_sse)
        if lora_dir and run_rag_lora:
            print_info("Waiting 5 seconds before next test...")
            time.sleep(5)
        test_num += 1
    elif run_lora and not lora_available:
        print_header(f"TEST {test_num}: LORA FINE-TUNED (SKIPPED)")
        print_error("LoRA adapter not available - test skipped")
        test_num += 1

    if run_rag_lora and lora_available and profiles_available:
        print_header(f"TEST {test_num}: RAG+LoRA (HYBRID)")
        rag_lora_dir, _ = run_e2e_test(mode="rag_lora", use_sse=use_sse)
        test_num += 1
    elif run_rag_lora and not lora_available:
        print_header(f"TEST {test_num}: RAG+LoRA (SKIPPED)")
        print_error("LoRA adapter not available - test skipped")
        test_num += 1
    elif run_rag_lora and not profiles_available:
        print_header(f"TEST {test_num}: RAG+LoRA (SKIPPED)")
        print_error("Dimensional profiles not available - test skipped")
        test_num += 1

    # Create comparison view
    comparison_file = None
    diff_file = None
    num_completed = sum([baseline_dir is not None, rag_dir is not None, lora_dir is not None, rag_lora_dir is not None])
    if num_completed >= 2:
        comparison_file = create_four_mode_comparison_html(baseline_dir, rag_dir, lora_dir, rag_lora_dir)
        
        # Create text diff comparison
        mode_dirs = {
            'baseline': baseline_dir,
            'rag': rag_dir,
            'lora': lora_dir,
            'rag_lora': rag_lora_dir
        }
        # Filter out None values
        mode_dirs = {k: v for k, v in mode_dirs.items() if v is not None}
        if len(mode_dirs) >= 2:
            diff_file = create_text_diff_comparison(mode_dirs)

    # Final summary
    print_header("TEST COMPLETE")
    num_modes = sum([baseline_dir is not None, rag_dir is not None, lora_dir is not None, rag_lora_dir is not None])
    if num_modes == 4:
        print_success("All four modes completed successfully")
    elif num_modes > 0:
        print_success(f"{num_modes} test(s) completed successfully")
    else:
        print_error("No tests completed successfully")
    
    print()
    print(f"{BOLD}Output Files:{NC}")
    if baseline_dir:
        print(f"  Baseline:     {baseline_dir}/")
    if rag_dir:
        print(f"  RAG:          {rag_dir}/")
    if lora_dir:
        print(f"  LoRA:         {lora_dir}/")
    if rag_lora_dir:
        print(f"  RAG+LoRA:     {rag_lora_dir}/")
    if comparison_file:
        print(f"  Comparison:   {comparison_file}")
    if diff_file:
        print(f"  Diff:         {diff_file}")
    print()
    if comparison_file or diff_file:
        print(f"{BOLD}View in browser:{NC}")
        print(f"  1. Start HTTP server:")
        print(f"     cd analysis_output && python3 -m http.server 8080")
        print(f"  2. Open in browser:")
        if comparison_file:
            print(f"     http://localhost:8080/{comparison_file.name}")
        if diff_file:
            print(f"     http://localhost:8080/{diff_file.name}")
        print()

if __name__ == "__main__":
    main()
