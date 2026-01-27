#!/usr/bin/env python3
"""
Check if latest LLM output has parse error at column 945, character 944
"""
import sqlite3
import json

db_path = "mondrian.db"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT id, advisor, created_at, llm_outputs FROM jobs 
    ORDER BY created_at DESC 
    LIMIT 1
""")

row = cursor.fetchone()
conn.close()

if not row:
    print("❌ No jobs found")
    exit(1)

job_id = row['id']
llm_outputs_raw = row['llm_outputs']

print(f"Job ID: {job_id}")
print(f"Raw output length: {len(llm_outputs_raw)}")
print(f"\nAttempting JSON parse...")

try:
    llm_data = json.loads(llm_outputs_raw)
    print("✅ SUCCESS: JSON parsed without errors")
    print(f"Top-level keys: {list(llm_data.keys())}")
except json.JSONDecodeError as e:
    print(f"❌ JSON PARSE ERROR!")
    print(f"Error: {e}")
    print(f"Position: {e.pos}")
    print(f"Line: {e.lineno}")
    print(f"Column: {e.colno}")
    
    # Check if this matches the reported error
    if e.pos == 944 and e.colno == 945:
        print(f"\n🎯 MATCHES REPORTED ERROR: column 945, character 944")
    
    # Show context
    start = max(0, e.pos - 100)
    end = min(len(llm_outputs_raw), e.pos + 100)
    
    print(f"\nContext around error ({start}-{end}):")
    print(f"Before error: {repr(llm_outputs_raw[start:e.pos])}")
    print(f"Error char: {repr(llm_outputs_raw[e.pos])}")
    print(f"After error: {repr(llm_outputs_raw[e.pos:end])}")
