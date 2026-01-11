#!/usr/bin/env python3
"""
Minimal start_services.py for Mondrian project
Launches all core services in the correct order.
"""

import subprocess
import os
import sys
import signal
import time


SERVICES = [
    [sys.executable, "job_service_v2.3.py", "--port", "5005"],
    [sys.executable, "ai_advisor_service.py", "--port", "5100"],
    # Add other services here as needed
]

SERVICE_SCRIPTS = ["job_service_v2.3.py", "ai_advisor_service.py"]


def stop_services():
    """Find and kill running Mondrian service processes by script name."""
    import psutil
    killed = 0
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

def main():
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
        print("Restarting Mondrian services...")
        stop_services()
        print("Waiting for processes to terminate...")
        time.sleep(2)
        print("Starting services...")
        # Continue to start services below
    
    # Determine working directory
    # If we're in scripts/, run services from parent mondrian/ directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(script_dir) == 'scripts':
        working_dir = os.path.join(os.path.dirname(script_dir), 'mondrian')
    else:
        working_dir = script_dir
    
    processes = []
    for cmd in SERVICES:
        print(f"Starting: {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, cwd=working_dir)
        processes.append(proc)
    for proc in processes:
        proc.wait()

if __name__ == "__main__":
    main()
