#!/usr/bin/env python3
"""
E2E iOS Test Suite for LoRA+RAG Mode
Tests the complete workflow: upload image → analyze with LoRA → stream progress → get results
Requires the service to be running with LoRA adapter loaded.

Usage:
    ./mondrian.sh --restart --mode=lora+rag --lora-path=./adapters/ansel
    python3 test_e2e_ios_lora_rag.py [--verbose]
"""
import requests
import time
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
AI_ADVISOR_URL = "http://localhost:5100"
RAG_SERVICE_URL = "http://localhost:5400"

# Test image - uses the standard test image for Ansel
TEST_IMAGE = Path("source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg")
# Fallback if primary image not found
FALLBACK_IMAGE = Path("source/mike-shrub.jpg")

ADVISOR = "ansel"
MODE = "lora+rag"  # Combined LoRA fine-tuned model with RAG context

# Results storage
RESULTS_DIR = Path("test_results")
RESULTS_DIR.mkdir(exist_ok=True)

# Timeouts
UPLOAD_TIMEOUT = 30
STREAM_TIMEOUT = 600  # LoRA+RAG can take longer
STATUS_POLL_TIMEOUT = 600
ANALYSIS_TIMEOUT = 30


def get_test_image():
    """Find a test image to use"""
    if TEST_IMAGE.exists():
        return TEST_IMAGE
    if FALLBACK_IMAGE.exists():
        return FALLBACK_IMAGE
    # Try to find any jpg in source/
    source_dir = Path("source")
    if source_dir.exists():
        jpgs = list(source_dir.glob("*.jpg"))
        if jpgs:
            return jpgs[0]
    return None


def check_health(verbose=False):
    """Verify all services are healthy and LoRA is loaded"""
    print("📋 Checking service health (LoRA+RAG mode)...")
    
    all_healthy = True
    lora_loaded = False
    
    # Check Job Service
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ Job Service (:5005) - healthy")
        else:
            print(f"  ❌ Job Service (:5005) - status {response.status_code}")
            all_healthy = False
    except Exception as e:
        print(f"  ❌ Job Service (:5005) - {str(e)[:50]}")
        all_healthy = False
    
    # Check AI Advisor with LoRA status
    try:
        response = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            fine_tuned = data.get('fine_tuned', False)
            lora_path = data.get('lora_path', 'none')
            device = data.get('device', 'unknown')
            model = data.get('model', 'unknown')
            
            print(f"  ✅ AI Advisor (:5100) - healthy")
            print(f"     Model: {model}")
            print(f"     Device: {device}")
            
            if fine_tuned:
                print(f"     LoRA: ✅ Loaded ({lora_path})")
                lora_loaded = True
            else:
                print(f"     LoRA: ❌ NOT loaded")
                print(f"     ⚠️  Service needs to be running with --mode=lora+rag --lora-path=...")
                all_healthy = False
            
            if verbose:
                print(f"     Full health: {json.dumps(data, indent=6)}")
        else:
            print(f"  ❌ AI Advisor (:5100) - status {response.status_code}")
            all_healthy = False
    except Exception as e:
        print(f"  ❌ AI Advisor (:5100) - {str(e)[:50]}")
        all_healthy = False
    
    # Check RAG Service (optional but recommended for lora+rag mode)
    try:
        response = requests.get(f"{RAG_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ RAG Service (:5400) - healthy")
        else:
            print(f"  ⚠️  RAG Service (:5400) - status {response.status_code} (optional)")
    except Exception:
        print(f"  ⚠️  RAG Service (:5400) - not available (optional for this test)")
    
    return all_healthy and lora_loaded


def test_image_upload(test_image, verbose=False):
    """Test image upload with LoRA+RAG mode"""
    print(f"\n🔷 Test 1: Image Upload & Job Creation (mode={MODE})")
    
    try:
        with open(test_image, "rb") as f:
            response = requests.post(
                f"{JOB_SERVICE_URL}/upload",
                files={"image": (test_image.name, f, "image/jpeg")},
                data={
                    "advisor": ADVISOR,
                    "mode": MODE,
                    "enable_rag": "true"
                },
                timeout=UPLOAD_TIMEOUT
            )
        
        if response.status_code in [200, 201]:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ Job created: {job_id}")
            if verbose:
                print(f"     Response: {json.dumps(data, indent=6)}")
            return job_id
        else:
            print(f"  ❌ Upload failed: {response.status_code}")
            print(f"     Response: {response.text[:300]}")
            return None
    except Exception as e:
        print(f"  ❌ Upload error: {str(e)}")
        return None


