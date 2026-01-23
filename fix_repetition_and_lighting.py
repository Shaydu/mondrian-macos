#!/usr/bin/env python3
"""
Fix Repetition and Rename Lighting Dimension

Issues:
1. LLM repeating recommendations across dimensions
2. Need to rename "Lighting" to "Exposure & Lighting"
3. Need to soften harsh "NEVER praise" language

Solutions:
1. Add explicit anti-repetition guidance to prompt
2. Update dimension name throughout system
3. Increase repetition_penalty from 1.0 to 1.15
4. Soften harsh language while keeping improvement focus
"""
import sqlite3
import json
import sys
from datetime import datetime

DB_PATH = "mondrian.db"
CONFIG_PATH = "model_config.json"

def backup_prompt(prompt):
    """Save backup of current prompt"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"prompt-backup/system_prompt_{timestamp}_before_repetition_fix.txt"
    import os
    os.makedirs("prompt-backup", exist_ok=True)
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    return backup_file

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
    print("FIX: Repetition Issue & Rename Lighting Dimension")
    print("=" * 80)
    
    # Get current prompt
    current_prompt = get_current_prompt()
    if not current_prompt:
        print("❌ ERROR: No system_prompt found in database")
        sys.exit(1)
    
    print(f"\n✓ Current prompt: {len(current_prompt)} characters")
    
    # Backup
    backup_file = backup_prompt(current_prompt)
    print(f"✓ Backed up to: {backup_file}")
    
    updated_prompt = current_prompt
    changes = []
    
    # 1. Soften harsh "NEVER praise" language
    harsh_text = """**CRITICAL: The "recommendation" field MUST ALWAYS suggest improvement, NEVER praise.**
- Even for dimensions scoring 8-10, identify the NEXT LEVEL of mastery to pursue
- NEVER write "keep up the good work", "continue this strength", or similar encouragement
- ALWAYS provide actionable advice for how to push beyond the current level"""
    
    softer_text = """**IMPORTANT: The "recommendation" field should focus on improvement and growth.**
- Even for high-scoring dimensions (8-10), identify the NEXT LEVEL of mastery to pursue
- Provide actionable advice for how to push beyond the current level"""
    
    if harsh_text in updated_prompt:
        updated_prompt = updated_prompt.replace(harsh_text, softer_text)
        changes.append("Softened 'NEVER praise' language")
    
    # Soften TOP 3 section
    harsh_top3 = """- These recommendations MUST be improvement-focused, NEVER praise or encouragement"""
    softer_top3 = """- These recommendations should be improvement-focused and actionable"""
    if harsh_top3 in updated_prompt:
        updated_prompt = updated_prompt.replace(harsh_top3, softer_top3)
        changes.append("Softened TOP 3 section")
    
    # Remove harsh closing
    harsh_closing = """REMEMBER: Your job is to help photographers IMPROVE, not to congratulate them."""
    if harsh_closing in updated_prompt:
        updated_prompt = updated_prompt.replace(harsh_closing, "")
        changes.append("Removed harsh closing statement")
    
    # 2. Add anti-repetition guidance
    anti_repetition_text = """

