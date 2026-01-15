#!/usr/bin/env python3
"""
End-to-End Test for LoRA Mode
Tests the complete iOS API data flow with LoRA strategy.

This test simulates the exact flow that the iOS app uses:
1. Upload image with mode="lora"
2. Monitor progress via SSE stream (with polling fallback)
3. Fetch all HTML outputs (advisor bio, summary, detailed analysis)
4. Verify LoRA mode was used (adapter loaded, no fallback)
5. Optional: Compare LoRA vs baseline side-by-side

Usage:
    # Basic LoRA test
    python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel

    # Test with comparison mode
    python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare

    # Test different modes
    python3 test_lora_e2e.py --image source/test.jpg --advisor ansel --mode rag
    python3 test_lora_e2e.py --image source/test.jpg --advisor ansel --mode baseline
"""

import argparse
import base64
import json
import os
import requests
import sys
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

# Try to import sseclient for SSE streaming
try:
    import sseclient
except ImportError:
    sseclient = None


# Configuration
JOB_SERVICE_URL = "http://127.0.0.1:5005"
AI_ADVISOR_URL = "http://127.0.0.1:5100"


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_step(step_num: int, message: str):
    """Print a numbered step"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}[Step {step_num}]{Colors.ENDC} {message}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {message}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗{Colors.ENDC} {message}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {message}")


def check_services():
    """Check if required services are running"""
    print_step(1, "Checking services...")

    services = {
        "Job Service": f"{JOB_SERVICE_URL}/health",
        "AI Advisor Service": f"{AI_ADVISOR_URL}/health"
    }

    all_healthy = True
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print_success(f"{name} is running")
            else:
                print_error(f"{name} returned status {response.status_code}")
                all_healthy = False
        except requests.exceptions.RequestException as e:
            print_error(f"{name} is not reachable: {e}")
            all_healthy = False

    if not all_healthy:
        print_error("Some services are not running. Please start them first.")
        print_info("Run: python3 mondrian/start_services.py")
        sys.exit(1)


def check_lora_adapter(advisor_id: str) -> bool:
    """Check if LoRA adapter exists for advisor"""
    print_step(2, f"Checking LoRA adapter for '{advisor_id}'...")

    adapter_path = Path(f"adapters/{advisor_id}/adapters.safetensors")

    if adapter_path.exists():
        size_mb = adapter_path.stat().st_size / (1024 * 1024)
        print_success(f"LoRA adapter found: {adapter_path} ({size_mb:.1f} MB)")
        return True
    else:
        print_error(f"LoRA adapter not found at: {adapter_path}")
        print_info("To create a LoRA adapter, follow the guide in README_LORA_PLAN.md")
        return False


def upload_image(image_path: str, advisor_id: str, mode: str = "lora") -> Optional[dict]:
    """Upload image to Job Service (simulates iOS upload)"""
    print_step(3, f"Uploading image with mode='{mode}'...")

    if not os.path.exists(image_path):
        print_error(f"Image not found: {image_path}")
        return None

    # Prepare multipart form data (exactly as iOS does)
    with open(image_path, 'rb') as f:
        files = {'image': (os.path.basename(image_path), f, 'image/jpeg')}
        data = {
            'advisor': advisor_id,
            'mode': mode,
            'auto_analyze': 'true'
        }

        try:
            response = requests.post(
                f"{JOB_SERVICE_URL}/upload",
                files=files,
                data=data,
                timeout=10
            )

            if response.status_code == 201:
                result = response.json()
                print_success(f"Image uploaded successfully")
                print_info(f"Job ID: {result['job_id']}")
                print_info(f"Status URL: {result.get('status_url', 'N/A')}")
                print_info(f"Stream URL: {result.get('stream_url', 'N/A')}")
                return result
            else:
                print_error(f"Upload failed with status {response.status_code}")
                print_error(f"Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print_error(f"Upload request failed: {e}")
            return None


def stream_sse_updates(stream_url: str, output_dir: Path) -> bool:
    """Stream SSE updates and save to file"""
    print_step(4, "Streaming SSE Updates")

    if sseclient is None:
        print_error("sseclient-py not installed, cannot use SSE streaming")
        return False

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


def monitor_progress(job_id: str, output_dir: Path, timeout: int = 300) -> bool:
    """Monitor job progress via polling (simulates iOS status polling)"""
    print_step(4, "Monitoring Progress (Polling)")

    status_log_file = output_dir / "status_polling.log"
    start_time = time.time()
    last_progress = -1
    last_step = ""

    with open(status_log_file, 'w') as log:
        log.write(f"Status Polling Started: {datetime.now()}\n")
        log.write(f"Job ID: {job_id}\n")
        log.write("="*80 + "\n\n")

        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{JOB_SERVICE_URL}/status/{job_id}",
                    timeout=5
                )

                if response.status_code != 200:
                    print_error(f"Status check failed: {response.status_code}")
                    log.write(f"ERROR: Status check failed: {response.status_code}\n")
                    return False

                status_data = response.json()
                
                # Access fields at top level (not nested under 'job')
                status = status_data.get('status')
                progress = status_data.get('progress_percentage', 0)
                current_step = status_data.get('current_step', '')
                thinking = status_data.get('llm_thinking', '')

                timestamp = datetime.now().strftime("%H:%M:%S")
                log_line = f"[{timestamp}] Status: {status} | Progress: {progress}% | Step: {current_step}\n"
                log.write(log_line)
                log.flush()

                # Print updates
                if progress != last_progress or current_step != last_step:
                    print_info(f"[{progress}%] {current_step}")
                    if thinking:
                        print(f"  └─ {Colors.OKCYAN}{thinking}{Colors.ENDC}")
                    last_progress = progress
                    last_step = current_step

                # Check completion
                if status == 'done' or status == 'completed':
                    print_success("Analysis completed!")
                    log.write(f"\n[{timestamp}] COMPLETED\n")
                    return True
                elif status == 'error' or status == 'failed':
                    error_msg = status_data.get('error', 'Unknown error')
                    print_error(f"Analysis failed: {error_msg}")
                    log.write(f"\n[{timestamp}] FAILED: {error_msg}\n")
                    return False

                time.sleep(2)  # Poll every 2 seconds

            except requests.exceptions.RequestException as e:
                print_error(f"Status check error: {e}")
                log.write(f"ERROR: {e}\n")
                time.sleep(2)
                continue

        print_error(f"Timeout after {timeout} seconds")
        log.write(f"\nTIMEOUT after {timeout} seconds\n")
        return False


def get_analysis_html(job_id: str) -> Optional[str]:
    """Get analysis HTML output (detailed analysis)"""
    try:
        resp = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=10)

        if resp.status_code == 200:
            html = resp.text
            print_success(f"Retrieved detailed HTML ({len(html)} bytes)")
            return html
        else:
            print_error(f"Failed to get analysis: {resp.status_code}")
            return None

    except Exception as e:
        print_error(f"Exception getting analysis: {e}")
        return None


def get_summary_html(job_id: str) -> Optional[str]:
    """Fetch summary HTML (top 3 recommendations)"""
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


def get_advisor_bio_html(advisor_id: str) -> Optional[str]:
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


def save_outputs(full_html: str, job_id: str, mode: str, output_dir: Path, advisor_id: str) -> tuple:
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
        'advisor': advisor_id,
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


def verify_lora_mode(job_id: str, expected_mode: str = "lora") -> tuple:
    """Verify that the expected mode was actually used

    Returns:
        (verified: bool, mode_used: str, fallback_occurred: bool)
    """
    print_step(6, f"Verifying {expected_mode.upper()} mode was used...")

    try:
        # Check AI Advisor Service health for model info
        try:
            health_resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
            if health_resp.status_code == 200:
                health_data = health_resp.json()
                model_mode = health_data.get('model_mode', 'base')
                is_fine_tuned = health_data.get('fine_tuned', False)

                print_info(f"AI Advisor Service - Model Mode: {model_mode}, Fine-tuned: {is_fine_tuned}")

                if expected_mode == "lora" and model_mode == "fine_tuned" and is_fine_tuned:
                    print_success("✓ AI Advisor Service is running in fine-tuned mode")
                elif expected_mode == "lora":
                    print_error(f"✗ AI Advisor Service is NOT in fine-tuned mode (mode={model_mode})")
        except Exception as e:
            print_info(f"Could not check AI Advisor Service health: {e}")

        # Check job details
        response = requests.get(
            f"{JOB_SERVICE_URL}/status/{job_id}",
            timeout=5
        )

        if response.status_code != 200:
            print_error("Failed to fetch job status")
            return False, "unknown", False

        status_data = response.json()
        
        # Debug: Show response structure
        print_info(f"Status response keys: {list(status_data.keys())}")
        print_info(f"Status: {status_data.get('status')}")
        
        # Check for mode_used metadata (from AnalysisResult)
        # llm_outputs is at the top level of the response, not nested under 'job'
        llm_outputs = status_data.get('llm_outputs')
        mode_used = None
        fallback_occurred = False

        if llm_outputs:
            print_info(f"llm_outputs type: {type(llm_outputs)}")
            
            # llm_outputs is already a dict, not a JSON string
            if isinstance(llm_outputs, str):
                try:
                    outputs = json.loads(llm_outputs)
                except json.JSONDecodeError:
                    print_error("Failed to parse llm_outputs as JSON string")
                    outputs = None
            else:
                outputs = llm_outputs
            
            if outputs:
                # Check if any output contains mode_used
                for advisor, output in outputs.items():
                    if isinstance(output, dict):
                        mode_used = output.get('mode_used')
                        metadata = output.get('metadata', {})
                        fallback_occurred = metadata.get('fallback_occurred', False)

                        if mode_used:
                            print_info(f"Mode used: {mode_used}")
                            if fallback_occurred:
                                print_error(f"✗ Fallback occurred! Requested '{expected_mode}' but used '{mode_used}'")
                                requested_mode = metadata.get('requested_mode')
                                if requested_mode:
                                    print_info(f"Requested mode: {requested_mode}")
                                return False, mode_used, True
                            elif mode_used == expected_mode:
                                print_success(f"✓ {expected_mode.upper()} mode confirmed for {advisor}")
                                return True, mode_used, False
                            else:
                                print_error(f"✗ Expected '{expected_mode}' but got '{mode_used}' for {advisor}")
                                return False, mode_used, False
            else:
                print_error("llm_outputs is empty or could not be parsed")

        # If no mode_used found, check prompt for indicators
        prompt = status_data.get('prompt', '')
        if expected_mode == "lora" and ('lora' in prompt.lower() or 'adapter' in prompt.lower()):
            print_success("LoRA indicators found in prompt")
            return True, "lora", False

        print_error(f"Could not verify {expected_mode.upper()} mode was used")
        print_info("This might mean the mode fell back to RAG or baseline")
        return False, mode_used or "unknown", True

    except Exception as e:
        print_error(f"Verification failed: {e}")
        return False, "unknown", False


def run_test(image_path: str, advisor_id: str, mode: str = "lora") -> Optional[Path]:
    """Run complete end-to-end test

    Returns:
        Path to output directory if successful, None otherwise
    """
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  LoRA End-to-End Test - {mode.upper()} Mode{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"\n{Colors.BOLD}Configuration:{Colors.ENDC}")
    print(f"  Image: {image_path}")
    print(f"  Advisor: {advisor_id}")
    print(f"  Mode: {mode}")
    print(f"  Job Service: {JOB_SERVICE_URL}")
    print(f"  AI Advisor: {AI_ADVISOR_URL}")

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("analysis_output") / f"lora_e2e_{mode}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print_info(f"Output directory: {output_dir}")

    # Check if SSE client is available
    use_sse = sseclient is not None
    if not use_sse:
        print_info("sseclient-py not installed, will use status polling")
        print_info("Install with: pip install sseclient-py")

    # Step 1: Check services
    check_services()

    # Step 2: Check LoRA adapter
    has_adapter = check_lora_adapter(advisor_id)
    if not has_adapter and mode == "lora":
        print_error("\nTest cannot proceed without LoRA adapter")
        print_info("Either:")
        print_info("  1. Train a LoRA adapter (see README_LORA_PLAN.md)")
        print_info("  2. Run test with --mode baseline or --mode rag")
        return None

    # Step 3: Upload image
    upload_result = upload_image(image_path, advisor_id, mode)
    if not upload_result:
        print_error("\nTest failed at upload step")
        return None

    job_id = upload_result['job_id']
    stream_url = upload_result.get('stream_url')

    # Step 4: Monitor progress (SSE with polling fallback)
    if use_sse and stream_url:
        success = stream_sse_updates(stream_url, output_dir)
        if not success:
            print_error("SSE streaming failed, falling back to polling")
            success = monitor_progress(job_id, output_dir)
    else:
        success = monitor_progress(job_id, output_dir)

    if not success:
        print_error("\nTest failed at monitoring step")
        return None

    # Step 5: Fetch and save all HTML outputs
    html = get_analysis_html(job_id)
    if not html:
        print_error("\nTest failed to fetch analysis")
        return None

    detailed_file, summary_file, bio_file = save_outputs(html, job_id, mode, output_dir, advisor_id)

    # Step 6: Verify mode
    verified, mode_used, fallback_occurred = verify_lora_mode(job_id, mode)

    # For lora mode, verification is REQUIRED
    if mode == "lora" and not verified:
        print(f"\n{Colors.FAIL}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.FAIL}{Colors.BOLD}  ✗ End-to-End Test FAILED{Colors.ENDC}")
        print(f"{Colors.FAIL}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
        
        print(f"{Colors.BOLD}Failure Reason:{Colors.ENDC}")
        print(f"  LoRA mode verification failed")
        print(f"  Expected mode: {mode}")
        print(f"  Actual mode: {mode_used}")
        print(f"  Fallback occurred: {fallback_occurred}")
        print()
        
        print(f"{Colors.BOLD}Troubleshooting:{Colors.ENDC}")
        print(f"  1. Check adapter: adapters/{advisor_id}/adapters.safetensors")
        print(f"  2. Check health: curl http://127.0.0.1:5100/health")
        print(f"  3. Check service logs for adapter loading errors")
        print()
        
        return None  # Fail the test

    # For other modes, just warn if verification couldn't confirm
    if not verified and mode in ["baseline", "rag"]:
        print_error(f"\nWarning: Could not verify {mode} mode was used")
        if fallback_occurred:
            print_info("Fallback occurred - this is unexpected")

    # Success! (Only reached if verification passed or mode allows flexibility)
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{Colors.BOLD}  ✓ End-to-End Test PASSED{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

    print(f"{Colors.BOLD}Results:{Colors.ENDC}")
    print(f"  Job ID: {job_id}")
    print(f"  Mode Requested: {mode}")
    print(f"  Mode Used: {mode_used}")
    print(f"  Fallback: {'Yes' if fallback_occurred else 'No'}")
    print(f"\n{Colors.BOLD}Output Files:{Colors.ENDC}")
    print(f"  Output Dir: {output_dir}")
    if bio_file:
        print(f"  Advisor Bio: {bio_file}")
    if summary_file:
        print(f"  Summary: {summary_file}")
    print(f"  Detailed: {detailed_file}")
    print(f"\n{Colors.BOLD}View in browser:{Colors.ENDC}")
    if summary_file:
        print(f"  open {summary_file}")
    print(f"  open {detailed_file}")

    return output_dir


def create_comparison_html(lora_dir: Path, baseline_dir: Path) -> Path:
    """Create side-by-side comparison HTML"""
    print_step(7, "Creating Comparison View")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = Path("analysis_output") / f"lora_e2e_comparison_{timestamp}.html"

    # Helper to get relative paths
    def get_rel_path(dir_path):
        return str(dir_path).replace("analysis_output/", "").replace("analysis_output\\", "")

    lora_rel = get_rel_path(lora_dir)
    baseline_rel = get_rel_path(baseline_dir)

    comparison_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LoRA vs Baseline Comparison</title>
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
    </style>
</head>
<body>
    <div class="header">
        <h1>LoRA vs Baseline Comparison</h1>
        <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="section">
        <h2>Summary (Top 3 Recommendations)</h2>
        <div class="comparison-grid">
            <div class="panel baseline">
                <h3>Baseline</h3>
                <iframe src="{baseline_rel}/analysis_summary.html"></iframe>
                <a href="{baseline_rel}/analysis_summary.html" class="file-link" target="_blank">📄 Open Summary</a>
            </div>
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                <iframe src="{lora_rel}/analysis_summary.html"></iframe>
                <a href="{lora_rel}/analysis_summary.html" class="file-link" target="_blank">📄 Open Summary</a>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Detailed Analysis</h2>
        <div class="comparison-grid">
            <div class="panel baseline">
                <h3>Baseline</h3>
                <iframe src="{baseline_rel}/analysis_detailed.html"></iframe>
                <a href="{baseline_rel}/analysis_detailed.html" class="file-link" target="_blank">📄 Open Detailed</a>
            </div>
            <div class="panel lora">
                <h3>LoRA Fine-tuned</h3>
                <iframe src="{lora_rel}/analysis_detailed.html"></iframe>
                <a href="{lora_rel}/analysis_detailed.html" class="file-link" target="_blank">📄 Open Detailed</a>
            </div>
        </div>
    </div>
</body>
</html>"""

    with open(comparison_file, 'w') as f:
        f.write(comparison_html)

    print_success(f"Comparison HTML saved to: {comparison_file}")
    return comparison_file


