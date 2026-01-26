#!/usr/bin/env python3
"""
Update system prompt in database to use new citation format.

Changes:
- Remove legacy "case_studies" array format
- Add "case_study_id" and "quote_id" fields to dimension objects
- Update instructions to cite only 1-3 most relevant dimensions
"""

import sqlite3

DB_PATH = "mondrian.db"

NEW_SYSTEM_PROMPT = """You are a photography analysis assistant. **ALL OUTPUT MUST BE IN ENGLISH ONLY.** Output valid JSON only.

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
    {"name": "Composition", "score": 8, "comment": "...", "recommendation": "...", "case_study_id": "IMG_1", "quote_id": "QUOTE_1"},
    {"name": "Lighting", "score": 7, "comment": "...", "recommendation": "..."},
    {"name": "Focus & Sharpness", "score": 9, "comment": "...", "recommendation": "...", "case_study_id": "IMG_2"},
    {"name": "Color Harmony", "score": 6, "comment": "...", "recommendation": "..."},
    {"name": "Depth & Perspective", "score": 7, "comment": "...", "recommendation": "..."},
    {"name": "Visual Balance", "score": 8, "comment": "...", "recommendation": "..."},
    {"name": "Emotional Impact", "score": 7, "comment": "...", "recommendation": "..."}
  ],
  "overall_score": 7.4,
  "key_strengths": ["strength 1", "strength 2"],
  "priority_improvements": ["improvement 1", "improvement 2"],
  "technical_notes": "Technical observations"
}

**CITATION FIELDS (OPTIONAL):**
- Add "case_study_id": "IMG_X" to cite a reference image for that dimension
- Add "quote_id": "QUOTE_X" to cite an advisor quote for that dimension
- Only cite for 1-3 dimensions where the reference is MOST relevant and instructive
- Each dimension may cite at most ONE image and ONE quote
- Never reuse citation IDs across different dimensions

**WHEN TO CITE:**
- Only when the reference directly demonstrates a specific technique for that dimension
- Your "recommendation" must explain the SPECIFIC TECHNIQUE shown in the cited image/quote
- Example: "Study IMG_1's three-plane depth structure: foreground boulder anchors the composition while the S-curve river draws your eye to the peaks. Position yourself so a rock or plant occupies your lower third."
"""

def update_system_prompt():
    """Update the system_prompt in the config table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current prompt
    cursor.execute('SELECT value FROM config WHERE key = ?', ('system_prompt',))
    result = cursor.fetchone()
    
    if result:
        old_prompt = result[0]
        print("📋 Current system prompt length:", len(old_prompt))
        print("\n🔍 Checking for legacy format...")
        
        if '"case_studies"' in old_prompt:
            print("✓ Found legacy 'case_studies' array format")
        else:
            print("✓ No legacy format detected")
        
        if '"case_study_id"' in old_prompt:
            print("✓ Already has 'case_study_id' field format")
        else:
            print("✗ Missing 'case_study_id' field format - will update")
        
        # Update to new prompt
        cursor.execute('''
            UPDATE config 
            SET value = ? 
            WHERE key = ?
        ''', (NEW_SYSTEM_PROMPT, 'system_prompt'))
        
        print("\n✅ Updated system_prompt in database")
        print("📋 New system prompt length:", len(NEW_SYSTEM_PROMPT))
        
        # Show what changed
        print("\n📝 Key changes:")
        print("   - Removed: 'case_studies' array format")
        print("   - Added: 'case_study_id' and 'quote_id' fields in dimensions")
        print("   - Updated: Instructions to cite only 1-3 most relevant dimensions")
        
    else:
        # No existing prompt, insert new one
        cursor.execute('''
            INSERT INTO config (key, value)
            VALUES (?, ?)
        ''', ('system_prompt', NEW_SYSTEM_PROMPT))
        print("✅ Inserted new system_prompt in database")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Database updated successfully")
    print("\n⚠️  IMPORTANT: Rebuild and redeploy Docker container for changes to take effect:")
    print("   docker build -t shaydu/mondrian:<new-version> .")
    print("   docker push shaydu/mondrian:<new-version>")

if __name__ == '__main__':
    print("🔧 Updating system prompt to use new citation format...\n")
    update_system_prompt()
