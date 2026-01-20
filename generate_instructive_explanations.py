#!/usr/bin/env python3
"""
Generate Instructive Explanations for Reference Images

For each reference image with high scores in specific dimensions,
generate instructive text explaining WHY this image teaches that dimension well.

This uses the LLM to generate focused, actionable explanations that help users
understand what to learn from each reference image.

IMPORTANT CONSTRAINTS:
- Zone System references ONLY for lighting/exposure-related dimensions
- Each dimension gets its own focused feedback relevant to that dimension
"""

import sqlite3
import requests
import json
import argparse
import time
from pathlib import Path

DB_PATH = "mondrian.db"
AI_ADVISOR_URL = "http://127.0.0.1:5100"

# Dimensions mapped to their instructive focus
DIMENSION_FOCUS = {
    'composition': {
        'focus': 'compositional techniques, visual structure, rule of thirds, leading lines, framing, layering',
        'avoid': 'Zone System, tonal values'
    },
    'lighting': {
        'focus': 'light quality, direction, tonal range, Zone System for exposure, shadow/highlight detail',
        'allow_zone_system': True
    },
    'focus_sharpness': {
        'focus': 'sharpness, depth of field, focus point selection, f-stop choice, critical sharpness',
        'avoid': 'Zone System, composition, lighting quality'
    },
    'color_harmony': {
        'focus': 'color relationships, palette choices, color temperature, saturation, color contrast',
        'avoid': 'Zone System, black and white tonal values'
    },
    'subject_isolation': {
        'focus': 'subject separation, depth of field, background simplification, visual hierarchy',
        'avoid': 'Zone System, overall composition'
    },
    'depth_perspective': {
        'focus': 'three-dimensional space, perspective, foreground/background relationships, atmospheric perspective, layering',
        'avoid': 'Zone System, color choices'
    },
    'visual_balance': {
        'focus': 'visual weight distribution, asymmetry vs symmetry, equilibrium, tension',
        'avoid': 'Zone System, specific lighting techniques'
    },
    'emotional_impact': {
        'focus': 'emotional resonance, mood, feeling, viewer connection, expressive intent',
        'avoid': 'technical specifics, Zone System details'
    }
}

def generate_instructive_prompt(image_info, dimension, score):
    """Generate prompt for LLM to create instructive explanation"""
    
    image_title = image_info.get('image_title', 'Untitled')
    image_desc = image_info.get('image_description', '')
    dimension_comment = image_info.get(f'{dimension}_comment', '')
    
    dim_focus = DIMENSION_FOCUS.get(dimension, {})
    focus_areas = dim_focus.get('focus', '')
    avoid_topics = dim_focus.get('avoid', '')
    allow_zone_system = dim_focus.get('allow_zone_system', False)
    
    zone_system_instruction = ""
    if allow_zone_system:
        zone_system_instruction = """
- You MAY reference the Zone System ONLY if directly relevant to tonal range and exposure
- Keep Zone System references brief (1-2 mentions max)
- Focus on WHY the tonal range works, not just listing zones"""
    else:
        zone_system_instruction = f"""
- DO NOT mention the Zone System - this dimension is about {focus_areas}, not tonal values
- Focus entirely on {focus_areas}"""
    
    prompt = f"""You are Ansel Adams explaining to a photography student WHY this reference image is instructive for learning the {dimension.replace('_', ' ')} dimension.

IMAGE: "{image_title}"
DESCRIPTION: {image_desc}
TECHNICAL ANALYSIS: {dimension_comment}
SCORE: {score}/10 in {dimension.replace('_', ' ')}

Generate a 2-3 sentence explanation that:
1. Points out the SPECIFIC technique or quality in THIS image that demonstrates mastery
2. Explains WHY this technique works and what effect it creates  
3. Gives ACTIONABLE guidance on what the student should learn and try

CONSTRAINTS:
- Write in FIRST PERSON as Ansel Adams (use "I", "my")
- Focus ONLY on: {focus_areas}
- AVOID discussing: {avoid_topics}{zone_system_instruction}
- Be specific to THIS image - don't give generic advice
- Maximum 100 words
- Be encouraging but technically precise

Example format:
"Study how [specific technique in this image]. This [explains the effect it creates]. When you photograph [subject type], try [actionable specific guidance]."

Generate the instructive explanation now:"""
    
    return prompt

