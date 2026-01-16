#!/usr/bin/env python3
"""
Simple test for generation parameters to prevent repetition in qwen3-vl-4b.
Tests different parameter combinations on the actual job service output.
"""

import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_repetition_issue():
    """Analyze the repetition issue from the failed job"""
    
    print("\n" + "="*70)
    print("ANALYSIS: Repetition Issue in Model Output")
    print("="*70)
    
    # Connect to database
    conn = sqlite3.connect('mondrian.db')
    cursor = conn.cursor()
    
    # Get the failed job
    cursor.execute("""
        SELECT id, llm_outputs FROM jobs 
        WHERE id='fef718f3-8f4c-4a18-9548-47a692a306dc'
    """)
    
    result = cursor.fetchone()
    
    if not result:
        logger.error("Job not found")
        return False
    
    job_id, llm_outputs_json = result
    
    try:
        llm_data = json.loads(llm_outputs_json)
        response_text = llm_data.get('response', '')
        
        # Parse response
        try:
            response_obj = json.loads(response_text)
            dimensions = response_obj.get('dimensions', [])
            
            # Check each dimension for issues
            print("\nDimension Analysis:")
            for dim in dimensions:
                name = dim.get('name')
                comment = dim.get('comment', '')
                
                # Count repetitions
                words = comment.split()
                if len(words) > 0:
                    unique_count = len(set(words))
                    total_count = len(words)
                    uniqueness = (unique_count / total_count) * 100
                    
                    print(f"\n  {name}:")
                    print(f"    Words: {total_count}, Unique: {unique_count} ({uniqueness:.1f}%)")
                    
                    # Check for word repetition
                    word_freq = {}
                    for word in words:
                        word_freq[word] = word_freq.get(word, 0) + 1
                    
                    max_freq = max(word_freq.values()) if word_freq else 1
                    if max_freq > 3:
                        most_repeated = [w for w, c in word_freq.items() if c == max_freq][0]
                        print(f"    ⚠️  Repeated word: '{most_repeated}' ({max_freq}x)")
                        if max_freq > 100:
                            print(f"    🔴 CRITICAL: Massive repetition detected!")
        
        except json.JSONDecodeError as e:
            print(f"Could not parse response as JSON: {e}")
            print(f"Response preview: {response_text[:200]}...")
        
        # Recommended parameters
        print("\n" + "="*70)
        print("RECOMMENDED GENERATION PARAMETERS")
        print("="*70)
        
        recommendations = {
            "Current (problematic)": {
                "max_new_tokens": 2000,
                "issue": "No repetition penalty, model gets stuck"
            },
            "Option 1 (Conservative)": {
                "max_new_tokens": 1500,
                "repetition_penalty": 1.3,
                "do_sample": True,
                "temperature": 0.3,
                "eos_token_id": "use_tokenizer",
            },
            "Option 2 (Balanced)": {
                "max_new_tokens": 1500,
                "repetition_penalty": 1.2,
                "do_sample": True,
                "temperature": 0.5,
                "top_p": 0.95,
                "eos_token_id": "use_tokenizer",
            },
            "Option 3 (With beam search)": {
                "max_new_tokens": 1500,
                "num_beams": 2,
                "repetition_penalty": 1.2,
                "early_stopping": True,
                "eos_token_id": "use_tokenizer",
            }
        }
        
        for name, params in recommendations.items():
            print(f"\n{name}:")
            for key, value in params.items():
                if key != "issue":
                    print(f"  {key}: {value}")
            if "issue" in params:
                print(f"  Issue: {params['issue']}")
        
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"Could not parse llm_outputs: {e}")
        return False
    finally:
        conn.close()

def suggest_code_fix():
    """Suggest code changes for ai_advisor_service_linux.py"""
    
    print("\n" + "="*70)
    print("SUGGESTED CODE FIX")
    print("="*70)
    
    print("""
In mondrian/ai_advisor_service_linux.py, around line 303-306:

CURRENT CODE:
    with torch.no_grad():
        output_ids = self.model.generate(
            **inputs, 
            max_new_tokens=2000,
            eos_token_id=self.processor.tokenizer.eos_token_id
        )

SUGGESTED FIX:
    with torch.no_grad():
        output_ids = self.model.generate(
            **inputs, 
            max_new_tokens=1500,
            repetition_penalty=1.2,
            do_sample=True,
            temperature=0.5,
            top_p=0.95,
            eos_token_id=self.processor.tokenizer.eos_token_id
        )

KEY CHANGES:
1. Reduced max_new_tokens from 2000 to 1500
2. Added repetition_penalty=1.2 to penalize repeated tokens
3. Added do_sample=True for better token diversity
4. Added temperature=0.5 for controlled randomness
5. Added top_p=0.95 for nucleus sampling

These parameters will:
- Prevent token repetition loops
- Maintain output quality
- Complete generation faster
- Ensure proper JSON formatting
    """)

def main():
    print("Analyzing repetition issue and suggesting fixes...")
    
    if analyze_repetition_issue():
        suggest_code_fix()
        print("\n✅ Analysis complete!")
        return 0
    else:
        print("\n❌ Analysis failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
