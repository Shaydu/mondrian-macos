#!/usr/bin/env python3
"""
Diagnostic script for "Job not found" 404 errors in iOS app

This script helps identify why jobs created via /upload endpoint
are returning 404 when checked via /status endpoint.
"""

import sqlite3
import json
import sys
from pathlib import Path

def check_db_file(db_path):
    """Check if database file exists and is readable"""
    print(f"\n📂 Database File Check")
    print(f"   Path: {db_path}")
    
    if not Path(db_path).exists():
        print(f"   ❌ File does not exist")
        return False
    
    print(f"   ✓ File exists")
    
    try:
        size_mb = Path(db_path).stat().st_size / (1024*1024)
        print(f"   ✓ File size: {size_mb:.2f} MB")
    except Exception as e:
        print(f"   ❌ Cannot read file size: {e}")
        return False
    
    return True

def check_db_connection(db_path):
    """Check if we can connect to database"""
    print(f"\n🔌 Database Connection Check")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        print(f"   ✓ Connected to SQLite {version}")
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def check_jobs_table(db_path):
    """Check if jobs table exists and has data"""
    print(f"\n📋 Jobs Table Check")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
        if not cursor.fetchone():
            print(f"   ❌ 'jobs' table does not exist")
            conn.close()
            return False
        
        print(f"   ✓ 'jobs' table exists")
        
        # Count jobs
        cursor.execute("SELECT COUNT(*) FROM jobs")
        count = cursor.fetchone()[0]
        print(f"   ✓ Total jobs in database: {count}")
        
        if count == 0:
            print(f"   ⚠️  No jobs found in database")
        
        # Show recent jobs
        cursor.execute("""
            SELECT id, advisor, mode, status, created_at 
            FROM jobs 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        recent = cursor.fetchall()
        if recent:
            print(f"\n   Recent jobs:")
            for job_id, advisor, mode, status, created_at in recent:
                short_id = job_id[:8]
                print(f"   • {short_id}... | {advisor:10s} | {mode:10s} | {status:12s} | {created_at}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Table check failed: {e}")
        return False

def check_specific_job(db_path, job_id):
    """Look up a specific job ID"""
    print(f"\n🔍 Job Lookup: {job_id}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        
        if not job:
            print(f"   ❌ Job not found in database")
            
            # Try partial match
            partial_id = job_id[:16]
            cursor.execute("SELECT id FROM jobs WHERE id LIKE ?", (f"{partial_id}%",))
            similar = cursor.fetchall()
            
            if similar:
                print(f"   ⚠️  Found similar job IDs:")
                for row in similar:
                    print(f"      • {row[0]}")
            
            conn.close()
            return False
        
        print(f"   ✓ Job found!")
        print(f"\n   Job Details:")
        print(f"   • ID:       {job['id']}")
        print(f"   • Advisor:  {job['advisor']}")
        print(f"   • Mode:     {job['mode']}")
        print(f"   • Status:   {job['status']}")
        print(f"   • Created:  {job['created_at']}")
        print(f"   • Filename: {job['filename']}")
        print(f"   • RAG:      {job['enable_rag']}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Lookup failed: {e}")
        return False

def check_ios_request_log():
    """Suggest checking iOS logs for the exact request"""
    print(f"\n📱 iOS App Debugging Steps")
    print(f"   1. Check iOS app logs for the job_id returned from /upload")
    print(f"   2. Look for: '📡 Checking status from: http://.../status/<job_id>'")
    print(f"   3. Note the job_id from that line")
    print(f"   4. Run this script with: python3 diagnose_job_not_found.py <job_id>")

def main():
    db_path = "mondrian.db"
    
    # Allow specifying custom DB path
    if len(sys.argv) > 1 and sys.argv[1] != "--help":
        # Check if first arg is a job ID (UUID format) or a path
        arg = sys.argv[1]
        if len(arg) == 36 and arg.count('-') == 4:  # UUID format
            job_id = arg
        else:
            db_path = arg
            job_id = None
    else:
        job_id = None
    
    print("=" * 70)
    print(" iOS Job Status 404 - Diagnostic Tool")
    print("=" * 70)
    
    # Run checks
    if not check_db_file(db_path):
        print(f"\n❌ Cannot proceed - database file not accessible")
        sys.exit(1)
    
    if not check_db_connection(db_path):
        print(f"\n❌ Cannot proceed - cannot connect to database")
        sys.exit(1)
    
    check_jobs_table(db_path)
    
    # If job ID provided, check it specifically
    if job_id:
        check_specific_job(db_path, job_id)
    
    # Show next steps
    check_ios_request_log()
    
    print("\n" + "=" * 70)
    print(" Summary")
    print("=" * 70)
    print("""
If jobs are being created but not found:
  1. Check if the database path is correct
  2. Verify the job service and iOS app use the SAME database
  3. Check for database locking issues
  4. Restart the job service: ./mondrian.sh --restart --mode=lora+rag

If no jobs appear at all:
  1. Verify /upload endpoint is returning the correct job_id
  2. Check iOS app logs for the exact job_id returned
  3. Check job service logs for "[UPLOAD]" messages
  4. Ensure the database was initialized before starting the service
  
If you see "Job not found" in browser but /upload returned a job_id:
  - There's likely a database connection/transaction issue
  - Check the job service logs for errors
  - Restart both services and try again
""")

if __name__ == '__main__':
    main()
