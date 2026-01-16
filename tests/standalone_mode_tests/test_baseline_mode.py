#!/usr/bin/env python3
"""
E2E iOS Baseline Mode Test Suite
Tests the complete baseline workflow: upload image → analyze → stream progress → get results
Validates all 8 iOS API endpoints in baseline mode
Saves all results to timestamped JSON file in results/ directory
"""
import requests
import time
import json
import sys
from pathlib import Path
from datetime import datetime

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
AI_ADVISOR_URL = "http://localhost:5100"
RAG_SERVICE_URL = "http://localhost:5400"  # RAG service for semantic search

# Test image
TEST_IMAGE = Path("../../source/mike-shrub.jpg")
ADVISOR = "ansel"

# Results storage
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

def check_health():
    """Verify all services are healthy"""
    print("📋 Checking service health...")
    # Critical services (must be running)
    critical_services = {
        "Job Service": (JOB_SERVICE_URL, 5005),
        "AI Advisor": (AI_ADVISOR_URL, 5100),
    }
    
    # Optional services (nice to have but not required)
    optional_services = {
        "RAG Service": (RAG_SERVICE_URL, 5400),
    }
    
    all_critical_healthy = True
    for name, (url, port) in critical_services.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {name} (:{port}) - healthy")
            else:
                print(f"  ⚠️  {name} (:{port}) - responded but status {response.status_code}")
                all_critical_healthy = False
        except Exception as e:
            print(f"  ❌ {name} (:{port}) - {str(e)[:50]}")
            all_critical_healthy = False
    
    # Check optional services but don't fail
    for name, (url, port) in optional_services.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {name} (:{port}) - healthy")
            else:
                print(f"  ⚠️  {name} (:{port}) - not available (optional)")
        except Exception as e:
            print(f"  ⚠️  {name} (:{port}) - not available (optional)")
    
    return all_critical_healthy

