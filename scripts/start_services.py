#!/usr/bin/env python3
"""
Minimal start_services.py for Mondrian project
Launches all core services in the correct order.
Supports different modes: base, rag, lora
"""

import subprocess
import os
import sys
import signal
import time
import json
import sqlite3

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required but not installed.")
    print("Please install it with: pip install requests")
    sys.exit(1)


# Global flag to track if we're in cleanup phase
_in_cleanup = False

def signal_handler(signum, frame):
    """Handle signals during cleanup phase."""
    global _in_cleanup
    if _in_cleanup:
        # During cleanup, ignore SIGTERM to prevent parent process termination
        print(f"[DEBUG] Received signal {signum} during cleanup phase - ignoring to prevent interruption")
        return
    # Otherwise, re-raise to allow normal termination
    raise KeyboardInterrupt()

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal.default_int_handler)


# Determine the correct Python executable to use
def get_python_executable():
    """Get the Python executable, preferring venv if available."""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check for venv in root directory
    venv_python = os.path.join(script_dir, "venv", "bin", "python3")
    if os.path.exists(venv_python):
        return venv_python
    
    # Check for venv in mondrian subdirectory
    venv_python = os.path.join(script_dir, "mondrian", "venv", "bin", "python3")
    if os.path.exists(venv_python):
        return venv_python
    
    # Check VIRTUAL_ENV environment variable
    if 'VIRTUAL_ENV' in os.environ:
        venv_python = os.path.join(os.environ['VIRTUAL_ENV'], "bin", "python3")
        if os.path.exists(venv_python):
            return venv_python
    
    # Fall back to current Python
    return sys.executable

PYTHON_EXECUTABLE = get_python_executable()
print(f"Using Python: {PYTHON_EXECUTABLE}")


# Default services (will be configured based on mode)
def get_services_for_mode(mode="base", lora_path=None, model=None):
    """
    Get service configurations based on mode.
    
    Modes:
        - base: Base model only, no RAG, no LoRA
        - rag: Base model with RAG enabled
        - lora: Base model with LoRA adapter (requires --lora-path)
        - lora+rag: LoRA model with RAG enabled
    """
    # Summary Service should start first (port 5006)
    services = [
        [PYTHON_EXECUTABLE, "mondrian/summary_service.py", "--port", "5006"],
    ]
    
    # Job Service (port 5005) - explicitly specify database path
    services.append([PYTHON_EXECUTABLE, "mondrian/job_service_v2.3.py", "--port", "5005", "--db", "mondrian.db"])
    
    # Configure AI Advisor Service based on mode and platform
    import platform
    if platform.system() == "Linux":
        ai_advisor_cmd = [PYTHON_EXECUTABLE, "mondrian/ai_advisor_service_linux.py", "--port", "5100"]
    else:
        ai_advisor_cmd = [PYTHON_EXECUTABLE, "mondrian/ai_advisor_service.py", "--port", "5100"]
    
    # Add model if specified
    if model:
        ai_advisor_cmd.extend(["--model", model])
    
    if mode == "base":
        # Base mode: default settings (no special flags)
        print("[MODE] Base model only (no RAG, no LoRA)")
        pass  # Use defaults
        
    elif mode == "rag":
        # RAG mode: enable RAG by default
        print("[MODE] Base model with RAG enabled")
        # RAG is controlled by environment variable RAG_ENABLED or per-request
        # We don't need to pass args here, just document the mode
        pass
        
    elif mode == "lora":
        # LoRA mode: use fine-tuned model
        print("[MODE] LoRA fine-tuned model")
        if not lora_path:
            print("ERROR: --lora-path required for lora mode")
            print("Example: ./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel")
            sys.exit(1)
        if platform.system() == "Linux":
            ai_advisor_cmd.extend(["--adapter", lora_path, "--load_in_4bit"])
        else:
            ai_advisor_cmd.extend(["--lora_path", lora_path, "--model_mode", "fine_tuned"])
        
    elif mode == "lora+rag":
        # Combined mode: LoRA with RAG
        print("[MODE] LoRA fine-tuned model with RAG")
        if not lora_path:
            print("ERROR: --lora-path required for lora+rag mode")
            print("Example: ./mondrian.sh --restart --mode=lora+rag --lora-path=./models/qwen3-vl-4b-lora-ansel")
            sys.exit(1)
        if platform.system() == "Linux":
            ai_advisor_cmd.extend(["--adapter", lora_path, "--load_in_4bit"])
        else:
            ai_advisor_cmd.extend(["--lora_path", lora_path, "--model_mode", "fine_tuned"])
        
    elif mode == "ab-test":
        # A/B testing mode: randomly split between base and LoRA
        print("[MODE] A/B testing (base vs LoRA)")
        if not lora_path:
            print("ERROR: --lora-path required for ab-test mode")
            print("Example: ./mondrian.sh --restart --mode=ab-test --lora-path=./models/qwen3-vl-4b-lora-ansel --ab-split=0.5")
            sys.exit(1)
        
        # Get split ratio (default 0.5 = 50/50)
        ab_split = "0.5"
        for arg in sys.argv:
            if arg.startswith("--ab-split="):
                ab_split = arg.split("=", 1)[1]
        
        ai_advisor_cmd.extend([
            "--lora_path", lora_path,
            "--model_mode", "ab_test",
            "--ab_test_split", ab_split
        ])
        print(f"[MODE] A/B split: {float(ab_split)*100:.0f}% LoRA, {(1-float(ab_split))*100:.0f}% base")
        
    else:
        print(f"ERROR: Unknown mode '{mode}'")
        print("Supported modes: base, rag, lora, lora+rag, ab-test")
        sys.exit(1)
    
    services.append(ai_advisor_cmd)
    return services