**CRITICAL: AVOID REPETITION ACROSS DIMENSIONS**
- Each dimension's recommendation MUST be UNIQUE and specific to that dimension
- DO NOT repeat the same advice for multiple dimensions (e.g., "try golden hour lighting" in both Composition and Exposure & Lighting)
- Each recommendation should address the specific technical aspect of that dimension
- If multiple dimensions share a root cause, vary your language and focus on dimension-specific solutions
- Example: For Composition, suggest framing/arrangement; for Exposure & Lighting, suggest exposure settings/light quality; for Focus, suggest depth of field/sharpness techniques"""
    
    # Insert before the EXAMPLES section if it exists, otherwise before technical_notes
    if "EXAMPLES OF IMPROVEMENT-FOCUSED RECOMMENDATIONS:" in updated_prompt:
        updated_prompt = updated_prompt.replace(
            "EXAMPLES OF IMPROVEMENT-FOCUSED RECOMMENDATIONS:",
            anti_repetition_text + "\n\nEXAMPLES OF IMPROVEMENT-FOCUSED RECOMMENDATIONS:"
        )
        changes.append("Added anti-repetition guidance before examples")
    elif "- technical_notes:" in updated_prompt:
        updated_prompt = updated_prompt.replace(
            "- technical_notes:",
            anti_repetition_text + "\n\n- technical_notes:"
        )
        changes.append("Added anti-repetition guidance before technical_notes")
    else:
        # Append to end
        updated_prompt += anti_repetition_text
        changes.append("Added anti-repetition guidance at end")
    
    # 3. Rename "Lighting" to "Exposure & Lighting"
    lighting_count = 0
    replacements = [
        ('"Lighting"', '"Exposure & Lighting"'),
        ("'Lighting'", "'Exposure & Lighting'"),
        ('name": "Lighting"', 'name": "Exposure & Lighting"'),
        ("Score 8/10 Lighting:", "Score 8/10 Exposure & Lighting:"),
    ]
    
    for old, new in replacements:
        count = updated_prompt.count(old)
        if count > 0:
            updated_prompt = updated_prompt.replace(old, new)
            lighting_count += count
    
    if lighting_count > 0:
        changes.append(f"Renamed 'Lighting' to 'Exposure & Lighting' ({lighting_count} instances)")
    
    # 4. Update model_config.json to increase repetition_penalty
    print("\n" + "=" * 80)
    print("Updating model_config.json...")
    print("=" * 80)
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Update repetition_penalty for all profiles that have it at 1.0
        config_changes = []
        for profile_name, profile in config.get('generation_profiles', {}).items():
            if profile.get('repetition_penalty') == 1.0:
                profile['repetition_penalty'] = 1.15
                config_changes.append(f"  - {profile_name}: 1.0 → 1.15")
        
        if config_changes:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            print("✓ Updated repetition_penalty in generation profiles:")
            for change in config_changes:
                print(change)
            changes.append(f"Updated model config repetition_penalty")
        else:
            print("⚠ No repetition_penalty values needed updating")
    except Exception as e:
        print(f"⚠ Could not update model_config.json: {e}")
    
    # Summary
    print(f"\n✓ Updated prompt: {len(updated_prompt)} characters")
    print(f"  Change: {len(updated_prompt) - len(current_prompt):+d} characters")
    
    print("\n" + "=" * 80)
    print("CHANGES SUMMARY:")
    print("=" * 80)
    for i, change in enumerate(changes, 1):
        print(f"{i}. ✓ {change}")
    
    # Confirm
    print("\n" + "=" * 80)
    response = input("Proceed with update? (yes/no): ").strip().lower()
    
    if response == 'yes':
        update_system_prompt(updated_prompt)
        print("\n✅ System prompt updated successfully!")
        
        print("\n" + "=" * 80)
        print("NEXT STEPS:")
        print("=" * 80)
        print("1. Restart AI advisor service to load new prompt:")
        print("   ./mondrian.sh --restart --mode=lora+rag")
        print("")
        print("2. Test with an image:")
        print("   curl -X POST -F 'image=@source/mike-shrub-01004b68.jpg' \\")
        print("        -F 'advisor=ansel' -F 'enable_rag=true' \\")
        print("        http://localhost:5100/analyze")
        print("")
        print("3. Verify:")
        print("   - Each dimension has UNIQUE recommendation (no repetition)")
        print("   - 'Exposure & Lighting' appears instead of 'Lighting'")
        print("   - Recommendations are improvement-focused but not harsh")
        print("")
        print("4. Re: Adapter retraining:")
        print("   - Try with current adapter first")
        print("   - If repetition persists, the prompt fix should resolve it")
        print("   - Only retrain if you see persistent quality issues after prompt fix")
        print("=" * 80)
    else:
        print("\n❌ Update cancelled")
        sys.exit(1)

if __name__ == "__main__":
    main()
