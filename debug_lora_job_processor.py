#!/usr/bin/env python3
"""
Debug Tool for LoRA Job Processing Issues

This tool helps diagnose why LoRA jobs hang and never return.
Use this to trace the entire job pipeline and identify bottlenecks.
"""

import sqlite3
import requests
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
AI_ADVISOR_URL = "http://localhost:5100"
DB_PATH = "mondrian.db"

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")

def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}▶ {text}{Colors.RESET}")
    print(f"{Colors.BLUE}{'-'*70}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.WHITE}ℹ {text}{Colors.RESET}")

def check_service_health():
    """Check if both services are running"""
    print_section("SERVICE HEALTH CHECK")
    
    services = {
        "Job Service": (JOB_SERVICE_URL, "/health"),
        "AI Advisor": (AI_ADVISOR_URL, "/health")
    }
    
    all_healthy = True
    for service_name, (url, endpoint) in services.items():
        try:
            response = requests.get(f"{url}{endpoint}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "UNKNOWN")
                print_success(f"{service_name}: {url} - Status: {status}")
            else:
                print_error(f"{service_name}: {url} - HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            print_error(f"{service_name}: {url} - {str(e)}")
            all_healthy = False
    
    return all_healthy

def get_queue_status() -> Optional[Dict]:
    """Get current job queue status"""
    print_section("QUEUE STATUS")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get counts by status
        statuses = ['pending', 'queued', 'analyzing', 'processing', 'completed', 'failed']
        counts = {}
        
        for status in statuses:
            cursor.execute(f"SELECT COUNT(*) as count FROM jobs WHERE status = ?", (status,))
            counts[status] = cursor.fetchone()['count']
        
        total = sum(counts.values())
        
        print_info(f"Total jobs: {total}")
        for status, count in counts.items():
            if count > 0:
                print_info(f"  {status.upper():15s}: {count}")
        
        return counts
    except Exception as e:
        print_error(f"Failed to get queue status: {e}")
        return None

def get_stuck_jobs() -> List[Dict]:
    """Find jobs that appear to be stuck"""
    print_section("STUCK JOBS ANALYSIS")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Find jobs stuck in analyzing/processing for more than 5 minutes
        cursor.execute("""
            SELECT id, advisor, mode, status, current_step, created_at, last_activity
            FROM jobs
            WHERE status IN ('analyzing', 'processing', 'queued')
            ORDER BY last_activity ASC
        """)
        
        stuck_jobs = []
        for row in cursor.fetchall():
            job_dict = dict(row)
            
            # Parse timestamps
            last_activity = datetime.fromisoformat(job_dict['last_activity'])
            elapsed = (datetime.now() - last_activity).total_seconds()
            
            # Consider stuck if no activity for >5 minutes
            if elapsed > 300:
                stuck_jobs.append({
                    **job_dict,
                    'elapsed_seconds': elapsed
                })
                print_warning(f"JOB STUCK: {job_dict['id'][:8]}...")
                print_info(f"  Status: {job_dict['status']}")
                print_info(f"  Step: {job_dict['current_step']}")
                print_info(f"  Elapsed: {elapsed/60:.1f} minutes")
                print_info(f"  Mode: {job_dict['mode']}")
        
        if not stuck_jobs:
            print_success("No stuck jobs detected")
        
        return stuck_jobs
    except Exception as e:
        print_error(f"Failed to analyze stuck jobs: {e}")
        return []

def get_recent_jobs(limit=5) -> List[Dict]:
    """Get recent jobs for analysis"""
    print_section(f"RECENT JOBS (last {limit})")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, advisor, mode, status, current_step, error, created_at, last_activity
            FROM jobs
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        jobs = [dict(row) for row in cursor.fetchall()]
        
        for job in jobs:
            status_icon = "✓" if job['status'] == 'completed' else "✗" if job['status'] == 'failed' else "⟳"
            print_info(f"{status_icon} {job['id'][:8]}... | {job['advisor']:15s} | {job['mode']:10s} | {job['status']:12s}")
            
            if job['error']:
                print_error(f"    Error: {job['error']}")
            if job['current_step']:
                print_info(f"    Step: {job['current_step']}")
        
        return jobs
    except Exception as e:
        print_error(f"Failed to get recent jobs: {e}")
        return []

def test_ai_advisor_direct(test_image: str = "source/mike-shrub.jpg") -> bool:
    """Test AI Advisor service directly"""
    print_section("DIRECT AI ADVISOR TEST")
    
    if not Path(test_image).exists():
        print_error(f"Test image not found: {test_image}")
        return False
    
    print_info(f"Testing with: {test_image}")
    
    try:
        with open(test_image, 'rb') as f:
            print_info("Sending request to AI Advisor...")
            start_time = time.time()
            
            response = requests.post(
                f"{AI_ADVISOR_URL}/analyze",
                files={'image': f},
                data={'advisor': 'ansel', 'mode': 'lora', 'enable_rag': 'false'},
                timeout=60
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print_success(f"Response received in {elapsed:.2f}s")
                
                data = response.json()
                
                # Check response completeness
                required_fields = ['image_description', 'dimensions', 'overall_grade']
                missing_fields = [f for f in required_fields if f not in data]
                
                if missing_fields:
                    print_warning(f"Missing fields: {missing_fields}")
                else:
                    print_success(f"Response complete with all required fields")
                
                # Show sample
                if 'dimensions' in data and isinstance(data['dimensions'], list):
                    print_info(f"  Dimensions returned: {len(data['dimensions'])}")
                
                return True
            else:
                print_error(f"AI Advisor returned {response.status_code}")
                print_error(response.text[:200])
                return False
                
    except requests.Timeout:
        print_error("Request timeout - service may be stuck")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False

def create_test_lora_job(test_image: str = "source/mike-shrub.jpg") -> Optional[str]:
    """Create a test LoRA job and monitor it"""
    print_section("CREATE TEST LORA JOB")
    
    if not Path(test_image).exists():
        print_error(f"Test image not found: {test_image}")
        return None
    
    try:
        # Create job via API
        with open(test_image, 'rb') as f:
            print_info("Creating job...")
            response = requests.post(
                f"{JOB_SERVICE_URL}/jobs",
                files={'image': f},
                data={'advisor': 'ansel', 'mode': 'lora'},
                timeout=10
            )
        
        if response.status_code != 200 and response.status_code != 201:
            print_error(f"Failed to create job: {response.status_code}")
            print_error(response.text[:200])
            return None
        
        data = response.json()
        job_id = data.get('job_id') or data.get('id')
        
        if not job_id:
            print_error("No job_id in response")
            return None
        
        print_success(f"Job created: {job_id}")
        
        # Monitor job
        print_info("Monitoring job (20 seconds)...")
        start_time = time.time()
        last_status = None
        last_step = None
        
        while time.time() - start_time < 20:
            try:
                response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=5)
                if response.status_code == 200:
                    job = response.json()
                    current_status = job.get('status')
                    current_step = job.get('current_step')
                    progress = job.get('progress_percentage', 0)
                    
                    # Log status changes
                    if current_status != last_status:
                        print_info(f"Status: {last_status} → {current_status} ({progress}%)")
                        last_status = current_status
                    
                    # Log step changes
                    if current_step and current_step != last_step:
                        print_info(f"Step: {current_step}")
                        last_step = current_step
                    
                    # Check for completion
                    if current_status in ['completed', 'failed']:
                        elapsed = time.time() - start_time
                        print_success(f"Job finished in {elapsed:.2f}s: {current_status}")
                        
                        if current_status == 'failed':
                            error = job.get('error')
                            if error:
                                print_error(f"Error: {error}")
                        
                        return job_id
                
            except Exception as e:
                print_warning(f"Status check failed: {e}")
            
            time.sleep(2)
        
        print_warning("Job did not complete in 20 seconds - may be stuck")
        return job_id
        
    except Exception as e:
        print_error(f"Job creation failed: {e}")
        return None

def analyze_job_logs(job_id: str):
    """Analyze logs for a specific job"""
    print_section(f"JOB LOGS: {job_id[:8]}...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, advisor, mode, status, created_at, last_activity, 
                   current_step, progress_percentage, error, retry_count
            FROM jobs
            WHERE id = ?
        """, (job_id,))
        
        job = cursor.fetchone()
        
        if not job:
            print_error(f"Job not found: {job_id}")
            return
        
        job_dict = dict(job)
        
        # Timeline
        created = datetime.fromisoformat(job_dict['created_at'])
        last_activity = datetime.fromisoformat(job_dict['last_activity'])
        total_duration = (last_activity - created).total_seconds()
        
        print_info(f"Advisor: {job_dict['advisor']}")
        print_info(f"Mode: {job_dict['mode']}")
        print_info(f"Status: {job_dict['status']}")
        print_info(f"Progress: {job_dict['progress_percentage']}%")
        print_info(f"Current Step: {job_dict['current_step']}")
        print_info(f"Total Duration: {total_duration:.1f}s")
        print_info(f"Retries: {job_dict['retry_count']}")
        
        if job_dict['error']:
            print_error(f"Error: {job_dict['error']}")
    
    except Exception as e:
        print_error(f"Log analysis failed: {e}")

def main():
    """Run all diagnostics"""
    print_header("LORA JOB PROCESSING DEBUGGER")
    
    # Check services
    if not check_service_health():
        print_error("\nServices are not healthy. Please start them first:")
        print_info("  python3 mondrian/job_service_v2.3.py --port 5005 --db mondrian.db")
        print_info("  python3 mondrian/start_services.py --mode=lora")
        return
    
    # Get queue status
    queue_status = get_queue_status()
    
    # Check for stuck jobs
    stuck_jobs = get_stuck_jobs()
    
    # Show recent jobs
    recent_jobs = get_recent_jobs(5)
    
    # Test AI Advisor directly
    print_section("DIRECT SERVICE TEST")
    print_info("Testing if AI Advisor responds to requests...")
    ai_advisor_works = test_ai_advisor_direct()
    
    if not ai_advisor_works:
        print_error("\nAI Advisor is not responding correctly!")
        print_warning("This is likely why jobs are hanging.")
        print_info("Steps to fix:")
        print_info("  1. Check AI Advisor logs: tail -50 logs/ai_advisor_service_*.log")
        print_info("  2. Check if model is still loading")
        print_info("  3. Try restarting: python3 mondrian/start_services.py --mode=lora")
        return
    
    # Create test job if queue is not full
    if queue_status and queue_status.get('analyzing', 0) == 0 and queue_status.get('processing', 0) == 0:
        test_job_id = create_test_lora_job()
        
        if test_job_id:
            print_info("\nAnalyzing test job...")
            analyze_job_logs(test_job_id)
    
    # Final recommendations
    print_header("RECOMMENDATIONS")
    
    if stuck_jobs:
        print_warning("HUNG JOBS DETECTED!")
        print_info("Likely causes:")
        print_info("  1. AI Advisor service crashed or hung (check: ps aux | grep ai_advisor)")
        print_info("  2. Request timeout to AI Advisor (check: tail logs/ai_advisor_service_*.log)")
        print_info("  3. GPU memory exhausted (check: nvidia-smi or mlx_gpu_utils)")
        print_info("  4. LoRA adapter loading issue (check: logs for adapter load failures)")
        
        print_info("\nQuick fixes:")
        print_info("  1. Kill hung processes: pkill -f 'ai_advisor_service|job_service'")
        print_info("  2. Clear any stuck jobs: python3 clear_jobs.py")
        print_info("  3. Restart services: python3 mondrian/start_services.py --mode=lora")
    else:
        print_success("No obvious issues detected!")
    
    print_info("\nFor more details:")
    print_info("  • Check job logs: sqlite3 mondrian.db \"SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1;\"")
    print_info("  • Monitor real-time: watch -n 1 'sqlite3 mondrian.db \"SELECT status, COUNT(*) FROM jobs GROUP BY status;\"'")
    print_info("  • Check service logs: tail -f logs/ai_advisor_service_*.log logs/job_service_*.log")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\n\nInterrupted by user")
        sys.exit(0)
