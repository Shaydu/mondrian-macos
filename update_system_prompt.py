#!/usr/bin/env python3
"""
Update system prompt in database with new scoring philosophy and alignment penalties.
"""
import sys
import os
from pathlib import Path

# Add paths
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'scripts'))
sys.path.insert(0, os.path.join(script_dir, 'mondrian'))

from scripts.sqlite_helper import set_config, get_config

ROOT = Path(__file__).resolve().parent
DB_PATH = str(ROOT / 'mondrian.db')

def main():
    print("=" * 70)
    print("System Prompt Update Tool")
    print("=" * 70)

    # Define new system prompt with scoring philosophy and alignment penalties
    new_prompt = """You are a photography analysis assistant. **ALL OUTPUT MUST BE IN ENGLISH ONLY.** Output valid JSON only.

**SCORING PHILOSOPHY:**
- Score range is 3-10, NOT 7-10. Apply critical judgment.
- Most scores should fall in the 6-8 range (majority of work).
- Scores 9-10 are reserved for exceptional technical or artistic excellence.
- Scores 3-5 indicate significant issues needing improvement.
- Scores below 6 should be used when there are clear weaknesses or misalignment with the advisor's style.

**STYLE & SUBJECT MATTER ALIGNMENT:**
- If the image's subject matter or style drastically differs from the selected advisor's characteristic work, apply a SERIOUS PENALTY (reduce scores by 2-3 points).
- Consider whether the content aligns with the advisor's typical themes, subject matter, and artistic vision.
- Misalignment should be flagged in "technical_notes" and reflected proportionally across relevant dimensions.

Required JSON Structure:
{
  "image_description": "2-3 sentence description",
  "dimensions": [
    {"name": "Composition", "score": 8, "comment": "...", "recommendation": "..."},
    {"name": "Lighting", "score": 7, "comment": "...", "recommendation": "..."},
    {"name": "Focus & Sharpness", "score": 9, "comment": "...", "recommendation": "..."},
    {"name": "Color Harmony", "score": 6, "comment": "...", "recommendation": "..."},
    {"name": "Depth & Perspective", "score": 7, "comment": "...", "recommendation": "..."},
    {"name": "Visual Balance", "score": 8, "comment": "...", "recommendation": "..."},
    {"name": "Emotional Impact", "score": 7, "comment": "...", "recommendation": "..."}
  ],
  "overall_score": 7.4,
  "key_strengths": ["strength 1", "strength 2"],
  "priority_improvements": ["improvement 1", "improvement 2"],
  "technical_notes": "Technical observations",
  "case_studies": [
    {"image_title": "Moon and Half Dome", "year": "1960", "dimension": "Lighting", "explanation": "Study the zone system technique..."},
    {"image_title": "The Tetons and the Snake River", "year": "1942", "dimension": "Composition", "explanation": "..."}
  ]
}

**CRITICAL**: If reference images are provided in the prompt, you MUST include a case_studies array with up to 3 entries. Each case study must cite the EXACT image title from the references and explain how it demonstrates mastery in a specific dimension."""

    print(f"\n[INFO] New prompt prepared: {len(new_prompt)} characters")

    # Get current prompt for backup
    current_prompt = get_config(DB_PATH, "system_prompt")
    if current_prompt:
        print(f"[INFO] Current prompt: {len(current_prompt)} characters")

        # Save backup
        backup_file = "mondrian/prompts/system_backup_before_scoring_update.md"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(current_prompt)
        print(f"[INFO] Backed up current prompt to: {backup_file}")
    else:
        print("[WARN] No current prompt found in database")

    # Update database
    print("\n[INFO] Updating system prompt in database...")
    success = set_config(DB_PATH, "system_prompt", new_prompt)

    if success:
        print("[SUCCESS] ✅ System prompt updated successfully!")

        # Verify
        verify_prompt = get_config(DB_PATH, "system_prompt")
        if verify_prompt == new_prompt:
            print("[SUCCESS] ✅ Verification passed - prompt correctly stored")
            print("\n" + "=" * 70)
            print("NEXT STEPS:")
            print("=" * 70)
            print("1. Restart AI Advisor Service to use new prompt")
            print("2. The model will now:")
            print("   - Apply scores across 3-10 range with most in 6-8")
            print("   - Penalize images that don't match advisor's style")
            print("   - Use more critical judgment overall")
            print("=" * 70)
        else:
            print("[ERROR] ❌ Verification failed - stored prompt doesn't match")
            sys.exit(1)
    else:
        print("[ERROR] ❌ Failed to update system prompt")
        sys.exit(1)

if __name__ == "__main__":
    main()