def main():
    parser = argparse.ArgumentParser(
        description="Test LoRA mode end-to-end with iOS API data flow"
    )
    parser.add_argument(
        "--image",
        type=str,
        required=True,
        help="Path to image file (e.g., source/test.jpg)"
    )
    parser.add_argument(
        "--advisor",
        type=str,
        default="ansel",
        help="Advisor ID (default: ansel)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="lora",
        choices=["baseline", "rag", "lora"],
        help="Analysis mode (default: lora)"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run LoRA vs baseline comparison"
    )
    parser.add_argument(
        "--job-service-url",
        type=str,
        default="http://127.0.0.1:5005",
        help="Job Service URL"
    )
    parser.add_argument(
        "--ai-advisor-url",
        type=str,
        default="http://127.0.0.1:5100",
        help="AI Advisor Service URL"
    )

    args = parser.parse_args()

    # Update global URLs
    global JOB_SERVICE_URL, AI_ADVISOR_URL
    JOB_SERVICE_URL = args.job_service_url
    AI_ADVISOR_URL = args.ai_advisor_url

    try:
        if args.compare:
            # Run comparison mode: LoRA vs baseline
            print(f"\n{Colors.HEADER}{Colors.BOLD}Running Comparison Mode: LoRA vs Baseline{Colors.ENDC}\n")

            # Run LoRA test
            lora_dir = run_test(args.image, args.advisor, "lora")
            if not lora_dir:
                print_error("LoRA test failed")
                sys.exit(1)

            print_info("\nWaiting 5 seconds before running baseline test...")
            time.sleep(5)

            # Run baseline test
            baseline_dir = run_test(args.image, args.advisor, "baseline")
            if not baseline_dir:
                print_error("Baseline test failed")
                sys.exit(1)

            # Create comparison HTML
            comparison_file = create_comparison_html(lora_dir, baseline_dir)

            print(f"\n{Colors.OKGREEN}{Colors.BOLD}{'='*60}{Colors.ENDC}")
            print(f"{Colors.OKGREEN}{Colors.BOLD}  ✓ Comparison Complete{Colors.ENDC}")
            print(f"{Colors.OKGREEN}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
            print(f"{Colors.BOLD}Comparison File:{Colors.ENDC}")
            print(f"  {comparison_file}")
            print(f"\n{Colors.BOLD}View in browser:{Colors.ENDC}")
            print(f"  open {comparison_file}")

        else:
            # Run single test
            output_dir = run_test(args.image, args.advisor, args.mode)
            if not output_dir:
                sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
