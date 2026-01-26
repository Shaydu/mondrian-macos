#!/usr/bin/env python3
"""
Setup prompt versioning system.
Creates system_prompt_1 and system_prompt_2 as copies of current system_prompt.
"""
import sqlite3
import sys

DB_PATH = "mondrian.db"

try:
    print("=" * 70)
    print("Setting Up Prompt Versioning System")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get current system_prompt
    cursor.execute('SELECT value FROM config WHERE key = ?', ('system_prompt',))
    result = cursor.fetchone()
    
    if not result:
        print("[ERROR] ❌ No system_prompt found in database")
        sys.exit(1)
    
    current_prompt = result[0]
    print(f"[INFO] Current prompt size: {len(current_prompt)} characters")
    
    # Create system_prompt_1
    cursor.execute('DELETE FROM config WHERE key = ?', ('system_prompt_1',))
    cursor.execute('INSERT INTO config (key, value) VALUES (?, ?)', ('system_prompt_1', current_prompt))
    print("[SUCCESS] ✅ Created system_prompt_1")
    
    # Create system_prompt_2 (duplicate)
    cursor.execute('DELETE FROM config WHERE key = ?', ('system_prompt_2',))
    cursor.execute('INSERT INTO config (key, value) VALUES (?, ?)', ('system_prompt_2', current_prompt))
    print("[SUCCESS] ✅ Created system_prompt_2")
    
    # Create config entry for which version is active
    cursor.execute('DELETE FROM config WHERE key = ?', ('system_prompt_version',))
    cursor.execute('INSERT INTO config (key, value) VALUES (?, ?)', ('system_prompt_version', '1'))
    print("[SUCCESS] ✅ Created system_prompt_version config (currently set to 1)")
    
    conn.commit()
    
    # Verify
    cursor.execute('SELECT key FROM config WHERE key LIKE "system_prompt%" ORDER BY key')
    versions = cursor.fetchall()
    print("\n[INFO] Available prompt versions:")
    for (key,) in versions:
        size = len(cursor.execute('SELECT value FROM config WHERE key = ?', (key,)).fetchone()[0])
        print(f"  - {key} ({size} chars)")
    
    cursor.execute('SELECT value FROM config WHERE key = ?', ('system_prompt_version',))
    active = cursor.fetchone()[0]
    print(f"\n[INFO] Active version: system_prompt_{active}")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Update ai_advisor_service_linux.py to use system_prompt_version")
    print("2. Update mondrian.sh to support --prompt-version flag")
    print("3. Restart services to use versioning system")
    print("=" * 70)
    
    conn.close()
    
except Exception as e:
    print(f"[ERROR] ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
