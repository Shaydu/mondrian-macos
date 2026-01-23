#!/usr/bin/env python3
"""
Update System Prompt: Enforce Improvement-Focused Recommendations

Problem: The "recommendation" field is intended for improvement advice, but the LLM
generates praise ("keep up the good work") for higher-scoring dimensions.

Solution: Explicitly instruct that recommendations MUST ALWAYS suggest improvements,
never praise, even for scores 8-10.
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
    backup_file = f"prompt-backup/system_prompt_{timestamp}_before_improvement_fix.txt"
    import os
    os.makedirs("prompt-backup", exist_ok=True)
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    return backup_file

def main():
    print("=" * 80)
    print("ENFORCE IMPROVEMENT-FOCUSED RECOMMENDATIONS")
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
    
    # Update the recommendation field instructions
    # Find and replace the recommendation section
    old_rec_instruction = """- Each recommendation: 80-120 words REQUIRED - must include:
  * SPECIFIC technique to try (not generic advice)
  * CONCRETE steps the photographer can take on their next shoot
  * When citing references, explain the EXACT technique demonstrated and HOW to apply it"""
    
    new_rec_instruction = """- Each recommendation: 80-120 words REQUIRED - must include:
  * SPECIFIC technique to try (not generic advice)
  * CONCRETE steps the photographer can take on their next shoot
  * When citing references, explain the EXACT technique demonstrated and HOW to apply it
  
**CRITICAL: The "recommendation" field MUST ALWAYS suggest improvement, NEVER praise.**
- Even for dimensions scoring 8-10, identify the NEXT LEVEL of mastery to pursue
- NEVER write "keep up the good work", "continue this strength", or similar encouragement
- ALWAYS provide actionable advice for how to push beyond the current level
- For high scores: suggest advanced techniques or experimental approaches
- For low scores: identify fundamental issues and clear steps to address them

EXAMPLES OF IMPROVEMENT-FOCUSED RECOMMENDATIONS:
- Score 9/10 Composition: "While your rule-of-thirds placement is solid, experiment with breaking the rule—try extreme off-center positioning or unconventional aspect ratios to push your compositional vocabulary beyond safe choices."
- Score 8/10 Lighting: "Your use of golden hour light is competent, but consider working with more challenging light conditions—shoot at noon with harsh shadows and learn to use them as compositional elements, or embrace the subtlety of overcast light for intimate portraits."
- Score 7/10 Focus: "Sharp focus is achieved, but explore creative uses of selective focus—try focus stacking for extreme depth of field, or intentional soft focus for dreamlike effects."
- Score 5/10 Balance: "The composition feels weighted to one side. On your next shoot, use the camera's grid overlay to check visual weight distribution before shooting, and practice mirroring or counterbalancing strong elements."

REMEMBER: Your job is to help photographers IMPROVE, not to congratulate them."""
    
    if old_rec_instruction in current_prompt:
        updated_prompt = current_prompt.replace(old_rec_instruction, new_rec_instruction)
        print("\n✓ Updated recommendation field instructions")
    else:
        print("\n⚠ WARNING: Could not find exact recommendation instruction to replace")
        print("   Adding new instructions at the end of the structure section...")
        
        # Try to find a good insertion point
        if "- technical_notes:" in current_prompt:
            # Insert before technical_notes
            updated_prompt = current_prompt.replace(
                "- technical_notes:",
                new_rec_instruction + "\n\n- technical_notes:"
            )
        else:
            # Append to the end
            updated_prompt = current_prompt + "\n\n" + new_rec_instruction
    
    # Also add reinforcement in the "TOP 3 RECOMMENDATIONS" section if it exists
    top3_enhancement = """
**TOP 3 RECOMMENDATIONS (SUMMARY VIEW):**
- priority_improvements MUST address the photographer's WEAKEST dimensions (lowest scores)
- These recommendations MUST be improvement-focused, NEVER praise or encouragement
- Focus on specific, actionable techniques to address the identified weaknesses
- Each recommendation should clearly state WHAT to improve and HOW to improve it
- Do NOT write generic statements like "keep up the good work" or "continue developing"
- case_studies should demonstrate mastery techniques that address these specific weak areas"""
    
    if "**TOP 3 RECOMMENDATIONS (SUMMARY VIEW):**" in updated_prompt:
        # Replace existing section
        import re
        pattern = r'\*\*TOP 3 RECOMMENDATIONS \(SUMMARY VIEW\):\*\*[^\*]+'
        updated_prompt = re.sub(pattern, top3_enhancement + "\n\n", updated_prompt)
        print("✓ Enhanced TOP 3 RECOMMENDATIONS section")
    else:
        # Add new section before case studies or at appropriate location
        if "case_studies" in updated_prompt:
            # Find a good spot to insert
            lines = updated_prompt.split('\n')
            for i, line in enumerate(lines):
                if 'case_studies' in line and 'MUST' in lines[i-1] if i > 0 else False:
                    lines.insert(i-1, top3_enhancement)
                    break
            updated_prompt = '\n'.join(lines)
        print("✓ Added TOP 3 RECOMMENDATIONS guidance")
    
    print(f"\n✓ Updated prompt: {len(updated_prompt)} characters")
    print(f"  Change: {len(updated_prompt) - len(current_prompt):+d} characters")
    
    # Show what changed
    print("\n" + "=" * 80)
    print("KEY CHANGES:")
    print("=" * 80)
    print("1. ✓ Added explicit prohibition: 'NEVER praise or encourage'")
    print("2. ✓ Required improvement advice even for scores 8-10")
    print("3. ✓ Provided 4 concrete examples showing improvement-focused language")
    print("4. ✓ Enhanced TOP 3 RECOMMENDATIONS section with 'NEVER generic statements'")
    print("5. ✓ Emphasized: 'Your job is to help photographers IMPROVE'")
    
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
        print("2. Test with an image to verify improvement-focused recommendations:")
        print("   curl -X POST -F 'image=@source/mike-shrub-01004b68.jpg' \\")
        print("        -F 'advisor=ansel' -F 'enable_rag=true' \\")
        print("        http://localhost:5100/analyze")
        print("")
        print("3. Check that Top 3 Recommendations contain actionable improvement advice")
        print("   - Look for specific techniques to try")
        print("   - Verify NO 'keep up the good work' or similar praise")
        print("")
        print("4. Optional: If prompt-only fix is insufficient, retrain LoRA adapter:")
        print("   python train_lora_qwen3vl.py \\")
        print("       --base_model 'Qwen/Qwen2-VL-7B-Instruct' \\")
        print("       --data_dir ./training_data \\")
        print("       --output_dir ./adapters/ansel_pytorch \\")
        print("       --epochs 3 --batch_size 2 --load_in_4bit")
        print("=" * 80)
    else:
        print("\n❌ Update cancelled")
        sys.exit(1)

if __name__ == "__main__":
    main()
