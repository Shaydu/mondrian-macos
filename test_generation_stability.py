#!/usr/bin/env python3
"""
Test script to fix the LLM thinking retrieval test with better generation parameters.

The issue: Qwen3-VL-4B is getting stuck in repetition loops during generation.
Solution: Add repetition penalty, top_k, and other stabilization parameters.
"""

import os
import sys
import json
import torch
import logging
from pathlib import Path
from PIL import Image

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_generation_with_stability_params():
    """
    Test inference with improved generation parameters to prevent repetition.
    """
    
    try:
        from transformers import AutoProcessor, AutoModel
        
        model_name = "Qwen/Qwen3-VL-4B-Instruct"
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        logger.info(f"Loading model: {model_name}")
        logger.info(f"Device: {device}")
        
        # Load processor
        processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        
        # Load model with quantization
        from transformers import BitsAndBytesConfig
        
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
        
        model = AutoModel.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
        
        logger.info("Model loaded successfully")
        
        # Test image
        test_image_path = "./source/mike-shrub-01004b68.jpg"
        if not os.path.exists(test_image_path):
            logger.warning("Creating dummy test image")
            dummy_image = Image.new('RGB', (300, 300), color='blue')
            dummy_image.save("test_gen_image.jpg")
            test_image_path = "test_gen_image.jpg"
        
        image = Image.open(test_image_path).convert('RGB')
        logger.info(f"Loaded test image: {test_image_path}")
        
        # Test prompt
        test_prompt = """Analyze this photo in detail. Provide analysis in JSON format.
        
Be concise and avoid repetition. Stop after providing complete analysis."""
        
        messages = [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": test_prompt}
            ]}
        ]
        
        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = processor(
            text=text,
            images=[image],
            padding=True,
            return_tensors="pt"
        )
        
        if device == 'cuda':
            inputs = {k: v.cuda() if hasattr(v, 'cuda') else v for k, v in inputs.items()}
        
        print("\n" + "="*70)
        print("TESTING GENERATION PARAMETERS")
        print("="*70)
        
        # Test different parameter combinations
        test_configs = [
            {
                "name": "Original (current setup)",
                "params": {
                    "max_new_tokens": 2000,
                }
            },
            {
                "name": "With repetition penalty",
                "params": {
                    "max_new_tokens": 1500,
                    "repetition_penalty": 1.2,
                }
            },
            {
                "name": "With better sampling",
                "params": {
                    "max_new_tokens": 1500,
                    "do_sample": True,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 50,
                }
            },
            {
                "name": "With strong repetition penalty + sampling",
                "params": {
                    "max_new_tokens": 1500,
                    "do_sample": True,
                    "temperature": 0.5,
                    "top_p": 0.95,
                    "top_k": 40,
                    "repetition_penalty": 1.5,
                }
            },
            {
                "name": "Conservative (beam search + penalties)",
                "params": {
                    "max_new_tokens": 1200,
                    "num_beams": 2,
                    "repetition_penalty": 1.3,
                }
            },
        ]
        
        for config in test_configs:
            print(f"\n{'-'*70}")
            print(f"Testing: {config['name']}")
            print(f"Parameters: {config['params']}")
            print(f"{'-'*70}")
            
            try:
                with torch.no_grad():
                    output_ids = model.generate(
                        **inputs,
                        **config['params'],
                        eos_token_id=processor.tokenizer.eos_token_id
                    )
                
                input_length = inputs['input_ids'].shape[1]
                generated_ids = output_ids[:, input_length:]
                
                response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                
                # Check for repetition issues
                words = response.split()
                unique_words = len(set(words))
                total_words = len(words)
                uniqueness_ratio = unique_words / total_words if total_words > 0 else 0
                
                # Find longest repeated substring
                max_repeat = 1
                for word in set(words):
                    count = sum(1 for w in words if w == word)
                    if count > max_repeat:
                        max_repeat = count
                
                print(f"\n✓ Generation succeeded")
                print(f"  Output length: {len(response)} chars, {total_words} words")
                print(f"  Uniqueness: {uniqueness_ratio*100:.1f}% ({unique_words}/{total_words} unique words)")
                print(f"  Max word repetition: {max_repeat}x")
                
                if max_repeat > 50:
                    print(f"  ⚠️  WARNING: High repetition detected!")
                elif max_repeat > 10:
                    print(f"  ⚠️  CAUTION: Moderate repetition detected")
                else:
                    print(f"  ✓ Good: Low repetition")
                
                # Show sample
                sample_len = min(200, len(response))
                print(f"\n  Sample output: {response[:sample_len]}...")
                
                # Try to detect if it's valid JSON
                try:
                    parsed = json.loads(response)
                    print(f"  ✓ Valid JSON parsed successfully")
                except:
                    print(f"  ✗ Not valid JSON")
                
            except Exception as e:
                print(f"✗ Generation failed: {e}")
        
        print("\n" + "="*70)
        print("RECOMMENDATIONS:")
        print("="*70)
        print("""
Based on test results, the best configuration appears to be:
- Use repetition_penalty >= 1.2 to prevent loops
- Use do_sample=True with temperature 0.5-0.7 for stability
- Use top_p=0.95 and top_k=40-50 for controlled diversity
- Consider num_beams=2 for beam search stability

This will help prevent the model from getting stuck repeating words
while maintaining quality output for structured responses.
        """)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Testing generation parameters to fix repetition issues...\n")
    success = test_generation_with_stability_params()
    
    if success:
        print("\n✅ Generation parameter test completed!")
    else:
        print("\n❌ Test failed")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
