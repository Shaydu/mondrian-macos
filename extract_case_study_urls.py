#!/usr/bin/env python3
import sqlite3
import re

conn = sqlite3.connect('mondrian.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT id, summary_html 
    FROM jobs 
    WHERE status = 'completed' AND advisor IS NOT NULL
    ORDER BY created_at DESC 
    LIMIT 1
''')

row = cursor.fetchone()
if row:
    job_id, summary_html = row
    
    # Extract image URLs from case studies
    img_pattern = r'<img[^>]*src="([^"]*)"[^>]*class="case-study-image"'
    matches = re.findall(img_pattern, summary_html)
    
    print(f'Job ID: {job_id}')
    print(f'\nCase study image URLs found: {len(matches)}')
    for i, url in enumerate(matches, 1):
        print(f'{i}. {url}')
    
    # Extract case study titles
    title_pattern = r'<div class="case-study-title">([^<]*)</div>'
    titles = re.findall(title_pattern, summary_html)
    print(f'\nCase study titles found: {len(titles)}')
    for i, title in enumerate(titles, 1):
        print(f'{i}. {title}')
    
    # Check if there are any case study boxes
    if 'case-study-box' in summary_html:
        # Extract full case study boxes
        box_pattern = r'<div class="case-study-box">(.*?)</div>\s*</div>'
        boxes = re.findall(box_pattern, summary_html, re.DOTALL)
        print(f'\nFull case study boxes found: {len(boxes)}')
        if boxes:
            print('\nFirst case study box content:')
            print(boxes[0][:500])
            
conn.close()
