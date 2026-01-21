#!/usr/bin/env python3
"""
View Dimensional Profiles for Advisor Images in HTML

This script generates an HTML report showing all dimensional profiles
extracted from advisor images. These profiles are used for RAG comparison.

Usage:
    python3 tools/rag/view_dimensional_profiles.py [advisor_id]
    
    If advisor_id is not provided, shows all advisors.
"""

import os
import sys
import sqlite3
import json
import html
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from mondrian.config import DATABASE_PATH
    DB_PATH = DATABASE_PATH
except ImportError:
    # Fallback if config not available
    DB_PATH = os.path.join(Path(__file__).parent.parent.parent, "mondrian", "mondrian.db")


def get_dimensional_profiles(advisor_id=None):
    """Get all dimensional profiles from database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if advisor_id:
        cursor.execute("""
            SELECT * FROM dimensional_profiles 
            WHERE advisor_id = ?
            ORDER BY created_at DESC
        """, (advisor_id,))
    else:
        cursor.execute("""
            SELECT * FROM dimensional_profiles 
            ORDER BY advisor_id, created_at DESC
        """)
    
    profiles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return profiles


def format_score(score):
    """Format score for display."""
    if score is None:
        return "—"
    try:
        return f"{float(score):.1f}"
    except (ValueError, TypeError):
        return str(score) if score else "—"


def generate_html(profiles, advisor_id=None):
    """Generate HTML report of dimensional profiles."""
    
    # Group by advisor if showing all
    if not advisor_id:
        by_advisor = {}
        for profile in profiles:
            aid = profile.get('advisor_id', 'unknown')
            if aid not in by_advisor:
                by_advisor[aid] = []
            by_advisor[aid].append(profile)
    else:
        by_advisor = {advisor_id: profiles}
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dimensional Profiles - Advisor Images</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
            padding: 40px 20px;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        h1 {
            font-size: 42px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #1d1d1f;
        }
        
        .subtitle {
            font-size: 18px;
            color: #86868b;
            margin-bottom: 40px;
        }
        
        .advisor-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .advisor-header {
            border-bottom: 2px solid #f5f5f7;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .advisor-header h2 {
            font-size: 32px;
            font-weight: 600;
            color: #1d1d1f;
            text-transform: capitalize;
        }
        
        .profile-count {
            font-size: 16px;
            color: #86868b;
            margin-top: 8px;
        }
        
        .image-profile {
            background: #fafafa;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 30px;
            border-left: 4px solid #007AFF;
        }
        
        .image-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .image-info {
            flex: 1;
            min-width: 300px;
        }
        
        .image-title {
            font-size: 24px;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 8px;
        }
        
        .image-path {
            font-size: 14px;
            color: #86868b;
            font-family: 'Monaco', 'Menlo', monospace;
            word-break: break-all;
            margin-bottom: 12px;
        }
        
        .metadata {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 14px;
            color: #515154;
        }
        
        .metadata-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .metadata-label {
            font-weight: 600;
            color: #86868b;
        }
        
        .overall-grade {
            background: #007AFF;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 24px;
            font-weight: 600;
            text-align: center;
            min-width: 80px;
        }
        
        .scores-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 25px 0;
        }
        
        .dimension-card {
            background: white;
            border: 1px solid #e5e5e7;
            border-radius: 8px;
            padding: 20px;
        }
        
        .dimension-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .dimension-name {
            font-size: 18px;
            font-weight: 600;
            color: #1d1d1f;
        }
        
        .dimension-score {
            font-size: 24px;
            font-weight: 600;
            color: #007AFF;
        }
        
        .dimension-comment {
            font-size: 15px;
            color: #515154;
            line-height: 1.5;
            font-style: italic;
        }
        
        .description-section {
            background: #fafafa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }
        
        .description-title {
            font-size: 16px;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 10px;
        }
        
        .description-text {
            font-size: 15px;
            color: #515154;
            line-height: 1.6;
        }
        
        .created-at {
            font-size: 12px;
            color: #86868b;
            margin-top: 15px;
            text-align: right;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #86868b;
        }
        
        .empty-state h3 {
            font-size: 24px;
            margin-bottom: 10px;
            color: #515154;
        }
        
        .summary-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: #007AFF;
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 36px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .stat-label {
            font-size: 14px;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Dimensional Profiles</h1>
        <p class="subtitle">Analysis results for advisor images used in RAG comparison</p>
"""
    
    total_profiles = len(profiles)
    
    if total_profiles == 0:
        html += """
        <div class="advisor-section">
            <div class="empty-state">
                <h3>No Profiles Found</h3>
                <p>No dimensional profiles have been indexed yet.</p>
                <p style="margin-top: 20px;">Run <code>python3 tools/rag/index_ansel_dimensional_profiles.py</code> to index images.</p>
            </div>
        </div>
"""
    else:
        # Summary stats
        html += f"""
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-value">{total_profiles}</div>
                <div class="stat-label">Total Images</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(by_advisor)}</div>
                <div class="stat-label">Advisor{'' if len(by_advisor) == 1 else 's'}</div>
            </div>
        </div>
"""
        
        # Profiles by advisor
        for advisor_id_key, advisor_profiles in by_advisor.items():
            html += f"""
        <div class="advisor-section">
            <div class="advisor-header">
                <h2>{advisor_id_key.capitalize()} Adams</h2>
                <div class="profile-count">{len(advisor_profiles)} image{'' if len(advisor_profiles) == 1 else 's'} analyzed</div>
            </div>
"""
            
            for profile in advisor_profiles:
                image_path = profile.get('image_path', '')
                filename = os.path.basename(image_path) if image_path else 'Unknown'
                image_title = profile.get('image_title') or filename
                date_taken = profile.get('date_taken', '')
                location = profile.get('location', '')
                significance = profile.get('image_significance', '')
                overall_grade = profile.get('overall_grade', '')
                image_description = profile.get('image_description', '')
                created_at = profile.get('created_at', '')
                
                dimension_names = {
                    'composition': 'Composition',
                    'lighting': 'Lighting',
                    'focus_sharpness': 'Focus & Sharpness',
                    'depth_perspective': 'Depth & Perspective',
                    'visual_balance': 'Visual Balance',
                    'emotional_impact': 'Emotional Impact'
                }
                
                html += f"""
            <div class="image-profile">
                <div class="image-header">
                    <div class="image-info">
                        <div class="image-title">{html.escape(image_title)}</div>
                        <div class="image-path">{html.escape(image_path)}</div>
                        <div class="metadata">
"""
                
                if date_taken:
                    html += f'                            <div class="metadata-item"><span class="metadata-label">Date:</span> {html.escape(date_taken)}</div>\n'
                if location:
                    html += f'                            <div class="metadata-item"><span class="metadata-label">Location:</span> {html.escape(location)}</div>\n'
                if significance:
                    html += f'                            <div class="metadata-item"><span class="metadata-label">Significance:</span> {html.escape(significance[:100])}</div>\n'
                
                html += """                        </div>
                    </div>
"""
                
                if overall_grade:
                    html += f'                    <div class="overall-grade">{html.escape(str(overall_grade))}</div>\n'
                
                html += """                </div>
                
                <div class="scores-grid">
"""
                
                # Add dimension cards
                for dim_key, dim_name in dimension_names.items():
                    score_key = f'{dim_key}_score'
                    comment_key = f'{dim_key}_comment'
                    
                    score = format_score(profile.get(score_key))
                    comment = profile.get(comment_key, '')
                    
                    html += f"""                    <div class="dimension-card">
                        <div class="dimension-header">
                            <div class="dimension-name">{dim_name}</div>
                            <div class="dimension-score">{score}/10</div>
                        </div>
"""
                    if comment:
                        html += f'                        <div class="dimension-comment">{html.escape(comment)}</div>\n'
                    else:
                        html += '                        <div class="dimension-comment" style="color: #c7c7cc;">No comment</div>\n'
                    
                    html += """                    </div>
"""
                
                html += """                </div>
"""
                
                if image_description:
                    html += f"""                <div class="description-section">
                    <div class="description-title">Image Description</div>
                    <div class="description-text">{html.escape(image_description)}</div>
                </div>
"""
                
                if created_at:
                    html += f'                <div class="created-at">Indexed: {html.escape(created_at)}</div>\n'
                
                html += """            </div>
"""
            
            html += """        </div>
"""
    
    html += """    </div>
</body>
</html>"""
    
    return html


def main():
    advisor_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)
    
    print(f"Loading dimensional profiles from: {DB_PATH}")
    if advisor_id:
        print(f"Filtering for advisor: {advisor_id}")
    
    profiles = get_dimensional_profiles(advisor_id)
    
    print(f"Found {len(profiles)} profile(s)")
    
    html = generate_html(profiles, advisor_id)
    
    # Save to file
    output_file = "dimensional_profiles.html"
    if advisor_id:
        output_file = f"dimensional_profiles_{advisor_id}.html"
    
    output_path = os.path.join(Path(__file__).parent, output_file)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✓ HTML report generated: {output_path}")
    print(f"  Open in browser: open {output_path}")


if __name__ == "__main__":
    main()
