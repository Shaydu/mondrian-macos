#!/usr/bin/env python3
"""
Quick system prompt update using direct SQLite connection.
"""
import sqlite3
import sys

DB_PATH = "mondrian.db"

NEW_PROMPT = """You are a photography analysis assistant. **ALL OUTPUT MUST BE IN ENGLISH ONLY.** Output valid JSON only.

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

try:
    print("=" * 70)
    print("System Prompt Update")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if system_prompt exists
    cursor.execute('SELECT value FROM config WHERE key = ?', ('system_prompt',))
    result = cursor.fetchone()
    
    if result:
        print(f"[INFO] Current prompt: {len(result[0])} characters")
        cursor.execute('UPDATE config SET value = ? WHERE key = ?', (NEW_PROMPT, 'system_prompt'))
        print("[SUCCESS] ✅ Updated existing system_prompt")
    else:
        cursor.execute('INSERT INTO config (key, value) VALUES (?, ?)', ('system_prompt', NEW_PROMPT))
        print("[SUCCESS] ✅ Inserted new system_prompt")
    
    conn.commit()
    
    # Verify
    cursor.execute('SELECT value FROM config WHERE key = ?', ('system_prompt',))
    verify = cursor.fetchone()
    if verify and verify[0] == NEW_PROMPT:
        print("[SUCCESS] ✅ Verification passed")
        print(f"[INFO] New prompt: {len(NEW_PROMPT)} characters")
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
        print("[ERROR] ❌ Verification failed")
        sys.exit(1)
    
    conn.close()
    
except Exception as e:
    print(f"[ERROR] ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
