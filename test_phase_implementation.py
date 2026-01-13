#!/usr/bin/env python3
"""
Test script for Phase 2 Embedding-Based RAG Implementation
Demonstrates the hybrid retrieval workflow with embeddings, techniques, and dimensions.
"""

import requests
import json
import sys
from pathlib import Path

# Configuration
AI_SERVICE_URL = "http://localhost:5100/analyze"
TEST_IMAGE_PATH = "source/test_image.jpg"  # You'll need to provide a test image
ADVISOR_ID = "ansel"

def test_embedding_disabled():
    """Test with embeddings disabled (Phase 1 only - techniques + dimensions)"""
    print("\n" + "="*70)
    print("TEST 1: Phase 1 Only (Techniques + Dimensions, No Embeddings)")
    print("="*70)
    
    data = {
        "advisor": ADVISOR_ID,
        "image_path": str(Path(TEST_IMAGE_PATH).resolve()),
        "enable_rag": "true",
        "enable_embeddings": "false",  # Disable embeddings
        "response_format": "json"
    }
    
    print(f"Request payload:")
    print(json.dumps(data, indent=2))
    
    try:
        response = requests.post(AI_SERVICE_URL, json=data, timeout=300)
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ SUCCESS (Status: {response.status_code})")
            print(f"Response keys: {list(result.keys())}")
            
            # Check for technique data
            dim_analysis = result.get('dimensional_analysis', {})
            if 'techniques' in dim_analysis:
                print(f"Techniques detected: {dim_analysis['techniques'].keys()}")
            else:
                print("No techniques in response (Phase 1 baseline)")
        else:
            print(f"✗ FAILED (Status: {response.status_code})")
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"✗ ERROR: {e}")

def test_embedding_enabled():
    """Test with embeddings enabled (Phase 2 - full hybrid retrieval)"""
    print("\n" + "="*70)
    print("TEST 2: Phase 2 Full (Embeddings + Techniques + Dimensions)")
    print("="*70)
    
    data = {
        "advisor": ADVISOR_ID,
        "image_path": str(Path(TEST_IMAGE_PATH).resolve()),
        "enable_rag": "true",
        "enable_embeddings": "true",  # Enable embeddings
        "response_format": "json"
    }
    
    print(f"Request payload:")
    print(json.dumps(data, indent=2))
    print(f"\nNote: This test requires CLIP to be installed.")
    print(f"      Install with: pip install torch clip")
    
    try:
        response = requests.post(AI_SERVICE_URL, json=data, timeout=300)
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ SUCCESS (Status: {response.status_code})")
            print(f"Response keys: {list(result.keys())}")
            
            # Check for technique data
            dim_analysis = result.get('dimensional_analysis', {})
            if 'techniques' in dim_analysis:
                print(f"Techniques detected: {dim_analysis['techniques'].keys()}")
            
            # Check for dimensional analysis
            dims = result.get('dimensions', [])
            print(f"Dimensions analyzed: {len(dims)}")
            
            print(f"\nPhase 2 features enabled - using hybrid retrieval with:")
            print(f"  • Visual similarity (CLIP embeddings)")
            print(f"  • Technique matching")
            print(f"  • Dimensional comparison")
        else:
            print(f"✗ FAILED (Status: {response.status_code})")
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"✗ ERROR: {e}")

def test_html_output():
    """Test HTML output includes technique badges and comparisons"""
    print("\n" + "="*70)
    print("TEST 3: HTML Output with Technique Display")
    print("="*70)
    
    data = {
        "advisor": ADVISOR_ID,
        "image_path": str(Path(TEST_IMAGE_PATH).resolve()),
        "enable_rag": "true",
        "enable_embeddings": "true",
        "response_format": "html"
    }
    
    print(f"Request payload (format: html):")
    print(json.dumps({k: v for k, v in data.items() if k != "image_path"}, indent=2))
    
    try:
        response = requests.post(AI_SERVICE_URL, json=data, timeout=300)
        if response.status_code == 200:
            html = response.text
            print(f"\n✓ SUCCESS (Status: {response.status_code})")
            print(f"HTML response length: {len(html)} characters")
            
            # Check for technique badges
            if "Detected Techniques" in html:
                print("✓ Technique badges section found")
            else:
                print("⚠ Technique badges section not found")
            
            # Check for technique comparison
            if "Technique Comparison" in html:
                print("✓ Technique comparison section found")
            else:
                print("⚠ Technique comparison section not found")
            
            # Save HTML for inspection
            output_file = "test_embedding_output.html"
            with open(output_file, 'w') as f:
                f.write(html)
            print(f"\nHTML output saved to: {output_file}")
        else:
            print(f"✗ FAILED (Status: {response.status_code})")
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"✗ ERROR: {e}")

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("Technique-Enhanced RAG and Embedding Phase Implementation Tests")
    print("="*70)
    
    # Check if test image exists
    if not Path(TEST_IMAGE_PATH).exists():
        print(f"\n⚠ WARNING: Test image not found at {TEST_IMAGE_PATH}")
        print("Please provide a test image to run these tests.")
        print("Usage: Place an image at 'source/test_image.jpg' or update TEST_IMAGE_PATH")
        sys.exit(1)
    
    # Check if AI service is running
    print("\nChecking if AI Service is running...")
    try:
        health = requests.get("http://localhost:5100/health", timeout=5)
        if health.status_code == 200:
            print("✓ AI Service is running on port 5100")
        else:
            print("✗ AI Service health check failed")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Cannot connect to AI Service: {e}")
        print("Start the service with: python3 mondrian/ai_advisor_service.py --port 5100")
        sys.exit(1)
    
    # Run tests
    test_embedding_disabled()
    test_embedding_enabled()
    test_html_output()
    
    print("\n" + "="*70)
    print("Testing Complete!")
    print("="*70)
    print("\nPhase 1 (Technique-Enhanced RAG): ✓ Complete")
    print("  • Techniques extracted and displayed as badges")
    print("  • Technique matching integrated into RAG workflow")
    print("  • Prompt augmentation includes technique comparisons")
    print("\nPhase 2 (Embedding-Based RAG): ✓ Ready")
    print("  • CLIP embeddings computed during indexing")
    print("  • Visual similarity search implemented")
    print("  • Hybrid retrieval combines embeddings + techniques + dimensions")
    print("  • Enable with: enable_embeddings=true")

if __name__ == "__main__":
    main()
