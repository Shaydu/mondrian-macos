#!/usr/bin/env python3
"""
Import curated metadata from YAML file and generate dimensional scores from tags.
Maps tags to dimensional scores for Ansel Adams reference images.

Usage:
    python scripts/import_tagged_metadata.py
"""

import yaml
import sqlite3
import os
from pathlib import Path

# Configuration
WORKSPACE_ROOT = Path(__file__).parent.parent
DB_PATH = WORKSPACE_ROOT / "mondrian.db"
METADATA_FILE = WORKSPACE_ROOT / "mondrian/source/advisor/photographer/ansel/metadata.yaml"
ANSEL_DIR = WORKSPACE_ROOT / "mondrian/source/advisor/photographer/ansel"

# Tag to dimensional score mapping
# Each tag contributes to one or more dimensions
TAG_SCORE_MAP = {
    # Composition-related tags
    "composition": {"composition_score": 10.0},
    "layered_depth": {"composition_score": 9.5, "depth_perspective_score": 9.5},
    "rule_of_thirds": {"composition_score": 9.0, "visual_balance_score": 9.0},
    "leading_lines": {"composition_score": 9.5, "depth_perspective_score": 9.0},
    "foreground_interest": {"composition_score": 9.0, "depth_perspective_score": 9.0},
    "pattern": {"composition_score": 9.0, "visual_balance_score": 8.5},
    "symmetry": {"visual_balance_score": 10.0, "composition_score": 9.0},
    "geometric": {"composition_score": 8.5, "visual_balance_score": 8.5},
    
    # Lighting-related tags
    "zone_system": {"lighting_score": 10.0, "color_harmony_score": 9.0},
    "dramatic_lighting": {"lighting_score": 10.0, "emotional_impact_score": 9.5},
    "high_contrast": {"lighting_score": 9.5, "color_harmony_score": 8.5},
    "tonal_range": {"lighting_score": 9.5, "color_harmony_score": 9.0},
    "soft_light": {"lighting_score": 8.5, "emotional_impact_score": 8.5},
    "shadows": {"lighting_score": 9.0, "composition_score": 8.5},
    "atmospheric": {"lighting_score": 8.5, "emotional_impact_score": 9.0},
    
    # Depth & Perspective tags
    "depth": {"depth_perspective_score": 9.5},
    "layers": {"depth_perspective_score": 9.5, "composition_score": 9.0},
    "perspective": {"depth_perspective_score": 9.0, "composition_score": 8.5},
    "reflection": {"visual_balance_score": 9.0, "composition_score": 8.5},
    
    # Focus & Sharpness tags
    "texture": {"focus_sharpness_score": 9.5, "composition_score": 8.0},
    "motion": {"focus_sharpness_score": 9.0},
    "long_exposure": {"focus_sharpness_score": 8.5},
    
    # Subject Isolation tags
    "isolation": {"subject_isolation_score": 10.0, "visual_balance_score": 9.0},
    "negative_space": {"subject_isolation_score": 9.5, "visual_balance_score": 9.0},
    "minimalist": {"subject_isolation_score": 9.0, "composition_score": 8.5},
    
    # Emotional Impact tags
    "emotional": {"emotional_impact_score": 10.0},
    "timing": {"emotional_impact_score": 9.0, "composition_score": 8.5},
    "mood": {"emotional_impact_score": 9.5},
    "dramatic": {"emotional_impact_score": 9.5, "lighting_score": 9.0},
    
    # Other tags with dimensional impacts
    "landscape": {"composition_score": 8.5, "depth_perspective_score": 8.5},
    "architecture": {"composition_score": 9.0, "visual_balance_score": 8.5},
    "abstract": {"composition_score": 8.5, "visual_balance_score": 8.0},
    "documentary": {"emotional_impact_score": 8.5, "composition_score": 8.0},
    "curves": {"composition_score": 9.0, "visual_balance_score": 8.5},
    "vertical_lines": {"composition_score": 8.5, "visual_balance_score": 8.5},
    "scale": {"depth_perspective_score": 8.5, "composition_score": 8.0},
    "human_element": {"emotional_impact_score": 8.5, "composition_score": 8.0},
    "clouds": {"composition_score": 8.5, "emotional_impact_score": 8.0},
    "sky": {"composition_score": 8.0, "lighting_score": 8.5},
    "water": {"composition_score": 8.0, "visual_balance_score": 8.0},
    "winter": {"lighting_score": 8.5, "color_harmony_score": 8.5},
    "forest": {"depth_perspective_score": 8.5, "emotional_impact_score": 8.0},
}