def test_stream_progress(job_id, verbose=False):
    """Test SSE streaming with LoRA+RAG specific event handling"""
    print(f"\n🔷 Test 2: SSE Stream Progress (Job: {job_id})")
    
    try:
        stream_url = f"{JOB_SERVICE_URL}/stream/{job_id}"
        print(f"  Connecting to {stream_url}...")
        
        response = requests.get(stream_url, stream=True, timeout=STREAM_TIMEOUT)
        
        if response.status_code != 200:
            print(f"  ❌ Stream failed: {response.status_code}")
            return None
        
        print("  ✅ Stream connected")
        
        events_by_type = {
            "connected": 0,
            "status_update": 0,
            "thinking_update": 0,
            "analysis_complete": 0,
            "done": 0,
            "error": 0
        }
        
        llm_thinking_samples = []
        last_event_type = None
        last_status = None
        last_step = None
        error_message = None
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith("event:"):
                last_event_type = line.replace("event:", "").strip()
            elif line.startswith("data:"):
                data = line.replace("data:", "").strip()
                if data:
                    try:
                        msg = json.loads(data)
                        event_type = msg.get("type", last_event_type)
                        
                        if event_type in events_by_type:
                            events_by_type[event_type] += 1
                        
                        # Handle different event types
                        if event_type == "connected":
                            print(f"    🔗 Connected to job: {msg.get('job_id', 'unknown')}")
                        
                        elif event_type == "status_update":
                            job_data = msg.get("job_data", {})
                            progress = job_data.get("progress_percentage", 0)
                            step = job_data.get("current_step", "unknown")
                            status = job_data.get("status", "unknown")
                            step_phase = job_data.get("step_phase", "")
                            llm_thinking = job_data.get("llm_thinking", "")
                            
                            # Only print on status/step change
                            if status != last_status or step != last_step:
                                print(f"    📊 [{progress:3d}%] {status}: {step}")
                                last_status = status
                                last_step = step
                            
                            # Track llm_thinking samples
                            if llm_thinking and len(llm_thinking_samples) < 5:
                                sample = llm_thinking[:80].replace('\n', ' ')
                                llm_thinking_samples.append(sample)
                                if verbose:
                                    print(f"       💭 {sample}...")
                            
                            # Check for error status
                            if status == "error" or status == "failed":
                                error_message = job_data.get("error", step)
                                events_by_type["error"] += 1
                                print(f"    ❌ Error: {error_message}")
                        
                        elif event_type == "thinking_update":
                            thinking = msg.get("thinking", "")
                            if verbose and thinking:
                                print(f"    🧠 Thinking: {thinking[:100]}...")
                        
                        elif event_type == "analysis_complete":
                            print(f"    ✅ Analysis complete event received")
                        
                        elif event_type == "error":
                            error_message = msg.get("error", msg.get("message", "Unknown error"))
                            events_by_type["error"] += 1
                            print(f"    ❌ Error event: {error_message}")
                        
                        elif event_type == "done":
                            print(f"    🏁 Done event received")
                            break
                    
                    except json.JSONDecodeError:
                        pass
            
            # Safety limit
            if sum(events_by_type.values()) > 100:
                print(f"  ⚠️  Reached event limit, stopping early")
                break
        
        # Summary
        print(f"\n  📈 Event Summary:")
        for event_type, count in events_by_type.items():
            if count > 0:
                print(f"     {event_type}: {count}")
        
        print(f"  💭 llm_thinking samples captured: {len(llm_thinking_samples)}")
        
        # Determine success
        success = (
            events_by_type["connected"] > 0 and
            events_by_type["status_update"] > 0 and
            events_by_type["done"] > 0 and
            events_by_type["error"] == 0
        )
        
        if success:
            print(f"  ✅ SSE stream validation passed")
        elif events_by_type["error"] > 0:
            print(f"  ❌ SSE stream had errors: {error_message}")
        else:
            print(f"  ⚠️  Missing critical events")
        
        return {
            "success": success,
            "events": events_by_type,
            "llm_thinking_samples": llm_thinking_samples,
            "error": error_message
        }
    
    except requests.exceptions.Timeout:
        print(f"  ❌ Stream timeout after {STREAM_TIMEOUT}s")
        print(f"     LoRA+RAG mode may need more time or service may be stuck")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        print(f"  ❌ Stream error: {str(e)}")
        return {"success": False, "error": str(e)}


