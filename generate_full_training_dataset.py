#!/usr/bin/env python3
"""
Generate a comprehensive 9-dimension training dataset from ALL available Ansel Adams images.

This script:
1. Scans all available images in training/datasets/ansel-images/
2. Creates training examples for each image with 9 dimensions
3. Uses Linux-compatible absolute paths
4. Generates varied, high-quality responses for diverse training

The 9 dimensions are:
- Composition
- Lighting  
- Focus & Sharpness
- Color Harmony
- Subject Isolation
- Depth & Perspective
- Visual Balance
- Emotional Impact
- Subject Matter (NEW - ruthless scoring for off-topic images)
"""

import json
import os
from pathlib import Path
import random

# Base directory
BASE_DIR = Path("/home/doo/dev/mondrian-macos")
IMAGES_DIR = BASE_DIR / "training" / "datasets" / "ansel-images"
OUTPUT_FILE = BASE_DIR / "training" / "datasets" / "ansel_image_training_full_9dim.jsonl"

# Image descriptions for more varied training responses
# Maps filename patterns to descriptions and characteristic scores
IMAGE_METADATA = {
    # Sand dunes images
    "sand_dunes": {
        "description": "sweeping sand dunes with dramatic shadows and curves",
        "strengths": ["composition", "lighting", "visual_balance"],
        "notes": "Classic Ansel Adams desert landscape showing mastery of tonal range"
    },
    "dunes": {
        "description": "desert dunes with rich texture and contrast",
        "strengths": ["composition", "depth_perspective"],
        "notes": "The interplay of light and shadow creates sculptural forms"
    },
    # Mountain images
    "williamson": {
        "description": "dramatic mountain landscape with storm clouds",
        "strengths": ["emotional_impact", "lighting", "composition"],
        "notes": "Mount Williamson captures the raw power of the Sierra Nevada"
    },
    "tetons": {
        "description": "the iconic Tetons with Snake River in foreground",
        "strengths": ["composition", "depth_perspective", "visual_balance"],
        "notes": "Perfect example of using foreground to lead the eye"
    },
    "sierra": {
        "description": "Sierra Nevada mountain range in dramatic light",
        "strengths": ["lighting", "emotional_impact", "composition"],
        "notes": "The mountain majesty that defined Adams' career"
    },
    "half_dome": {
        "description": "Yosemite's Half Dome in striking monochrome",
        "strengths": ["subject_isolation", "composition", "emotional_impact"],
        "notes": "The quintessential Yosemite landmark captured with reverence"
    },
    "moonrise": {
        "description": "moonrise over landscape with dramatic sky",
        "strengths": ["lighting", "emotional_impact", "visual_balance"],
        "notes": "Timing and zone system mastery create timeless image"
    },
    # Water/coastal images  
    "lake": {
        "description": "serene lake reflecting surrounding landscape",
        "strengths": ["visual_balance", "composition", "focus_sharpness"],
        "notes": "The mirror-like water creates perfect symmetry"
    },
    "tidal": {
        "description": "coastal beach scene with tidal patterns",
        "strengths": ["composition", "lighting", "depth_perspective"],
        "notes": "The rhythmic patterns of tide and sand"
    },
    "geyser": {
        "description": "Old Faithful geyser erupting",
        "strengths": ["subject_isolation", "composition", "emotional_impact"],
        "notes": "Capturing the power of nature in motion"
    },
    # Forest/vegetation
    "redwoods": {
        "description": "towering coast redwoods reaching skyward",
        "strengths": ["depth_perspective", "composition", "emotional_impact"],
        "notes": "The vertical majesty of ancient trees"
    },
    "aspens": {
        "description": "aspen grove with their characteristic bark",
        "strengths": ["composition", "focus_sharpness", "visual_balance"],
        "notes": "The graphic quality of aspen trunks"
    },
    "tree": {
        "description": "solitary tree against landscape",
        "strengths": ["subject_isolation", "emotional_impact", "composition"],
        "notes": "Isolation emphasizes the tree's character"
    },
    # Rock formations
    "canyon": {
        "description": "Grand Canyon with layered rock strata",
        "strengths": ["depth_perspective", "composition", "lighting"],
        "notes": "Geological time made visible through careful composition"
    },
    "rock": {
        "description": "rock formations with dramatic textures",
        "strengths": ["focus_sharpness", "composition", "lighting"],
        "notes": "The tactile quality of stone rendered in silver"
    },
    "cliffs": {
        "description": "dramatic cliff face with lake below",
        "strengths": ["composition", "depth_perspective", "visual_balance"],
        "notes": "The frozen lake creates a powerful foreground"
    },
    "ruin": {
        "description": "White House Ruin in Canyon de Chelly",
        "strengths": ["composition", "depth_perspective", "emotional_impact"],
        "notes": "Ancient architecture nestled in natural setting"
    },
    # Weather/atmospheric
    "storm": {
        "description": "clearing winter storm over Yosemite Valley",
        "strengths": ["lighting", "emotional_impact", "composition"],
        "notes": "The drama of weather in landscape photography"
    },
    "fog": {
        "description": "Golden Gate Bridge shrouded in fog",
        "strengths": ["composition", "emotional_impact", "visual_balance"],
        "notes": "Atmospheric conditions create mystery and mood"
    },
    "clouds": {
        "description": "dramatic cloud formations over landscape",
        "strengths": ["composition", "lighting", "emotional_impact"],
        "notes": "Sky as dramatic backdrop for earth below"
    },
    "misty": {
        "description": "misty mountain scene with soft tones",
        "strengths": ["emotional_impact", "depth_perspective", "lighting"],
        "notes": "Atmospheric perspective creates depth and mystery"
    },
    # Other subjects
    "railroad": {
        "description": "railroad track leading into mountain landscape",
        "strengths": ["composition", "depth_perspective", "visual_balance"],
        "notes": "Leading lines draw the viewer deep into the scene"
    },
    "train": {
        "description": "train scene with mountain backdrop",
        "strengths": ["composition", "depth_perspective"],
        "notes": "Human element dwarfed by natural grandeur"
    },
    "courtyard": {
        "description": "architectural courtyard study",
        "strengths": ["composition", "lighting", "focus_sharpness"],
        "notes": "Architectural photography with careful geometric composition"
    },
    "western_town": {
        "description": "ghost town or western settlement",
        "strengths": ["composition", "emotional_impact", "lighting"],
        "notes": "The passage of time captured in abandoned structures"
    },
    "waterfall": {
        "description": "cascading waterfall with surrounding forest",
        "strengths": ["composition", "focus_sharpness", "depth_perspective"],
        "notes": "The eternal motion of water frozen in time"
    },
    "windmill": {
        "description": "windmill silhouette against dramatic sky",
        "strengths": ["composition", "subject_isolation", "lighting"],
        "notes": "Iconic American West imagery"
    },
    "white_sands": {
        "description": "White Sands New Mexico dunes",
        "strengths": ["composition", "lighting", "visual_balance"],
        "notes": "The pristine white gypsum dunes create abstract beauty"
    },
    "cathedral": {
        "description": "cathedral rock formations",
        "strengths": ["composition", "lighting", "depth_perspective"],
        "notes": "Nature's cathedral in stone"
    },
    # Default for unmatched
    "default": {
        "description": "classic Ansel Adams landscape photograph",
        "strengths": ["composition", "lighting", "emotional_impact"],
        "notes": "Masterful use of the zone system and careful composition"
    },
    # NEGATIVE EXAMPLES - casual snapshots that should receive low scores
    "neg": {
        "description": "casual snapshot lacking artistic intent",
        "weaknesses": ["composition", "lighting", "focus_sharpness", "subject_isolation", "visual_balance", "emotional_impact", "subject_matter"],
        "is_negative": True,
        "notes": "This casual photo lacks the intentionality required for landscape fine art photography"
    }
}