# Default scores for dimensions not affected by tags
DEFAULT_SCORES = {
    "composition_score": 8.0,
    "lighting_score": 8.0,
    "focus_sharpness_score": 9.0,  # Ansel's work is generally sharp
    "color_harmony_score": 8.0,
    "subject_isolation_score": 7.5,
    "depth_perspective_score": 8.0,
    "visual_balance_score": 8.0,
    "emotional_impact_score": 8.0
}


def calculate_scores_from_tags(tags):
    """Calculate dimensional scores based on image tags"""
    scores = DEFAULT_SCORES.copy()
    
    for tag in tags:
        if tag in TAG_SCORE_MAP:
            for dimension, score in TAG_SCORE_MAP[tag].items():
                # Take the maximum score for each dimension
                scores[dimension] = max(scores[dimension], score)
    
    return scores


def generate_instructive_text(title, description, dimension, score, tags):
    """Generate instructive text explaining WHY this image teaches this dimension well.
    
    IMPORTANT: Zone System references ONLY for lighting dimension, others get dimension-specific feedback.
    Returns 2-3 sentences, approximately 150-200 words max.
    """
    # Only generate instructive text for high-scoring dimensions (>=8.5)
    if score < 8.5:
        return None
    
    # Dimension-specific instructive templates based on image characteristics
    # These are actionable and specific to what makes THIS image instructive
    
    if dimension == "composition":
        if "leading_lines" in tags:
            return f"Study how {title.lower()} uses natural lines to guide your eye through multiple planes of depth, creating a visual journey rather than static viewing. The lines don't just lead to a single point - they create a path that moves you through foreground, middle ground, and background. This technique transforms the two-dimensional frame into an experience of exploration."
        elif "layered_depth" in tags or "layers" in tags:
            return f"Notice the foreground-middleground-background layering in {title.lower()} - this three-plane structure creates dimensional space that draws viewers into the scene. Each layer is clearly defined with distinct tonal values or scale changes, preventing visual confusion. This approach gives photographs the depth that makes them feel three-dimensional rather than flat."
        elif "rule_of_thirds" in tags:
            return f"Observe how key elements align with thirds divisions in {title.lower()}, creating balance without centering. This off-center placement makes the composition more engaging because it creates visual tension and movement. The rule of thirds is about creating dynamic equilibrium rather than static symmetry."
        else:
            return f"Study the spatial arrangement in {title.lower()} and how the positioning of elements creates both balance and visual flow. Notice how your eye naturally moves through the frame, guided by the placement of shapes, lines, and tonal masses. Strong composition controls the viewer's attention while maintaining visual harmony."
    
    elif dimension == "lighting":
        # Zone System references ONLY for lighting
        if "zone_system" in tags or "tonal_range" in tags:
            return f"Notice the full tonal range in {title.lower()} - from deep shadows (Zone II-III) to bright highlights (Zone VII-VIII). This complete range preserves texture and detail throughout while creating dimension and form. The Zone System technique ensures you capture information in both shadows and highlights rather than losing detail to blocked blacks or blown whites."
        elif "dramatic_lighting" in tags:
            return f"Study how the directional light in {title.lower()} reveals form through shadow and highlight, creating drama and three-dimensionality that flat lighting cannot achieve. Strong side or back lighting produces modeling - the gradual transition from light to shadow that gives subjects volume. This is what transforms flat surfaces into sculptural forms."
        elif "high_contrast" in tags:
            return f"Observe the strong tonal separation in {title.lower()} - high contrast creates visual impact and graphic strength. Notice how even in high contrast work, the shadow and highlight areas retain detail and texture rather than blocking up to pure black or blowing out to empty white. This control of contrast is what separates dramatic lighting from simply underexposed or overexposed images."
        else:
            return f"Notice how light quality and direction in {title.lower()} reveal texture and form in the subject. Study where highlights fall and where shadows anchor the composition - this interplay between light and dark creates both mood and visual structure. The way light wraps around forms tells us about their three-dimensional shape."
    
    elif dimension == "depth_perspective":
        if "layered_depth" in tags or "layers" in tags:
            return f"Study the clear foreground, middle ground, and background separation in {title.lower()} - this layering creates the sense of looking into three-dimensional space. Each plane is distinct through scale differences, tonal separation, or sharpness variation. This technique is essential for landscape photography as it prevents the 'flat wall' effect where everything appears at the same distance."
        elif "leading_lines" in tags:
            return f"Observe how converging lines in {title.lower()} create linear perspective that pulls your eye deep into the scene. These lines don't just point to something - they create the illusion of receding space by appearing to get closer together as they move away from the viewer. This transforms the flat photograph surface into dimensional space."
        elif "scale" in tags:
            return f"Notice how relative size of elements in {title.lower()} establishes depth - known objects like trees, buildings, or people help viewers understand distance and scale. When we see a tree in the foreground and mountains in the background, the size relationship immediately communicates spatial depth. This is one of the most powerful depth cues in two-dimensional images."
        else:
            return f"Study the atmospheric perspective in {title.lower()} - how distant elements become lighter, hazier, and less detailed than nearby objects. This natural phenomenon happens because more atmosphere exists between viewer and distant objects, scattering light and reducing contrast. Capturing this gradual change in tone and clarity creates convincing spatial recession."
    
    elif dimension == "visual_balance":
        if "symmetry" in tags:
            return f"Observe the symmetrical arrangement in {title.lower()} where one half mirrors the other, creating formal stability and visual calm. Perfect symmetry emphasizes the subject through repetition and creates a sense of order and monumentality. This approach works well when you want to convey permanence, stability, or timelessness."
        elif "negative_space" in tags:
            return f"Study how empty space balances occupied areas in {title.lower()} - this asymmetrical balance is more dynamic than centered symmetry. The negative space isn't just 'nothing' - it's an active element that gives the subject room to breathe and creates visual tension. This approach can make images feel more open and contemplative."
        else:
            return f"Notice how visual weight distributes across the frame in {title.lower()} - darker elements, larger shapes, and areas of detail have more weight than lighter, smaller, or simpler areas. The composition balances these elements to create equilibrium without rigid symmetry. This is what prevents images from feeling tilted or unstable."
    
    elif dimension == "emotional_impact":
        if "dramatic" in tags or "dramatic_lighting" in tags:
            return f"Study how technical choices in {title.lower()} serve emotional intent - the lighting, composition, and tonal drama combine to evoke feelings of awe and grandeur. Every technical decision from exposure to framing contributes to the emotional response. This is what elevates photography from mere documentation to expressive art."
        elif "mood" in tags or "atmospheric" in tags:
            return f"Notice the emotional quality in {title.lower()} created through soft gradations and atmospheric tones - this creates a contemplative mood that invites quiet observation. The technical restraint here is just as important as dramatic contrast in other images. Subtle tonality and gentle transitions can convey peace, mystery, or melancholy more effectively than high drama."
        else:
            return f"Observe how {title.lower()} makes you feel something beyond what you're seeing - this is where technical mastery serves expression. The craft of exposure, development, and printing enables the art rather than existing for itself. When all technical elements work together, they create an emotional experience that transcends the literal subject matter."
    
    elif dimension == "focus_sharpness":
        if "texture" in tags:
            return f"Study the edge acuity in {title.lower()} where critical sharpness reveals surface detail that gives tactile quality. You can almost feel the textures - rough bark, smooth stone, soft clouds - because the sharp focus renders every fine detail. This level of sharpness requires excellent lens quality, precise focus, and steady camera technique with adequate depth of field."
        else:
            return f"Notice the consistent sharpness throughout {title.lower()} from near to far - this typically requires deep depth of field (f/16-f/22 or smaller aperture). Everything from foreground to background maintains equal sharpness, keeping maximum clarity across the entire scene. This approach prioritizes complete information over selective focus and works well for landscapes and architectural subjects."
    
    elif dimension == "subject_isolation":
        if "negative_space" in tags:
            return f"Observe how empty space surrounds and emphasizes the subject in {title.lower()}, creating visual hierarchy through simplification. The isolation makes the subject impossible to miss because there's nothing competing for attention. This technique of 'less is more' often creates stronger images than busy, cluttered compositions."
        elif "minimalist" in tags:
            return f"Study the simplicity in {title.lower()} where removing competing elements makes the main subject dominant through subtraction rather than addition. Every element that doesn't support the subject has been eliminated from the frame. This discipline of reduction forces viewers to focus on what matters most."
        else:
            return f"Notice how the subject stands distinct and separate in {title.lower()} through techniques like tonal contrast, spatial separation, or selective focus. The subject isn't just present - it's clearly the star of the image. This isolation creates clear visual hierarchy and prevents viewer confusion about what they should be looking at."
    
    elif dimension == "color_harmony":
        # For B&W images, this is about tonal harmony
        if "high_contrast" in tags:
            return f"Study the tonal relationships in {title.lower()} where even high contrast work maintains harmony through smooth gradations between extreme values. The transitions from dark to light aren't harsh or jarring - they flow naturally even when the overall contrast is strong. This balance between impact and cohesion is what makes high-contrast images sophisticated rather than just dramatic."
        else:
            return f"Notice the tonal palette in {title.lower()} where the range of grays creates visual cohesion while maintaining enough separation for clarity. The tones relate to each other in a unified way - like musical notes in a chord. This harmony prevents visual discord and creates a sense of completeness in the image."
    
    # Default instructive text if no specific template matches
    return f"Study the technical execution in {title.lower()} which demonstrates mastery of {dimension.replace('_', ' ')} through deliberate choices. Each decision from exposure to framing serves the expressive intent of the image. This integration of craft and vision is what separates snapshots from considered photography."


