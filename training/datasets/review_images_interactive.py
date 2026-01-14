#!/usr/bin/env python3
"""
Interactive Image Review Tool with Independent Dimension Scoring

This tool allows nuanced evaluation where each dimension is scored independently.
A photo might have excellent composition (9/10) but poor focus (3/10).

Usage:
    python review_images_interactive.py
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


# Ansel's 8 evaluation dimensions
DIMENSIONS = [
    ("composition", "Arrangement of elements, visual hierarchy, rule of thirds"),
    ("lighting", "Quality of light, tonal range, Zone System application"),
    ("focus_sharpness", "Technical sharpness, depth of field, hyperfocal distance"),
    ("color_harmony", "Tonal relationships, grayscale values, tonal separation"),
    ("subject_isolation", "Subject clarity, separation from background"),
    ("depth_perspective", "Sense of space, near/far relationships, dimensionality"),
    ("visual_balance", "Distribution of visual weight, compositional balance"),
    ("emotional_impact", "Emotional resonance, connection, meaning beyond documentation")
]


# Ansel-style comments for different score ranges
COMMENT_TEMPLATES = {
    "composition": {
        (9, 10): [
            "Masterful arrangement—every element serves the whole with precision and purpose.",
            "The eye travels exactly as intended. Visual hierarchy established with authority.",
            "Compositional elements orchestrated like a symphony—each note contributing to the whole."
        ],
        (7, 8): [
            "Solid compositional structure with clear intent and good visual organization.",
            "The arrangement demonstrates understanding of visual weight and balance.",
            "Elements work together adequately, though refinement would strengthen the statement."
        ],
        (5, 6): [
            "Compositional awareness is present but execution lacks confidence or clarity.",
            "The arrangement is functional but uninspired—it documents rather than composes.",
            "Elements coexist without truly working together toward unified purpose."
        ],
        (3, 4): [
            "Compositional weaknesses distract from the subject. Visual hierarchy unclear.",
            "The arrangement lacks intentionality—elements compete rather than cooperate.",
            "Composition appears accidental rather than visualized and controlled."
        ],
        (0, 2): [
            "Compositional chaos. No clear subject, no hierarchy, no visual journey for the eye.",
            "The arrangement actively works against the image—cluttered, confused, purposeless."
        ]
    },
    "lighting": {
        (9, 10): [
            "Light sculpts form magnificently. The Zone System's power fully realized here.",
            "Illumination reveals texture, form, and dimension with technical mastery and artistic vision.",
            "Each tonal value precisely placed—shadows retain detail while highlights sing with brilliance."
        ],
        (7, 8): [
            "Light is well-handled, revealing form and creating adequate tonal separation.",
            "Good understanding of light's role in defining dimension and texture.",
            "The lighting works effectively, though not extraordinarily—competent and clear."
        ],
        (5, 6): [
            "Lighting is adequate but fails to sculpt or reveal. Functional but uninspired.",
            "Light exists without contributing meaningfully to form, texture, or mood.",
            "Acceptable illumination that neither enhances nor destroys the image."
        ],
        (3, 4): [
            "Flat lighting collapses dimensionality. Tonal range compressed into muddy midtones.",
            "Light merely illuminates—it does not reveal, sculpt, or define.",
            "Poor lighting obscures rather than clarifies—form and texture disappear."
        ],
        (0, 2): [
            "Catastrophic lighting. The subject exists in tonal poverty—no separation, no life.",
            "Light destroys what it should reveal. Harsh or flat beyond redemption."
        ]
    },
    "focus_sharpness": {
        (9, 10): [
            "Hyperfocal distance mastery—sharpness from foreground to infinity where needed.",
            "Technical precision absolute. Sharpness serves vision perfectly.",
            "Critical focus placement demonstrates understanding of both technique and intention."
        ],
        (7, 8): [
            "Good technical sharpness. Focus placement shows understanding of depth of field.",
            "Adequately sharp where it matters. Minor softness does not detract significantly.",
            "Solid technical execution—sharpness serves the image competently."
        ],
        (5, 6): [
            "Acceptable sharpness but lacks the precision fine photography demands.",
            "Focus is present but not optimized. Some detail loss in critical areas.",
            "Technically adequate though not exemplary—room for improvement in focus control."
        ],
        (3, 4): [
            "Soft focus undermines the image's authority. Technical precision lacking.",
            "Unacceptable blur or focus errors destroy detail where clarity is essential.",
            "Focus problems distract significantly. The image lacks the sharpness credibility requires."
        ],
        (0, 2): [
            "Catastrophic focus failure. The image is unacceptably soft throughout.",
            "So soft as to appear intentionally sabotaged. Technical incompetence evident."
        ]
    },
    "color_harmony": {
        (9, 10): [
            "Tonal values orchestrated brilliantly—each zone precisely placed for maximum effect.",
            "Grayscale relationships sing. The full tonal range from Zone 0 to Zone X present and purposeful.",
            "Tonal separation masterful. Values work together creating visual music."
        ],
        (7, 8): [
            "Good tonal management. Values generally well-separated and purposeful.",
            "Adequate tonal range with reasonable separation between key zones.",
            "Tonal relationships work effectively though not extraordinarily."
        ],
        (5, 6): [
            "Tonal palette adequate but uninspired. Limited range or poor separation.",
            "Values exist without particularly harmonious relationships.",
            "Acceptable tonal management that neither impresses nor offends."
        ],
        (3, 4): [
            "Tonal values compete and clash. Poor separation or extreme compression.",
            "Limited tonal range creates muddy, lifeless appearance.",
            "The Zone System would reveal the chaos here—values poorly managed."
        ],
        (0, 2): [
            "Tonal catastrophe. Values merge into undifferentiated gray or blown-out white.",
            "Complete absence of tonal discipline. The grayscale collapses entirely."
        ]
    },
    "subject_isolation": {
        (9, 10): [
            "The subject emerges with commanding authority. Context enriches without distracting.",
            "Perfect separation—the viewer's eye goes exactly where intended without confusion.",
            "Subject dominates with clarity while maintaining environmental context beautifully."
        ],
        (7, 8): [
            "Subject is clear and well-separated. Minor distractions do not significantly detract.",
            "Good isolation—the subject emerges adequately from its environment.",
            "Subject clarity is solid, though refinement could strengthen the statement."
        ],
        (5, 6): [
            "Subject is identifiable but does not dominate. Adequate but not strong isolation.",
            "The subject exists but competes with surroundings for attention.",
            "Acceptable subject presence without commanding authority."
        ],
        (3, 4): [
            "Subject struggles to emerge from visual clutter. What is this about?",
            "Poor isolation—the subject drowns in competing elements and distractions.",
            "Unclear subject identity. The eye searches but finds no clear focal point."
        ],
        (0, 2): [
            "No discernible subject. Visual chaos prevents any clear reading.",
            "The photograph has no clear point—everything and therefore nothing."
        ]
    },
    "depth_perspective": {
        (9, 10): [
            "Magnificent dimensional illusion—the viewer stands within the frame.",
            "Perfect spatial relationships from immediate foreground through to infinity.",
            "Depth rendered so convincingly one could walk into the photograph."
        ],
        (7, 8): [
            "Good sense of depth. Spatial relationships clearly established.",
            "Adequate dimensionality. The viewer perceives near and far effectively.",
            "Depth is present and functional, establishing clear spatial planes."
        ],
        (5, 6): [
            "Some sense of depth but not strongly conveyed. Spatial relationships weak.",
            "Dimensionality is suggested but not powerfully rendered.",
            "Acceptable spatial sense without strong three-dimensional illusion."
        ],
        (3, 4): [
            "Depth collapses. Poor spatial relationships flatten the image.",
            "Little sense of dimensionality—the image reads as flat and two-dimensional.",
            "Spatial confusion. No clear sense of near, middle, and far distances."
        ],
        (0, 2): [
            "Complete spatial collapse. The image is aggressively flat.",
            "No dimensional illusion whatsoever—pure two-dimensional rendering."
        ]
    },
    "visual_balance": {
        (9, 10): [
            "Visual weight distributed with the sensitivity of a master composer.",
            "Perfect equilibrium—tension and release orchestrated brilliantly.",
            "Balance achieved not through symmetry but through understanding of visual weight."
        ],
        (7, 8): [
            "Good visual balance. Elements arranged with consideration for weight and placement.",
            "Adequate equilibrium—no jarring imbalances distract from the image.",
            "Balance is solid, creating comfortable visual experience."
        ],
        (5, 6): [
            "Acceptable balance though not particularly refined or considered.",
            "Visual weight somewhat distributed but without strong intentionality.",
            "Balance is functional without being particularly artful or refined."
        ],
        (3, 4): [
            "Imbalance creates discomfort. Visual weight poorly distributed.",
            "Elements war for dominance. No sense of compositional equilibrium.",
            "Unbalanced arrangement that distracts and unsettles the viewer."
        ],
        (0, 2): [
            "Catastrophic imbalance. The image tilts visually toward chaos.",
            "Complete absence of compositional balance or weight consideration."
        ]
    },
    "emotional_impact": {
        (9, 10): [
            "One stands before such an image and feels the presence of something greater.",
            "Profound emotional resonance. The photograph speaks to the soul, not just the eye.",
            "This transcends documentation—it reveals truth and evokes genuine feeling."
        ],
        (7, 8): [
            "Good emotional content. The image communicates beyond mere documentation.",
            "The photograph speaks to the viewer, creating connection and meaning.",
            "Emotional resonance is present and genuine, engaging the viewer effectively."
        ],
        (5, 6): [
            "Some emotional content but not deeply moving or particularly memorable.",
            "The image is competent but fails to evoke strong feeling or response.",
            "Acceptable but not extraordinary—the photograph exists without deeply connecting."
        ],
        (3, 4): [
            "Little emotional impact. The image documents but does not move.",
            "Technically present but emotionally absent. No resonance or connection.",
            "The photograph leaves the viewer unmoved—execution without vision or feeling."
        ],
        (0, 2): [
            "Emotionally void. The image says absolutely nothing to the viewer.",
            "Complete absence of feeling, meaning, or emotional communication."
        ]
    }
}


def get_comment_for_score(dimension: str, score: int) -> str:
    """Get an appropriate Ansel-style comment for a dimension and score."""
    templates = COMMENT_TEMPLATES.get(dimension, {})

    for (low, high), comments in templates.items():
        if low <= score <= high:
            # Rotate through comments for variety
            import random
            return random.choice(comments)

    # Fallback
    return f"Score of {score} in {dimension} dimension."


def open_image(image_path: str):
    """Open image in system viewer."""
    try:
        subprocess.run(['open', image_path], check=True)
    except Exception as e:
        print(f"  ⚠ Could not open image automatically: {e}")
        print(f"  Please open manually: open {image_path}")


def score_dimension(dim_name: str, dim_description: str) -> Tuple[int, str]:
    """Prompt user to score a single dimension."""
    print(f"\n  {dim_name.upper()}")
    print(f"  {dim_description}")

    while True:
        try:
            score_input = input(f"  Score (0-10, or 'a' for auto-comment): ").strip().lower()

            if score_input == 'a':
                # Auto mode - use score-based comment
                while True:
                    try:
                        score = int(input(f"  Score (0-10): "))
                        if 0 <= score <= 10:
                            comment = get_comment_for_score(dim_name, score)
                            return score, comment
                    except ValueError:
                        print("    Invalid. Enter 0-10")
            else:
                score = int(score_input)
                if 0 <= score <= 10:
                    # Get custom comment or auto-generate
                    comment = input(f"  Comment (or Enter for auto): ").strip()
                    if not comment:
                        comment = get_comment_for_score(dim_name, score)
                    return score, comment
                else:
                    print("    Score must be 0-10")
        except ValueError:
            print("    Invalid input. Enter a number 0-10 or 'a'")


def review_image_interactive(image_path: Path) -> Dict:
    """Interactive review of a single image with independent dimension scoring."""
    print(f"\n{'='*80}")
    print(f"Image: {image_path.name}")
    print(f"{'='*80}\n")

    # Open image
    print("Opening image...")
    open_image(str(image_path))

    # Get label
    while True:
        label = input("\nLabel [p=positive (8-10), n=negative (0-6), s=skip]: ").lower()
        if label in ['p', 'n', 's']:
            break
        print("Invalid. Use 'p', 'n', or 's'")

    if label == 's':
        return None

    is_positive = (label == 'p')

    # Choose scoring mode
    print("\nScoring modes:")
    print("  1. Quick - Auto-assign scores based on overall grade")
    print("  2. Dimension by dimension - Score each independently")
    print("  3. Mixed - Set 2-3 key dimensions, auto-fill rest")

    while True:
        mode = input("Mode (1/2/3): ").strip()
        if mode in ['1', '2', '3']:
            break

    scores = {}
    comments = {}

    if mode == '1':
        # Quick mode
        while True:
            try:
                overall = int(input("Overall grade (0-10): "))
                if 0 <= overall <= 10:
                    break
            except ValueError:
                pass
            print("Invalid. Enter 0-10")

        # Apply overall score to all dimensions with slight variation
        import random
        for dim_name, _ in DIMENSIONS:
            variation = random.randint(-1, 1)
            score = max(0, min(10, overall + variation))
            scores[dim_name] = score
            comments[dim_name] = get_comment_for_score(dim_name, score)

        overall_grade = overall

    elif mode == '2':
        # Full dimension-by-dimension scoring
        print("\nScore each dimension independently (0-10):")
        for dim_name, dim_description in DIMENSIONS:
            score, comment = score_dimension(dim_name, dim_description)
            scores[dim_name] = score
            comments[dim_name] = comment

        overall_grade = sum(scores.values()) / len(scores)

    else:  # mode == '3'
        # Mixed mode
        print("\nSet key dimensions that stand out (good or bad):")
        print("Available dimensions:")
        for i, (dim_name, _) in enumerate(DIMENSIONS, 1):
            print(f"  {i}. {dim_name}")

        key_dims_input = input("\nEnter dimension numbers to customize (e.g., '2,3,7'): ").strip()
        key_dim_indices = [int(x.strip())-1 for x in key_dims_input.split(',') if x.strip().isdigit()]

        # Score key dimensions
        for idx in key_dim_indices:
            if 0 <= idx < len(DIMENSIONS):
                dim_name, dim_description = DIMENSIONS[idx]
                score, comment = score_dimension(dim_name, dim_description)
                scores[dim_name] = score
                comments[dim_name] = comment

        # Auto-fill remaining dimensions
        while True:
            try:
                base_score = int(input("\nBase score for other dimensions (0-10): "))
                if 0 <= base_score <= 10:
                    break
            except ValueError:
                pass

        import random
        for dim_name, _ in DIMENSIONS:
            if dim_name not in scores:
                variation = random.randint(-1, 1)
                score = max(0, min(10, base_score + variation))
                scores[dim_name] = score
                comments[dim_name] = get_comment_for_score(dim_name, score)

        overall_grade = sum(scores.values()) / len(scores)

    # Advisor notes
    print(f"\nOverall grade: {overall_grade:.1f}")
    advisor_notes = input("Advisor notes (or Enter for auto): ").strip()

    if not advisor_notes:
        if is_positive:
            advisor_notes = f"This image, '{image_path.stem}', demonstrates strong photographic understanding. The technical execution and visual intent work together effectively, showing mastery of the medium's fundamentals."
        else:
            strengths = [d for d, s in scores.items() if s >= 7]
            weaknesses = [d for d, s in scores.items() if s <= 4]

            if strengths and weaknesses:
                advisor_notes = f"This image, '{image_path.stem}', shows promise in {', '.join(strengths[:2])} but is undermined by significant weaknesses in {', '.join(weaknesses[:2])}. Study the fundamentals—technical precision must support artistic vision."
            elif weaknesses:
                advisor_notes = f"This image demonstrates common pitfalls in {', '.join(weaknesses[:2])}. Master the basics: previsualization, light, and technical precision are non-negotiable foundations."
            else:
                advisor_notes = f"This image, '{image_path.stem}', represents competent work that has not yet achieved distinction. Continue practicing—see more deeply, work more deliberately."

    # Build evaluation
    evaluation = {
        "dimensional_analysis": {
            dim: {
                "score": scores[dim],
                "comment": comments[dim]
            }
            for dim, _ in DIMENSIONS
        },
        "overall_grade": f"{overall_grade:.1f}",
        "advisor_notes": advisor_notes
    }

    entry = {
        "messages": [
            {
                "role": "user",
                "content": "<image>\nAs Ansel Adams, analyze this photograph across all 8 dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact).\n\nRespond in your authentic voice, drawing on your philosophy of previsualization, the Zone System, and your deep connection to the natural world. Provide scores from 0-10 and detailed comments."
            },
            {
                "role": "assistant",
                "content": json.dumps(evaluation, indent=2)
            }
        ],
        "image_path": str(image_path),
        "label": "positive" if is_positive else "negative",
        "scores": scores  # For analysis/filtering later
    }

    print(f"\n✓ Added as {'POSITIVE' if is_positive else 'NEGATIVE'} example")
    return entry


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Interactive image review with independent dimension scoring")
    parser.add_argument('--images-dir', default='../ansel_ocr/extracted_photos', help='Directory with images')
    parser.add_argument('--output', default='ansel_image_training_nuanced.jsonl', help='Output file')

    args = parser.parse_args()

    images_dir = Path(args.images_dir)

    if not images_dir.exists():
        print(f"Directory not found: {images_dir}")
        return

    image_files = sorted(list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg")))

    if not image_files:
        print(f"No images found in {images_dir}")
        return

    print(f"\nFound {len(image_files)} images to review\n")
    print("="*80)
    print("INDEPENDENT DIMENSION SCORING")
    print("="*80)
    print("\nEach dimension is scored independently (0-10):")
    print("  - A photo can have great composition (9) but poor focus (3)")
    print("  - Or excellent lighting (8) but weak emotional impact (4)")
    print("\nModes available:")
    print("  1. Quick - Set one overall grade, apply to all with variation")
    print("  2. Dimension by dimension - Score each of 8 dimensions independently")
    print("  3. Mixed - Set 2-3 standout dimensions, auto-fill rest")

    input("\nPress Enter to begin...")

    training_data = []

    for img_path in image_files:
        entry = review_image_interactive(img_path)
        if entry:
            training_data.append(entry)

    # Save
    with open(args.output, 'w') as f:
        for entry in training_data:
            f.write(json.dumps(entry) + '\n')

    print(f"\n{'='*80}")
    print(f"✓ Saved {len(training_data)} entries to {args.output}")

    # Summary
    positive = sum(1 for e in training_data if e['label'] == 'positive')
    negative = sum(1 for e in training_data if e['label'] == 'negative')

    print(f"  Positive: {positive}")
    print(f"  Negative: {negative}")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
