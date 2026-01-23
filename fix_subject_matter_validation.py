#!/usr/bin/env python3
"""
Fix Subject Matter Validation in System Prompt

PROBLEM: Text-only images (non-photographs) are receiving high composition scores (9/10)
because the system doesn't validate if the image is even a photograph.

SOLUTION: Add explicit subject matter validation to the system prompt only.
Advisor prompts remain focused on kind, critical mentoring.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = "mondrian.db"

def backup_prompts():
    """Backup current prompts before modification"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("prompt-backup")
    backup_dir.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Backup system prompt
    cursor.execute("SELECT value FROM config WHERE key='system_prompt'")
    result = cursor.fetchone()
    if result:
        backup_file = backup_dir / f"system_prompt_{timestamp}_before_subject_validation.txt"
        backup_file.write_text(result[0])
        print(f"✓ Backed up system prompt to: {backup_file}")
    
    conn.close()
    return timestamp


def update_system_prompt():
    """Add subject matter validation to system prompt"""
    
    addition = """

**CRITICAL: SUBJECT MATTER VALIDATION (APPLIES TO ALL ADVISORS)**
BEFORE evaluating photographic dimensions, validate the image:

**Step 1: Is this a photograph?**
- Photographs: landscapes, portraits, street photography, nature, architecture, etc.
- NOT photographs: pure text documents, screenshots, UI mockups, diagrams, charts, presentations
- If NOT a photograph → ALL dimensions MUST score 1-2/10 and state in image_description: "This is not a photograph. Unable to provide meaningful photographic critique."

**Step 2: Does subject align with advisor's specialty?**
Each advisor has expertise areas (e.g., Ansel Adams = landscapes/nature). Check alignment:
- PERFECT MATCH: No penalty, full evaluation
- SOMEWHAT RELATED: Minor penalty (-1 to -2 points per dimension)
- COMPLETELY MISALIGNED: Major penalty (-3 to -5 points per dimension)
- NON-PHOTOGRAPH: Score 1-2/10 regardless of advisor

**Examples for Ansel Adams (landscape/nature specialist):**
- Text document or screenshot → "Not a photograph" → ALL dimensions: 1/10
- Mountain landscape → Perfect match → No penalty, normal evaluation
- Urban street scene (no nature) → Misaligned → Apply -3 to -4 penalty to all dimensions
- Portrait in nature setting → Somewhat related → Apply -1 to -2 penalty

**Important:** In "image_description", explicitly state if the image is inappropriate and why. Be direct but kind about the mismatch."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM config WHERE key='system_prompt'")
    result = cursor.fetchone()
    
    if not result:
        print("❌ ERROR: No system_prompt found in database")
        conn.close()
        return False
    
    current_prompt = result[0]
    
    # Insert the addition after the TONE GUIDELINES section and before MANDATORY section
    # Look for "**MANDATORY: EVALUATE ALL 6 DIMENSIONS"
    insert_marker = "**MANDATORY: EVALUATE ALL 6 DIMENSIONS"
    
    if insert_marker in current_prompt:
        updated_prompt = current_prompt.replace(insert_marker, addition + "\n\n" + insert_marker)
    else:
        # Fallback: insert before JSON OUTPUT STRUCTURE
        insert_marker = "**JSON OUTPUT STRUCTURE**"
        if insert_marker in current_prompt:
            updated_prompt = current_prompt.replace(insert_marker, addition + "\n\n" + insert_marker)
        else:
            print("❌ ERROR: Could not find insertion point in system prompt")
            conn.close()
            return False
    
    cursor.execute("UPDATE config SET value = ? WHERE key = 'system_prompt'", (updated_prompt,))
    conn.commit()
    conn.close()
    
    print("✅ Updated system prompt with subject matter validation")
    return True


def verify_ansel_prompt():
    """Verify Ansel Adams prompt maintains kind, critical mentor tone"""
    
    # We're keeping the advisor prompt focused on mentoring style, not validation
    # Validation is handled in the system prompt
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT prompt FROM advisors WHERE id='ansel'")
    result = cursor.fetchone()
    
    if not result:
        print("❌ ERROR: No prompt found for Ansel Adams advisor")
        conn.close()
        return False
    
    current_prompt = result[0]
    
    # Verify the key mentoring elements are present
    required_elements = [
        "I am Ansel Adams",
        "fellow traveler on this path",
        "be patient with yourself"
    ]
    
    missing = [elem for elem in required_elements if elem not in current_prompt]
    if missing:
        print(f"⚠️  Warning: Ansel prompt missing elements: {missing}")
    else:
        print("✅ Ansel Adams prompt maintains kind, critical mentor tone")
    
    conn.close()
    return True


def main():
    print("=" * 70)
    print("Subject Matter Validation Fix")
    print("=" * 70)
    print()
    print("PROBLEM: Text-only images getting high scores (9/10 composition)")
    print("CAUSE:   No validation that image is a photograph in system prompt")
    print("FIX:     Add universal subject matter validation to system prompt")
    print()
    print("DESIGN: System prompt = validation, Advisor prompt = kind critique")
    print()
    
    # Backup existing prompts
    timestamp = backup_prompts()
    print()
    
    # Update system prompt
    if not update_system_prompt():
        print("\n❌ Failed to update system prompt")
        return
    
    # Verify Ansel prompt (no changes needed - it stays focused on mentoring)
    if not verify_ansel_prompt():
        print("\n❌ Failed to verify Ansel prompt")
        return
    
    print()
    print("=" * 70)
    print("✅ SUCCESS: System prompt updated with subject validation")
    print("=" * 70)
    print()
    print("WHAT CHANGED:")
    print("- System prompt: Added universal subject matter validation")
    print("- Advisor prompts: Unchanged (remain kind, critical mentors)")
    print()
    print("BEHAVIOR:")
    print("- Text/screenshots → 1-2/10 all dimensions (\"not a photograph\")")
    print("- Misaligned subjects → Penalty applied (-3 to -5 points)")
    print("- Appropriate photos → Normal kind, critical evaluation")
    print()
    print("NEXT STEPS:")
    print("1. Restart AI Advisor Service:")
    print("   ./mondrian.sh --restart --mode=lora+rag")
    print()
    print("2. Test with text-only image → expect 1-2/10 scores")
    print("3. Test with landscape photo → expect normal evaluation")
    print()
    print(f"4. Backups saved with timestamp: {timestamp}")
    print()


if __name__ == "__main__":
    main()