def import_metadata():
    """Import metadata from YAML and populate database"""
    print("=" * 70)
    print("Importing Curated Ansel Adams Metadata")
    print("=" * 70)
    print(f"Metadata file: {METADATA_FILE}")
    print(f"Database: {DB_PATH}")
    print()
    
    # Check files exist
    if not METADATA_FILE.exists():
        print(f"[✗] Metadata file not found: {METADATA_FILE}")
        print("    Please create the metadata.yaml file first")
        return
    
    if not DB_PATH.exists():
        print(f"[✗] Database not found: {DB_PATH}")
        return
    
    # Load metadata
    print("[→] Loading metadata YAML...")
    with open(METADATA_FILE) as f:
        data = yaml.safe_load(f)
    
    images = data.get('images', [])
    print(f"[✓] Loaded {len(images)} image metadata entries")
    print()
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing ansel profiles
    print("[→] Clearing existing Ansel Adams profiles...")
    cursor.execute("DELETE FROM dimensional_profiles WHERE advisor_id = 'ansel'")
    print(f"[✓] Cleared {cursor.rowcount} existing profiles")
    print()
    
    # Import each image
    success_count = 0
    skip_count = 0
    
    for img in images:
        filename = img['filename']
        image_path = ANSEL_DIR / filename
        
        # Check if image file exists
        if not image_path.exists():
            print(f"[SKIP] {filename} - file not found")
            skip_count += 1
            continue
        
        # Calculate scores from tags
        tags = img.get('tags', [])
        scores = calculate_scores_from_tags(tags)
        
        # Generate instructive text for each high-scoring dimension
        title = img['title']
        description = img.get('description', '')
        instructive_texts = {}
        
        for dim_key in ['composition', 'lighting', 'focus_sharpness', 'color_harmony',
                        'subject_isolation', 'depth_perspective', 'visual_balance', 'emotional_impact']:
            score_key = f"{dim_key}_score"
            score = scores.get(score_key, 0)
            instructive_text = generate_instructive_text(title, description, dim_key, score, tags)
            instructive_texts[f"{dim_key}_instructive"] = instructive_text
        
        # Insert into database
        cursor.execute("""
            INSERT INTO dimensional_profiles 
            (advisor_id, image_path, image_title, date_taken, image_description,
             composition_score, lighting_score, focus_sharpness_score, 
             color_harmony_score, subject_isolation_score, depth_perspective_score,
             visual_balance_score, emotional_impact_score, overall_grade,
             composition_instructive, lighting_instructive, focus_sharpness_instructive,
             color_harmony_instructive, subject_isolation_instructive, depth_perspective_instructive,
             visual_balance_instructive, emotional_impact_instructive)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'ansel',
            str(image_path),
            img['title'],
            img.get('year', ''),
            img.get('description', ''),
            scores['composition_score'],
            scores['lighting_score'],
            scores['focus_sharpness_score'],
            scores['color_harmony_score'],
            scores['subject_isolation_score'],
            scores['depth_perspective_score'],
            scores['visual_balance_score'],
            scores['emotional_impact_score'],
            'A+',  # All Ansel images are A+ grade
            instructive_texts['composition_instructive'],
            instructive_texts['lighting_instructive'],
            instructive_texts['focus_sharpness_instructive'],
            instructive_texts['color_harmony_instructive'],
            instructive_texts['subject_isolation_instructive'],
            instructive_texts['depth_perspective_instructive'],
            instructive_texts['visual_balance_instructive'],
            instructive_texts['emotional_impact_instructive']
        ))
        
        print(f"[✓] {img['title']}")
        print(f"    Tags: {', '.join(tags[:3])}{'...' if len(tags) > 3 else ''}")
        print(f"    Scores: Comp={scores['composition_score']:.1f}, Light={scores['lighting_score']:.1f}, Depth={scores['depth_perspective_score']:.1f}")
        success_count += 1
    
    # Commit changes
    conn.commit()
    conn.close()
    
    # Summary
    print()
    print("=" * 70)
    print("Import Complete")
    print("=" * 70)
    print(f"Successfully imported: {success_count}")
    print(f"Skipped (not found): {skip_count}")
    print()
    print("Next steps:")
    print("  1. python scripts/compute_embeddings.py --advisor ansel")
    print("  2. python scripts/compute_embeddings.py --advisor ansel --verify-only")
    print()


if __name__ == "__main__":
    import_metadata()
