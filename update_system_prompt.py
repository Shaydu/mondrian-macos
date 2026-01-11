#!/usr/bin/env python3
"""
Update system prompt in database to use HTML format instead of JSON
"""
import sys
import os

# Add mondrian directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mondrian'))

from sqlite_helper import set_config, get_config

DB_PATH = "mondrian/mondrian.db"
NEW_PROMPT_FILE = "mondrian/prompts/system_html.md"

def main():
    print("=" * 70)
    print("System Prompt Update Tool")
    print("=" * 70)

    # Check if new prompt file exists
    if not os.path.exists(NEW_PROMPT_FILE):
        print(f"[ERROR] New prompt file not found: {NEW_PROMPT_FILE}")
        sys.exit(1)

    # Read new prompt
    with open(NEW_PROMPT_FILE, 'r', encoding='utf-8') as f:
        new_prompt = f.read()

    print(f"\n[INFO] New prompt loaded: {len(new_prompt)} characters")

    # Get current prompt for backup
    current_prompt = get_config(DB_PATH, "system_prompt")
    if current_prompt:
        print(f"[INFO] Current prompt: {len(current_prompt)} characters")

        # Save backup
        backup_file = "mondrian/prompts/system_json_backup.md"
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
            print("2. Run: python3 mondrian/test/test_diagnose_500_error.py")
            print("3. Verify HTML output is generated correctly")
            print("=" * 70)
        else:
            print("[ERROR] ❌ Verification failed - stored prompt doesn't match")
            sys.exit(1)
    else:
        print("[ERROR] ❌ Failed to update system prompt")
        sys.exit(1)

if __name__ == "__main__":
    main()
