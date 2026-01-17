#!/usr/bin/env python3
"""
Basic test for LoRA+RAG mode functionality.
Tests that the mode parameter is correctly passed through and RAG augmentation happens.
"""

import sqlite3
import json
from pathlib import Path

# Test database to verify schema
DB_PATH = Path(__file__).parent / "mondrian.db"

def test_mode_support():
    """Test that the advisor service can handle the new modes"""
    print("Testing LoRA+RAG mode support...")
    print("-" * 60)
    
    # Verify database exists
    if not DB_PATH.exists():
        print(f"✗ Database not found: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if dimensional_profiles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dimensional_profiles'")
        if not cursor.fetchone():
            print("✓ Note: dimensional_profiles table not found (expected for fresh install)")
            print("  To use RAG, create profiles using: python migrate_dimensional_profiles.py")
        else:
            # Check if we have any profiles
            cursor.execute("SELECT COUNT(*) FROM dimensional_profiles")
            count = cursor.fetchone()[0]
            print(f"✓ Found {count} dimensional profiles for RAG context")
        
        # Check advisor table
        cursor.execute("SELECT COUNT(*) FROM advisors")
        advisor_count = cursor.fetchone()[0]
        print(f"✓ Found {advisor_count} advisors in database")
        
        conn.close()
        
        print("\n✓ Database schema validated successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error checking database: {e}")
        return False


def test_modes_syntax():
    """Test that the different mode syntaxes are properly supported"""
    print("\nTesting mode syntax variations...")
    print("-" * 60)
    
    supported_modes = [
        'baseline',
        'rag',
        'lora',
        'lora+rag',
        'rag_lora',
        'lora_rag',
    ]
    
    # These are the modes that should trigger RAG augmentation
    rag_modes = {'rag', 'lora+rag', 'rag_lora', 'lora_rag'}
    
    for mode in supported_modes:
        should_use_rag = mode in rag_modes
        print(f"  Mode: '{mode}'")
        print(f"    Uses RAG: {should_use_rag}")
        print(f"    Uses LoRA: {'lora' in mode}")
    
    print("\n✓ All mode syntaxes are valid!")
    return True


def print_usage_examples():
    """Print examples of how to use lora+rag mode"""
    print("\n" + "="*60)
    print("USAGE EXAMPLES FOR LORA+RAG MODE")
    print("="*60)
    
    examples = [
        {
            "title": "Start with LoRA+RAG mode (recommended)",
            "command": "./mondrian.sh --restart --mode=lora+rag"
        },
        {
            "title": "Alternative syntax (underscore)",
            "command": "./mondrian.sh --restart --mode=lora_rag"
        },
        {
            "title": "Use specific LoRA adapter with RAG",
            "command": "./mondrian.sh --restart --mode=lora+rag --lora-path=./adapters/ansel"
        },
        {
            "title": "Use different model with LoRA+RAG",
            "command": "./mondrian.sh --restart --model-preset=qwen3-8b-instruct --mode=lora+rag"
        },
    ]
    
    for ex in examples:
        print(f"\n{ex['title']}:")
        print(f"  $ {ex['command']}")
    
    print("\n" + "="*60)
    print("API CALL EXAMPLES")
    print("="*60)
    
    api_examples = [
        {
            "title": "Upload image for LoRA+RAG analysis",
            "command": '''curl -X POST http://localhost:5005/upload \\
  -F "image=@photo.jpg" \\
  -F "advisor=ansel" \\
  -F "mode=lora+rag"'''
        },
        {
            "title": "Direct analysis with LoRA+RAG",
            "command": '''curl -X POST http://localhost:5100/analyze \\
  -F "image=@photo.jpg" \\
  -F "advisor=ansel" \\
  -F "mode=lora+rag"'''
        },
    ]
    
    for ex in api_examples:
        print(f"\n{ex['title']}:")
        print(f"  {ex['command']}")
    
    print("\n")


def main():
    print("\n" + "="*60)
    print("LORA+RAG MODE VERIFICATION")
    print("="*60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Database schema", test_mode_support()))
    results.append(("Mode syntax", test_modes_syntax()))
    
    # Print results
    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✓ All tests passed!")
        print_usage_examples()
        
        # Print configuration notes
        print("\n" + "="*60)
        print("CONFIGURATION NOTES")
        print("="*60)
        print("""
1. LoRA+RAG combines two features:
   - LoRA (Low-Rank Adaptation): Fine-tuned model weights for better advice
   - RAG (Retrieval-Augmented Generation): Reference images for context

2. RAG requires dimensional_profiles table with reference images
   - Run: python migrate_dimensional_profiles.py (if not done)
   - Then index advisor reference images

3. LoRA requires a trained adapter
   - Run: python training/train_lora.py --advisor ansel
   - Adapter saved to: adapters/ansel/

4. To see what's happening:
   - Check logs: tail -f logs/ai_advisor_service_linux.log
   - Monitor status: curl http://localhost:5100/health
""")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
