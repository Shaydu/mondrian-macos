#!/usr/bin/env python3
"""
Test Enhanced Single-Pass Citation System

This test validates that the enhanced single-pass approach properly includes
reference images and quotes by:
1. Analyzing a user image
2. Determining weak dimensions from the analysis
3. Checking if LLM cited relevant references
4. Verifying citations appear in HTML output

Tests the fix for missing reference images and quotes issue from commit 7c06a41.
"""

import requests
import json
import time
import sys
from pathlib import Path

# Configuration
JOB_SERVICE_URL = "http://localhost:5005"
TEST_IMAGE = Path("source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg")
FALLBACK_IMAGE = Path("source/mike-shrub.jpg")
ADVISOR = "ansel"
MODE = "lora+rag"  # Or just "rag" without LoRA

def get_test_image():
    """Find a test image to use"""
    # Adjust paths for test directory
    root = Path(__file__).parent.parent
    test_img = root / TEST_IMAGE
    fallback_img = root / FALLBACK_IMAGE
    
    if test_img.exists():
        return test_img
    if fallback_img.exists():
        return fallback_img
    source_dir = root / "source"
    if source_dir.exists():
        jpgs = list(source_dir.glob("*.jpg"))
        if jpgs:
            return jpgs[0]
    print("❌ No test images found in source/ directory")
    return None

def check_service_health():
    """Verify job service is running"""
    print("\n🔍 Checking service health...")
    try:
        response = requests.get(f"{JOB_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Job service is healthy")
            return True
        else:
            print(f"❌ Job service returned {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to job service: {e}")
        print(f"   Make sure service is running on {JOB_SERVICE_URL}")
        return False

