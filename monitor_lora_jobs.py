#!/usr/bin/env python3
"""
Real-time Job Monitor for LoRA Processing

Continuously monitors job queue and service health in real-time.
Shows where jobs are getting stuck and why.
"""

import sqlite3
import requests
import sys
import time
import os
from datetime import datetime
from typing import Dict, List
from pathlib import Path

DB_PATH = "mondrian.db"
JOB_SERVICE_URL = "http://localhost:5005"
AI_ADVISOR_URL = "http://localhost:5100"

class JobMonitor:
    def __init__(self, refresh_interval=2):
        self.refresh_interval = refresh_interval
        self.last_statuses = {}
        
    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_queue_stats(self) -> Dict:
        """Get current queue statistics"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            statuses = ['pending', 'queued', 'analyzing', 'processing', 'completed', 'failed']
            stats = {}
            
            for status in statuses:
                cursor.execute(f"SELECT COUNT(*) FROM jobs WHERE status = ?", (status,))
                stats[status] = cursor.fetchone()[0]
            
            conn.close()
            return stats
        except Exception as e:
            return {}
    
    def get_active_jobs(self) -> List[Dict]:
        """Get jobs currently being processed"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, advisor, mode, status, current_step, progress_percentage, 
                       created_at, last_activity, error
                FROM jobs
                WHERE status IN ('analyzing', 'processing', 'queued', 'pending')
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            jobs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jobs
        except Exception as e:
            return []
    
    def check_service_health(self) -> Dict[str, bool]:
        """Check if services are responding"""
        health = {}
        
        try:
            response = requests.get(f"{JOB_SERVICE_URL}/health", timeout=2)
            health['job_service'] = response.status_code == 200
        except:
            health['job_service'] = False
        
        try:
            response = requests.get(f"{AI_ADVISOR_URL}/health", timeout=2)
            health['ai_advisor'] = response.status_code == 200
        except:
            health['ai_advisor'] = False
        
        return health
    
    def format_duration(self, seconds):
        """Format seconds as human-readable duration"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m {int(seconds%60)}s"
        else:
            return f"{int(seconds/3600)}h {int((seconds%3600)/60)}m"
    
    def format_elapsed(self, iso_time):
        """Calculate elapsed time from ISO timestamp"""
        try:
            then = datetime.fromisoformat(iso_time)
            now = datetime.now()
            elapsed = (now - then).total_seconds()
            return self.format_duration(elapsed), elapsed
        except:
            return "???", -1
    
    def display(self):
        """Display real-time monitoring dashboard"""
        while True:
            try:
                self.clear_screen()
                
                print("\033[1;36m" + "="*80)
                print(f"LORA JOB PROCESSOR - REAL-TIME MONITOR".center(80))
                print("="*80 + "\033[0m\n")
                
                # Timestamp
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"Timestamp: {now}")
                
                # Service health
                health = self.check_service_health()
                job_service_status = "\033[92m✓ UP\033[0m" if health['job_service'] else "\033[91m✗ DOWN\033[0m"
                ai_advisor_status = "\033[92m✓ UP\033[0m" if health['ai_advisor'] else "\033[91m✗ DOWN\033[0m"
                print(f"\nServices: Job Service {job_service_status}  |  AI Advisor {ai_advisor_status}")
                
                # Queue stats
                stats = self.get_queue_stats()
                print(f"\n\033[1;33mQueue Status:\033[0m")
                print(f"  Pending:   {stats.get('pending', 0):3d} | Queued:    {stats.get('queued', 0):3d}")
                print(f"  Analyzing: {stats.get('analyzing', 0):3d} | Processing: {stats.get('processing', 0):3d}")
                print(f"  Completed: {stats.get('completed', 0):3d} | Failed:   {stats.get('failed', 0):3d}")
                print(f"  Total:     {sum(stats.values()):3d}")
                
                # Active jobs
                print(f"\n\033[1;33mActive Jobs:\033[0m")
                print("-" * 80)
                print(f"{'ID':<8} {'Advisor':<12} {'Mode':<10} {'Status':<12} {'Step':<20} {'Elapsed':<12}")
                print("-" * 80)
                
                active_jobs = self.get_active_jobs()
                if not active_jobs:
                    print("  (no active jobs)")
                else:
                    for job in active_jobs:
                        job_id = job['id'][:8]
                        advisor = job['advisor'][:11]
                        mode = job['mode'][:9]
                        status = job['status'][:11]
                        step = (job['current_step'] or "")[:19]
                        
                        elapsed_str, elapsed_secs = self.format_elapsed(job['created_at'])
                        
                        # Color code based on duration and status
                        if status == 'analyzing' and elapsed_secs > 300:
                            color = "\033[91m"  # Red - might be stuck
                        elif status == 'analyzing' and elapsed_secs > 120:
                            color = "\033[93m"  # Yellow - taking long
                        else:
                            color = "\033[92m"  # Green - normal
                        
                        print(f"{color}{job_id:<8} {advisor:<12} {mode:<10} {status:<12} {step:<20} {elapsed_str:<12}\033[0m", end="")
                        
                        if job['error']:
                            print(f" [ERROR: {job['error'][:30]}]")
                        else:
                            print()
                
                # Warnings
                print("\n\033[1;33mAlerts:\033[0m")
                any_alerts = False
                
                if not health['job_service']:
                    print("  \033[91m✗ Job Service is DOWN - jobs cannot be processed\033[0m")
                    any_alerts = True
                
                if not health['ai_advisor']:
                    print("  \033[91m✗ AI Advisor is DOWN - jobs will fail\033[0m")
                    any_alerts = True
                
                # Check for stuck jobs
                for job in active_jobs:
                    _, elapsed = self.format_elapsed(job['created_at'])
                    if job['status'] in ['analyzing', 'processing'] and elapsed > 300:
                        print(f"  \033[91m✗ Job {job['id'][:8]} is STUCK ({self.format_duration(elapsed)})\033[0m")
                        any_alerts = True
                
                if stats.get('failed', 0) > 10:
                    print(f"  \033[91m✗ Many failed jobs ({stats.get('failed', 0)}) - check logs\033[0m")
                    any_alerts = True
                
                if not any_alerts and health['job_service'] and health['ai_advisor']:
                    print("  \033[92m✓ All systems nominal\033[0m")
                
                # Footer
                print(f"\n{'─'*80}")
                print(f"Press Ctrl+C to exit | Refreshing every {self.refresh_interval}s")
                print(f"\nDebug commands:")
                print(f"  • View database: sqlite3 mondrian.db")
                print(f"  • Check logs: tail -f logs/ai_advisor_service_*.log")
                print(f"  • Kill hung job: curl -X DELETE http://localhost:5005/jobs/{'{job_id}'}")
                
                time.sleep(self.refresh_interval)
                
            except KeyboardInterrupt:
                print("\n\nMonitor stopped")
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(self.refresh_interval)

if __name__ == "__main__":
    monitor = JobMonitor(refresh_interval=2)
    monitor.display()
