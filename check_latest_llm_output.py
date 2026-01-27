#!/usr/bin/env python3
"""
Check the latest LLM output from the database
"""
import sqlite3
import json
from datetime import datetime

db_path = "mondrian.db"

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get latest job
    cursor.execute("""
        SELECT id, advisor, created_at, llm_outputs FROM jobs 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("❌ No jobs found in database")
        exit(1)
    
    job_id = row['id']
    advisor = row['advisor']
    created_at = row['created_at']
    llm_outputs_raw = row['llm_outputs']
    
    print("=" * 80)
    print(f"Latest Job ID: {job_id}")
    print(f"Advisor: {advisor}")
    print(f"Created: {created_at}")
    print("=" * 80)
    
    if not llm_outputs_raw:
        print("❌ No LLM outputs in this job")
        exit(0)
    
    # Try to parse the JSON
    try:
        llm_data = json.loads(llm_outputs_raw)
        print("\n✅ JSON parsed successfully!")
        print(f"\nTop-level keys: {list(llm_data.keys())}")
        
        # Check for response key
        if 'response' in llm_data:
            response = llm_data['response']
            print(f"\nResponse type: {type(response)}")
            print(f"Response length: {len(response) if isinstance(response, str) else 'N/A'}")
            
            # Show first 500 chars
            if isinstance(response, str) and len(response) > 0:
                print(f"\nFirst 500 chars of response:")
                print("-" * 80)
                print(response[:500])
                print("-" * 80)
                
                # Check for markdown issues
                if response.count('```') % 2 != 0:
                    print("\n⚠️  WARNING: Uneven backticks detected (odd count)")
                    print(f"Total backtick groups: {response.count('```')}")
                
                # Check ending
                print(f"\nLast 200 chars:")
                print("-" * 80)
                print(repr(response[-200:]))
                print("-" * 80)
        
        # Print full JSON with pretty formatting
        print("\n" + "=" * 80)
        print("Full LLM Output JSON:")
        print("=" * 80)
        output_str = json.dumps(llm_data, indent=2)
        if len(output_str) < 5000:
            print(output_str)
        else:
            print(output_str[:5000])
            print(f"\n... [truncated, total size: {len(output_str)} chars] ...")
    
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON parse error: {e}")
        print(f"Error at position {e.pos}")
        
        # Show context around error
        start = max(0, e.pos - 100)
        end = min(len(llm_outputs_raw), e.pos + 100)
        
        print(f"\nContext around error position {e.pos}:")
        print("-" * 80)
        print(f"Before: {repr(llm_outputs_raw[start:e.pos])}")
        print(f"After:  {repr(llm_outputs_raw[e.pos:end])}")
        print("-" * 80)
        
        print(f"\nFirst 500 chars of raw content:")
        print(repr(llm_outputs_raw[:500]))

except sqlite3.Error as e:
    print(f"❌ Database error: {e}")
except FileNotFoundError:
    print(f"❌ Database file not found: {db_path}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
