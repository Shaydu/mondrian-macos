#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('mondrian.db')
cursor = conn.cursor()

# Get most recent completed job
cursor.execute('''
    SELECT id, advisor, mode, summary_html, analysis_html 
    FROM jobs 
    WHERE status = 'completed' AND advisor IS NOT NULL
    ORDER BY created_at DESC 
    LIMIT 1
''')

row = cursor.fetchone()
if row:
    job_id, advisor, mode, summary_html, analysis_html = row
    print(f'Job ID: {job_id}')
    print(f'Advisor: {advisor}, Mode: {mode}')
    print(f'\nSummary HTML length: {len(summary_html) if summary_html else 0}')
    print(f'Analysis HTML length: {len(analysis_html) if analysis_html else 0}')
    
    # Check for case studies in summary HTML
    if summary_html:
        has_case_study_box = 'case-study-box' in summary_html
        has_case_study_title = 'case-study-title' in summary_html
        has_case_study_image = 'case-study-image' in summary_html
        
        print(f'\nSummary HTML case study elements:')
        print(f'  - case-study-box: {has_case_study_box}')
        print(f'  - case-study-title: {has_case_study_title}')
        print(f'  - case-study-image: {has_case_study_image}')
        
        if has_case_study_box:
            count = summary_html.count('case-study-box')
            print(f'  - Number of case studies: {count}')
        
        # Show a snippet if case studies found
        if has_case_study_title:
            idx = summary_html.find('case-study-title')
            snippet = summary_html[max(0, idx-100):min(len(summary_html), idx+300)]
            print(f'\nSnippet around case-study-title:\n{snippet}')
    
    # Check for case studies in analysis HTML  
    if analysis_html:
        has_case_study_box = 'case-study-box' in analysis_html
        has_reference_citation = 'reference-citation' in analysis_html
        
        print(f'\nAnalysis HTML case study elements:')
        print(f'  - case-study-box: {has_case_study_box}')
        print(f'  - reference-citation: {has_reference_citation}')
        
        if has_case_study_box:
            count = analysis_html.count('case-study-box')
            print(f'  - Number of case studies: {count}')
else:
    print('No completed jobs found')

conn.close()
