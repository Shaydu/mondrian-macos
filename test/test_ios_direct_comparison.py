#!/usr/bin/env python3
"""
iOS Direct Comparison Test: RAG vs Baseline
Directly calls AI Advisor Service to compare RAG and baseline outputs
"""

import requests
import json
from pathlib import Path
from datetime import datetime
import re

# Configuration
AI_ADVISOR_URL = "http://127.0.0.1:5100"
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
NC = '\033[0m'

def print_header(text):
    print(f"\n{CYAN}{'='*80}{NC}")
    print(f"{CYAN}{BOLD}{text}{NC}")
    print(f"{CYAN}{'='*80}{NC}\n")

def print_success(text):
    print(f"{GREEN}✓{NC} {text}")

def print_error(text):
    print(f"{RED}✗{NC} {text}")

def print_info(text):
    print(f"{YELLOW}ℹ{NC} {text}")

def analyze_image(enable_rag=False):
    """Call AI Advisor Service directly"""
    mode = "RAG-ENABLED" if enable_rag else "BASELINE"
    print_header(f"Direct Analysis: {mode}")
    
    image_path = Path(TEST_IMAGE).resolve()
    if not image_path.exists():
        print_error(f"Test image not found: {TEST_IMAGE}")
        return None
    
    print_info(f"Image: {image_path}")
    print_info(f"Advisor: {ADVISOR}")
    print_info(f"RAG Enabled: {enable_rag}")
    
    payload = {
        "advisor": ADVISOR,
        "image_path": str(image_path),
        "enable_rag": "true" if enable_rag else "false"
    }
    
    try:
        print_info("Sending request to AI Advisor Service...")
        resp = requests.post(f"{AI_ADVISOR_URL}/analyze", json=payload, timeout=120)
        
        if resp.status_code == 200:
            # Try to parse as JSON first
            try:
                result = resp.json()
                html = result.get('html', '')
            except:
                # If not JSON, treat as HTML directly
                html = resp.text
            
            if not html:
                print_error("Empty response from AI service")
                print_info(f"Response text: {resp.text[:500]}")
                return None
            
            print_success(f"Analysis complete ({len(html)} bytes)")
            
            # Save output
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ios_direct_{mode.lower()}_{timestamp}.html"
            filepath = Path("analysis_output") / filename
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print_success(f"Saved to: {filepath}")
            return html
        else:
            print_error(f"Analysis failed: {resp.status_code}")
            print_error(f"Response: {resp.text[:500]}")
            return None
            
    except Exception as e:
        print_error(f"Exception: {e}")
        import traceback
        print_error(traceback.format_exc())
        return None

def extract_feedback_text(html):
    """Extract all feedback text from HTML"""
    # Remove HTML tags
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    # Clean up whitespace
    text = ' '.join(text.split())
    return text

def extract_scores(html):
    """Extract dimensional scores from HTML"""
    scores = {}
    patterns = [
        (r'Composition.*?\((\d+\.?\d*)/10\)', 'Composition'),
        (r'Lighting.*?\((\d+\.?\d*)/10\)', 'Lighting'),
        (r'Focus.*?\((\d+\.?\d*)/10\)', 'Focus & Sharpness'),
        (r'Color Harmony.*?\((\d+\.?\d*)/10\)', 'Color Harmony'),
        (r'Subject Isolation.*?\((\d+\.?\d*)/10\)', 'Subject Isolation'),
        (r'Depth.*?\((\d+\.?\d*)/10\)', 'Depth & Perspective'),
        (r'Visual Balance.*?\((\d+\.?\d*)/10\)', 'Visual Balance'),
        (r'Emotional Impact.*?\((\d+\.?\d*)/10\)', 'Emotional Impact'),
        (r'Overall Grade:\s*(\d+\.?\d*)/10', 'Overall'),
    ]
    
    for pattern, name in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            scores[name] = float(match.group(1))
    
    return scores