SERVICE_SCRIPTS = ["job_service_v2.3.py", "ai_advisor_service.py"]


def port_in_use(port):
    """Check if a port is currently bound."""
    import psutil
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == port and conn.status == 'LISTEN':
                return True
    except (psutil.AccessDenied, PermissionError):
        # Fallback to lsof if psutil has permission issues
        try:
            import subprocess
            result = subprocess.run(['lsof', '-i', f':{port}'],
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            pass
    return False


def kill_process_on_port(port):
    """Terminate process using a specific port."""
    import psutil
    import subprocess
    killed = False

    # Try psutil first
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    print(f"Killing process on port {port} (PID {conn.pid})...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        print(f"Force killing process on port {port} (PID {conn.pid})...")
                        proc.kill()
                    killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    print(f"Error killing process on port {port}: {e}")
    except (psutil.AccessDenied, PermissionError):
        # Fallback to lsof + kill with better signal handling
        try:
            result = subprocess.run(['lsof', '-t', '-i', f':{port}'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                pids_str = result.stdout.strip()
                # Handle multiple PIDs separated by newlines
                if pids_str:
                    pids = pids_str.split('\n')
                    for pid_str in pids:
                        pid_str = pid_str.strip()
                        if not pid_str:
                            continue
                        try:
                            pid = int(pid_str)
                            print(f"Killing process on port {port} (PID {pid})...")
                            # Use subprocess to send kill signal - more reliable
                            try:
                                subprocess.run(['kill', '-TERM', str(pid)], timeout=3, capture_output=True)
                                time.sleep(2)
                                # Check if still alive using subprocess
                                result = subprocess.run(['kill', '-0', str(pid)], capture_output=True)
                                if result.returncode == 0:
                                    print(f"Force killing process on port {port} (PID {pid})...")
                                    subprocess.run(['kill', '-9', str(pid)], timeout=3, capture_output=True)
                                killed = True
                            except subprocess.TimeoutExpired:
                                print(f"Timeout while killing process {pid}")
                            except Exception as e:
                                print(f"Error killing process {pid} via subprocess: {e}")
                        except ValueError:
                            print(f"Invalid PID format: '{pid_str}'")
        except subprocess.TimeoutExpired:
            print(f"Timeout while running lsof for port {port}")
        except Exception as e:
            print(f"Error using lsof to kill port {port}: {e}")

    return killed


def wait_for_port_free(port, max_wait=10):
    """Wait until port is available."""
    import psutil
    for i in range(max_wait):
        if not port_in_use(port):
            return True
        if i == 0:
            print(f"Waiting for port {port} to become available...")
        time.sleep(1)
    return False


def stop_services():
    """Find and kill running Mondrian service processes by script name and port."""
    global _in_cleanup
    _in_cleanup = True  # Set flag to ignore SIGTERM during cleanup
    
    import psutil
    killed = 0
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if not cmdline:
                    continue
                for script in SERVICE_SCRIPTS:
                    if any(script in arg for arg in cmdline):
                        print(f"Stopping {script} (PID {proc.pid})...")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            print(f"Force killing {script} (PID {proc.pid})...")
                            proc.kill()
                        killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if killed == 0:
            print("No Mondrian service processes found to stop.")
        else:
            print(f"Stopped {killed} Mondrian service process(es).")

        # Port-based cleanup as fallback
        service_ports = [5006, 5005, 5100]
        for port in service_ports:
            if port_in_use(port):
                print(f"Port {port} still in use, attempting port-based cleanup...")
                kill_process_on_port(port)

        # Verify ports are freed
        all_freed = True
        for port in service_ports:
            if not wait_for_port_free(port, max_wait=10):
                print(f"WARNING: Port {port} is still in use after cleanup attempts.")
                all_freed = False

        if all_freed:
            print("All service ports are now free.")
    finally:
        _in_cleanup = False  # Clear flag after cleanup


# Service health monitoring
SERVICE_HEALTH_CONFIG = {
    "summary_service": {
        "port": 5006,
        "health_url": "http://127.0.0.1:5006/health",
        "display_name": "Summary Service"
    },
    "job_service": {
        "port": 5005,
        "health_url": "http://127.0.0.1:5005/health",
        "display_name": "Job Service"
    },
    "ai_advisor": {
        "port": 5100,
        "health_url": "http://127.0.0.1:5100/health",
        "display_name": "AI Advisor"
    }
}


def check_service_health(service_name, config):
    """
    Check if a single service is healthy by querying its health endpoint.
    Returns a dict with status, version, and error info if any.
    """
    health_url = config["health_url"]
    port = config["port"]
    
    # Use longer timeout for AI Advisor (model may be processing)
    # Job Service is fast, but AI Advisor can take time during inference
    timeout = 10 if service_name == "ai_advisor" else 5
    
    try:
        response = requests.get(health_url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return {
                "status": data.get("status", "UP"),
                "version": data.get("version", "unknown"),
                "healthy": data.get("status") == "UP",
                "raw_data": data
            }
        else:
            return {
                "status": "DOWN",
                "error": f"HTTP {response.status_code}",
                "healthy": False
            }
    except requests.exceptions.Timeout:
        return {
            "status": "TIMEOUT",
            "error": "Connection timeout",
            "healthy": False
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "DOWN",
            "error": "Connection refused",
            "healthy": False
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "healthy": False
        }


def check_all_services_health():
    """
    Check health of all services and return results.
    Returns a dict with each service's health status.
    """
    results = {}
    for service_name, config in SERVICE_HEALTH_CONFIG.items():
        results[service_name] = check_service_health(service_name, config)
    return results


def format_health_display(results):
    """
    Format health check results for display.
    Returns formatted string.
    """
    output = []
    for service_name, config in SERVICE_HEALTH_CONFIG.items():
        health_info = results[service_name]
        status = health_info["status"]
        port = config["port"]
        display_name = config["display_name"]
        
        # Determine symbol and color
        if health_info["healthy"]:
            symbol = "✓"
            status_str = f"{symbol} {status}"
        else:
            symbol = "✗"
            status_str = f"{symbol} {status}"
        
        # Add version info if available
        version_info = ""
        if health_info.get("version"):
            version_info = f" - {health_info['version']}"
        elif health_info.get("error"):
            version_info = f" - {health_info['error']}"
        
        output.append(f"  {status_str} {display_name} ({port}){version_info}")
    
    return "\n".join(output)


def get_job_queue_status():
    """Get current job queue status from database"""
    try:
        try:
            from mondrian.config import DATABASE_PATH
        except ImportError:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            DATABASE_PATH = os.path.join(project_root, "mondrian", "mondrian.db")
        
        conn = sqlite3.connect(DATABASE_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get job counts by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM jobs 
            GROUP BY status
        """)
        
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        # Get active jobs details
        cursor.execute("""
            SELECT id, filename, status, current_step, current_advisor, total_advisors, mode
            FROM jobs 
            WHERE status NOT IN ('done', 'error')
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        active_jobs = cursor.fetchall()
        conn.close()
        
        return status_counts, active_jobs
    
    except Exception as e:
        return {}, []


def format_job_queue_display(status_counts, active_jobs):
    """Format job queue status for display"""
    output = []
    
    # Queue summary - show breakdown of all statuses
    total = sum(status_counts.values())
    pending = status_counts.get("pending", 0)
    queued = status_counts.get("queued", 0)
    processing = status_counts.get("processing", 0)
    analyzing = status_counts.get("analyzing", 0)
    done = status_counts.get("done", 0)
    error = status_counts.get("error", 0)
    
    output.append(f"  Queue: {total} total | {pending} pending | {queued} queued | {processing} processing | {analyzing} analyzing | {done} done | {error} error")
    
    # Show active jobs
    if active_jobs:
        output.append("  Active jobs:")
        for job in active_jobs[:3]:  # Show top 3
            job_uuid = job["id"].split(' (')[0] if ' (' in job["id"] else job["id"]
            mode_str = f" [{job['mode']}]" if job["mode"] else ""
            advisor_progress = ""
            if job["total_advisors"] and job["total_advisors"] > 0:
                advisor_progress = f" ({job['current_advisor']}/{job['total_advisors']})"
            
            output.append(f"    • {job_uuid[:8]}... ({job['status']}) {job['filename']}{mode_str}{advisor_progress}")
            if job["current_step"]:
                output.append(f"      Step: {job['current_step']}")
    
    return "\n".join(output)


def monitor_services(duration=None, interval=5):
    """
    Continuously monitor services and display their health status + job queue.
    
    Args:
        duration: How long to monitor in seconds (None = indefinite)
        interval: How often to check health in seconds
    """
    print("\nMonitoring services & jobs (Ctrl+C to exit)...")
    print("=" * 60)
    
    start_time = time.time()
    try:
        first_iteration = True
        while True:
            if duration and (time.time() - start_time) > duration:
                break
            
            results = check_all_services_health()
            status_counts, active_jobs = get_job_queue_status()
            
            # Calculate lines needed for clearing (service health + jobs + summary)
            lines_to_clear = 8  # Adjust based on content
            
            # Clear screen and show status
            if not first_iteration:
                # Move cursor up to overwrite previous output
                print(f"\033[{lines_to_clear}A", end="", flush=True)
                print("\033[J", end="", flush=True)   # Clear from cursor to end of screen
            
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Service Health Status:")
            print(format_health_display(results))
            
            # Check if all services are healthy
            all_healthy = all(info["healthy"] for info in results.values())
            if all_healthy:
                print("✓ All services healthy")
            else:
                unhealthy = [name for name, info in results.items() if not info["healthy"]]
                print(f"✗ Unhealthy services: {', '.join(unhealthy)}")
            
            # Show job queue status
            print("\nJob Queue Status:")
            print(format_job_queue_display(status_counts, active_jobs))
            
            first_iteration = False
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        return True


def verify_services_on_startup(max_wait=120, check_interval=2):
    """
    Verify that all services are healthy on startup.
    For AI Advisor, poll /model-status to show loading progress.
    Returns True if all services are healthy, False otherwise.
    """
    print("\nVerifying service health...")
    start_time = time.time()

    ai_model_ready = False
    job_service_ready = False
    last_ai_message = ""

    while time.time() - start_time < max_wait:
        elapsed = int(time.time() - start_time)

        # Check Job Service health
        if not job_service_ready:
            job_health = check_service_health("job_service", SERVICE_HEALTH_CONFIG["job_service"])
            job_service_ready = job_health.get("healthy", False)
            if job_service_ready:
                print(f"[{elapsed}s] ✓ Job Service is ready")

        # Check AI Advisor model loading status
        if not ai_model_ready:
            try:
                response = requests.get("http://127.0.0.1:5100/model-status", timeout=10)
                if response.status_code == 200:
                    status = response.json()
                    progress = status.get("progress", 0)
                    message = status.get("message", "Loading...")
                    stage = status.get("status", "unknown")

                    # Only print if message changed (reduce spam)
                    status_line = f"[{elapsed}s] AI Advisor: {stage} - {message} ({progress}%)"
                    if status_line != last_ai_message:
                        print(status_line)
                        last_ai_message = status_line

                    if stage == "ready":
                        ai_model_ready = True
                        print(f"[{elapsed}s] ✓ AI Advisor is ready")
                    elif stage == "error":
                        print(f"\n✗ Model loading failed: {message}")
                        return False
                else:
                    if last_ai_message != "starting":
                        print(f"[{elapsed}s] AI Advisor: Starting... (waiting for response)")
                        last_ai_message = "starting"
            except requests.exceptions.RequestException:
                if last_ai_message != "connecting":
                    print(f"[{elapsed}s] AI Advisor: Starting Flask server...")
                    last_ai_message = "connecting"

        # Check if both ready
        if ai_model_ready and job_service_ready:
            print("\n" + "=" * 60)
            print("✓ All services are healthy!")
            print("=" * 60)
            # Final health check display
            results = check_all_services_health()
            print(format_health_display(results))

            # Check GPU status for AI Advisor
            if "ai_advisor" in results and results["ai_advisor"].get("healthy"):
                ai_data = results["ai_advisor"].get("raw_data", {})
                device = ai_data.get("device", "unknown")
                using_gpu = ai_data.get("using_gpu", False)

                if not using_gpu and device == "Device(cpu, 0)":
                    print(f"\n{'=' * 60}")
                    print(f"WARNING: AI Advisor running in CPU mode (slow performance)")
                    print(f"Device: {device}")
                    print(f"Check environment variables and GPU availability")
                    print(f"{'=' * 60}")
                elif using_gpu:
                    print(f"\n✓ GPU acceleration active: {device}")

            return True

        time.sleep(check_interval)

    print(f"\n✗ Services did not become ready within {max_wait} seconds")
    print("Final status:")
    results = check_all_services_health()
    print(format_health_display(results))
    return False


def show_active_jobs():
    """Show active jobs from the database"""
    try:
        # Try to import from mondrian config, fallback to direct path
        try:
            from mondrian.config import DATABASE_PATH
        except ImportError:
            # Fallback: use default database path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            DATABASE_PATH = os.path.join(project_root, "mondrian", "mondrian.db")
        
        conn = sqlite3.connect(DATABASE_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get active jobs (not done or error)
        cursor.execute("""
            SELECT id, filename, advisor, status, current_step, current_advisor, total_advisors, mode
            FROM jobs 
            WHERE status NOT IN ('done', 'error', 'pending')
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        jobs = cursor.fetchall()
        conn.close()
        
        if not jobs:
            print("  No active jobs")
            return
        
        print(f"  Active jobs ({len(jobs)}):")
        for job in jobs:
            # Extract UUID from job_id (may have mode suffix)
            job_uuid = job["id"].split(' (')[0] if ' (' in job["id"] else job["id"]
            mode_str = f" [{job['mode']}]" if job["mode"] else ""
            advisor_progress = ""
            if job["total_advisors"] and job["total_advisors"] > 0:
                advisor_progress = f" ({job['current_advisor']}/{job['total_advisors']})"
            
            print(f"    - {job_uuid[:8]}... ({job['status']}) {job['filename']}{mode_str}{advisor_progress}")
            if job["current_step"]:
                print(f"      Step: {job['current_step']}")
    
    except Exception as e:
        print(f"  Could not fetch active jobs: {e}")


def cleanup_stale_jobs_on_restart():
    """
    Clean up stale jobs from previous runs immediately on restart.
    This marks jobs that are in an intermediate state ('pending', 'started', 'processing', 
    'analyzing', 'finalizing') as errors, since their processing services were killed.
    """
    try:
        try:
            from mondrian.config import DATABASE_PATH
        except ImportError:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            DATABASE_PATH = os.path.join(project_root, "mondrian", "mondrian.db")
        
        if not os.path.exists(DATABASE_PATH):
            return  # Database doesn't exist yet, nothing to clean
        
        conn = sqlite3.connect(DATABASE_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find jobs in intermediate states (they were killed when we stopped services)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE status IN ('pending', 'started', 'processing', 'analyzing', 'finalizing', 'queued')
        """)
        
        result = cursor.fetchone()
        stale_count = result['count'] if result else 0
        
        if stale_count > 0:
            print(f"\nCleaning up {stale_count} stale job(s) from previous run...")
            
            # Mark them as error
            cursor.execute("""
                UPDATE jobs
                SET status = 'error',
                    current_step = 'Cancelled - services restarted',
                    completed_at = CURRENT_TIMESTAMP,
                    last_activity = CURRENT_TIMESTAMP
                WHERE status IN ('pending', 'started', 'processing', 'analyzing', 'finalizing', 'queued')
            """)
            
            conn.commit()
            print(f"✓ Marked {stale_count} stale job(s) as error")
        
        conn.close()
    
    except Exception as e:
        print(f"  Warning: Could not cleanup stale jobs: {e}")


def main():
    # Parse mode argument
    mode = "lora"  # Default mode (using LoRA adapter for best performance)
    lora_path = "./adapters/ansel_qwen3_4b_10ep"  # Default LoRA adapter trained on Qwen3-VL-4B
    model_arg = None
    all_services = False
    
    for arg in sys.argv:
        if arg.startswith("--mode="):
            mode = arg.split("=", 1)[1]
        elif arg.startswith("--lora-path="):
            lora_path = arg.split("=", 1)[1]
        elif arg.startswith("--model="):
            model_arg = arg.split("=", 1)[1]
        elif arg == "--all-services" or arg == "--full":
            all_services = True
    
    # Show usage if --help
    if '--help' in sys.argv or '-h' in sys.argv:
        print("""
Mondrian Services Launcher

Usage:
    ./mondrian.sh [options]

Options:
    --stop              Stop all services
    --restart           Restart all services
    --status            Show active jobs
    --mode=<mode>       Set service mode (default: lora)
    --lora-path=<path>  Path to LoRA adapter (default: ./adapters/ansel_qwen3_4b_10ep)
    --model=<model>     Base model to use (default: Qwen/Qwen3-VL-4B-Instruct)
    --ab-split=<ratio>  A/B test split ratio (default: 0.5)
    --help, -h          Show this help

Modes:
    base                Base model only
    rag                 Base model with RAG enabled
    lora                LoRA fine-tuned model (DEFAULT)
    lora+rag            LoRA model with RAG enabled
    ab-test             A/B testing (base vs LoRA)

Examples:
    # Start with default (Qwen3-VL-4B + LoRA ansel_qwen3_4b_10ep)
    ./mondrian.sh --restart

    # Start with base model (no LoRA)
    ./mondrian.sh --restart --mode=base

    # Use LoRA with custom adapter
    ./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel_qwen3_4b_10ep

    # A/B test: 70% LoRA, 30% base
    ./mondrian.sh --restart --mode=ab-test --ab-split=0.7

    # RAG mode with default LoRA
    ./mondrian.sh --restart --mode=lora+rag

    # Check active jobs
    ./mondrian.sh --status

    # Stop all services
    ./mondrian.sh --stop
""")
        return
    
    if '--status' in sys.argv:
        print("Active jobs (10):")
        show_active_jobs()
        return
    
    if '--stop' in sys.argv:
        try:
            import psutil
        except ImportError:
            print("psutil is required for stopping services. Please install with 'pip install psutil'.")
            sys.exit(1)
        stop_services()
        return
    
    if '--restart' in sys.argv:
        try:
            import psutil
        except ImportError:
            print("psutil is required for restarting services. Please install with 'pip install psutil'.")
            sys.exit(1)
        print("=" * 60)
        print(f"Restarting Mondrian services in {mode.upper()} mode...")
        print("=" * 60)
        stop_services()
        print("Waiting for processes to terminate...")
        time.sleep(3)
        
        # Clean up stale jobs from the previous run
        cleanup_stale_jobs_on_restart()

        # Verify ports are free before starting
        service_ports = [5006, 5005, 5100]
        ports_free = True
        for port in service_ports:
            if port_in_use(port):
                print(f"ERROR: Port {port} is still in use. Cannot restart services.")
                ports_free = False

        if not ports_free:
            print("Please manually kill processes using the required ports and try again.")
            print("Use: lsof -i :5100 and lsof -i :5005 to find processes.")
            sys.exit(1)

        print("All ports are free. Starting services...")
        # Continue to start services below
    
    # Determine working directory
    # If we're in scripts/, run services from project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) == 'scripts':
        working_dir = os.path.dirname(script_dir)  # Project root
    else:
        working_dir = script_dir

    # Set PYTHONPATH to include project root so 'mondrian' package can be imported
    env = os.environ.copy()

    # CRITICAL: Remove environment variables that force CPU mode
    # These variables can override GPU settings and cause slow performance
    cpu_forcing_vars = ['MLX_USE_CPU', 'PYTORCH_ENABLE_MPS_FALLBACK', 'CUDA_VISIBLE_DEVICES']
    removed_vars = []
    for var in cpu_forcing_vars:
        if var in env:
            removed_vars.append(f"{var}={env[var]}")
            env.pop(var)

    if removed_vars:
        print(f"\n{'=' * 60}")
        print(f"WARNING: Removed CPU-forcing environment variables:")
        for var_setting in removed_vars:
            print(f"  - {var_setting}")
        print(f"These may be set in your shell profile (.zshrc, .bashrc)")
        print(f"GPU acceleration will now be enabled")
        print(f"{'=' * 60}\n")

    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{working_dir}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = working_dir

    # Set ANALYSIS_MODE environment variable based on the selected mode
    # This tells the AI Advisor service what mode to operate in
    # Supported modes: base, rag, lora, rag_lora (internally used)
    mode_to_analysis = {
        "base": "baseline",      # Base model only
        "rag": "rag",           # Base model with RAG
        "lora": "lora",         # Fine-tuned model only
        "lora+rag": "rag_lora", # Fine-tuned model with RAG
        "ab-test": "baseline",  # A/B testing uses baseline as default
    }
    env['ANALYSIS_MODE'] = mode_to_analysis.get(mode, "baseline")
    print(f"[ENV] ANALYSIS_MODE set to: {env['ANALYSIS_MODE']}")

    # Get services for the selected mode
    services = get_services_for_mode(mode, lora_path, model_arg)
    
    print("\n" + "=" * 60)
    print(f"Starting Mondrian services in {mode.upper()} mode")
    print("=" * 60)

    # Create log directory if doesn't exist
    log_dir = os.path.join(working_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    processes = []
    for cmd in services:
        service_name = os.path.basename(cmd[1]).replace('.py', '')
        log_file = os.path.join(log_dir, f"{service_name}_{int(time.time())}.log")

        print(f"\nStarting: {' '.join(cmd)}")
        print(f"  Logging to: {log_file}")

        with open(log_file, 'w') as log_f:
            proc = subprocess.Popen(
                cmd,
                cwd=working_dir,
                env=env,
                stdout=log_f,
                stderr=subprocess.STDOUT  # Merge stderr into stdout
            )
        processes.append((proc, log_file))
        print(f"✓ Started {service_name} (PID: {proc.pid})")
        time.sleep(1)  # Brief delay between service starts

    print("\n" + "=" * 60)
    print(f"All services started successfully in {mode.upper()} mode")
    print("=" * 60)

    # Check if any processes died immediately
    print("\nChecking process health...")
    time.sleep(2)  # Give processes a moment to potentially crash
    dead_processes = []
    for proc, log_file in processes:
        poll_result = proc.poll()
        if poll_result is not None:
            # Process has terminated
            service_name = os.path.basename(log_file).replace(f"_{int(time.time())}.log", "")
            dead_processes.append((service_name, log_file, poll_result))

    if dead_processes:
        print(f"\n{'=' * 60}")
        print("ERROR: Some services died immediately after startup!")
        print(f"{'=' * 60}")
        for service_name, log_file, exit_code in dead_processes:
            print(f"\n[{service_name}] exited with code {exit_code}")
            print(f"Log file: {log_file}")
            print("\nLast 50 lines of log:")
            print("-" * 60)
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:
                        print(line, end='')
            except Exception as e:
                print(f"Could not read log file: {e}")
            print("-" * 60)
        sys.exit(1)

    # Verify services are healthy (if restart was used)
    if '--restart' in sys.argv:
        print("\nWaiting for services to initialize...")
        time.sleep(3)  # Brief initial wait for processes to start
        if not verify_services_on_startup(max_wait=60, check_interval=2):
            print("\nWARNING: Some services may not be fully initialized yet.")
            print("Services should be running in the background.")
            sys.exit(1)
        else:
            # Show active jobs
            print("\nDatabase status:")
            show_active_jobs()
            
            # Check if we should enter monitoring mode
            # If --no-monitor is specified, exit cleanly (for automated testing)
            # Otherwise, start continuous monitoring
            if '--no-monitor' in sys.argv:
                print("\nServices started successfully. Exiting to allow tests to proceed.")
                sys.exit(0)
            else:
                print("\nStarting health monitoring (Ctrl+C to stop)...")
                try:
                    monitor_services(duration=None, interval=5)
                except KeyboardInterrupt:
                    print("\n\nHealth monitoring stopped.")
                    sys.exit(0)
    else:
        print("\nServices are running in the background.")
        print(f"\nTo compare modes, restart with different --mode:")
        print(f"  ./mondrian.sh --restart --mode=base")
        print(f"  ./mondrian.sh --restart --mode=rag")
        if lora_path:
            print(f"  ./mondrian.sh --restart --mode=lora --lora-path={lora_path}")
        print(f"\nTo stop services:")
        print(f"  ./mondrian.sh --stop")

if __name__ == "__main__":
    main()