def submit_analysis_job(image_path):
    """Submit image for analysis"""
    print(f"\n📤 Uploading image: {image_path.name}")
    print(f"   Advisor: {ADVISOR}")
    print(f"   Mode: {MODE}")
    
    try:
        with open(image_path, "rb") as f:
            response = requests.post(
                f"{JOB_SERVICE_URL}/upload",
                files={"image": (image_path.name, f, "image/jpeg")},
                data={"advisor": ADVISOR, "mode": MODE},
                timeout=30
            )
        
        if response.status_code not in [200, 201]:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
        
        job_data = response.json()
        job_id = job_data.get("job_id")
        print(f"✅ Job created: {job_id}")
        return job_id
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def wait_for_completion(job_id, max_wait=300):
    """Poll job status until completion"""
    print(f"\n⏳ Waiting for analysis (max {max_wait}s)...")
    start_time = time.time()
    last_progress = -1
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{JOB_SERVICE_URL}/status/{job_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                progress = data.get("progress", 0)
                
                if progress != last_progress:
                    print(f"   Progress: {progress}% - {status}")
                    last_progress = progress
                
                if status == "completed":
                    elapsed = time.time() - start_time
                    print(f"✅ Analysis completed in {elapsed:.1f}s")
                    return data
                elif status == "failed":
                    error = data.get("error", "Unknown error")
                    print(f"❌ Analysis failed: {error}")
                    return None
            
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️  Status check error: {e}")
            time.sleep(2)
    
    print(f"❌ Job timed out after {max_wait}s")
    return None

def analyze_citations(result_data):
    """Analyze the result for citations and dimensional scores"""
    print("\n" + "="*70)
    print("CITATION ANALYSIS")
    print("="*70)
    
    # Try multiple paths to find the analysis data
    # Path 1: Direct result.analysis (AI service direct call)
    result = result_data.get("result", {})
    analysis = result.get("analysis", {})
    
    # Path 2: Top-level llm_outputs (job service response)
    if not analysis:
        llm_outputs = result_data.get("llm_outputs")
        if llm_outputs:
            import json
            try:
                llm_data = json.loads(llm_outputs) if isinstance(llm_outputs, str) else llm_outputs
                # The response field contains the actual JSON
                response_str = llm_data.get("response", "")
                if response_str:
                    analysis = json.loads(response_str) if isinstance(response_str, str) else response_str
            except json.JSONDecodeError as e:
                print(f"⚠️  Failed to parse llm_outputs: {e}")
    
    # 1. Check dimensional scores
    print("\n📊 DIMENSIONAL SCORES")
    print("-" * 70)
    dimensions = analysis.get("dimensions", [])
    
    if not dimensions:
        print("❌ No dimensions found in analysis")
        return False
    
    weak_dims = []
    for dim in dimensions:
        name = dim.get("name", "Unknown")
        score = dim.get("score", 0)
        print(f"   {name}: {score}/10", end="")
        
        if score <= 6:
            print(" ⚠️  WEAK", end="")
            weak_dims.append(name)
        
        print()
    
    print(f"\n   Identified {len(weak_dims)} weak dimensions: {', '.join(weak_dims)}")
    
    # 2. Check for image citations
    print("\n📷 IMAGE CITATIONS")
    print("-" * 70)
    
    image_citations = []
    for dim in dimensions:
        case_study_id = dim.get("case_study_id")
        cited_image = dim.get("_cited_image")
        
        if case_study_id or cited_image:
            dim_name = dim.get("name", "Unknown")
            title = cited_image.get("image_title", "Unknown") if cited_image else case_study_id
            image_citations.append((dim_name, title, case_study_id))
            print(f"   ✅ {dim_name}: cited {case_study_id} ({title})")
    
    if not image_citations:
        print("   ❌ No image citations found")
    else:
        print(f"\n   Total: {len(image_citations)} image citations")
    
    # 3. Check for quote citations
    print("\n💬 QUOTE CITATIONS")
    print("-" * 70)
    
    quote_citations = []
    for dim in dimensions:
        quote_id = dim.get("quote_id")
        cited_quote = dim.get("_cited_quote")
        
        if quote_id or cited_quote:
            dim_name = dim.get("name", "Unknown")
            book = cited_quote.get("book_title", "Unknown") if cited_quote else "Unknown"
            quote_citations.append((dim_name, quote_id, book))
            print(f"   ✅ {dim_name}: cited {quote_id} from \"{book}\"")
    
    if not quote_citations:
        print("   ❌ No quote citations found")
    else:
        print(f"\n   Total: {len(quote_citations)} quote citations")
    
    # 4. Check HTML output for embedded references
    print("\n🌐 HTML OUTPUT CHECK")
    print("-" * 70)
    
    analysis_html = result.get("analysis_html", "")
    
    has_case_study_box = "case-study-box" in analysis_html
    has_quote_box = "advisor-quote-box" in analysis_html
    has_reference_citation = "reference-citation" in analysis_html
    
    print(f"   Case study boxes: {'✅ FOUND' if has_case_study_box else '❌ NOT FOUND'}")
    print(f"   Quote boxes: {'✅ FOUND' if has_quote_box else '❌ NOT FOUND'}")
    print(f"   Reference citations: {'✅ FOUND' if has_reference_citation else '❌ NOT FOUND'}")
    
    # 5. Check if citations match weak dimensions
    print("\n🎯 RELEVANCE CHECK")
    print("-" * 70)
    
    relevant_citations = 0
    for dim_name, title, case_id in image_citations:
        if dim_name in weak_dims:
            print(f"   ✅ Image citation for weak dimension: {dim_name}")
            relevant_citations += 1
    
    for dim_name, quote_id, book in quote_citations:
        if dim_name in weak_dims:
            print(f"   ✅ Quote citation for weak dimension: {dim_name}")
            relevant_citations += 1
    
    if relevant_citations == 0:
        print("   ⚠️  No citations match weak dimensions")
    else:
        print(f"\n   {relevant_citations} relevant citations found")
    
    # Final verdict
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    
    has_citations = len(image_citations) > 0 or len(quote_citations) > 0
    has_html_citations = has_case_study_box or has_quote_box
    
    if has_citations and has_html_citations:
        print("✅ PASS: Citations are working!")
        print(f"   - {len(image_citations)} image citations")
        print(f"   - {len(quote_citations)} quote citations")
        print(f"   - Citations appear in HTML output")
        return True
    elif has_citations and not has_html_citations:
        print("⚠️  PARTIAL: LLM cited references, but HTML generation may have issues")
        print(f"   - {len(image_citations)} image citations in JSON")
        print(f"   - {len(quote_citations)} quote citations in JSON")
        print(f"   - But no case-study-box or advisor-quote-box in HTML")
        return False
    else:
        print("❌ FAIL: No citations found")
        print("   - LLM did not cite any references")
        print("   - Check prompt instructions and RAG context")
        return False

def save_debug_output(job_id, result_data):
    """Save full result for debugging"""
    root = Path(__file__).parent.parent
    output_file = root / f"test_results/citation_test_{job_id}.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(result_data, f, indent=2)
    
    print(f"\n💾 Full results saved to: {output_file}")
    
    # Also save HTML for visual inspection
    result = result_data.get("result", {})
    html = result.get("analysis_html", "")
    if html:
        html_file = root / f"test_results/citation_test_{job_id}.html"
        with open(html_file, "w") as f:
            f.write(html)
        print(f"💾 HTML output saved to: {html_file}")

def main():
    print("="*70)
    print("ENHANCED SINGLE-PASS CITATION TEST")
    print("="*70)
    print("\nThis test validates that reference images and quotes appear")
    print("in the analysis output when using the enhanced single-pass approach.")
    print("="*70)
    
    # Step 1: Check service health
    if not check_service_health():
        return 1
    
    # Step 2: Find test image
    test_image = get_test_image()
    if not test_image:
        return 1
    
    # Step 3: Submit analysis job
    job_id = submit_analysis_job(test_image)
    if not job_id:
        return 1
    
    # Step 4: Wait for completion
    result_data = wait_for_completion(job_id)
    if not result_data:
        return 1
    
    # Step 5: Analyze citations
    success = analyze_citations(result_data)
    
    # Step 6: Save debug output
    save_debug_output(job_id, result_data)
    
    # Final summary
    print("\n" + "="*70)
    if success:
        print("✅ TEST PASSED: Citations are working correctly")
        print("="*70)
        return 0
    else:
        print("❌ TEST FAILED: Citations not appearing as expected")
        print("="*70)
        print("\nTroubleshooting:")
        print("1. Check that ENABLE_CITATIONS=True in ai_advisor_service_linux.py")
        print("2. Verify reference images have embeddings: python scripts/compute_embeddings.py --advisor ansel --verify-only")
        print("3. Check book passages exist: sqlite3 mondrian.db 'SELECT COUNT(*) FROM book_passages WHERE advisor_id=\"ansel\"'")
        print("4. Review system prompt and advisor prompt for citation instructions")
        print("5. Check service logs for citation validation messages")
        return 1

if __name__ == "__main__":
    sys.exit(main())