def call_llm(prompt, max_retries=3):
    """Call LLM via AI Advisor Service"""
    for attempt in range(max_retries):
        try:
            # Use the chat endpoint for text generation
            response = requests.post(
                f"{AI_ADVISOR_URL}/chat",
                json={"message": prompt},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                print(f"  [WARN] LLM call failed: {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None
                
        except Exception as e:
            print(f"  [ERROR] LLM call exception: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    
    return None

def get_reference_images(advisor_id, min_score=8.0):
    """Get reference images that need instructive text"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all dimensions
    dimensions = [
        'composition', 'lighting', 'focus_sharpness', 'color_harmony',
        'subject_isolation', 'depth_perspective', 'visual_balance', 'emotional_impact'
    ]
    
    # Build query to find images with high scores but missing instructive text
    score_conditions = []
    instructive_conditions = []
    
    for dim in dimensions:
        score_conditions.append(f"{dim}_score >= {min_score}")
        instructive_conditions.append(f"{dim}_instructive IS NULL")
    
    query = f"""
        SELECT 
            id, image_title, image_path, image_description,
            composition_score, composition_comment, composition_instructive,
            lighting_score, lighting_comment, lighting_instructive,
            focus_sharpness_score, focus_sharpness_comment, focus_sharpness_instructive,
            color_harmony_score, color_harmony_comment, color_harmony_instructive,
            subject_isolation_score, subject_isolation_comment, subject_isolation_instructive,
            depth_perspective_score, depth_perspective_comment, depth_perspective_instructive,
            visual_balance_score, visual_balance_comment, visual_balance_instructive,
            emotional_impact_score, emotional_impact_comment, emotional_impact_instructive
        FROM dimensional_profiles
        WHERE advisor_id = ?
        AND ({' OR '.join(score_conditions)})
        ORDER BY image_title
    """
    
    cursor.execute(query, (advisor_id,))
    images = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return images

def update_instructive_text(image_id, dimension, text):
    """Update instructive text in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    column = f"{dimension}_instructive"
    cursor.execute(
        f"UPDATE dimensional_profiles SET {column} = ? WHERE id = ?",
        (text, image_id)
    )
    
    conn.commit()
    conn.close()

def generate_for_image(image_info, dimensions_to_generate, min_score=8.0):
    """Generate instructive text for specific dimensions of an image"""
    
    image_id = image_info['id']
    image_title = image_info.get('image_title', 'Untitled')
    
    print(f"\n📷 {image_title}")
    print(f"   ID: {image_id}")
    
    generated_count = 0
    skipped_count = 0
    
    for dimension in dimensions_to_generate:
        score = image_info.get(f'{dimension}_score')
        existing_instructive = image_info.get(f'{dimension}_instructive')
        
        # Skip if score too low
        if not score or score < min_score:
            continue
        
        # Skip if already has instructive text
        if existing_instructive:
            print(f"   ⏭️  {dimension}: already has instructive text")
            skipped_count += 1
            continue
        
        print(f"   🔄 {dimension} ({score:.1f}/10)...", end='', flush=True)
        
        # Generate prompt
        prompt = generate_instructive_prompt(image_info, dimension, score)
        
        # Call LLM
        instructive_text = call_llm(prompt)
        
        if instructive_text:
            # Update database
            update_instructive_text(image_id, dimension, instructive_text)
            print(f" ✓ ({len(instructive_text)} chars)")
            generated_count += 1
            
            # Brief pause to avoid overwhelming the service
            time.sleep(0.5)
        else:
            print(f" ✗ Failed to generate")
    
    return generated_count, skipped_count

def main():
    parser = argparse.ArgumentParser(
        description="Generate instructive explanations for reference images"
    )
    parser.add_argument(
        '--advisor',
        type=str,
        default='ansel',
        help='Advisor ID (default: ansel)'
    )
    parser.add_argument(
        '--min-score',
        type=float,
        default=8.0,
        help='Minimum score to generate instructive text (default: 8.0)'
    )
    parser.add_argument(
        '--dimensions',
        type=str,
        nargs='+',
        help='Specific dimensions to generate (default: all high-scoring)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of images to process'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenerate even if instructive text already exists'
    )
    
    args = parser.parse_args()
    
    # Get images needing instructive text
    print(f"Finding reference images for {args.advisor} with scores >= {args.min_score}...")
    images = get_reference_images(args.advisor, args.min_score)
    
    if args.limit:
        images = images[:args.limit]
    
    print(f"Found {len(images)} images to process\n")
    print("="*70)
    
    if not images:
        print("No images found needing instructive text!")
        return
    
    # Determine which dimensions to process
    all_dimensions = [
        'composition', 'lighting', 'focus_sharpness', 'color_harmony',
        'subject_isolation', 'depth_perspective', 'visual_balance', 'emotional_impact'
    ]
    
    dimensions_to_process = args.dimensions if args.dimensions else all_dimensions
    
    total_generated = 0
    total_skipped = 0
    
    for i, image_info in enumerate(images, 1):
        print(f"\n[{i}/{len(images)}]")
        generated, skipped = generate_for_image(
            image_info, 
            dimensions_to_process,
            args.min_score
        )
        total_generated += generated
        total_skipped += skipped
    
    print("\n" + "="*70)
    print(f"Generation Complete: {args.advisor}")
    print("="*70)
    print(f"✓ Generated:  {total_generated} instructive explanations")
    print(f"⏭️  Skipped:    {total_skipped} (already exist)")
    print("="*70)
    print("\nNext step: Restart services and test with a user image!")

if __name__ == '__main__':
    main()
