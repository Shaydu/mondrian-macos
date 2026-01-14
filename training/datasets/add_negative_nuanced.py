#!/usr/bin/env python3
"""
Add Negative Examples with Nuanced Dimension Scoring

This script generates negative training examples where each dimension
can be scored independently. A photo might have:
  - Good composition (7) but terrible focus (2)
  - Decent lighting (6) but no emotional impact (2)

This creates more realistic training data that reflects how real photos
can have mixed qualities.

Usage:
    python add_negative_nuanced.py --dir /path/to/photos --output negative_nuanced.jsonl
"""

import json
import argparse
from pathlib import Path
from typing import Dict
import random


# Dimension score ranges and comments for nuanced problems
NUANCED_PROBLEMS = {
    "good_comp_bad_focus": {
        "description": "Good composition undermined by poor technical execution (soft focus)",
        "scores": {
            "composition": (7, 8),
            "lighting": (5, 7),
            "focus_sharpness": (2, 3),
            "color_harmony": (5, 6),
            "subject_isolation": (5, 7),
            "depth_perspective": (4, 6),
            "visual_balance": (6, 8),
            "emotional_impact": (3, 5)
        },
        "advisor_notes": "Compositional merit is utterly destroyed by technical failure. One can visualize a strong image here, but soft focus renders it worthless. Photography demands both vision AND technical precision—one without the other produces only frustration."
    },
    "good_light_bad_comp": {
        "description": "Beautiful light wasted on poor composition",
        "scores": {
            "composition": (3, 4),
            "lighting": (8, 9),
            "focus_sharpness": (6, 7),
            "color_harmony": (7, 8),
            "subject_isolation": (3, 5),
            "depth_perspective": (5, 6),
            "visual_balance": (3, 4),
            "emotional_impact": (4, 5)
        },
        "advisor_notes": "Magnificent light utterly wasted on a poorly conceived composition. The photographer saw the light but failed to organize the visual elements. This is the tragedy of the untrained eye—recognizing one aspect of photography while remaining blind to composition's fundamental importance."
    },
    "sharp_but_boring": {
        "description": "Technically perfect but emotionally void",
        "scores": {
            "composition": (6, 7),
            "lighting": (5, 6),
            "focus_sharpness": (9, 10),
            "color_harmony": (6, 7),
            "subject_isolation": (6, 7),
            "depth_perspective": (5, 6),
            "visual_balance": (6, 7),
            "emotional_impact": (2, 3)
        },
        "advisor_notes": "Technical perfection in service of nothing. Sharp focus, adequate composition, yet the image is emotionally void—it documents but does not speak. This demonstrates the limitation of technique without vision. Master the craft, yes, but remember: photography is art, not merely technical exercise."
    },
    "one_bad_dimension": {
        "description": "Generally solid with one critical failure",
        "scores": {
            "composition": (7, 8),
            "lighting": (7, 8),
            "focus_sharpness": (7, 8),
            "color_harmony": (7, 8),
            "subject_isolation": (6, 8),
            "depth_perspective": (6, 8),
            "visual_balance": (7, 8),
            "emotional_impact": (6, 8)
        },
        "critical_failure": "random",  # One dimension will be set to 2-3
        "advisor_notes": "This image demonstrates competence across most dimensions, yet one critical failure undermines the whole. In photography, weakness in any fundamental area compromises the entire image. Excellence requires mastery of ALL aspects—composition, light, technique, vision working in concert."
    },
    "mixed_amateur": {
        "description": "Inconsistent - some good instincts, poor execution elsewhere",
        "scores": {
            "composition": (4, 7),  # Wide range - random
            "lighting": (4, 7),
            "focus_sharpness": (3, 6),
            "color_harmony": (4, 6),
            "subject_isolation": (3, 7),
            "depth_perspective": (3, 6),
            "visual_balance": (4, 7),
            "emotional_impact": (3, 6)
        },
        "advisor_notes": "Inconsistent work showing flashes of understanding alongside fundamental gaps. The photographer has instincts but lacks disciplined practice and study. Focus on the basics: see clearly, expose correctly, compose deliberately. Master one aspect at a time rather than attempting everything poorly."
    },
    "flat_lighting_only": {
        "description": "Composition and technique OK, but lighting destroys dimension",
        "scores": {
            "composition": (6, 7),
            "lighting": (2, 3),
            "focus_sharpness": (6, 8),
            "color_harmony": (3, 4),
            "subject_isolation": (5, 6),
            "depth_perspective": (3, 4),
            "visual_balance": (6, 7),
            "emotional_impact": (3, 5)
        },
        "advisor_notes": "Flat lighting crushes this image's potential. Composition shows understanding, focus is adequate, but light—the photographer's primary medium—has been ignored. Dimensionality collapses into muddy midtones. Wait for the light. Return when illumination reveals rather than merely exists."
    },
    "cluttered_but_sharp": {
        "description": "Technical excellence, compositional chaos",
        "scores": {
            "composition": (2, 3),
            "lighting": (6, 7),
            "focus_sharpness": (8, 9),
            "color_harmony": (5, 6),
            "subject_isolation": (2, 3),
            "depth_perspective": (4, 5),
            "visual_balance": (2, 3),
            "emotional_impact": (3, 4)
        },
        "advisor_notes": "Sharp focus only makes the compositional chaos more painfully visible. The photographer has mastered the technical but not the visual. What is this image about? Where should the eye go? Too much everywhere—simplify, exclude, focus not just optically but conceptually."
    },
    "good_vision_poor_execution": {
        "description": "Strong concept undermined by technical problems",
        "scores": {
            "composition": (7, 8),
            "lighting": (4, 5),
            "focus_sharpness": (4, 5),
            "color_harmony": (4, 5),
            "subject_isolation": (6, 7),
            "depth_perspective": (5, 6),
            "visual_balance": (7, 8),
            "emotional_impact": (6, 7)
        },
        "advisor_notes": "One can see the photographer's vision here—the image that was previsualized. But technical execution fails to match the concept. This is the reverse tragedy: vision without craft. Study exposure, master your equipment, practice until technique becomes transparent. Vision must be supported by technical excellence."
    }
}


