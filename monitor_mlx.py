#!/usr/bin/env python3
"""
MLX Model Monitoring Script for Qwen3-VL-4B

This script monitors the AI Advisor Service running the MLX model:
- Service health and uptime
- Memory usage of the Python process
- GPU/Metal memory usage (if available)
- Request latency
- Model performance metrics
- Real-time log tailing
"""

import sys
import os
import time
import psutil
import requests
import subprocess
from datetime import datetime

# Configuration
SERVICE_URL = "http://localhost:5100"
LOG_FILE = "/Users/shaydu/dev/mondrian-macos/mondrian/logs/ai_advisor_out.log"
SERVICE_PORT = 5100

def format_bytes(bytes_val):
    """Format bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"

def get_service_pid():
    """Find the PID of the service running on port 5100"""
    try:
        result = subprocess.run(
            ['lsof', '-i', f':{SERVICE_PORT}', '-t'],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            return int(result.stdout.strip().split('\n')[0])
    except Exception as e:
        print(f"Error finding service PID: {e}")
    return None

def get_process_info(pid):
    """Get detailed process information"""
    try:
        process = psutil.Process(pid)

        # Memory info
        mem_info = process.memory_info()
        mem_percent = process.memory_percent()

        # CPU info
        cpu_percent = process.cpu_percent(interval=0.1)

        # Process details
        create_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - create_time

        return {
            'pid': pid,
            'name': process.name(),
            'status': process.status(),
            'cpu_percent': cpu_percent,
            'memory_rss': mem_info.rss,
            'memory_vms': mem_info.vms,
            'memory_percent': mem_percent,
            'num_threads': process.num_threads(),
            'create_time': create_time,
            'uptime': uptime,
        }
    except psutil.NoSuchProcess:
        return None
    except Exception as e:
        print(f"Error getting process info: {e}")
        return None

def get_metal_memory():
    """Get Metal GPU memory usage (macOS specific)"""
    try:
        # Try to get GPU memory using system_profiler
        result = subprocess.run(
            ['system_profiler', 'SPDisplaysDataType'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse VRAM info (this is approximate)
        output = result.stdout
        if 'VRAM' in output or 'Metal' in output:
            for line in output.split('\n'):
                if 'VRAM' in line or 'Chipset Model' in line:
                    print(f"  {line.strip()}")

        # Alternative: Try to use Metal performance stats
        # Note: This requires additional tools or frameworks

    except Exception as e:
        print(f"  (Unable to get GPU memory: {e})")

def check_service_health():
    """Check if the service is responding"""
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Service health check failed: {e}")
        return None

def test_inference_latency(image_path=None):
    """Test model inference latency"""
    if not image_path or not os.path.exists(image_path):
        print("\n  No test image provided for latency test")
        print(f"  Usage: python3 monitor_mlx.py --test-image /path/to/image.jpg")
        return None

    print(f"\n🧪 Testing inference latency with: {image_path}")

    try:
        start = time.time()

        with open(image_path, 'rb') as f:
            response = requests.post(
                f"{SERVICE_URL}/analyze",
                files={'image': f},
                data={
                    'advisor': 'default',
                    'job_id': f'monitor_test_{int(time.time())}'
                },
                timeout=120
            )

        elapsed = time.time() - start

        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Request completed in {elapsed:.2f}s")
            print(f"  Response length: {len(result.get('analysis', ''))} chars")
            return elapsed
        else:
            print(f"  ❌ Request failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"  ❌ Inference test failed: {e}")
        return None

def tail_logs(num_lines=20):
    """Show recent log entries"""
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            recent = lines[-num_lines:] if len(lines) > num_lines else lines

            print(f"\n📋 Recent logs (last {len(recent)} lines):")
            print("─" * 80)
            for line in recent:
                print(f"  {line.rstrip()}")
            print("─" * 80)
    except Exception as e:
        print(f"Error reading logs: {e}")

def monitor_continuous():
    """Continuous monitoring mode"""
    print("Starting continuous monitoring (Press Ctrl+C to stop)...")
    print("")

    try:
        while True:
            os.system('clear')
            print_status(test_image=None)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")

def print_status(test_image=None):
    """Print current status"""
    print("=" * 80)
    print("MLX Model Monitoring - Qwen3-VL-4B")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Service health
    print("\n🏥 Service Health:")
    health = check_service_health()
    if health:
        print(f"  ✅ Status: {health.get('status', 'UNKNOWN')}")
        print(f"  Model: {health.get('model', 'Unknown')}")
        print(f"  Script: {health.get('script', 'Unknown')}")
        print(f"  DB Path: {health.get('db_path', 'Unknown')}")
    else:
        print(f"  ❌ Service not responding on {SERVICE_URL}")
        return

    # Process info
    print("\n💻 Process Information:")
    pid = get_service_pid()
    if pid:
        info = get_process_info(pid)
        if info:
            print(f"  PID: {info['pid']}")
            print(f"  Status: {info['status']}")
            print(f"  Uptime: {str(info['uptime']).split('.')[0]}")
            print(f"  CPU Usage: {info['cpu_percent']:.1f}%")
            print(f"  Memory (RSS): {format_bytes(info['memory_rss'])} ({info['memory_percent']:.1f}%)")
            print(f"  Memory (VMS): {format_bytes(info['memory_vms'])}")
            print(f"  Threads: {info['num_threads']}")
    else:
        print(f"  ⚠️  Unable to find process on port {SERVICE_PORT}")

    # System memory
    print("\n🖥️  System Memory:")
    mem = psutil.virtual_memory()
    print(f"  Total: {format_bytes(mem.total)}")
    print(f"  Available: {format_bytes(mem.available)}")
    print(f"  Used: {format_bytes(mem.used)} ({mem.percent}%)")

    # GPU/Metal info
    print("\n🎮 GPU/Metal Information:")
    get_metal_memory()

    # Test latency if image provided
    if test_image:
        test_inference_latency(test_image)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor MLX Model Service")
    parser.add_argument('--test-image', type=str, help='Path to test image for latency testing')
    parser.add_argument('--logs', action='store_true', help='Show recent logs')
    parser.add_argument('--continuous', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--tail', type=int, default=20, help='Number of log lines to show (default: 20)')

    args = parser.parse_args()

    if args.continuous:
        monitor_continuous()
    else:
        print_status(test_image=args.test_image)

        if args.logs:
            tail_logs(args.tail)

        print("\n💡 Monitoring Options:")
        print("  • Continuous monitoring: python3 monitor_mlx.py --continuous")
        print("  • Test latency: python3 monitor_mlx.py --test-image /path/to/image.jpg")
        print("  • View logs: python3 monitor_mlx.py --logs")
        print("  • Tail more logs: python3 monitor_mlx.py --logs --tail 50")