def test_job_status(job_id, verbose=False):
    """Poll job status until completion"""
    print(f"\n🔷 Test 3: Job Status Polling (Job: {job_id})")
    
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < STATUS_POLL_TIMEOUT:
        try:
            response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                step = data.get("current_step", "")
                
                if status != last_status:
                    print(f"  [{progress:3d}%] Status: {status} {step}")
                    last_status = status
                
                if status == "completed":
                    print(f"  ✅ Job completed successfully")
                    return data
                elif status in ("error", "failed"):
                    error = data.get("error", "Unknown error")
                    print(f"  ❌ Job error: {error}")
                    return None
                
                time.sleep(2)
            else:
                print(f"  ⚠️  Status check returned {response.status_code}")
                time.sleep(5)
        
        except Exception as e:
            print(f"  ⚠️  Status check error: {str(e)[:50]}")
            time.sleep(5)
    
    print(f"  ❌ Job did not complete within {STATUS_POLL_TIMEOUT}s")
    return None


def test_get_summary(job_id, verbose=False):
    """Test retrieving summary HTML"""
    print(f"\n🔷 Test 4: Get Summary HTML (Job: {job_id})")
    
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/summary/{job_id}", timeout=ANALYSIS_TIMEOUT)
        
        if response.status_code == 200:
            html = response.text
            print(f"  ✅ Summary retrieved ({len(html)} bytes)")
            
            # Validate HTML structure
            has_html = "<html" in html.lower() or "<!doctype" in html.lower()
            has_grade = "grade" in html.lower() or "score" in html.lower()
            
            if has_html:
                print(f"     ✓ Valid HTML structure")
            if has_grade:
                print(f"     ✓ Contains grading info")
            
            return {"html": html, "length": len(html)}
        else:
            print(f"  ❌ Summary failed: {response.status_code}")
            if verbose:
                print(f"     Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  ❌ Summary error: {str(e)}")
        return None


def test_get_analysis(job_id, verbose=False):
    """Test retrieving full analysis HTML"""
    print(f"\n🔷 Test 5: Get Full Analysis HTML (Job: {job_id})")
    
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=ANALYSIS_TIMEOUT)
        
        if response.status_code == 200:
            html = response.text
            print(f"  ✅ Analysis retrieved ({len(html)} bytes)")
            
            # Validate HTML structure
            has_html = "<html" in html.lower() or "<!doctype" in html.lower()
            has_dimensional = "dimensional" in html.lower() or "dimension" in html.lower()
            has_ansel = "ansel" in html.lower()
            
            if has_html:
                print(f"     ✓ Valid HTML structure")
            if has_dimensional:
                print(f"     ✓ Contains dimensional analysis")
            if has_ansel:
                print(f"     ✓ Contains Ansel-specific content")
            
            if verbose:
                # Extract grade if present
                import re
                grade_match = re.search(r'overall[_\s]?(grade|score)["\s:]+([A-F][+-]?|\d+)', html, re.I)
                if grade_match:
                    print(f"     Overall Grade: {grade_match.group(2)}")
            
            return {"html": html, "length": len(html)}
        else:
            print(f"  ❌ Analysis failed: {response.status_code}")
            if verbose:
                print(f"     Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  ❌ Analysis error: {str(e)}")
        return None