# Specific comments for each dimension at different score levels
DIMENSION_COMMENTS = {
    "composition": {
        (8, 10): "Compositional strength evident—thoughtful arrangement with clear visual hierarchy.",
        (6, 7): "Adequate composition showing basic understanding of visual organization.",
        (4, 5): "Compositional awareness present but execution lacks confidence.",
        (2, 3): "Poor compositional organization—elements compete without purpose.",
        (0, 1): "Compositional chaos. No discernible structure or intent."
    },
    "lighting": {
        (8, 10): "Light handled with skill—revealing form and creating dimension.",
        (6, 7): "Adequate lighting providing reasonable tonal separation.",
        (4, 5): "Lighting functional but uninspired—neither reveals nor destroys.",
        (2, 3): "Flat lighting collapses dimensionality into muddy midtones.",
        (0, 1): "Catastrophic lighting destroys all tonal relationships."
    },
    "focus_sharpness": {
        (8, 10): "Excellent sharpness where needed—technical precision evident.",
        (6, 7): "Acceptable focus serving the image adequately.",
        (4, 5): "Soft in critical areas—precision lacking.",
        (2, 3): "Unacceptable blur undermines the image's credibility.",
        (0, 1): "Catastrophically soft throughout—technical incompetence."
    },
    "color_harmony": {
        (8, 10): "Tonal relationships well-managed with good separation.",
        (6, 7): "Adequate tonal range without exceptional management.",
        (4, 5): "Tonal palette limited—values poorly separated.",
        (2, 3): "Tonal chaos—values merge without distinction.",
        (0, 1): "Complete tonal collapse—no meaningful relationships."
    },
    "subject_isolation": {
        (8, 10): "Subject emerges clearly with strong separation.",
        (6, 7): "Subject identifiable though not commanding.",
        (4, 5): "Subject competes with surroundings for attention.",
        (2, 3): "Subject drowns in visual clutter—unclear focus.",
        (0, 1): "No discernible subject—complete visual confusion."
    },
    "depth_perspective": {
        (8, 10): "Strong dimensional illusion—clear spatial relationships.",
        (6, 7): "Adequate depth perception—spaces reasonably defined.",
        (4, 5): "Weak spatial sense—dimensionality not strongly conveyed.",
        (2, 3): "Depth collapses—poor spatial relationships flatten image.",
        (0, 1): "Complete spatial collapse—aggressively flat."
    },
    "visual_balance": {
        (8, 10): "Visual weight thoughtfully distributed—balanced composition.",
        (6, 7): "Adequate balance without particularly refined distribution.",
        (4, 5): "Balance functional but not artful—weak weight management.",
        (2, 3): "Imbalance creates discomfort—poor weight distribution.",
        (0, 1): "Catastrophic imbalance tilting toward visual chaos."
    },
    "emotional_impact": {
        (8, 10): "Genuine emotional resonance—the image speaks meaningfully.",
        (6, 7): "Some emotional content present—communicates adequately.",
        (4, 5): "Limited emotional impact—competent but not moving.",
        (2, 3): "Emotionally void—technical execution without feeling.",
        (0, 1): "Complete absence of emotional communication or meaning."
    }
}


