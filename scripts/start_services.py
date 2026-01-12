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
        # Fallback to lsof + kill
        try:
            result = subprocess.run(['lsof', '-t', '-i', f':{port}'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        pid = int(pid)
                        print(f"Killing process on port {port} (PID {pid})...")
                        import os
                        os.kill(pid, signal.SIGTERM)
                        time.sleep(2)
                        # Check if still alive, force kill if needed
                        try:
                            os.kill(pid, 0)  # Check if process exists
                            print(f"Force killing process on port {port} (PID {pid})...")
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            pass  # Process already dead
                        killed = True
                    except (ValueError, OSError) as e:
                        print(f"Error killing process {pid}: {e}")
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

    # Port-based cleanup as fallback
    service_ports = [5005, 5100]
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
        time.sleep(3)

        # Verify ports are free before starting
        service_ports = [5005, 5100]
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
        print(f"Started {cmd[1]} (PID: {proc.pid})")

    print("\nAll services started successfully.")
    print("Services are running in the background.")

if __name__ == "__main__":
    main()