# Negative example patterns - these get low scores
NEGATIVE_PATTERNS = ["neg", "snapshot", "casual", "iphone", "selfie"]

def get_image_metadata(filename: str) -> dict:
    """Get metadata based on filename patterns."""
    filename_lower = filename.lower()
    
    # Check for negative examples first
    for pattern in NEGATIVE_PATTERNS:
        if filename_lower.startswith(pattern) or f"_{pattern}" in filename_lower:
            return IMAGE_METADATA["neg"]
    
    for pattern, metadata in IMAGE_METADATA.items():
        if pattern in filename_lower and pattern != "neg":  # Skip neg pattern in regular matching
            return metadata
    return IMAGE_METADATA["default"]

def generate_score(dimension: str, is_strength: bool, is_negative: bool = False, base_score: int = 9) -> int:
    """Generate a realistic score with some variation."""
    if is_negative:
        # Negative examples get low scores - this is critical for training realistic output
        if dimension == "subject_matter":
            return random.choice([1, 1, 2, 2, 3])  # Ruthless - 1-3 for wrong subject matter
        else:
            return random.choice([3, 4, 4, 5, 5, 6])  # Poor to mediocre for other dimensions
    elif is_strength:
        return random.choice([9, 9, 10, 10, 10])  # Biased toward 9-10 for strengths
    else:
        return random.choice([7, 8, 8, 9, 9])  # Still good but room for improvement

