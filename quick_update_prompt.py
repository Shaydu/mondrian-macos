#!/usr/bin/env python3
"""
Quick system prompt update using direct SQLite connection.
"""
import sqlite3
import sys

DB_PATH = "mondrian.db"

NEW_PROMPT = """You are a photography analysis assistant. **ALL OUTPUT MUST BE IN ENGLISH ONLY.** Output valid JSON only.

**RESPONSE BUDGET**: Keep your total JSON response to approximately 3500 tokens. Be detailed and specific.

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
    {
      "name": "Composition",
      "score": 8,
      "comment": "Technical observation about the compositional choices, leading lines, framing, and visual structure",
      "recommendation": "Consider how you could strengthen the compositional framework. Think about using natural leading lines to guide the viewer's eye, adjusting camera position to create stronger foreground-midground-background layering, or repositioning elements for better visual balance.",
      "case_study_id": "IMG_1",
      "quote_id": "QUOTE_2"
    }
  ],
  "overall_score": 7.4,
  "key_strengths": ["strength 1", "strength 2"],
  "priority_improvements": ["improvement 1", "improvement 2"],
  "technical_notes": "Technical observations"
}

**CITATION INSTRUCTIONS:**
- The "case_study_id" and "quote_id" fields are OPTIONAL
- Use "case_study_id" to cite a reference image (format: "IMG_1", "IMG_2", etc.) when it demonstrates mastery in that specific dimension
- Use "quote_id" to cite an advisor quote (format: "QUOTE_1", "QUOTE_2", etc.) when it provides relevant insight for that dimension
- Reference images and quotes will be provided in the prompt if available
- You may cite UP TO 3 images and UP TO 3 quotes total across all dimensions
- Do NOT repeat the same citation ID across multiple dimensions

**CRITICAL INSTRUCTIONS**:
- Generate ORIGINAL recommendations tailored to THIS specific image
- NEVER output placeholder recommendations like "Study IMG_X" or generic phrases
- Each recommendation must be specific, actionable, and grounded in what you observe in the photograph
- Keep recommendations practical and implementable for future work"""

try:
    print("=" * 70)
    print("System Prompt Update")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find the latest version number
    cursor.execute("SELECT key FROM config WHERE key LIKE 'system_prompt%' ORDER BY key")
    existing = cursor.fetchall()
    
    # Determine next version
    max_version = -1
    for (key,) in existing:
        if key == 'system_prompt':
            max_version = max(max_version, 0)
        elif key.startswith('system_prompt_'):
            try:
                version = int(key.split('_')[-1])
                max_version = max(max_version, version)
            except ValueError:
                pass
    
    next_version = max_version + 1
    new_key = f'system_prompt_{next_version}'
    
    print(f"[INFO] Creating new version: {new_key}")
    
    # Insert new version
    cursor.execute('INSERT INTO config (key, value) VALUES (?, ?)', (new_key, NEW_PROMPT))
    print(f"[SUCCESS] ✅ Created {new_key}")
    
    # Also update system_prompt for active use
    cursor.execute('SELECT value FROM config WHERE key = ?', ('system_prompt',))
    result = cursor.fetchone()
    
    if result:
        print(f"[INFO] Current active prompt: {len(result[0])} characters")
        cursor.execute('UPDATE config SET value = ? WHERE key = ?', (NEW_PROMPT, 'system_prompt'))
        print("[SUCCESS] ✅ Updated active system_prompt")
    else:
        cursor.execute('INSERT INTO config (key, value) VALUES (?, ?)', ('system_prompt', NEW_PROMPT))
        print("[SUCCESS] ✅ Inserted active system_prompt")
    
    conn.commit()
    
    # Verify
    cursor.execute('SELECT value FROM config WHERE key = ?', (new_key,))
    verify = cursor.fetchone()
    if verify and verify[0] == NEW_PROMPT:
        print("[SUCCESS] ✅ Verification passed")
        print(f"[INFO] New prompt: {len(NEW_PROMPT)} characters")
        print(f"[INFO] Saved as: {new_key}")
        print("\n" + "=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print("1. Restart AI Advisor Service to use new prompt")
        print("2. The model will now:")
        print("   - Use 3500 token budget (up from 2500)")
        print("   - Generate more detailed recommendations")
        print("   - Avoid generic 'Study IMG_X' phrases")
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
