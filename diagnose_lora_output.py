#!/usr/bin/env python3
"""
LoRA Output Diagnostic Script

Analyzes the LoRA model output issue and provides solutions.
The problem: LoRA model is producing incomplete JSON (only image_description field)
Expected: Complete JSON with dimensional_analysis, overall_grade, etc.
"""

import os
import sys
import json
from pathlib import Path

print("\n" + "="*70)
print("LORA OUTPUT DIAGNOSTIC TOOL")
print("="*70 + "\n")

# Check 1: Verify adapter files exist
print("[1] Checking LoRA adapter files...")
adapter_dir = Path("adapters/ansel")

files_to_check = [
    "adapters.safetensors",
    "training_config.json",
    "adapter_config.json"
]

all_exist = True
for fname in files_to_check:
    fpath = adapter_dir / fname
    exists = fpath.exists()
    size_str = f" ({fpath.stat().st_size / 1024:.1f}KB)" if exists else ""
    status = "✓" if exists else "✗"
    print(f"    {status} {fname}{size_str}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n    ⚠️  Some adapter files are missing!")
    sys.exit(1)

# Check 2: Analyze training config
print("\n[2] Training Configuration:")
with open(adapter_dir / "training_config.json") as f:
    config = json.load(f)

for key, value in config.items():
    print(f"    {key}: {value}")

# Check 3: Look at recent log entries
print("\n[3] Analyzing recent logs...")
log_dir = Path("logs")
log_files = sorted(log_dir.glob("ai_advisor_service_*.log"), reverse=True)[:3]

incomplete_json_count = 0
json_parse_errors = 0
successful_parses = 0

for log_file in log_files:
    with open(log_file) as f:
        content = f.read()
        
    # Count parsing issues
    incomplete_json_count += content.count("line 2 column 491")
    json_parse_errors += content.count("[JSON PARSER] All parsing strategies failed")
    successful_parses += content.count("[JSON PARSER] Strategy 1 (as-is) succeeded")

print(f"    Recent log files analyzed: {len(log_files)}")
print(f"    Incomplete JSON errors: {incomplete_json_count}")
print(f"    Complete JSON parsing failures: {json_parse_errors}")
print(f"    Successful parses: {successful_parses}")

# Check 4: Root cause analysis
print("\n" + "="*70)
print("ROOT CAUSE ANALYSIS")
print("="*70 + "\n")

print("""
The LoRA model is producing INCOMPLETE JSON output:
- Model generates only: {"image_description": "..."}
- Expected: Full JSON with dimensional_analysis, overall_grade, techniques, etc.
- Last char in output: a trailing comma (,)
- Output length: ~492 chars (should be 3000-5000+ chars)

POSSIBLE CAUSES:
""")

causes = [
    ("1. Training data was incomplete", [
        "The training JSONL file may have contained only 'image_description'",
        "during LoRA fine-tuning, causing the model to learn partial output",
        "Risk: HIGH - Most likely cause"
    ]),
    
    ("2. Model context window exhaustion", [
        "The model is hitting max token limits during generation",
        "However, lora.py sets max_tokens=8192, so unlikely",
        "Risk: LOW"
    ]),
    
    ("3. Prompt formatting issue", [
        "The system prompt or advisor prompt may be malformed",
        "causing the model to produce unexpected output structure",
        "Risk: MEDIUM"
    ]),
    
    ("4. Adapter corruption/incompatibility", [
        "The adapter may not be properly compatible with inference",
        "The adapter was trained with one config but loaded differently",
        "Risk: MEDIUM"
    ]),
]

for cause_title, details in causes:
    print(f"\n{cause_title}")
    for detail in details:
        print(f"  • {detail}")

# Check 5: Solutions
print("\n" + "="*70)
print("RECOMMENDED SOLUTIONS")
print("="*70 + "\n")

solutions = [
    {
        "title": "SOLUTION 1: Retrain the LoRA adapter",
        "description": "Train a new adapter with complete JSON output",
        "steps": [
            "1. Verify training data contains FULL JSON with all fields",
            "2. Run: python3 train_mlx_lora.py --advisor ansel --epochs 3",
            "3. Wait for training to complete (~30-60 min)",
            "4. Restart AI Advisor Service",
            "5. Test with: python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora",
        ],
        "time_estimate": "45 minutes",
        "reliability": "HIGH (most likely to fix)"
    },
    
    {
        "title": "SOLUTION 2: Use baseline or RAG mode instead",
        "description": "Work around the broken LoRA by using working modes",
        "steps": [
            "1. Test baseline mode: python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline",
            "2. Test RAG mode: python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag",
            "3. Both should produce complete output",
            "4. Use RAG mode as primary until LoRA is fixed",
        ],
        "time_estimate": "5 minutes",
        "reliability": "VERY HIGH (immediate workaround)"
    },
    
    {
        "title": "SOLUTION 3: Debug the training data",
        "description": "Check if training data contains complete JSON",
        "steps": [
            "1. Check training data: ls -lh training/ansel_training_data.jsonl",
            "2. Inspect first example: head -1 training/ansel_training_data.jsonl | python3 -m json.tool",
            "3. Check if JSON has all required fields (dimensional_analysis, overall_grade, etc.)",
            "4. If incomplete, regenerate training data with complete outputs",
            "5. Retrain adapter with corrected data",
        ],
        "time_estimate": "30 minutes",
        "reliability": "HIGH"
    },
    
    {
        "title": "SOLUTION 4: Clear LoRA cache and retry",
        "description": "Force reload of the model/adapter",
        "steps": [
            "1. Stop AI Advisor Service (Ctrl+C)",
            "2. Clear cache: rm -rf ~/.cache/mlx* (if applicable)",
            "3. Clear Python cache: find mondrian -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null",
            "4. Restart services: python3 mondrian/start_services.py",
            "5. Test again",
        ],
        "time_estimate": "2 minutes",
        "reliability": "VERY LOW (unlikely to help)"
    },
]

for i, sol in enumerate(solutions, 1):
    print(f"\n{'─'*70}")
    print(f"{sol['title']}")
    print(f"Reliability: {sol['reliability']} | Est. Time: {sol['time_estimate']}")
    print(f"{'─'*70}")
    print(f"\n{sol['description']}\n")
    print("Steps:")
    for step in sol['steps']:
        print(f"  {step}")

# Check 6: Immediate action
print("\n" + "="*70)
print("IMMEDIATE ACTIONS")
print("="*70 + "\n")

print("""
RECOMMENDED: Use Solution 2 (immediate workaround) while doing Solution 1 (fix)

Quick test to confirm:
  1. Test baseline (should work):
     python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
  
  2. Test LoRA (currently broken):
     python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
  
  3. Check training data integrity:
     head -1 training/ansel_training_data.jsonl | python3 -m json.tool | head -20

Then decide: Is baseline sufficient, or must we retrain LoRA?
""")

print("\n" + "="*70 + "\n")
