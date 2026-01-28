#!/usr/bin/env python3
"""Check the latest job to see why case studies aren't appearing"""
import sqlite3
import json
import sys

conn = sqlite3.connect('mondrian.db')
cursor = conn.cursor()

# Get latest completed job
cursor.execute("""
    SELECT id, advisor, llm_outputs, analysis_html 
    FROM jobs 
    WHERE advisor = 'ansel' 
    ORDER BY created_at DESC 
    LIMIT 1
""")

row = cursor.fetchone()
if not row:
    print("No jobs found")
    sys.exit(1)

job_id, advisor, llm_outputs, analysis_html = row

print("="*70)
print(f"Latest Job: {job_id}")
print("="*70)

if llm_outputs:
    data = json.loads(llm_outputs)
    
    # Check if analysis exists
    if 'analysis' in data:
        analysis = data['analysis']
        
        print("\n1. RAG Candidates:")
        if 'rag_candidates' in analysis:
            print(f"   Images: {analysis['rag_candidates'].get('images', 0)}")
            print(f"   Quotes: {analysis['rag_candidates'].get('quotes', 0)}")
        else:
            print("   ❌ No rag_candidates field")
        
        print("\n2. Dimensions with case_study_id:")
        dimensions = analysis.get('dimensions', [])
        has_case_studies = False
        for dim in dimensions:
            if 'case_study_id' in dim or '_cited_image' in dim:
                has_case_studies = True
                cited = '✓ _cited_image' if '_cited_image' in dim else ''
                case_id = dim.get('case_study_id', 'N/A')
                print(f"   - {dim.get('name')}: case_study_id={case_id} {cited}")
        
        if not has_case_studies:
            print("   ❌ No dimensions have case_study_id or _cited_image")
            print("\n3. First dimension structure:")
            if dimensions:
                first_dim = dimensions[0]
                print(f"   Keys: {list(first_dim.keys())}")
                print(f"   Name: {first_dim.get('name')}")
                print(f"   Score: {first_dim.get('score')}")
    else:
        print("❌ No 'analysis' key in llm_outputs")
        print(f"Keys: {list(data.keys())}")
else:
    print("❌ No llm_outputs")

print("\n4. Check HTML for case study elements:")
if analysis_html:
    if 'case-study-box' in analysis_html:
        print("   ✓ Found 'case-study-box' in HTML")
        import re
        matches = re.findall(r'<div class="case-study-title">([^<]+)</div>', analysis_html)
        print(f"   Case studies: {matches}")
    else:
        print("   ❌ No 'case-study-box' found in HTML")
    
    if 'reference-citation' in analysis_html:
        print("   ✓ Found 'reference-citation' in HTML")
    else:
        print("   ❌ No 'reference-citation' found in HTML")
else:
    print("   ❌ No analysis_html")

print("\n" + "="*70)

conn.close()
