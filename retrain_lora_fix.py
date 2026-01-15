#!/usr/bin/env python3
"""
Quick LoRA Retraining Script
Retrains the ansel adapter with CORRECT image analysis data instead of philosophy text
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Configuration
CORRECT_TRAINING_DATA = "training/datasets/ansel_image_training_nuanced.jsonl"
CURRENT_ADAPTER = "adapters/ansel"
NEW_ADAPTER_DIR = "adapters/ansel_new"

# Training hyperparameters (match original config)
EPOCHS = 3
BATCH_SIZE = 1
LEARNING_RATE = "5e-05"

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_step(num, text):
    """Print a numbered step"""
    print(f"\n[{num}/4] {text}")
    print("-" * 70)

def print_success(text):
    """Print success message"""
    print(f"  ✓ {text}")

def print_error(text):
    """Print error message"""
    print(f"  ✗ {text}")

def print_info(text):
    """Print info message"""
    print(f"  ℹ {text}")

def main():
    print_header("LORA ADAPTER RETRAINING")
    print("""
PROBLEM: Current adapter was trained on philosophy text (ansel_combined_train.jsonl)
SOLUTION: Retrain with image analysis data (ansel_image_training_nuanced.jsonl)

This will:
  1. Verify the correct training data exists
  2. Train a new adapter with image analysis examples
  3. Replace the old adapter with the new one
  4. Keep backup of old adapter
""")
    
    # Step 1: Verify training data
    print_step(1, "Verifying correct training data")
    
    if not os.path.exists(CORRECT_TRAINING_DATA):
        print_error(f"Training data not found: {CORRECT_TRAINING_DATA}")
        sys.exit(1)
    
    print_success(f"Training data found: {CORRECT_TRAINING_DATA}")
    
    with open(CORRECT_TRAINING_DATA) as f:
        lines = sum(1 for _ in f)
    print_info(f"Training examples: {lines}")
    
    # Show sample of training data
    with open(CORRECT_TRAINING_DATA) as f:
        import json
        first_example = json.loads(f.readline())
    
    print_info(f"Sample format:")
    print_info(f"  - Messages: {len(first_example.get('messages', []))} (user + assistant)")
    if 'messages' in first_example and len(first_example['messages']) > 1:
        assistant_msg = first_example['messages'][1].get('content', '')
        if '"dimensional_analysis"' in assistant_msg:
            print_success("  Contains full dimensional_analysis JSON ✓")
    
    # Step 2: Check current state
    print_step(2, "Checking current adapter")
    
    if os.path.exists(CURRENT_ADAPTER):
        adapter_size = sum(os.path.getsize(os.path.join(CURRENT_ADAPTER, f)) 
                          for f in os.listdir(CURRENT_ADAPTER) 
                          if os.path.isfile(os.path.join(CURRENT_ADAPTER, f)))
        print_info(f"Current adapter size: {adapter_size / 1024 / 1024:.1f}MB")
        print_info(f"Current adapter will be backed up before replacement")
    else:
        print_info("No existing adapter found")
    
    # Step 3: Run training
    print_step(3, "Training new adapter with correct data")
    
    print_info("Starting training...")
    print_info(f"  Model: mlx-community/Qwen3-VL-4B-Instruct-4bit")
    print_info(f"  Data: {CORRECT_TRAINING_DATA}")
    print_info(f"  Output: {NEW_ADAPTER_DIR}")
    print_info(f"  Epochs: {EPOCHS}")
    print_info(f"  Batch size: {BATCH_SIZE}")
    print_info(f"  Learning rate: {LEARNING_RATE}")
    print("\n  This will take 10-30 minutes depending on GPU speed...")
    print()
    
    cmd = [
        sys.executable, "train_mlx_lora.py",
        "--train_data", CORRECT_TRAINING_DATA,
        "--output_dir", NEW_ADAPTER_DIR,
        "--epochs", str(EPOCHS),
        "--batch_size", str(BATCH_SIZE),
        "--learning_rate", LEARNING_RATE,
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print_error("Training failed!")
        sys.exit(1)
    
    print_success("Training completed successfully!")
    
    # Step 4: Install new adapter
    print_step(4, "Installing new adapter")
    
    # Backup old adapter
    if os.path.exists(CURRENT_ADAPTER):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"{CURRENT_ADAPTER}_backup_{timestamp}"
        print_info(f"Backing up old adapter to: {backup_dir}")
        shutil.move(CURRENT_ADAPTER, backup_dir)
        print_success(f"Backup complete")
    
    # Install new adapter
    print_info(f"Installing new adapter...")
    shutil.move(NEW_ADAPTER_DIR, CURRENT_ADAPTER)
    print_success(f"New adapter installed to: {CURRENT_ADAPTER}")
    
    # Summary
    print_header("RETRAINING COMPLETE!")
    
    print("""
Next steps:

  1. Start the AI Advisor Service:
     python3 mondrian/start_services.py

  2. Test the new LoRA adapter:
     python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora

  3. Compare all modes side-by-side:
     python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare

Troubleshooting:

  If you still see incomplete JSON output, check:
    • tail -50 logs/ai_advisor_service_*.log | grep "JSON PARSER"
    • The training may have been too short (only 21 examples)
    • Consider generating more training data from baseline model outputs
    
  To see detailed model output:
    • curl -X POST http://127.0.0.1:5100/analyze \\
        -F "image=@source/mike-shrub.jpg" \\
        -F "advisor=ansel" \\
        -F "mode=lora" 2>/dev/null | python3 -m json.tool | head -100
""")

if __name__ == "__main__":
    main()