def get_comment_for_dimension_score(dimension: str, score: int) -> str:
    """Get appropriate comment for a dimension and score."""
    comments = DIMENSION_COMMENTS.get(dimension, {})

    for (low, high), comment in comments.items():
        if low <= score <= high:
            return comment

    return f"Score of {score}/10 in {dimension}."


def generate_nuanced_negative(image_path: str, problem_type: str) -> Dict:
    """Generate negative example with nuanced dimension-by-dimension scoring."""
    template = NUANCED_PROBLEMS[problem_type]

    scores = {}
    comments = {}

    # Generate scores with randomization within ranges
    for dim, score_range in template['scores'].items():
        if isinstance(score_range, tuple):
            score = random.randint(score_range[0], score_range[1])
        else:
            score = score_range

        scores[dim] = score
        comments[dim] = get_comment_for_dimension_score(dim, score)

    # Handle special case: "one_bad_dimension" - pick one dimension to fail
    if template.get('critical_failure') == 'random':
        # Pick one random dimension to be the critical failure
        failing_dim = random.choice(list(scores.keys()))
        scores[failing_dim] = random.randint(2, 3)
        comments[failing_dim] = f"Critical failure here—{get_comment_for_dimension_score(failing_dim, scores[failing_dim])}"

    overall_grade = sum(scores.values()) / len(scores)

    evaluation = {
        "dimensional_analysis": {
            dim: {
                "score": scores[dim],
                "comment": comments[dim]
            }
            for dim in scores.keys()
        },
        "overall_grade": f"{overall_grade:.1f}",
        "advisor_notes": template['advisor_notes']
    }

    return {
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
        "label": "negative",
        "problem_type": problem_type,
        "scores": scores
    }


def main():
    parser = argparse.ArgumentParser(description="Add nuanced negative examples with independent dimension scoring")
    parser.add_argument('--dir', required=True, help='Directory containing photos')
    parser.add_argument('--output', default='negative_examples_nuanced.jsonl', help='Output file')
    parser.add_argument('--problem', choices=list(NUANCED_PROBLEMS.keys()) + ['random'],
                        default='random', help='Problem type to apply (or random)')

    args = parser.parse_args()

    images_dir = Path(args.dir)

    if not images_dir.exists():
        print(f"Directory not found: {images_dir}")
        return

    image_files = list(images_dir.glob("*.png")) + \
                  list(images_dir.glob("*.jpg")) + \
                  list(images_dir.glob("*.jpeg"))

    if not image_files:
        print(f"No images found in {images_dir}")
        return

    print(f"\nFound {len(image_files)} images")
    print("\nNuanced problem types:")
    for i, (key, value) in enumerate(NUANCED_PROBLEMS.items(), 1):
        print(f"  {i}. {key}: {value['description']}")

    print(f"\nUsing: {'random mix' if args.problem == 'random' else args.problem}\n")

    training_data = []

    for img_path in image_files:
        # Pick problem type
        if args.problem == 'random':
            problem_type = random.choice(list(NUANCED_PROBLEMS.keys()))
        else:
            problem_type = args.problem

        entry = generate_nuanced_negative(str(img_path), problem_type)
        training_data.append(entry)

        print(f"✓ {img_path.name}: {problem_type} (avg score: {sum(entry['scores'].values())/8:.1f})")

    # Save
    with open(args.output, 'w') as f:
        for entry in training_data:
            f.write(json.dumps(entry) + '\n')

    print(f"\n✓ Saved {len(training_data)} nuanced negative examples to {args.output}")

    # Show score distribution
    all_scores = []
    for entry in training_data:
        all_scores.extend(entry['scores'].values())

    print(f"\nScore distribution:")
    print(f"  Average: {sum(all_scores)/len(all_scores):.1f}")
    print(f"  Range: {min(all_scores)}-{max(all_scores)}")


if __name__ == '__main__':
    main()