def test_rag_features(job_id, test_image, verbose=False):
    """Test RAG-specific features (optional)"""
    print(f"\n🔷 Test 6: RAG Features (Optional)")
    
    results = {"index": None, "search": None}
    
    # Test indexing
    try:
        payload = {
            "job_id": job_id,
            "image_path": str(test_image)
        }
        response = requests.post(f"{RAG_SERVICE_URL}/index", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ RAG Index: Image indexed")
            if verbose:
                print(f"     Caption: {data.get('caption', '')[:80]}...")
            results["index"] = data
        else:
            print(f"  ⚠️  RAG Index: status {response.status_code} (optional)")
    except requests.exceptions.ConnectionError:
        print(f"  ⚠️  RAG Service not available (optional)")
    except Exception as e:
        print(f"  ⚠️  RAG Index error: {str(e)[:50]} (optional)")
    
    # Test search
    try:
        payload = {"query": "dramatic landscape photography", "top_k": 3}
        response = requests.post(f"{RAG_SERVICE_URL}/search", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            print(f"  ✅ RAG Search: {total} results")
            results["search"] = data
        else:
            print(f"  ⚠️  RAG Search: status {response.status_code} (optional)")
    except Exception as e:
        print(f"  ⚠️  RAG Search error: {str(e)[:50]} (optional)")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="E2E iOS Test Suite for LoRA+RAG Mode"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output with detailed responses")
    parser.add_argument("--skip-rag", action="store_true",
                       help="Skip RAG feature tests")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🚀 MONDRIAN E2E iOS LoRA+RAG MODE TEST")
    print("=" * 70)
    print(f"Mode: {MODE}")
    print(f"Advisor: {ADVISOR}")
    print()
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "mode": MODE,
        "advisor": ADVISOR,
        "services_tested": {
            "job_service": JOB_SERVICE_URL,
            "ai_advisor": AI_ADVISOR_URL,
            "rag_service": RAG_SERVICE_URL,
        },
        "results": {}
    }
    
    # Find test image
    test_image = get_test_image()
    if not test_image:
        print("❌ No test image found in source/ directory")
        sys.exit(1)
    print(f"Test image: {test_image}")
    test_results["test_image"] = str(test_image)
    
    # Health check with LoRA verification
    if not check_health(args.verbose):
        print("\n❌ Service health check failed.")
        print("   Make sure to start with LoRA+RAG mode:")
        print("   ./mondrian.sh --restart --mode=lora+rag --lora-path=./adapters/ansel")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("iOS API Flow Test - LoRA+RAG Mode")
    print("=" * 70)
    
    # Test 1: Upload image with lora+rag mode
    job_id = test_image_upload(test_image, args.verbose)
    if not job_id:
        print("\n❌ Failed to upload image (critical)")
        sys.exit(1)
    test_results["results"]["job_id"] = job_id
    test_results["results"]["upload"] = {"success": True, "job_id": job_id}
    
    # Test 2: SSE Stream
    stream_result = test_stream_progress(job_id, args.verbose)
    if stream_result:
        test_results["results"]["stream"] = stream_result
        if not stream_result.get("success"):
            print(f"\n⚠️  SSE stream issues detected, continuing with polling...")
    else:
        test_results["results"]["stream"] = {"success": False}
    
    # Test 3: Poll status
    status_data = test_job_status(job_id, args.verbose)
    if not status_data:
        print("\n❌ Job did not complete (critical)")
        # Try to get any partial results
        print("   Attempting to retrieve partial results...")
    else:
        test_results["results"]["status"] = {
            "success": True,
            "final_status": status_data.get("status", "unknown")
        }
    
    # Test 4: Get summary
    summary_result = test_get_summary(job_id, args.verbose)
    test_results["results"]["summary"] = {
        "success": summary_result is not None,
        "html_length": summary_result.get("length", 0) if summary_result else 0
    }
    
    # Test 5: Get full analysis
    analysis_result = test_get_analysis(job_id, args.verbose)
    test_results["results"]["analysis"] = {
        "success": analysis_result is not None,
        "html_length": analysis_result.get("length", 0) if analysis_result else 0
    }
    
    # Test 6: RAG features (optional)
    if not args.skip_rag:
        rag_result = test_rag_features(job_id, test_image, args.verbose)
        test_results["results"]["rag"] = {
            "index_success": rag_result.get("index") is not None,
            "search_success": rag_result.get("search") is not None
        }
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"e2e_ios_lora_rag_{job_id}_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(test_results, f, indent=2)
    
    # Final summary
    print("\n" + "=" * 70)
    
    # Determine overall success
    critical_passed = (
        test_results["results"].get("upload", {}).get("success", False) and
        test_results["results"].get("status", {}).get("success", False) and
        test_results["results"].get("analysis", {}).get("success", False)
    )
    
    stream_passed = test_results["results"].get("stream", {}).get("success", False)
    
    if critical_passed:
        print("✅ LoRA+RAG E2E TEST PASSED")
        print("=" * 70)
    else:
        print("❌ LoRA+RAG E2E TEST FAILED")
        print("=" * 70)
    
    print(f"\n📊 Test Results:")
    print(f"   Upload:   {'✅' if test_results['results'].get('upload', {}).get('success') else '❌'}")
    print(f"   Stream:   {'✅' if stream_passed else '⚠️ '}")
    print(f"   Status:   {'✅' if test_results['results'].get('status', {}).get('success') else '❌'}")
    print(f"   Summary:  {'✅' if test_results['results'].get('summary', {}).get('success') else '❌'}")
    print(f"   Analysis: {'✅' if test_results['results'].get('analysis', {}).get('success') else '❌'}")
    
    if not args.skip_rag:
        rag_res = test_results["results"].get("rag", {})
        print(f"   RAG:      {'✅' if rag_res.get('index_success') or rag_res.get('search_success') else '⚠️ '} (optional)")
    
    print(f"\nJob ID: {job_id}")
    if status_data:
        print(f"Final Status: {status_data.get('status', 'unknown')}")
    if summary_result:
        print(f"Summary HTML: {summary_result.get('length', 0)} bytes")
    if analysis_result:
        print(f"Analysis HTML: {analysis_result.get('length', 0)} bytes")
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Exit code
    if not critical_passed:
        sys.exit(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
