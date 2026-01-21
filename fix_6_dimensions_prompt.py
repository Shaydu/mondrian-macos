#!/usr/bin/env python3
"""
Fix system prompt to enforce all 6 dimensions in output.
Ensures LLM generates complete dimensional analysis.
"""
import sqlite3
import sys
from datetime import datetime

DB_PATH = "mondrian.db"

def get_current_prompt():
    """Get current system prompt from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key='system_prompt'")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_system_prompt(new_prompt):
    """Update system prompt in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE config SET value = ? WHERE key = 'system_prompt'", (new_prompt,))
    conn.commit()
    conn.close()

def main():
    print("=" * 80)
    print("FIX: Enforce All 6 Dimensions in Detailed Output")
    print("=" * 80)
    
    # Get current prompt
    current_prompt = get_current_prompt()
    if not current_prompt:
        print("❌ ERROR: No system_prompt found in database")
        sys.exit(1)
    
    print(f"\n✓ Current prompt: {len(current_prompt)} characters")
    
    # Replace the dimension section to be more explicit
    updated_prompt = current_prompt.replace(
        '**CRITICAL - EVALUATE THESE 6 DIMENSIONS ONLY**:',
        '**MANDATORY: EVALUATE ALL 6 DIMENSIONS - YOUR JSON MUST INCLUDE EXACTLY 6 DIMENSION ENTRIES**:'
    )
    
    # Add enforcement after the example JSON structure
    # Find the JSON structure section and add enforcement note
    if '"dimensions": [' in updated_prompt:
        # Add a strong reminder after the JSON structure
        json_example_end = updated_prompt.find('**MANDATORY CITATION RULES**')
        if json_example_end > 0:
            enforcement_note = '''\n\n**CRITICAL VALIDATION - YOUR RESPONSE WILL BE REJECTED IF:**
- The "dimensions" array contains fewer than 6 entries
- Any of the 6 required dimensions are missing
- Dimension names don't match exactly: "Composition", "Lighting", "Focus & Sharpness", "Depth & Perspective", "Visual Balance", "Emotional Impact"

**YOU MUST ANALYZE ALL 6 DIMENSIONS.** Do not skip dimensions even if you think they're less relevant. Each dimension provides valuable feedback to the photographer.

'''
            updated_prompt = updated_prompt[:json_example_end] + enforcement_note + updated_prompt[json_example_end:]
    
    # Update response budget to accommodate 6 dimensions with detailed feedback
    updated_prompt = updated_prompt.replace(
        '**RESPONSE BUDGET**: Keep your total JSON response to approximately 3500 tokens.',
        '**RESPONSE BUDGET**: Target approximately 4000-4500 tokens to ensure complete coverage of all 6 dimensions.'
    )
    
    # Adjust length guidelines to be more concise per dimension to fit all 6
    updated_prompt = updated_prompt.replace(
        '- Each comment: 100-150 words REQUIRED',
        '- Each comment: 80-120 words REQUIRED'
    )
    updated_prompt = updated_prompt.replace(
        '- Each recommendation: 100-150 words REQUIRED',
        '- Each recommendation: 80-120 words REQUIRED'
    )
    
    print(f"\n✓ Updated prompt: {len(updated_prompt)} characters")
    print(f"  Change: {len(updated_prompt) - len(current_prompt):+d} characters")
    
    # Show what changed
    print("\n" + "=" * 80)
    print("KEY CHANGES:")
    print("=" * 80)
    print("1. Changed 'EVALUATE THESE 6 DIMENSIONS ONLY' → 'MANDATORY: EVALUATE ALL 6 DIMENSIONS'")
    print("2. Added validation requirements: JSON will be rejected if < 6 dimensions")
    print("3. Increased token budget: 3500 → 4000-4500 tokens")
    print("4. Adjusted length per dimension: 100-150 → 80-120 words (to fit all 6)")
    print("5. Explicit requirement that all 6 dimensions must be included")
    
    # Confirm before updating
    print("\n" + "=" * 80)
    response = input("Proceed with update? (yes/no): ").strip().lower()
    
    if response == 'yes':
        update_system_prompt(updated_prompt)
        print("\n✓ System prompt updated successfully!")
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("1. Restart the AI advisor service:")
        print("   ./mondrian.sh --restart --mode=lora+rag")
        print("")
        print("2. Test with an image to verify all 6 dimensions appear:")
        print("   curl -X POST -F 'image=@source/mike-shrub-01004b68.jpg' \\")
        print("        -F 'advisor=ansel' -F 'enable_rag=true' \\")
        print("        http://localhost:5100/analyze")
        print("")
        print("3. Check the detailed output HTML has 6 feedback cards")
        print("4. Verify summary view still shows only top 3 worst dimensions")
        print("=" * 80)
    else:
        print("\n❌ Update cancelled")
        sys.exit(1)

if __name__ == "__main__":
    main()