def compare_outputs(baseline_html, rag_html):
    """Compare baseline and RAG outputs"""
    print_header("DETAILED COMPARISON")
    
    # Extract text
    baseline_text = extract_feedback_text(baseline_html)
    rag_text = extract_feedback_text(rag_html)
    
    # Extract scores
    baseline_scores = extract_scores(baseline_html)
    rag_scores = extract_scores(rag_html)
    
    # Show scores comparison
    print(f"{BOLD}DIMENSIONAL SCORES:{NC}\n")
    print(f"{'Dimension':<25} {'Baseline':>10} {'RAG':>10} {'Diff':>10}")
    print(f"{'-'*60}")
    
    for dimension in baseline_scores:
        baseline_val = baseline_scores.get(dimension, 0)
        rag_val = rag_scores.get(dimension, 0)
        diff = rag_val - baseline_val
        diff_str = f"{diff:+.1f}" if diff != 0 else "0.0"
        
        color = GREEN if abs(diff) > 0.1 else NC
        print(f"{dimension:<25} {baseline_val:>10.1f} {rag_val:>10.1f} {color}{diff_str:>10}{NC}")
    
    # Text comparison
    print(f"\n{BOLD}TEXT COMPARISON:{NC}\n")
    
    print(f"{BOLD}Baseline length:{NC} {len(baseline_text)} characters")
    print(f"{BOLD}RAG length:{NC} {len(rag_text)} characters")
    
    # Calculate similarity
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, baseline_text, rag_text).ratio()
    print(f"\n{BOLD}Text Similarity:{NC} {similarity*100:.1f}%")
    
    if similarity > 0.95:
        print_error("⚠️  Outputs are >95% similar - RAG may not be working")
    elif similarity > 0.8:
        print_info("Outputs are 80-95% similar - RAG is making subtle changes")
    else:
        print_success("Outputs are <80% similar - RAG is significantly different")
    
    # Show sample differences
    print(f"\n{BOLD}BASELINE SAMPLE (first 800 chars):{NC}")
    print(baseline_text[:800])
    print(f"\n{BOLD}RAG SAMPLE (first 800 chars):{NC}")
    print(rag_text[:800])
    
    # Check for RAG-specific indicators
    rag_indicators = [
        "similar", "reference", "compared to", "like", "reminiscent",
        "historical", "previous", "example", "demonstrates"
    ]
    
    baseline_indicators = sum(1 for ind in rag_indicators if ind.lower() in baseline_text.lower())
    rag_indicators_count = sum(1 for ind in rag_indicators if ind.lower() in rag_text.lower())
    
    print(f"\n{BOLD}RAG INDICATOR WORDS:{NC}")
    print(f"Baseline: {baseline_indicators} occurrences")
    print(f"RAG: {rag_indicators_count} occurrences")
    
    if rag_indicators_count > baseline_indicators:
        print_success("✓ RAG output contains more comparative/reference language")
    else:
        print_error("⚠️  RAG output doesn't show expected comparative language")

def main():
    print_header("iOS Direct Comparison Test")
    print(f"Test Image: {TEST_IMAGE}")
    print(f"Advisor: {ADVISOR}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check service
    try:
        resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
        if resp.status_code == 200:
            print_success("AI Advisor Service is running")
        else:
            print_error("AI Advisor Service health check failed")
            return
    except Exception as e:
        print_error(f"AI Advisor Service not available: {e}")
        return
    
    # Run baseline analysis
    baseline_html = analyze_image(enable_rag=False)
    if not baseline_html:
        print_error("Baseline analysis failed")
        return
    
    print_info("\nWaiting 3 seconds before RAG test...")
    import time
    time.sleep(3)
    
    # Run RAG analysis
    rag_html = analyze_image(enable_rag=True)
    if not rag_html:
        print_error("RAG analysis failed")
        return
    
    # Compare
    compare_outputs(baseline_html, rag_html)
    
    print_header("TEST COMPLETE")
    print_success("Both analyses completed successfully")
    print_info("Check analysis_output/ directory for HTML files")

if __name__ == "__main__":
    main()

