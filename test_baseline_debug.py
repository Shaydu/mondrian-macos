#!/usr/bin/env python3
"""
Debug script to test baseline mode and see raw model output.
This will help diagnose why dimensional_analysis is empty.
"""

import sys
import os
import json

# Add mondrian directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mondrian'))

from mondrian.ai_advisor_service import (
    get_advisor_metadata,
    SYSTEM_PROMPT,
    run_model_mlx,
)
from mondrian.json_to_html_converter import parse_json_response

def test_baseline_analysis(image_path: str, advisor_id: str = "ansel"):
    """Test baseline analysis and show raw output"""
    
    print("=" * 80)
    print("BASELINE MODE DEBUG TEST")
    print("=" * 80)
    print(f"Image: {image_path}")
    print(f"Advisor: {advisor_id}")
    print()
    
    # Get advisor prompt
    print("[1/5] Loading advisor metadata...")
    advisor_metadata = get_advisor_metadata(advisor_id)
    if not advisor_metadata or not advisor_metadata.get("prompt"):
        print(f"ERROR: Advisor prompt not found: {advisor_id}")
        return False
    
    adv_prompt = advisor_metadata["prompt"]
    print(f"✓ Advisor prompt loaded ({len(adv_prompt)} characters)")
    print()
    
    # Build full prompt
    print("[2/5] Building prompt...")
    full_prompt = (
        SYSTEM_PROMPT.replace("<AdvisorName>", advisor_id)
        + "\n\n"
        + adv_prompt
        + "\n\nAnalyze the provided image."
    )
    print(f"✓ Full prompt built ({len(full_prompt)} characters)")
    print()
    print("System prompt preview (first 500 chars):")
    print("-" * 80)
    print(SYSTEM_PROMPT[:500])
    print("-" * 80)
    print()
    
    # Run model
    print("[3/5] Running MLX model...")
    print("This may take 30-60 seconds...")
    response = run_model_mlx(full_prompt, image_path=image_path)
    print(f"✓ Model completed")
    print(f"✓ Response length: {len(response)} characters")
    print()
    
    # Show raw response
    print("[4/5] RAW MODEL OUTPUT:")
    print("=" * 80)
    print(response)
    print("=" * 80)
    print()
    
    # Parse JSON
    print("[5/5] Parsing JSON response...")
    json_data = parse_json_response(response)
    
    if not json_data:
        print("✗ ERROR: Could not parse model response as JSON")
        return False
    
    print("✓ JSON parsed successfully")
    print()
    
    # Analyze the parsed JSON
    print("PARSED JSON STRUCTURE:")
    print("=" * 80)
    print(json.dumps(json_data, indent=2))
    print("=" * 80)
    print()
    
    # Check for dimensions
    print("DIMENSION ANALYSIS:")
    print("-" * 80)
    
    if "dimensions" in json_data:
        dims = json_data["dimensions"]
        print(f"✓ 'dimensions' key found (type: {type(dims).__name__})")
        if isinstance(dims, list):
            print(f"✓ dimensions is a list with {len(dims)} items")
            if len(dims) == 0:
                print("✗ WARNING: dimensions list is EMPTY!")
            else:
                print("\nDimensions found:")
                for i, dim in enumerate(dims, 1):
                    if isinstance(dim, dict):
                        name = dim.get('name', 'Unknown')
                        score = dim.get('score', 'N/A')
                        has_comment = 'comment' in dim and dim['comment']
                        has_rec = 'recommendation' in dim and dim['recommendation']
                        print(f"  {i}. {name}: {score}/10 "
                              f"(comment: {has_comment}, recommendation: {has_rec})")
                    else:
                        print(f"  {i}. {dim} (not a dict)")
        else:
            print(f"✗ WARNING: dimensions is not a list, it's a {type(dims).__name__}")
    else:
        print("✗ 'dimensions' key NOT found in JSON")
    
    if "dimensional_analysis" in json_data:
        dim_analysis = json_data["dimensional_analysis"]
        print(f"\n✓ 'dimensional_analysis' key found (type: {type(dim_analysis).__name__})")
        if isinstance(dim_analysis, dict):
            print(f"✓ dimensional_analysis is a dict with {len(dim_analysis)} keys")
            if len(dim_analysis) == 0:
                print("✗ WARNING: dimensional_analysis dict is EMPTY!")
            else:
                print("\nKeys in dimensional_analysis:")
                for key in dim_analysis.keys():
                    print(f"  - {key}")
        else:
            print(f"✗ WARNING: dimensional_analysis is not a dict")
    else:
        print("\n✗ 'dimensional_analysis' key NOT found in JSON")
    
    print("-" * 80)
    print()
    
    # Check other expected fields
    print("OTHER FIELDS:")
    print("-" * 80)
    for field in ["image_description", "overall_score", "overall_grade", 
                  "key_strengths", "priority_improvements", "technical_notes"]:
        if field in json_data:
            value = json_data[field]
            if isinstance(value, str):
                preview = value[:50] + "..." if len(value) > 50 else value
                print(f"✓ {field}: {preview}")
            elif isinstance(value, list):
                print(f"✓ {field}: [{len(value)} items]")
            else:
                print(f"✓ {field}: {value}")
        else:
            print(f"✗ {field}: NOT FOUND")
    print("-" * 80)
    print()
    
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug baseline mode analysis")
    parser.add_argument(
        "--image",
        type=str,
        default="source/mike-shrub-01004b68.jpg",
        help="Path to image file"
    )
    parser.add_argument(
        "--advisor",
        type=str,
        default="ansel",
        help="Advisor ID"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image):
        print(f"ERROR: Image file not found: {args.image}")
        sys.exit(1)
    
    success = test_baseline_analysis(args.image, args.advisor)
    sys.exit(0 if success else 1)
