#!/usr/bin/env python3
"""
iOS End-to-End Test: Three-Mode Comparison (Baseline vs RAG vs LoRA)
Simulates the complete iOS workflow with baseline, RAG-enabled, and LoRA fine-tuned analysis
Saves summary HTML, detailed HTML, advisor bio HTML, and SSE/status updates for each mode

Usage:
    # Activate venv first
    source mondrian/venv/bin/activate

    # Run all three modes (default)
    python3 test/test_ios_e2e_three_mode_comparison.py
    python3 test/test_ios_e2e_three_mode_comparison.py --all

    # Run specific modes with service restart
    python3 test/test_ios_e2e_three_mode_comparison.py --mode=base
    python3 test/test_ios_e2e_three_mode_comparison.py --mode=rag
    python3 test/test_ios_e2e_three_mode_comparison.py --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
    
    # Run specific tests (legacy)
    python3 test/test_ios_e2e_three_mode_comparison.py --baseline
    python3 test/test_ios_e2e_three_mode_comparison.py --rag
    python3 test/test_ios_e2e_three_mode_comparison.py --lora
    python3 test/test_ios_e2e_three_mode_comparison.py --baseline --lora
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

def restart_services_with_mode(mode, lora_path=None):
    """Restart services with specific mode"""
    print_header(f"Restarting Services in {mode.upper()} Mode")
    
    import subprocess
    
    # Build restart command
    cmd = ["./mondrian.sh", "--restart", f"--mode={mode}"]
    if lora_path and mode in ["lora", "lora+rag", "ab-test"]:
        cmd.append(f"--lora-path={lora_path}")
    
    print_info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print_success(f"Services restarted in {mode.upper()} mode")
            print()
            # Wait for services to be ready
            print_info("Waiting for services to be ready...")
            time.sleep(5)
            return True
        else:
            print_error(f"Failed to restart services: {result.stderr}")
            print()
            return False
    except Exception as e:
        print_error(f"Exception restarting services: {e}")
        print()
        return False

def check_services(expected_mode=None, lora_path=None, auto_restart=False):
    """Check that all required services are running
    
    Args:
        expected_mode: Expected service mode (base, rag, lora, etc.)
        lora_path: Path to LoRA adapter (if using LoRA mode)
        auto_restart: If True, automatically restart services if mode doesn't match
    """
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
                
                # Check mode if AI Advisor Service
                if name == "AI Advisor Service" and expected_mode:
                    try:
                        health_data = resp.json()
                        current_mode = health_data.get('model_mode', 'base')
                        is_fine_tuned = health_data.get('fine_tuned', False)
                        
                        print_info(f"Current mode: {current_mode}, Fine-tuned: {is_fine_tuned}")
                        
                        # Check if mode matches
                        mode_matches = False
                        if expected_mode == "base" and current_mode == "base":
                            mode_matches = True
                        elif expected_mode == "rag":
                            # RAG doesn't change service mode, just runtime behavior
                            mode_matches = True
                        elif expected_mode == "lora" and current_mode == "fine_tuned" and is_fine_tuned:
                            mode_matches = True
                        elif expected_mode == "lora+rag" and current_mode == "fine_tuned" and is_fine_tuned:
                            mode_matches = True
                        
                        if not mode_matches and auto_restart:
                            print_warning(f"Service mode mismatch: expected {expected_mode}, got {current_mode}")
                            print_info("Auto-restarting services with correct mode...")
                            if restart_services_with_mode(expected_mode, lora_path):
                                print_success("Services restarted successfully")
                            else:
                                print_error("Failed to restart services")
                                sys.exit(1)
                        elif not mode_matches:
                            print_warning(f"Service mode mismatch: expected {expected_mode}, got {current_mode}")
                            print_info(f"To restart services: ./mondrian.sh --restart --mode={expected_mode}")
                    except Exception as e:
                        print_warning(f"Could not check service mode: {e}")
            else:
                print_error(f"{name} (port {port}) - DOWN (status {resp.status_code})")
                all_required_up = False
                down_services.append(f"{name} (port {port})")
        except Exception as e:
            print_error(f"{name} (port {port}) - DOWN ({e})")
            all_required_up = False
            down_services.append(f"{name} (port {port})")

    if not all_required_up:
        if auto_restart and expected_mode:
            print()
            print_warning("Services are down. Attempting to start them...")
            if restart_services_with_mode(expected_mode, lora_path):
                print_success("Services started successfully")
                print()
                return
            else:
                print_error("Failed to start services")
        
        print()
        print_error("Not all required services are running. Please start them first.")
        print()
        print(f"{YELLOW}Required services that are DOWN:{NC}")
        for service in down_services:
            print(f"  ✗ {service}")
        print()
        print(f"{BLUE}To start all services, run:{NC}")
        if expected_mode:
            mode_cmd = f"./mondrian.sh --restart --mode={expected_mode}"
            if lora_path and expected_mode in ["lora", "lora+rag"]:
                mode_cmd += f" --lora-path={lora_path}"
            print(f"  {mode_cmd}")
        else:
            print(f"  ./mondrian.sh --restart")
        print()
        sys.exit(1)

    print()
    print_success("All required services are running")
    print()

def check_lora_adapter():
    """Check if LoRA adapter is available"""
    adapter_path = Path("adapters/ansel_image")
    adapter_file = adapter_path / "adapters.safetensors"

    if adapter_file.exists():
        print_success(f"LoRA adapter found: {adapter_path}")
        return True
    else:
        print_warning(f"LoRA adapter not found at: {adapter_path}")
        print_info("LoRA tests will be skipped unless --lora is explicitly specified")
        return False

def upload_image(mode="baseline"):
    """Upload image and start analysis (simulates iOS upload)

    Args:
        mode: "baseline", "rag", or "lora"
    """
    mode_display = mode.upper()
    print_step(2, f"Uploading Image ({mode_display})")

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
            'mode': mode  # Send mode parameter
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

def save_outputs(full_html, job_id, mode, output_dir, advisor_id=None):
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
            'status_polling_log': 'status_polling.log'
        }
    }

    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print_success(f"Metadata saved to: {metadata_file}")

    return full_html_file, summary_html_file, advisor_bio_html_file

def create_three_mode_comparison_html(baseline_dir, rag_dir, lora_dir):
    """Create three-way comparison HTML"""
    print_step(6, "Creating Three-Mode Comparison View")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = Path("analysis_output") / f"ios_e2e_three_mode_{timestamp}.html"

    # Helper to get relative paths
    def get_rel_path(dir_path):
        if dir_path:
            return str(dir_path).replace("analysis_output/", "").replace("analysis_output\\", "")
        return None

    baseline_rel = get_rel_path(baseline_dir)
    rag_rel = get_rel_path(rag_dir)
    lora_rel = get_rel_path(lora_dir)

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

    # Count how many modes we're comparing
    num_modes = sum([baseline_dir is not None, rag_dir is not None, lora_dir is not None])
    grid_cols = num_modes

    comparison_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iOS E2E Test - Three Mode Comparison</title>
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
        <h1>iOS End-to-End Test - Three Mode Comparison</h1>
        <p>Baseline vs RAG vs LoRA Fine-tuned - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p style="color: #999; font-size: 14px;">Comparing HTML outputs across all three analysis modes</p>
    </div>

    <!-- Advisor Bio Section -->
    <div class="section">
        <h2>1. Advisor Bio HTML</h2>
        <div class="comparison-grid">"""

    # Add baseline panel
    if baseline_dir:
        comparison_html += f"""
            <div class="panel baseline">
                <h3>Baseline (No Enhancement)</h3>
                {"<iframe src=\"" + baseline_bio + "\"></iframe>" if baseline_bio else "<p class=\"missing\">Advisor bio HTML not available</p>"}
                {"<a href=\"" + baseline_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open Advisor Bio HTML</a>" if baseline_bio else ""}
            </div>"""

    # Add RAG panel
    if rag_dir:
        comparison_html += f"""
            <div class="panel rag">
                <h3>RAG-Enhanced</h3>
                {"<iframe src=\"" + rag_bio + "\"></iframe>" if rag_bio else "<p class=\"missing\">Advisor bio HTML not available</p>"}
                {"<a href=\"" + rag_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open Advisor Bio HTML</a>" if rag_bio else ""}
            </div>"""

    # Add LoRA panel
    if lora_dir:
        comparison_html += f"""
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                {"<iframe src=\"" + lora_bio + "\"></iframe>" if lora_bio else "<p class=\"missing\">Advisor bio HTML not available</p>"}
                {"<a href=\"" + lora_bio + "\" class=\"file-link\" target=\"_blank\">📄 Open Advisor Bio HTML</a>" if lora_bio else ""}
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
                {"<iframe src=\"" + baseline_summary + "\"></iframe>" if baseline_summary else "<p class=\"missing\">Summary HTML not available</p>"}
                {"<a href=\"" + baseline_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open Summary HTML</a>" if baseline_summary else ""}
            </div>"""

    # Add RAG panel
    if rag_dir:
        comparison_html += f"""
            <div class="panel rag">
                <h3>RAG-Enhanced</h3>
                {"<iframe src=\"" + rag_summary + "\"></iframe>" if rag_summary else "<p class=\"missing\">Summary HTML not available</p>"}
                {"<a href=\"" + rag_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open Summary HTML</a>" if rag_summary else ""}
            </div>"""

    # Add LoRA panel
    if lora_dir:
        comparison_html += f"""
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                {"<iframe src=\"" + lora_summary + "\"></iframe>" if lora_summary else "<p class=\"missing\">Summary HTML not available</p>"}
                {"<a href=\"" + lora_summary + "\" class=\"file-link\" target=\"_blank\">📄 Open Summary HTML</a>" if lora_summary else ""}
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
                {"<iframe src=\"" + baseline_detailed + "\"></iframe>" if baseline_detailed else "<p class=\"missing\">Detailed HTML not available</p>"}
                {"<a href=\"" + baseline_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open Detailed HTML</a>" if baseline_detailed else ""}
            </div>"""

    # Add RAG panel
    if rag_dir:
        comparison_html += f"""
            <div class="panel rag">
                <h3>RAG-Enhanced</h3>
                {"<iframe src=\"" + rag_detailed + "\"></iframe>" if rag_detailed else "<p class=\"missing\">Detailed HTML not available</p>"}
                {"<a href=\"" + rag_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open Detailed HTML</a>" if rag_detailed else ""}
            </div>"""

    # Add LoRA panel
    if lora_dir:
        comparison_html += f"""
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                {"<iframe src=\"" + lora_detailed + "\"></iframe>" if lora_detailed else "<p class=\"missing\">Detailed HTML not available</p>"}
                {"<a href=\"" + lora_detailed + "\" class=\"file-link\" target=\"_blank\">📄 Open Detailed HTML</a>" if lora_detailed else ""}
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

    comparison_html += """
        </div>
    </div>
