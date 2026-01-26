#!/usr/bin/env python3
"""
Test the new prompt loading logic from the rebuilt container
"""
import sqlite3
import sys

DB_PATH = "mondrian.db"

def get_config(db_path: str, key: str):
    """Get a configuration value from the database config table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key=?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            value = row[0]
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            return value
        return None
    except Exception as e:
        print(f"ERROR: Failed to get config {key}: {e}")
        return None


def get_latest_system_prompt_version(db_path: str):
    """
    Query database to find the latest system_prompt_X version.
    Returns the system prompt content from the highest numbered version.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all system_prompt_N keys (excluding system_prompt_version) and find the highest version number
        cursor.execute(
            "SELECT key FROM config WHERE key LIKE 'system_prompt_%' AND key != 'system_prompt_version' ORDER BY key DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            latest_key = row[0]  # e.g., "system_prompt_10"
            prompt_content = get_config(db_path, latest_key)
            if prompt_content:
                print(f"✅ Loaded latest prompt version: {latest_key}")
                return prompt_content, latest_key
        
        return None, None
    except Exception as e:
        print(f"ERROR: Failed to get latest system prompt version: {e}")
        return None, None


def test_prompt_loading():
    """Test the prompt loading logic"""
    print("=" * 80)
    print("Testing Prompt Loading Logic")
    print("=" * 80)
    
    # Test the new function
    prompt, key = get_latest_system_prompt_version(DB_PATH)
    
    if not prompt:
        print("❌ FAILED: No versioned system_prompt found")
        return False
    
    print(f"\nPrompt loaded from: {key}")
    print(f"Prompt length: {len(prompt)} characters")
    
    # Check for citation fields
    print("\n" + "-" * 80)
    print("Checking for citation field requirements:")
    print("-" * 80)
    
    checks = {
        "case_study_id": "case_study_id" in prompt,
        "quote_id": "quote_id" in prompt,
        "CITATION INSTRUCTIONS": "CITATION INSTRUCTIONS" in prompt,
        "IMG_": "IMG_" in prompt,
        "QUOTE_": "QUOTE_" in prompt,
        "JSON Structure": "Required JSON Structure" in prompt,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {result}")
        if not result:
            all_passed = False
    
    # Check for personality/style guidance
    print("\n" + "-" * 80)
    print("Checking for guidance content:")
    print("-" * 80)
    
    guidance_checks = {
        "SCORING PHILOSOPHY": "SCORING PHILOSOPHY" in prompt,
        "recommendations": "recommendation" in prompt.lower(),
        "technical_notes": "technical_notes" in prompt,
        "dimensions": "dimensions" in prompt,
    }
    
    for check_name, result in guidance_checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {result}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - Prompt is properly configured for citations")
    else:
        print("❌ SOME TESTS FAILED - Check prompt configuration")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    success = test_prompt_loading()
    sys.exit(0 if success else 1)