def generate_comment(dimension: str, is_strength: bool, description: str, notes: str, is_negative: bool = False) -> str:
    """Generate a varied comment for a dimension."""
    
    # Negative example comments - harsh but constructive
    negative_templates = {
        "composition": [
            "The composition appears unplanned and lacks visual structure",
            "No clear compositional framework guides the viewer's eye",
            "The framing feels arbitrary without intentional arrangement"
        ],
        "lighting": [
            "The lighting is flat and uninteresting - no drama or dimension",
            "Harsh midday light creates unflattering shadows and blown highlights",
            "The exposure lacks the tonal richness expected in fine art photography"
        ],
        "focus_sharpness": [
            "Soft focus throughout suggests camera shake or missed focus",
            "Critical areas lack sharpness - technical execution needs improvement",
            "The image suffers from inadequate depth of field control"
        ],
        "color_harmony": [
            "The tonal palette lacks cohesion and visual harmony",
            "No evidence of intentional tonal control or zone system application",
            "The grayscale values feel muddy and undifferentiated"
        ],
        "subject_isolation": [
            "No clear subject emerges from the cluttered composition",
            "The intended subject competes with distracting background elements",
            "Lack of visual hierarchy makes it unclear what to focus on"
        ],
        "depth_perspective": [
            "The image feels flat with no sense of three-dimensional space",
            "Missing foreground and layered planes that create depth",
            "No use of perspective techniques to draw the viewer in"
        ],
        "visual_balance": [
            "The composition feels weighted and unbalanced",
            "Elements are distributed without consideration of visual weight",
            "The frame lacks the equilibrium of thoughtful arrangement"
        ],
        "emotional_impact": [
            "The image fails to evoke any emotional response",
            "No connection between subject and viewer is established",
            "The photograph documents but doesn't inspire or move"
        ],
        "subject_matter": [
            "CRITICAL: This subject matter falls completely outside the landscape/wilderness domain - casual snapshots are not appropriate for this advisor",
            "NO ALIGNMENT: This appears to be a casual phone photo with no artistic intent - subject matter scores 1-3 for complete misalignment",
            "WRONG DOMAIN: This advisor specializes in wilderness landscape photography. Casual snapshots, portraits, and everyday subjects receive minimum scores"
        ]
    }
    
    strength_templates = {
        "composition": [
            f"Masterful arrangement of elements - {notes}",
            f"The composition demonstrates exceptional visual organization",
            f"Classic compositional framework executed with precision"
        ],
        "lighting": [
            f"Exquisite use of natural light - {notes}",
            f"The tonal range showcases zone system mastery",
            f"Light and shadow interplay creates dimensional depth"
        ],
        "focus_sharpness": [
            "Exceptional clarity throughout the frame with careful depth of field control",
            "Technical precision evident in the sharpness from foreground to background",
            "The crisp detail rewards prolonged viewing"
        ],
        "color_harmony": [
            "The monochromatic palette achieves remarkable tonal richness",
            "Classic black and white treatment with full tonal scale",
            "The grayscale harmonies demonstrate mastery of photographic chemistry"
        ],
        "subject_isolation": [
            f"The primary subject commands attention through careful placement",
            f"Strong visual hierarchy guides the viewer's eye",
            f"The main subject is clearly distinguished from supporting elements"
        ],
        "depth_perspective": [
            f"Remarkable sense of three-dimensional space - {notes}",
            "The layered planes create compelling depth",
            "Excellent use of atmospheric and linear perspective"
        ],
        "visual_balance": [
            "Harmonious distribution of visual weight throughout the frame",
            "The composition achieves equilibrium through careful element placement",
            "Balanced yet dynamic arrangement of forms"
        ],
        "emotional_impact": [
            f"Profound emotional resonance - {notes}",
            "The image evokes a powerful sense of place and moment",
            "Deeply moving connection between subject and viewer"
        ],
        "subject_matter": [
            "Perfect alignment with Ansel Adams' artistic domain - wilderness landscape photography at its finest",
            "This wilderness/nature photograph exemplifies the landscape mastery that defined Adams' life work",
            "Quintessential subject matter for this advisor - pristine landscape photography"
        ]
    }
    
    moderate_templates = {
        "composition": [
            "Solid compositional framework with room for more dynamic arrangements",
            "Well-organized composition, though some elements could be refined",
            "Competent arrangement - consider stronger leading lines"
        ],
        "lighting": [
            "Good use of available light with potential for more dramatic effect",
            "Adequate lighting that could benefit from stronger directional quality",
            "The light is workable but lacks the drama of ideal conditions"
        ],
        "focus_sharpness": [
            "Generally sharp with minor softness in some areas",
            "Good technical execution - a smaller aperture might extend depth of field",
            "Acceptable sharpness throughout the key areas"
        ],
        "color_harmony": [
            "The tonal palette is cohesive but could have more dynamic range",
            "Reasonable tonal distribution with room for refinement",
            "The grayscale values work together adequately"
        ],
        "subject_isolation": [
            "The subject is identifiable but could be more prominently featured",
            "Subject separation could be stronger for clearer visual hierarchy",
            "Consider techniques to further isolate the primary subject"
        ],
        "depth_perspective": [
            "Adequate sense of depth - additional foreground interest would help",
            "The perspective could be enhanced with different vantage point",
            "Some sense of depth present but not fully exploited"
        ],
        "visual_balance": [
            "Reasonably balanced composition with minor weight distribution issues",
            "The balance works but feels slightly asymmetrical",
            "Consider adjusting element placement for stronger equilibrium"
        ],
        "emotional_impact": [
            "Evokes a response but hasn't reached its full emotional potential",
            "Pleasant but could deliver a more powerful emotional punch",
            "The connection could be deeper with more decisive timing"
        ],
        "subject_matter": [
            "Perfect alignment with wilderness/nature landscape domain",
            "Excellent subject matter choice for this advisor",
            "This landscape subject is ideally suited to Adams' expertise"
        ]
    }
    
    if is_negative:
        templates = negative_templates
    elif is_strength:
        templates = strength_templates
    else:
        templates = moderate_templates
    return random.choice(templates.get(dimension, ["Demonstrates competent handling of this dimension"]))