def test_get_advisors():
    """Test 0: Get available advisors (iOS Step 1)"""
    print("\n🔷 Test 0: Get Available Advisors")
    
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/advisors", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            advisors = data.get("advisors", [])
            print(f"  ✅ Found {len(advisors)} advisors")
            
            # Validate advisor structure
            if advisors:
                first = advisors[0]
                required_fields = ["id", "name", "specialty"]
                for field in required_fields:
                    if field not in first:
                        print(f"  ⚠️  Missing required field: {field}")
                        return None
                
                print(f"  Example: {first.get('name')} - {first.get('specialty')}")
            
            return data
        else:
            print(f"  ❌ Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return None

def test_image_upload():
    """Test image upload and job creation"""
    print("\n🔷 Test 1: Image Upload & Job Creation")
    
    if not TEST_IMAGE.exists():
        print(f"  ❌ Test image not found: {TEST_IMAGE}")
        return None
    
    try:
        with open(TEST_IMAGE, "rb") as f:
            response = requests.post(
                f"{JOB_SERVICE_URL}/upload",
                files={"image": ("test.jpg", f, "image/jpeg")},
                data={"advisor": ADVISOR},
                timeout=10
            )
        
        if response.status_code in [200, 201]:
            data = response.json()
            job_id = data.get("job_id")
            print(f"  ✅ Job created: {job_id}")
            return job_id
        else:
            print(f"  ❌ Upload failed: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  ❌ Upload error: {str(e)}")
        return None

def test_stream_progress(job_id):
    """Test SSE streaming of analysis progress with proper event validation"""
    print(f"\n🔷 Test 2: SSE Stream Progress (Job: {job_id})")
    
    try:
        stream_url = f"{JOB_SERVICE_URL}/stream/{job_id}"
        print(f"  Connecting to {stream_url}...")
        
        response = requests.get(stream_url, stream=True, timeout=300)
        
        if response.status_code != 200:
            print(f"  ❌ Stream failed: {response.status_code}")
            return None
        
        print("  ✅ Stream connected")
        
        events_by_type = {
            "connected": 0,
            "status_update": 0,
            "thinking_update": 0,
            "analysis_complete": 0,
            "done": 0
        }
        
        llm_thinking_samples = []
        last_event_type = None
        
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
                            llm_thinking = job_data.get("llm_thinking", "")
                            
                            print(f"    📊 [{progress}%] {step}")
                            
                            # Track llm_thinking samples
                            if llm_thinking:
                                llm_thinking_samples.append(llm_thinking[:60])
                                if len(llm_thinking_samples) <= 3:
                                    print(f"       💭 {llm_thinking[:80]}...")
                        
                        elif event_type == "thinking_update":
                            thinking = msg.get("thinking", "")
                            print(f"    🧠 Thinking: {thinking}")
                        
                        elif event_type == "analysis_complete":
                            print(f"    ✅ Analysis complete event received")
                        
                        elif event_type == "done":
                            print(f"    🏁 Done event received")
                            break
                    
                    except json.JSONDecodeError:
                        pass
            
            # Safety limit
            if sum(events_by_type.values()) > 50:
                print(f"  ⚠️  Reached event limit, stopping early")
                break
        
        # Summary
        print(f"\n  📈 Event Summary:")
        for event_type, count in events_by_type.items():
            if count > 0:
                print(f"     {event_type}: {count}")
        
        print(f"  💭 llm_thinking samples captured: {len(llm_thinking_samples)}")
        
        # Validation
        success = (
            events_by_type["connected"] > 0 and
            events_by_type["status_update"] > 0 and
            events_by_type["done"] > 0
        )
        
        if success:
            print(f"  ✅ SSE stream validation passed")
        else:
            print(f"  ⚠️  Missing critical events")
        
        return {
            "events": events_by_type,
            "llm_thinking_samples": llm_thinking_samples
        }
    
    except Exception as e:
        print(f"  ❌ Stream error: {str(e)}")
        return None

def test_job_status(job_id):
    """Test polling job status"""
    print(f"\n🔷 Test 3: Job Status Polling (Job: {job_id})")
    
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                
                print(f"  [{progress}%] Status: {status}")
                
                if status == "completed":
                    print(f"  ✅ Job completed successfully")
                    return data
                elif status == "error":
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
    
    print(f"  ❌ Job did not complete within {max_wait}s")
    return None

def test_get_summary(job_id):
    """Test retrieving summary (iOS Step 4 - quick preview)"""
    print(f"\n🔷 Test 4: Get Summary HTML (Job: {job_id})")
    
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/summary/{job_id}", timeout=10)
        
        if response.status_code == 200:
            html = response.text
            print(f"  ✅ Summary retrieved ({len(html)} bytes)")
            
            # Validate HTML structure
            has_html = "<html" in html.lower() or "<!doctype" in html.lower()
            has_style = "<style" in html.lower() or "style=" in html.lower()
            
            if has_html:
                print(f"     ✓ Valid HTML structure")
            if has_style:
                print(f"     ✓ Contains styling")
            
            return {"html": html, "length": len(html)}
        else:
            print(f"  ❌ Summary failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"  ❌ Summary error: {str(e)}")
        return None

def test_get_analysis(job_id):
    """Test retrieving full analysis (iOS Step 5 - detailed view)"""
    print(f"\n🔷 Test 5: Get Full Analysis HTML (Job: {job_id})")
    
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/analysis/{job_id}", timeout=10)
        
        if response.status_code == 200:
            html = response.text
            print(f"  ✅ Analysis retrieved ({len(html)} bytes)")
            
            # Validate HTML structure
            has_html = "<html" in html.lower() or "<!doctype" in html.lower()
            has_table = "<table" in html.lower()
            
            if has_html:
                print(f"     ✓ Valid HTML structure")
            if has_table:
                print(f"     ✓ Contains analysis table")
            
            return {"html": html, "length": len(html)}
        else:
            print(f"  ❌ Analysis failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"  ❌ Analysis error: {str(e)}")
        return None

def test_rag_index(job_id, image_path):
    """Test RAG indexing (iOS Step 6 - optional)"""
    print(f"\n🔷 Test 6: RAG Index Image (Job: {job_id})")
    
    try:
        payload = {
            "job_id": job_id,
            "image_path": image_path
        }
        
        response = requests.post(
            f"{RAG_SERVICE_URL}/index",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            caption = data.get("caption", "")
            embedding_dim = data.get("embedding_dim", 0)
            
            print(f"  ✅ Image indexed successfully")
            print(f"     Caption: {caption[:80]}...")
            print(f"     Embedding dim: {embedding_dim}")
            return data
        else:
            print(f"  ⚠️  Index failed: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"  ⚠️  RAG service not running (optional)")
        return None
    except Exception as e:
        print(f"  ⚠️  Index error: {str(e)[:50]}")
        return None

def test_rag_search():
    """Test RAG semantic search (iOS Step 7 - optional)"""
    print(f"\n🔷 Test 7: RAG Semantic Search")
    
    try:
        payload = {
            "query": "landscape photography with dramatic lighting",
            "top_k": 5
        }
        
        response = requests.post(
            f"{RAG_SERVICE_URL}/search",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            total = data.get("total", 0)
            
            print(f"  ✅ Search completed")
            print(f"     Found {total} results")
            
            if results:
                for i, result in enumerate(results[:3], 1):
                    similarity = int(result.get("similarity", 0) * 100)
                    caption = result.get("caption", "")[:60]
                    print(f"     {i}. [{similarity}%] {caption}...")
            
            return data
        else:
            print(f"  ⚠️  Search failed: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"  ⚠️  RAG service not running (optional)")
        return None
    except Exception as e:
        print(f"  ⚠️  Search error: {str(e)[:50]}")
        return None

def main():
    print("=" * 70)
    print("🚀 MONDRIAN E2E iOS BASELINE MODE TEST")
    print("=" * 70)
    print("Testing all 8 iOS API endpoints in baseline mode")
    print()
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "mode": "baseline",
        "advisor": ADVISOR,
        "test_image": str(TEST_IMAGE),
        "services_tested": {
            "job_service": JOB_SERVICE_URL,
            "ai_advisor": AI_ADVISOR_URL,
            "rag_service": RAG_SERVICE_URL,
        },
        "results": {}
    }
    
    # Health check
    if not check_health():
        print("\n❌ Not all critical services are healthy. Please start services:")
        print("   ./mondrian.sh")
        sys.exit(1)
    
    # iOS Step 0: Get advisors (before upload)
    print("\n" + "=" * 70)
    print("iOS API Flow Test - Following Exact iOS Pattern")
    print("=" * 70)
    
    advisors_data = test_get_advisors()
    if advisors_data:
        test_results["results"]["advisors"] = {
            "count": len(advisors_data.get("advisors", [])),
            "success": True
        }
    else:
        print("⚠️  Advisors endpoint failed, continuing anyway...")
        test_results["results"]["advisors"] = {"success": False}
    
    # iOS Step 1: Upload image
    job_id = test_image_upload()
    if not job_id:
        print("\n❌ Failed to upload image (critical)")
        sys.exit(1)
    test_results["results"]["job_id"] = job_id
    test_results["results"]["upload"] = {"success": True, "job_id": job_id}
    
    # iOS Step 2: SSE Stream (real-time updates)
    stream_data = test_stream_progress(job_id)
    if stream_data:
        test_results["results"]["stream"] = {
            "success": True,
            "events": stream_data.get("events", {}),
            "llm_thinking_captured": len(stream_data.get("llm_thinking_samples", []))
        }
    else:
        print("⚠️  SSE stream failed, falling back to polling...")
        test_results["results"]["stream"] = {"success": False}
    
    # iOS Step 3: Poll status (fallback or concurrent)
    status_data = test_job_status(job_id)
    if not status_data:
        print("\n❌ Job did not complete (critical)")
        sys.exit(1)
    test_results["results"]["status"] = {
        "success": True,
        "final_status": status_data.get('status', 'unknown')
    }
    
    # iOS Step 4: Get summary (quick preview)
    summary_result = test_get_summary(job_id)
    if summary_result:
        test_results["results"]["summary"] = {
            "success": True,
            "html_length": summary_result.get("length", 0)
        }
    else:
        test_results["results"]["summary"] = {"success": False}
    
    # iOS Step 5: Get full analysis (detailed view)
    analysis_result = test_get_analysis(job_id)
    if not analysis_result:
        print("\n❌ Failed to get analysis (critical)")
        sys.exit(1)
    test_results["results"]["analysis"] = {
        "success": True,
        "html_length": analysis_result.get("length", 0)
    }
    
    # iOS Step 6: Index for RAG (optional)
    image_path = f"source/{TEST_IMAGE.name}"
    index_result = test_rag_index(job_id, image_path)
    if index_result:
        test_results["results"]["rag_index"] = {
            "success": True,
            "caption_length": len(index_result.get("caption", ""))
        }
    else:
        test_results["results"]["rag_index"] = {"success": False, "optional": True}
    
    # iOS Step 7: Semantic search (optional)
    search_result = test_rag_search()
    if search_result:
        test_results["results"]["rag_search"] = {
            "success": True,
            "results_count": search_result.get("total", 0)
        }
    else:
        test_results["results"]["rag_search"] = {"success": False, "optional": True}
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"baseline_mode_{job_id}_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(test_results, f, indent=2)
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ iOS BASELINE MODE TEST COMPLETE")
    print("=" * 70)
    
    # Count successes
    critical_tests = ["upload", "stream", "status", "analysis"]
    optional_tests = ["advisors", "summary", "rag_index", "rag_search"]
    
    critical_passed = sum(1 for test in critical_tests if test_results["results"].get(test, {}).get("success", False))
    optional_passed = sum(1 for test in optional_tests if test_results["results"].get(test, {}).get("success", False))
    
    print(f"\n📊 Test Results:")
    print(f"   Critical: {critical_passed}/{len(critical_tests)} passed")
    print(f"   Optional: {optional_passed}/{len(optional_tests)} passed")
    print(f"\nJob ID: {job_id}")
    print(f"Final Status: {test_results['results']['status']['final_status']}")
    if summary_result:
        print(f"Summary HTML: {summary_result.get('length', 0)} bytes")
    if analysis_result:
        print(f"Analysis HTML: {analysis_result.get('length', 0)} bytes")
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Exit with appropriate code
    if critical_passed < len(critical_tests):
        print("\n⚠️  Some critical tests failed!")
        sys.exit(1)
    
    print("\n✅ All critical tests passed! Ready for iOS integration.")

if __name__ == "__main__":
    main()
