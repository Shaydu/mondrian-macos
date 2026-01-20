#!/usr/bin/env python3
"""
Generate instructive text for reference images.

For each reference image with high scores (>=8) in a dimension,
generate text explaining WHY this image is instructive for learning that dimension.

You can either:
1. Generate this automatically with an LLM
2. Manually curate high-quality instructive text
3. Mix of both - generate with LLM, then manually refine
"""

import sqlite3
import argparse

DB_PATH = "mondrian.db"

# Example manually-curated instructive text for Ansel's iconic images
MANUAL_INSTRUCTIVE_TEXT = {
    "Adams The Tetons and the Snake River": {
        "composition": "Study how the S-curve of the Snake River creates a natural leading line that draws your eye from the dark foreground through the silvery water to the majestic peaks. The rule of thirds places the horizon in the upper third, emphasizing the land. This layering of foreground, middle ground, and background creates depth and invites the viewer to journey through the scene.",
        "lighting": "Notice the dramatic sky with rich tonal gradation from deep shadows in the storm clouds to bright highlights on the peaks. The side lighting reveals texture in every surface - from the ripples in the water to the ridges on the mountains. This is the Zone System in practice: preserving detail in both shadows (Zones II-III) and highlights (Zones VII-VIII).",
        "depth_perspective": "Observe how the converging lines of the river banks create strong linear perspective, while the atmospheric perspective makes distant peaks appear lighter and softer. The dark foreground rocks anchor the viewer's position, establishing a clear sense of scale and distance. This three-dimensional effect transforms a flat photograph into an immersive space.",
        "visual_balance": "The river's diagonal movement from lower left to upper right creates dynamic energy, balanced by the solid horizontal mass of the mountains. The darker left side is counterweighted by the brighter right side, creating equilibrium without symmetry. This asymmetrical balance is more engaging than centered composition.",
        "emotional_impact": "The grandeur of the peaks combined with the threatening storm clouds evokes both awe and the untamed power of nature. The human-less landscape emphasizes wilderness and scale, inviting contemplation. This emotional resonance comes from technical mastery serving expressive intent - the tonal drama and compositional depth working together to create feeling."
    },
    # Add more images here as you process them
}

def get_reference_images(advisor_id='ansel', min_score=8.0):
    """Get all reference images with high scores"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT 
            id, image_title, image_path,
            composition_score, lighting_score, focus_sharpness_score,
            color_harmony_score, subject_isolation_score, 
            depth_perspective_score, visual_balance_score, emotional_impact_score
        FROM dimensional_profiles
        WHERE advisor_id = ?
        AND (
            composition_score >= ? OR
            lighting_score >= ? OR
            focus_sharpness_score >= ? OR
            color_harmony_score >= ? OR
            subject_isolation_score >= ? OR
            depth_perspective_score >= ? OR
            visual_balance_score >= ? OR
            emotional_impact_score >= ?
        )
        ORDER BY image_title
    """
    
    params = [advisor_id] + [min_score] * 8
    cursor.execute(query, params)
    
    images = []
    for row in cursor.fetchall():
        images.append(dict(row))
    
    conn.close()
    return images

def update_instructive_text(image_id, dimension, instructive_text):
    """Update instructive text for a specific image and dimension"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    column_name = f"{dimension}_instructive"
    query = f"UPDATE dimensional_profiles SET {column_name} = ? WHERE id = ?"
    
    cursor.execute(query, (instructive_text, image_id))
    conn.commit()
    conn.close()

def populate_manual_instructive_text():
    """Populate database with manually-curated instructive text"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Populating manually-curated instructive text...\n")
    
    for image_title, dimension_texts in MANUAL_INSTRUCTIVE_TEXT.items():
        # Find the image in the database
        cursor.execute(
            "SELECT id FROM dimensional_profiles WHERE image_title = ?",
            (image_title,)
        )
        row = cursor.fetchone()
        
        if not row:
            print(f"⚠️  Image not found: {image_title}")
            continue
        
        image_id = row[0]
        print(f"📷 {image_title}")
        
        for dimension, text in dimension_texts.items():
            column_name = f"{dimension}_instructive"
            cursor.execute(
                f"UPDATE dimensional_profiles SET {column_name} = ? WHERE id = ?",
                (text, image_id)
            )
            print(f"   ✓ {dimension}: {len(text)} chars")
        
        print()
    
    conn.commit()
    conn.close()
    print("✓ Manual instructive text populated!")

def generate_with_llm(advisor_id='ansel', min_score=8.0):
    """Generate instructive text using LLM (placeholder for future implementation)"""
    print("LLM generation not yet implemented.")
    print("You can:")
    print("  1. Add entries to MANUAL_INSTRUCTIVE_TEXT dict in this script")
    print("  2. Update database directly with SQL")
    print("  3. Implement LLM generation here")

def show_missing_instructive_text(advisor_id='ansel', min_score=8.0):
    """Show which high-scoring images are missing instructive text"""
    images = get_reference_images(advisor_id, min_score)
    dimensions = [
        'composition', 'lighting', 'focus_sharpness', 'color_harmony',
        'subject_isolation', 'depth_perspective', 'visual_balance', 'emotional_impact'
    ]
    
    print(f"\n📊 Reference images with high scores (>={min_score}) missing instructive text:\n")
    
    missing_count = 0
    for img in images:
        title = img['image_title'] or img['image_path']
        missing_dims = []
        
        for dim in dimensions:
            score = img.get(f'{dim}_score')
            instructive = img.get(f'{dim}_instructive')
            
            if score and score >= min_score and not instructive:
                missing_dims.append(f"{dim}:{score}")
        
        if missing_dims:
            print(f"📷 {title}")
            print(f"   Missing: {', '.join(missing_dims)}")
            missing_count += 1
    
    if missing_count == 0:
        print("✅ All high-scoring dimensions have instructive text!")
    else:
        print(f"\n⚠️  {missing_count} images need instructive text")

def main():
    parser = argparse.ArgumentParser(description="Generate instructive text for reference images")
    parser.add_argument('--advisor', default='ansel', help='Advisor ID')
    parser.add_argument('--min-score', type=float, default=8.0, help='Minimum score to consider')
    parser.add_argument('--populate-manual', action='store_true', 
                       help='Populate with manually-curated text')
    parser.add_argument('--show-missing', action='store_true',
                       help='Show which images need instructive text')
    parser.add_argument('--generate-llm', action='store_true',
                       help='Generate with LLM (not yet implemented)')
    
    args = parser.parse_args()
    
    if args.populate_manual:
        populate_manual_instructive_text()
    elif args.show_missing:
        show_missing_instructive_text(args.advisor, args.min_score)
    elif args.generate_llm:
        generate_with_llm(args.advisor, args.min_score)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
