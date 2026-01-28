#!/usr/bin/env python3
"""
View all instructive text for advisor reference images
"""

import sqlite3
import argparse

DB_PATH = "mondrian.db"

DIMENSIONS = [
    'composition', 'lighting', 'focus_sharpness', 'color_harmony',
    'subject_isolation', 'depth_perspective', 'visual_balance', 'emotional_impact'
]

def view_instructive_text(advisor_id='ansel', format='text'):
    """Display all instructive text for an advisor's images"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT 
            id, image_title, image_path,
            composition_score, composition_instructive,
            lighting_score, lighting_instructive,
            focus_sharpness_score, focus_sharpness_instructive,
            color_harmony_score, color_harmony_instructive,
            subject_isolation_score, subject_isolation_instructive,
            depth_perspective_score, depth_perspective_instructive,
            visual_balance_score, visual_balance_instructive,
            emotional_impact_score, emotional_impact_instructive
        FROM dimensional_profiles
        WHERE advisor_id = ?
        ORDER BY image_title
    """
    
    cursor.execute(query, (advisor_id,))
    images = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if format == 'markdown':
        print_markdown(images)
    else:
        print_text(images)

def print_text(images):
    """Print in readable text format"""
    print(f"\n{'='*80}")
    print(f"INSTRUCTIVE TEXT FOR ALL ADVISOR IMAGES ({len(images)} images)")
    print(f"{'='*80}\n")
    
    for img in images:
        print(f"\n{'='*80}")
        print(f"📷 {img['image_title']}")
        print(f"{'='*80}")
        
        has_content = False
        for dim in DIMENSIONS:
            score = img.get(f'{dim}_score')
            instructive = img.get(f'{dim}_instructive')
            
            filtered_instructive = filter_user_focused_guidance(instructive)
            
            if filtered_instructive:
                has_content = True
                dim_name = dim.replace('_', ' ').title()
                print(f"\n{dim_name} ({score:.1f}/10):")
                print(f"  {filtered_instructive}")
        
        if not has_content:
            print("  (No improvement recommendations available)")

def print_markdown(images):
    """Print in Markdown format"""
    print(f"# Guidance - Improve Your Images\n")
    print(f"Based on {len(images)} advisor reference images\n")
    
    for img in images:
        print(f"\n## {img['image_title']}\n")
        
        has_content = False
        for dim in DIMENSIONS:
            score = img.get(f'{dim}_score')
            instructive = img.get(f'{dim}_instructive')
            
            filtered_instructive = filter_user_focused_guidance(instructive)
            
            if filtered_instructive:
                has_content = True
                dim_name = dim.replace('_', ' ').title()
                print(f"### {dim_name} ({score:.1f}/10)\n")
                print(f"{filtered_instructive}\n")
        
        if not has_content:
            print("*No improvement recommendations available*\n")

def filter_user_focused_guidance(instructive_text):
    """
    Filter instructive text to focus only on user's image improvements.
    Removes feedback about the advisor's image and keeps only actionable recommendations.
    """
    if not instructive_text:
        return None
    
    lines = instructive_text.split('\n')
    user_focused_lines = []
    
    for line in lines:
        line_lower = line.lower()
        # Skip lines that describe the advisor's image qualities
        skip_phrases = [
            'this image', 'the image shows', 'demonstrates', 'exemplifies',
            'reference image', 'advisor image', 'example of'
        ]
        
        if any(phrase in line_lower for phrase in skip_phrases):
            # Check if it's a recommendation (has "consider", "try", "improve", "should", "could")
            recommendation_phrases = ['consider', 'try', 'improve', 'should', 'could', 'recommend', 'increase', 'decrease', 'adjust', 'enhance']
            if not any(phrase in line_lower for phrase in recommendation_phrases):
                continue
        
        user_focused_lines.append(line)
    
    filtered_text = '\n'.join(user_focused_lines).strip()
    return filtered_text if filtered_text else None

def main():
    parser = argparse.ArgumentParser(
        description="View instructive text for advisor images"
    )
    parser.add_argument(
        '--advisor',
        type=str,
        default='ansel',
        help='Advisor ID (default: ansel)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['text', 'markdown'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save to file instead of printing to console'
    )
    
    args = parser.parse_args()
    
    if args.output:
        import sys
        with open(args.output, 'w') as f:
            sys.stdout = f
            view_instructive_text(args.advisor, args.format)
            sys.stdout = sys.__stdout__
        print(f"\n✓ Saved to {args.output}")
    else:
        view_instructive_text(args.advisor, args.format)

if __name__ == '__main__':
    main()
