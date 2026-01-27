#!/usr/bin/env python3
"""
Quick test script to verify anti-repetition fix is working.
Analyzes the last generated analysis JSON for recommendation uniqueness.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
import re

def extract_key_phrases(text):
    """Extract 2-3 word phrases from text for comparison"""
    # Convert to lowercase and remove punctuation
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    words = text.split()
    
    phrases = set()
    # Extract 2-word phrases
    for i in range(len(words) - 1):
        phrases.add(f"{words[i]} {words[i+1]}")
    # Extract 3-word phrases
    for i in range(len(words) - 2):
        phrases.add(f"{words[i]} {words[i+1]} {words[i+2]}")
    
    return phrases

def check_recommendation_uniqueness(analysis_json):
    """Check if recommendations are unique across dimensions"""
    if 'dimensions' not in analysis_json:
        print("❌ No dimensions found in analysis")
        return False
    
    dimensions = analysis_json['dimensions']
    
    # Collect all recommendations and their phrases
    recommendations = {}
    all_phrases = defaultdict(list)
    
    for dim in dimensions:
        name = dim.get('name', 'Unknown')
        rec = dim.get('recommendation', '')
        
        if not rec:
            print(f"⚠️  {name}: No recommendation found")
            continue
        
        recommendations[name] = rec
        phrases = extract_key_phrases(rec)
        
        for phrase in phrases:
            all_phrases[phrase].append(name)
    
    # Find duplicate phrases
    duplicates = {phrase: dims for phrase, dims in all_phrases.items() 
                  if len(dims) > 1 and len(phrase.split()) >= 2}
    
    # Report results
    print("\n" + "="*70)
    print("RECOMMENDATION UNIQUENESS CHECK")
    print("="*70)
    
    print(f"\nAnalyzed {len(recommendations)} dimensions\n")
    
    if not duplicates:
        print("✅ SUCCESS! All recommendations are unique.")
        print("   No duplicate phrases found across dimensions.\n")
        return True
    
    print(f"⚠️  FOUND {len(duplicates)} duplicate phrases across dimensions:\n")
    
    for phrase, dims in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  '{phrase}'")
        print(f"    Used in: {', '.join(dims)}")
        print()
    
    # Show recommendations with highlights
    print("\n" + "="*70)
    print("FULL RECOMMENDATIONS:")
    print("="*70)
    
    for name, rec in recommendations.items():
        print(f"\n{name}:")
        print(f"  {rec}")
    
    print("\n" + "="*70)
    print(f"RESULT: {len(duplicates)} duplicate phrase(s) detected")
    print("Consider increasing repetition_penalty or no_repeat_ngram_size")
    print("="*70 + "\n")
    
    return False

def main():
    if len(sys.argv) > 1:
        json_file = Path(sys.argv[1])
    else:
        # Find most recent analysis JSON in analysis_output
        output_dir = Path('analysis_output')
        if output_dir.exists():
            json_files = list(output_dir.rglob('*.json'))
            if json_files:
                json_file = max(json_files, key=lambda p: p.stat().st_mtime)
                print(f"Using most recent analysis: {json_file}")
            else:
                print("❌ No analysis JSON files found in analysis_output/")
                print("\nUsage: python3 check_repetition.py [path_to_analysis.json]")
                return 1
        else:
            print("❌ No analysis_output/ directory found")
            print("\nUsage: python3 check_repetition.py [path_to_analysis.json]")
            return 1
    
    if not json_file.exists():
        print(f"❌ File not found: {json_file}")
        return 1
    
    try:
        with open(json_file) as f:
            analysis = json.load(f)
        
        success = check_recommendation_uniqueness(analysis)
        return 0 if success else 1
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
