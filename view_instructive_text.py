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
            
            if instructive and instructive.strip():
                has_content = True
                dim_name = dim.replace('_', ' ').title()
                print(f"\n{dim_name} ({score:.1f}/10):")
                print(f"  {instructive}")
        
        if not has_content:
            print("  (No instructive text available)")

def print_markdown(images):
    """Print in Markdown format"""
    print(f"# Instructive Text - All Advisor Images\n")
    print(f"Total images: {len(images)}\n")
    
    for img in images:
        print(f"\n## {img['image_title']}\n")
        
        has_content = False
        for dim in DIMENSIONS:
            score = img.get(f'{dim}_score')
            instructive = img.get(f'{dim}_instructive')
            
            if instructive and instructive.strip():
                has_content = True
                dim_name = dim.replace('_', ' ').title()
                print(f"### {dim_name} ({score:.1f}/10)\n")
                print(f"{instructive}\n")
        
        if not has_content:
            print("*No instructive text available*\n")

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
