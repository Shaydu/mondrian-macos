#!/usr/bin/env python3
"""
Direct LoRA Strategy Test
Tests the LoRA strategy in isolation to debug model output
"""
import sys
import os
import json

# Add mondrian to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mondrian'))

from strategies.lora import LoRAStrategy

def test_lora_strategy():
    """Test LoRA strategy directly"""
    
    print("\n" + "="*70)
    print("LORA STRATEGY DIRECT TEST")
    print("="*70 + "\n")
    
    strategy = LoRAStrategy()
    advisor_id = "ansel"
    
    # Check if adapter is available
    print(f"[1] Checking if LoRA adapter is available for '{advisor_id}'...")
    if not strategy.is_available(advisor_id):
        print(f"    ❌ LoRA adapter not available for {advisor_id}")
        print(f"    Expected path: {strategy._get_adapter_path(advisor_id)}/adapters.safetensors")
        sys.exit(1)
    
    print(f"    ✓ LoRA adapter found")
    print(f"    Path: {strategy._get_adapter_path(advisor_id)}")
    
    # Check image exists
    image_path = "source/mike-shrub.jpg"
    if not os.path.exists(image_path):
        print(f"\n[2] ❌ Image not found: {image_path}")
        sys.exit(1)
    
    print(f"\n[2] Image file: {image_path} ✓")
    
    # Mock config
    class MockConfig:
        pass
    
    config = MockConfig()
    
    print(f"\n[3] Running LoRA analysis...")
    print(f"    Advisor: {advisor_id}")
    print(f"    Image: {image_path}")
    print(f"    " + "-"*60)
    
    try:
        result = strategy.analyze(
            image_path=image_path,
            advisor_id=advisor_id,
            config=config,
            thinking_callback=lambda msg: print(f"    [Thinking] {msg}")
        )
        
        print(f"\n    " + "-"*60)
        print(f"    ✓ Analysis completed successfully!")
        
        print("\n" + "="*70)
        print("ANALYSIS RESULT SUMMARY")
        print("="*70)
        print(f"\nMode used: {result.mode_used}")
        print(f"Overall grade: {result.overall_grade}")
        print(f"Advisor ID: {result.advisor_id}")
        
        print(f"\nDimensional Analysis Keys: {list(result.dimensional_analysis.keys())}")
        print(f"Dimensional Analysis Size: {len(json.dumps(result.dimensional_analysis))} chars")
        
        if result.dimensional_analysis:
            print(f"\nDimensional Analysis (first 1000 chars):")
            dim_str = json.dumps(result.dimensional_analysis, indent=2)
            print(dim_str[:1000])
            if len(dim_str) > 1000:
                print(f"... [{len(dim_str) - 1000} more characters]")
        else:
            print(f"\n⚠️  WARNING: dimensional_analysis is EMPTY!")
        
        print(f"\nMetadata:")
        print(json.dumps(result.metadata, indent=2))
        
        print("\n" + "="*70)
        print("✓ TEST PASSED - Model produced valid output")
        print("="*70 + "\n")
        
        return True
        
    except ValueError as e:
        print(f"\n    " + "-"*60)
        print(f"    ❌ ValueError: {e}")
        print(f"\nThis error means the model output couldn't be parsed as JSON.")
        print(f"This is the root cause of the end-to-end test failure.")
        return False
        
    except Exception as e:
        print(f"\n    " + "-"*60)
        print(f"    ❌ {type(e).__name__}: {e}")
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_lora_strategy()
    sys.exit(0 if success else 1)