def generate_recommendation(dimension: str, is_strength: bool, is_negative: bool = False) -> str:
    """Generate a recommendation for improvement."""
    
    # Negative example recommendations - direct guidance
    if is_negative:
        negative_recommendations = {
            "composition": [
                "FUNDAMENTAL: Before shooting, identify your subject and consciously arrange the frame",
                "Study basic compositional rules - rule of thirds, leading lines, framing",
                "Stop and think before pressing the shutter - what story are you telling?"
            ],
            "lighting": [
                "ESSENTIAL: Avoid harsh midday light. Shoot during golden hour or in open shade",
                "Learn to see light direction and quality before committing to a shot",
                "Consider how shadows and highlights will render in your final image"
            ],
            "focus_sharpness": [
                "BASIC: Use a tripod for landscape work and carefully focus on your subject",
                "Check sharpness before leaving the location - zoom in on your LCD",
                "Understand your camera's autofocus system and when to use manual focus"
            ],
            "color_harmony": [
                "Study the zone system to understand tonal relationships",
                "Pre-visualize your final image before capturing",
                "Consider how different tones will interact in the final print"
            ],
            "subject_isolation": [
                "CRITICAL: Every photograph needs a clear subject - what is this image about?",
                "Simplify, simplify, simplify - remove distracting elements",
                "Use selective focus or positioning to separate subject from background"
            ],
            "depth_perspective": [
                "Include foreground, middle ground, and background elements",
                "Choose camera position carefully to create depth through overlapping forms",
                "Wide-angle lenses at low angles can dramatically enhance depth"
            ],
            "visual_balance": [
                "Consider the visual weight of elements when composing",
                "Move around your subject to find the most balanced composition",
                "Use the viewfinder edges to evaluate element placement"
            ],
            "emotional_impact": [
                "ASK YOURSELF: Why are you making this photograph? What moved you?",
                "Connect emotionally with your subject before pressing the shutter",
                "If it doesn't move you when you're there, it won't move viewers later"
            ],
            "subject_matter": [
                "WRONG ADVISOR: This photograph does not align with Ansel Adams' wilderness/landscape domain. Consider seeking feedback from an advisor whose expertise matches your subject matter",
                "This advisor specializes in landscape and nature photography. Casual snapshots, portraits, events, and everyday subjects fall outside this expertise area",
                "To benefit from this advisor's feedback, focus on wilderness landscapes, mountains, forests, deserts, and natural formations"
            ]
        }
        return random.choice(negative_recommendations.get(dimension, ["Seek fundamental training in this aspect of photography"]))
    
    if is_strength:
        recommendations = [
            "Continue developing this strength - it's a hallmark of your emerging style",
            "This represents a signature element of your photographic vision",
            "Build on this foundation to create a distinctive portfolio",
            "Let this strength inform your approach to other dimensions"
        ]
    else:
        recommendations = {
            "composition": [
                "Experiment with rule of thirds and golden ratio placements",
                "Study Adams' use of leading lines and frame-within-frame techniques",
                "Consider how foreground elements can strengthen overall composition"
            ],
            "lighting": [
                "Wait for optimal light conditions - the golden and blue hours reward patience",
                "Study the zone system to maximize tonal range in your captures",
                "Scout locations at different times to understand how light transforms them"
            ],
            "focus_sharpness": [
                "Use a tripod and optimal aperture (f/8-f/11) for maximum sharpness",
                "Practice hyperfocal distance focusing for landscape work",
                "Consider focus stacking for scenes requiring extensive depth of field"
            ],
            "color_harmony": [
                "Study how different tonal values interact across the frame",
                "Practice pre-visualization - see the scene in black and white before shooting",
                "Use filters to control and separate tonal values"
            ],
            "subject_isolation": [
                "Look for natural frames and leading lines to emphasize your subject",
                "Use depth of field selectively to separate subject from background",
                "Consider timing and positioning to reduce competing elements"
            ],
            "depth_perspective": [
                "Include compelling foreground elements to create depth",
                "Experiment with different focal lengths to control perspective",
                "Use atmospheric conditions to enhance sense of distance"
            ],
            "visual_balance": [
                "Practice the counterweight principle - balance large masses with smaller points of interest",
                "Study Japanese aesthetics of asymmetrical balance",
                "Consider how empty space functions as a compositional element"
            ],
            "emotional_impact": [
                "Wait for the decisive moment when all elements align",
                "Connect personally with your subject before photographing",
                "Let the land speak to you - photograph what moves you emotionally"
            ],
            "subject_matter": [
                "Continue pursuing landscapes, wilderness, and natural subjects",
                "Portraits, snapshots, urban scenes, or event photography fall outside this advisor's expertise and would receive severe scores (1-3)"
            ]
        }
        return random.choice(recommendations.get(dimension, ["Continue developing this aspect of your craft"]))
    
    return random.choice(recommendations)

