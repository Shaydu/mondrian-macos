#!/usr/bin/env python3
"""Extract a successful job's prompt and output"""
import sqlite3
import json

conn = sqlite3.connect('mondrian.db')
cursor = conn.cursor()

# Get a successful completed job
cursor.execute("""
    SELECT id, created_at, status, llm_prompt, llm_outputs FROM jobs 
    WHERE status='completed'
    ORDER BY created_at DESC 
    LIMIT 1
""")

row = cursor.fetchone()
conn.close()

if not row:
    print("No completed jobs found")
    exit(1)

job_id, created_at, status, llm_prompt, llm_outputs_raw = row

print(f"Job ID: {job_id}")
print(f"Created: {created_at}")
print(f"Status: {status}")
print(f"\n{'='*80}")
print("PROMPT USED:")
print(f"{'='*80}")
print(llm_prompt[:2000])
print(f"\n... [truncated, {len(llm_prompt)} total chars]")

print(f"\n{'='*80}")
print("LLM OUTPUT:")
print(f"{'='*80}")

try:
    llm_data = json.loads(llm_outputs_raw)
    response = llm_data.get('response', '')
    
    try:
        response_json = json.loads(response)
        dimensions = response_json.get('dimensions', [])
        print(f"✅ Generated {len(dimensions)} dimensions:")
        for dim in dimensions:
            print(f"  - {dim.get('name')}: {dim.get('score')}")
        
        print(f"\nImage description: {response_json.get('image_description', 'N/A')[:150]}")
        print(f"Overall score: {response_json.get('overall_score', 'N/A')}")
    except:
        print(f"Response (first 1000 chars): {response[:1000]}")
except Exception as e:
    print(f"Error: {e}")
