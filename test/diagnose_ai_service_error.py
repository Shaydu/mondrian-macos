#!/usr/bin/env python3
"""
Diagnostic script to check AI Advisor Service status and test the /analyze endpoint
Helps diagnose 500 errors from the AI advisor service
"""

import requests
import json
import sys
import os
from pathlib import Path

AI_ADVISOR_URL = "http://127.0.0.1:5100"
TEST_IMAGE = "source/mike-shrub.jpg"

def check_service_health():
    """Check if AI advisor service is running"""
    print("=" * 80)
    print("1. Checking AI Advisor Service Health")
    print("=" * 80)
    
    try:
        resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
        if resp.status_code == 200:
            health_data = resp.json()
            print(f"✓ Service is running")
            print(f"  Status: {health_data.get('status', 'N/A')}")
            print(f"  Version: {health_data.get('version', 'N/A')}")
            print(f"  Port: {health_data.get('port', 'N/A')}")
            return True
        else:
            print(f"✗ Service returned status {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to {AI_ADVISOR_URL}")
        print(f"  Is the AI advisor service running?")
        return False
    except Exception as e:
        print(f"✗ Error checking service: {e}")
        return False

def test_analyze_endpoint():
    """Test the /analyze endpoint with a test image"""
    print("\n" + "=" * 80)
    print("2. Testing /analyze Endpoint")
    print("=" * 80)
    
    image_path = Path(TEST_IMAGE)
    if not image_path.exists():
        print(f"✗ Test image not found: {TEST_IMAGE}")
        print(f"  Please provide a valid image path")
        return False
    
    print(f"Using test image: {TEST_IMAGE}")
    print(f"Image size: {image_path.stat().st_size:,} bytes")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': (image_path.name, f, 'image/jpeg')}
            data = {
                'advisor': 'ansel',
                'job_id': 'test-diagnostic',
                'job_service_url': 'http://127.0.0.1:5005',
                'enable_rag': 'false'  # Test baseline first
            }
            
            print(f"\nSending request to {AI_ADVISOR_URL}/analyze...")
            print(f"  Advisor: {data['advisor']}")
            print(f"  RAG Enabled: {data['enable_rag']}")
            
            resp = requests.post(
                f"{AI_ADVISOR_URL}/analyze",
                files=files,
                data=data,
                timeout=300  # 5 minute timeout for analysis
            )
            
            print(f"\nResponse Status: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")
            
            if resp.status_code == 200:
                print(f"✓ Analysis successful!")
                html = resp.text
                print(f"  Response length: {len(html):,} characters")
                
                # Check for error indicators in HTML
                if 'error' in html.lower()[:500]:
                    print(f"\n⚠ Warning: Response contains 'error' text")
                    print(f"  Preview: {html[:300]}")
                
                return True
            else:
                print(f"✗ Analysis failed with status {resp.status_code}")
                print(f"\nResponse headers:")
                for key, value in resp.headers.items():
                    print(f"  {key}: {value}")
                
                print(f"\nResponse body (first 1000 chars):")
                print("-" * 80)
                try:
                    # Try to parse as JSON first
                    error_json = resp.json()
                    print(json.dumps(error_json, indent=2))
                except:
                    # If not JSON, show as text
                    print(resp.text[:1000])
                print("-" * 80)
                
                return False
                
    except requests.exceptions.Timeout:
        print(f"✗ Request timed out after 5 minutes")
        print(f"  The model may be taking too long to process")
        return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to {AI_ADVISOR_URL}")
        print(f"  Is the AI advisor service running?")
        return False
    except Exception as e:
        print(f"✗ Exception during request: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_logs():
    """Check recent error logs"""
    print("\n" + "=" * 80)
    print("3. Checking Recent Logs")
    print("=" * 80)
    
    log_files = [
        "logs/ai_advisor_err.log",
        "logs/ai_advisor_out.log",
        "logs/ai_advisor_service.log",
        "mondrian/logs/ai_advisor_err.log",
        "mondrian/logs/ai_advisor_out.log",
    ]
    
    found_logs = False
    for log_path in log_files:
        log_file = Path(log_path)
        if log_file.exists():
            found_logs = True
            print(f"\n{log_path}:")
            print("-" * 80)
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Show last 30 lines
                    for line in lines[-30:]:
                        print(line.rstrip())
            except Exception as e:
                print(f"  Error reading log: {e}")
    
    if not found_logs:
        print("No log files found in expected locations")
        print("Log files checked:")
        for log_path in log_files:
            print(f"  - {log_path}")

def main():
    """Run all diagnostics"""
    print("\n" + "=" * 80)
    print("AI Advisor Service Diagnostic Tool")
    print("=" * 80)
    print()
    
    # Check service health
    service_ok = check_service_health()
    
    if not service_ok:
        print("\n" + "=" * 80)
        print("RECOMMENDATION: Start the AI advisor service first")
        print("=" * 80)
        print("Run: ./mondrian.sh --restart")
        print("Or manually: cd mondrian && python3 ai_advisor_service.py")
        sys.exit(1)
    
    # Test analyze endpoint
    analyze_ok = test_analyze_endpoint()
    
    # Check logs
    check_logs()
    
    # Summary
    print("\n" + "=" * 80)
    print("Diagnostic Summary")
    print("=" * 80)
    print(f"Service Health: {'✓ OK' if service_ok else '✗ FAILED'}")
    print(f"Analyze Endpoint: {'✓ OK' if analyze_ok else '✗ FAILED'}")
    
    if not analyze_ok:
        print("\nCommon causes of 500 errors:")
        print("  1. MLX model not loaded (check GPU/Metal availability)")
        print("  2. Image file cannot be processed")
        print("  3. Advisor metadata not found in database")
        print("  4. Model inference failure (check logs above)")
        print("  5. Out of memory (GPU or system)")
        print("\nNext steps:")
        print("  - Check the logs above for detailed error messages")
        print("  - Verify the MLX model is loaded (check service startup logs)")
        print("  - Try restarting the service: ./mondrian.sh --restart")
    
    sys.exit(0 if (service_ok and analyze_ok) else 1)

if __name__ == "__main__":
    main()