</body>
</html>"""

    with open(comparison_file, 'w') as f:
        f.write(comparison_html)

    print_success(f"Three-mode comparison HTML saved to: {comparison_file}")
    return comparison_file

def run_e2e_test(mode="baseline", use_sse=True):
    """Run complete end-to-end test for a specific mode"""
    print_header(f"iOS End-to-End Test: {mode.upper()}")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("analysis_output") / f"ios_e2e_{mode}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print_info(f"Output directory: {output_dir}")

    # Upload and analyze
    job_id, stream_url = upload_image(mode=mode)

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

    # Save outputs
    detailed_file, summary_file, advisor_bio_file = save_outputs(html, job_id, mode, output_dir, advisor_id=ADVISOR)

    print_success(f"{mode.upper()} test complete!")
    print()

    return output_dir, html

def main():
    """Main test flow"""
    parser = argparse.ArgumentParser(
        description="iOS End-to-End Test: Three-Mode Comparison (Baseline vs RAG vs LoRA)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all three modes (default)
  %(prog)s
  %(prog)s --all

  # Run specific mode with automatic service restart
  %(prog)s --mode=base
  %(prog)s --mode=rag
  %(prog)s --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
  %(prog)s --mode=lora+rag --lora-path=./models/qwen3-vl-4b-lora-ansel

  # Run specific tests (legacy)
  %(prog)s --baseline
  %(prog)s --rag
  %(prog)s --lora
  %(prog)s --baseline --lora
        """
    )
    parser.add_argument('--baseline', action='store_true', help='Run baseline test')
    parser.add_argument('--rag', action='store_true', help='Run RAG-enhanced test')
    parser.add_argument('--lora', action='store_true', help='Run LoRA fine-tuned test')
    parser.add_argument('--all', action='store_true', help='Run all three modes (default)')
    parser.add_argument('--mode', type=str, choices=['base', 'rag', 'lora', 'lora+rag', 'ab-test'],
                        help='Service mode to use (will restart services if needed)')
    parser.add_argument('--lora-path', type=str, 
                        help='Path to LoRA adapter (required for lora/lora+rag/ab-test modes)')
    parser.add_argument('--auto-restart', action='store_true', default=True,
                        help='Automatically restart services if mode doesn\'t match (default: True)')
    parser.add_argument('--no-auto-restart', action='store_false', dest='auto_restart',
                        help='Do not automatically restart services')
    args = parser.parse_args()

    # Handle --mode flag (new approach)
    if args.mode:
        # Single mode test with automatic service restart
        if args.mode in ['lora', 'lora+rag', 'ab-test'] and not args.lora_path:
            print_error(f"--lora-path required for mode={args.mode}")
            print()
            print(f"Example: {sys.argv[0]} --mode={args.mode} --lora-path=./models/qwen3-vl-4b-lora-ansel")
            sys.exit(1)
        
        print_header(f"iOS End-to-End Test: {args.mode.upper()} Mode")
        print(f"Test Image: {TEST_IMAGE}")
        print(f"Advisor: {ADVISOR}")
        print(f"Mode: {args.mode}")
        if args.lora_path:
            print(f"LoRA Path: {args.lora_path}")
        print(f"Auto-restart: {args.auto_restart}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Check SSE client
        if sseclient is None:
            print_warning("sseclient-py not installed. Will use status polling instead")
            print_info("Install with: pip install sseclient-py")
            use_sse = False
        else:
            use_sse = True
        
        # Check services (with mode validation and auto-restart)
        check_services(expected_mode=args.mode, lora_path=args.lora_path, auto_restart=args.auto_restart)
        
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
        if (output_dir / "advisor_bio.html").exists():
            print(f"  open {output_dir}/advisor_bio.html")
        print()
        return
    
    # Legacy approach: Determine which tests to run (default: all)
    if not any([args.baseline, args.rag, args.lora, args.all]):
        run_baseline = run_rag = run_lora = True
    elif args.all:
        run_baseline = run_rag = run_lora = True
    else:
        run_baseline = args.baseline
        run_rag = args.rag
        run_lora = args.lora

    print_header("iOS End-to-End Test: Three-Mode Comparison")
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

    # Check services (no mode validation for legacy multi-mode tests)
    check_services()

    # Check LoRA adapter if testing LoRA
    if run_lora:
        lora_available = check_lora_adapter()
        if not lora_available:
            print_warning("LoRA adapter not found - LoRA test may fail")
            print_info("Train adapter first with: python training/train_lora.py")

    baseline_dir = rag_dir = lora_dir = None

    # Run tests
    if run_baseline:
        print_header("TEST 1: BASELINE")
        baseline_dir, _ = run_e2e_test(mode="baseline", use_sse=use_sse)
        if baseline_dir and (run_rag or run_lora):
            print_info("Waiting 5 seconds before next test...")
            time.sleep(5)

    if run_rag:
        test_num = 2 if run_baseline else 1
        print_header(f"TEST {test_num}: RAG-ENHANCED")
        rag_dir, _ = run_e2e_test(mode="rag", use_sse=use_sse)
        if rag_dir and run_lora:
            print_info("Waiting 5 seconds before next test...")
            time.sleep(5)

    if run_lora:
        test_num = sum([run_baseline, run_rag]) + 1
        print_header(f"TEST {test_num}: LORA FINE-TUNED")
        lora_dir, _ = run_e2e_test(mode="lora", use_sse=use_sse)

    # Create comparison view
    comparison_file = None
    if sum([baseline_dir is not None, rag_dir is not None, lora_dir is not None]) >= 2:
        comparison_file = create_three_mode_comparison_html(baseline_dir, rag_dir, lora_dir)

    # Final summary
    print_header("TEST COMPLETE")
    if baseline_dir and rag_dir and lora_dir:
        print_success("All three modes completed successfully")
    else:
        print_success("Selected tests completed successfully")
    print()
    print(f"{BOLD}Output Files:{NC}")
    if baseline_dir:
        print(f"  Baseline:    {baseline_dir}/")
    if rag_dir:
        print(f"  RAG:         {rag_dir}/")
    if lora_dir:
        print(f"  LoRA:        {lora_dir}/")
    if comparison_file:
        print(f"  Comparison:  {comparison_file}")
    print()
    if comparison_file:
        print(f"{BOLD}View in browser:{NC}")
        print(f"  file://{comparison_file.absolute()}")
        print()

if __name__ == "__main__":
    main()
