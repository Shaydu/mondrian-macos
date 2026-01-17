#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('mondrian.db')
cursor = conn.cursor()
cursor.execute('SELECT id, llm_outputs, summary_html FROM jobs WHERE advisor = ? ORDER BY created_at DESC LIMIT 1', ('ansel',))
row = cursor.fetchone()

if row and row[1]:
    job_id = row[0]
    data = json.loads(row[1])
    summary_html = row[2]
    
    print(f'Job ID: {job_id}')
    print(f'Top-level keys: {list(data.keys())}')
    
    # Check if this is the new format from ai_advisor_service
    if 'analysis' in data:
        analysis = data['analysis']
        print(f'\nAnalysis keys: {list(analysis.keys())}')
        if 'case_studies' in analysis:
            print(f'\n✓ Case studies found: {len(analysis["case_studies"])} entries')
            print(json.dumps(analysis['case_studies'], indent=2))
        else:
            print('\n✗ NO case_studies in analysis')
    else:
        print('\n✗ NO analysis key in output (old format)')
    
    # Check summary HTML
    if summary_html:
        has_case_study = 'case-study' in summary_html.lower() or 'case study' in summary_html.lower()
        print(f'\nSummary HTML has case study content: {has_case_study}')
        if has_case_study:
            # Count occurrences
            count = summary_html.lower().count('case-study-box')
            print(f'Number of case-study-box divs: {count}')
    else:
        print('\n✗ NO summary_html')
else:
    print('No jobs found')

conn.close()
