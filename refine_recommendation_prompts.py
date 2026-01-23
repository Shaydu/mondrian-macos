#!/usr/bin/env python3
"""
Refine Recommendation Prompts:
1. Soften the "never praise" language while keeping improvement focus
2. Rename "Lighting" dimension to "Exposure & Lighting"
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

def backup_prompt(prompt):
    """Save backup of current prompt"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"prompt-backup/system_prompt_{timestamp}_before_refinement.txt"
    import os
    os.makedirs("prompt-backup", exist_ok=True)
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    return backup_file

def main():
    print("=" * 80)
    print("REFINE RECOMMENDATION PROMPTS")
    print("=" * 80)
    
    # Get current prompt
    current_prompt = get_current_prompt()
    if not current_prompt:
        print("❌ ERROR: No system_prompt found in database")
        sys.exit(1)
    
    print(f"\n✓ Current prompt: {len(current_prompt)} characters")
    
    # Backup current prompt
    backup_file = backup_prompt(current_prompt)
    print(f"✓ Backed up to: {backup_file}")
    
    updated_prompt = current_prompt
    
    # 1. Remove harsh "NEVER praise or encourage" language
    # Replace with softer, improvement-focused guidance
    harsh_text = """**CRITICAL: The "recommendation" field MUST ALWAYS suggest improvement, NEVER praise.**
- Even for dimensions scoring 8-10, identify the NEXT LEVEL of mastery to pursue
- NEVER write "keep up the good work", "continue this strength", or similar encouragement
- ALWAYS provide actionable advice for how to push beyond the current level"""
    
    softer_text = """**IMPORTANT: The "recommendation" field should focus on improvement and growth.**
- Even for high-scoring dimensions (8-10), identify the NEXT LEVEL of mastery to pursue
- Provide actionable advice for how to push beyond the current level"""
    
    if harsh_text in updated_prompt:
        updated_prompt = updated_prompt.replace(harsh_text, softer_text)
        print("\n✓ Softened harsh 'NEVER praise' language")
    
    # Also update TOP 3 section
    harsh_top3 = """- These recommendations MUST be improvement-focused, NEVER praise or encouragement"""
    softer_top3 = """- These recommendations should be improvement-focused and actionable"""
    
    if harsh_top3 in updated_prompt:
        updated_prompt = updated_prompt.replace(harsh_top3, softer_top3)
        print("✓ Softened TOP 3 section language")
    
    # Remove the harsh closing statement
    harsh_closing = """REMEMBER: Your job is to help photographers IMPROVE, not to congratulate them."""
    if harsh_closing in updated_prompt:
        updated_prompt = updated_prompt.replace(harsh_closing, "")
        print("✓ Removed harsh closing statement")
    
    # 2. Rename "Lighting" to "Exposure & Lighting"
    # Replace all instances in the prompt
    lighting_replacements = [
        ('"Lighting"', '"Exposure & Lighting"'),
        ("'Lighting'", "'Exposure & Lighting'"),
        ('Lighting:', 'Exposure & Lighting:'),
        ('name": "Lighting"', 'name": "Exposure & Lighting"'),
        ("Score 8/10 Lighting:", "Score 8/10 Exposure & Lighting:"),
    ]
    
    for old, new in lighting_replacements:
        if old in updated_prompt:
            updated_prompt = updated_prompt.replace(old, new)
    
    print("✓ Renamed 'Lighting' to 'Exposure & Lighting'")
    
    print(f"\n✓ Updated prompt: {len(updated_prompt)} characters")
    print(f"  Change: {len(updated_prompt) - len(current_prompt):+d} characters")
    
    # Show what changed
    print("\n" + "=" * 80)
    print("KEY CHANGES:")
    print("=" * 80)
    print("1. ✓ Softened language: 'NEVER praise' → 'should focus on improvement'")
    print("2. ✓ Removed harsh tone while keeping improvement focus")
    print("3. ✓ Renamed dimension: 'Lighting' → 'Exposure & Lighting'")
    
    # Confirm before updating
    print("\n" + "=" * 80)
    response = input("Proceed with update? (yes/no): ").strip().lower()
    
    if response == 'yes':
        update_system_prompt(updated_prompt)
        print("\n✅ System prompt updated successfully!")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("1. Restart the AI advisor service:")
        print("   ./mondrian.sh --restart --mode=lora+rag")
        print("")
        print("2. Test with an image to verify changes:")
        print("   curl -X POST -F 'image=@source/mike-shrub-01004b68.jpg' \\")
        print("        -F 'advisor=ansel' -F 'enable_rag=true' \\")
        print("        http://localhost:5100/analyze")
        print("")
        print("3. Verify:")
        print("   - Dimension appears as 'Exposure & Lighting' not 'Lighting'")
        print("   - Recommendations are improvement-focused but not harsh")
        print("=" * 80)
    else:
        print("\n❌ Update cancelled")
        sys.exit(1)

if __name__ == "__main__":
    main()