def create_training_example(image_path: Path) -> dict:
    """Create a single training example from an image."""
    
    metadata = get_image_metadata(image_path.name)
    strengths = metadata.get("strengths", [])
    weaknesses = metadata.get("weaknesses", [])
    is_negative = metadata.get("is_negative", False)
    description = metadata.get("description", "landscape photograph")
    notes = metadata.get("notes", "Classic Ansel Adams style")
    
    # Generate the 9 dimensions
    dimensions = []
    dimension_names = [
        "Composition",
        "Lighting", 
        "Focus & Sharpness",
        "Color Harmony",
        "Subject Isolation",
        "Depth & Perspective",
        "Visual Balance",
        "Emotional Impact",
        "Subject Matter"
    ]
    
    dimension_keys = [
        "composition",
        "lighting",
        "focus_sharpness", 
        "color_harmony",
        "subject_isolation",
        "depth_perspective",
        "visual_balance",
        "emotional_impact",
        "subject_matter"
    ]
    
    total_score = 0
    for name, key in zip(dimension_names, dimension_keys):
        if is_negative:
            # Negative examples get low scores across the board
            is_strength = False
            score = generate_score(key, is_strength, is_negative=True)
        else:
            is_strength = key in strengths or key == "subject_matter"  # subject_matter always strong for reference images
            score = generate_score(key, is_strength) if key != "subject_matter" else 10  # Always 10 for subject matter on ref images
        total_score += score
        
        dimensions.append({
            "name": name,
            "score": score,
            "comment": generate_comment(key, is_strength, description, notes, is_negative=is_negative),
            "recommendation": generate_recommendation(key, is_strength, is_negative=is_negative)
        })
    
    # Calculate overall score
    overall = round(total_score / 9, 1)
    
    # For negative examples with low subject matter scores, cap overall at 4.0
    if is_negative:
        overall = min(overall, 4.0)
    
    # Generate summary based on whether it's a negative example
    if is_negative:
        summaries = [
            f"This {description} falls short of fine art photography standards. {notes}. To improve, focus on intentional composition, optimal lighting, and subject matter that aligns with wilderness/landscape photography.",
            f"FEEDBACK: This image lacks the technical and artistic qualities expected for landscape photography critique. {notes}. Consider what story you want to tell before pressing the shutter.",
            f"This {description} needs fundamental improvements in most dimensions. More importantly, the subject matter does not align with this advisor's wilderness/landscape expertise.",
            f"The photograph shows {description} - this falls outside the landscape/nature domain. Without proper subject alignment, meaningful critique within this advisor's expertise is limited."
        ]
    else:
        summaries = [
            f"This {description} demonstrates Ansel Adams' masterful approach to landscape photography. {notes}",
            f"A compelling {description} that showcases the technical precision and emotional depth characteristic of Adams' work.",
            f"This image of {description} exemplifies the wilderness photography that made Ansel Adams a legend.",
            f"Powerful {description} capturing the essence of the American landscape through Adams' distinctive vision."
        ]
    
    response = {
        "dimensions": dimensions,
        "overall_score": overall,
        "summary": random.choice(summaries),
        "advisor_context": "Ansel Adams - Master of American landscape photography, pioneer of the zone system, and conservationist who captured the grandeur of the American West."
    }
    
    # Create the training example in chat format
    user_prompt = f"""<image>

Please analyze this photograph and provide detailed feedback across all 9 dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact, subject_matter).

Return your analysis as a JSON object with:
- "dimensions": array of dimension analyses
- "overall_score": float from 1-10
- "summary": overall assessment string
- "advisor_context": context about the advisor"""

    example = {
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            },
            {
                "role": "assistant", 
                "content": json.dumps(response, indent=2)
            }
        ],
        "image_path": str(image_path)
    }
    
    return example

def collect_all_images() -> list[Path]:
    """Collect all available training images."""
    images = []
    
    # Main images directory only (exclude downloaded folder - those files are invalid)
    for ext in ["*.jpg", "*.jpeg", "*.png"]:
        images.extend(IMAGES_DIR.glob(ext))
    
    # Exclude headshot and obvious non-landscape images
    # Also exclude empty files (failed downloads)
    images = [img for img in images 
              if "headshot" not in img.name.lower() 
              and img.stat().st_size > 0]  # Filter out empty files
    
    return sorted(images)

def main():
    """Generate the full training dataset."""
    
    print("=" * 60)
    print("Generating Full 9-Dimension Training Dataset")
    print("=" * 60)
    
    # Collect all images
    images = collect_all_images()
    print(f"\nFound {len(images)} training images:")
    for img in images:
        rel_path = img.relative_to(BASE_DIR)
        print(f"  - {rel_path}")
    
    # Generate training examples
    examples = []
    for image_path in images:
        example = create_training_example(image_path)
        examples.append(example)
    
    # Write to JSONL
    with open(OUTPUT_FILE, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"\n✓ Generated {len(examples)} training examples")
    print(f"✓ Output: {OUTPUT_FILE}")
    
    # Verify all images exist
    missing = 0
    for example in examples:
        if not Path(example['image_path']).exists():
            print(f"  WARNING: Missing {example['image_path']}")
            missing += 1
    
    if missing == 0:
        print(f"✓ All {len(examples)} images verified as existing")
    else:
        print(f"⚠ {missing} images missing")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
