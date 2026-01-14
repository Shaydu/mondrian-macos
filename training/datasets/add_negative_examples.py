#!/usr/bin/env python3
"""
Add Negative Training Examples

This script helps you quickly add negative examples (bad photos) to your training set.
You can point it at a directory of "bad" photos and it will generate Ansel-style critiques.

Usage:
    # Add from a directory of bad examples
    python add_negative_examples.py --dir /path/to/bad/photos --output negative_examples.jsonl

    # Use quick mode with templates
    python add_negative_examples.py --dir /path/to/bad/photos --quick
"""

import json
import argparse
from pathlib import Path
from typing import Dict


# Common problems for negative examples
COMMON_PROBLEMS = {
    "poor_composition": {
        "scores": {
            "composition": 3,
            "lighting": 5,
            "focus_sharpness": 5,
            "color_harmony": 4,
            "subject_isolation": 3,
            "depth_perspective": 4,
            "visual_balance": 3,
            "emotional_impact": 3
        },
        "comments": {
            "composition": "The arrangement lacks intentionality. Elements compete for attention without clear visual hierarchy.",
            "lighting": "Adequate illumination, but light merely documents rather than reveals.",
            "focus_sharpness": "Technical focus is acceptable, but sharpness cannot salvage poor composition.",
            "color_harmony": "Tonal values exist without relationship. No sense of the Zone System's discipline.",
            "subject_isolation": "What is this photograph about? The subject drowns in visual clutter.",
            "depth_perspective": "Space collapses. No invitation to enter the frame, no sense of dimension.",
            "visual_balance": "Visual weight distributed carelessly. The eye finds no rest.",
            "emotional_impact": "Execution without vision. The photograph documents but does not speak."
        },
        "advisor_notes": "This image demonstrates a fundamental problem: composition without intent. Before releasing the shutter, one must ask: what is the photograph about? Every element must serve that purpose, or it becomes distraction."
    },
    "flat_lighting": {
        "scores": {
            "composition": 6,
            "lighting": 2,
            "focus_sharpness": 7,
            "color_harmony": 4,
            "subject_isolation": 5,
            "depth_perspective": 3,
            "visual_balance": 5,
            "emotional_impact": 3
        },
        "comments": {
            "composition": "The arrangement shows consideration, though not mastery.",
            "lighting": "Flat, even illumination destroys form. Light must sculpt, reveal, define—here it merely exists.",
            "focus_sharpness": "Technically sharp, but sharpness without dimensional light creates no presence.",
            "color_harmony": "A narrow tonal range compresses all values into muddy midtones. The Zone System would reveal the poverty here.",
            "subject_isolation": "The subject exists but does not emerge. Flat light provides no separation.",
            "depth_perspective": "Without light to define planes, depth collapses into a single dimension.",
            "visual_balance": "Balance means little when light provides no visual weight to balance.",
            "emotional_impact": "One sees the subject but feels nothing. Light creates mood—without it, emptiness."
        },
        "advisor_notes": "Light is the photographer's medium, yet here it is ignored. Flat illumination robs the subject of form, texture, dimension—everything that makes photography powerful. Wait for the light. Return when the sun reveals rather than merely illuminates."
    },
    "soft_focus": {
        "scores": {
            "composition": 6,
            "lighting": 6,
            "focus_sharpness": 2,
            "color_harmony": 5,
            "subject_isolation": 4,
            "depth_perspective": 4,
            "visual_balance": 5,
            "emotional_impact": 3
        },
        "comments": {
            "composition": "Reasonable arrangement undermined by technical failure.",
            "lighting": "Light works adequately but cannot overcome fundamental softness.",
            "focus_sharpness": "Unacceptable softness destroys credibility. Sharpness where needed is non-negotiable in fine photography.",
            "color_harmony": "Tonal relationships are present but obscured by optical imprecision.",
            "subject_isolation": "The subject blurs into its surroundings—literally. Focus defines presence.",
            "depth_perspective": "Soft focus collapses spatial relationships. The viewer cannot orient within the frame.",
            "visual_balance": "Balance exists in theory but cannot be perceived through the fog of poor focus.",
            "emotional_impact": "Technical incompetence overwhelms any potential emotional content."
        },
        "advisor_notes": "Photography demands technical excellence. Soft focus—whether from motion, poor optics, or focusing error—destroys the image's authority. Master hyperfocal distance, use a tripod, wait for stillness. Technical precision is not the end, but it is the necessary foundation."
    },
    "cluttered_frame": {
        "scores": {
            "composition": 2,
            "lighting": 5,
            "focus_sharpness": 6,
            "color_harmony": 4,
            "subject_isolation": 2,
            "depth_perspective": 3,
            "visual_balance": 2,
            "emotional_impact": 2
        },
        "comments": {
            "composition": "Visual chaos. Every element competes, none dominates, nothing serves the whole.",
            "lighting": "Adequate light wasted on a cluttered frame.",
            "focus_sharpness": "Ironically, sharp focus only makes the clutter more painfully visible.",
            "color_harmony": "So many tonal values fighting for attention that none register.",
            "subject_isolation": "What is the subject? Everything screams, nothing speaks.",
            "depth_perspective": "Clutter fills every plane. No breathing room, no rest for the eye.",
            "visual_balance": "Not imbalance but cacophony. Too much everywhere.",
            "emotional_impact": "Confusion, fatigue, the desperate wish to look away."
        },
        "advisor_notes": "Simplify. Remove. Exclude. Photography is not about including everything seen, but about seeing what matters and excluding everything else. Move closer. Change angles. Wait for the perfect moment when clutter clears. The photographer must be ruthless in service of clarity."
    },
    "no_subject": {
        "scores": {
            "composition": 3,
            "lighting": 5,
            "focus_sharpness": 6,
            "color_harmony": 5,
            "subject_isolation": 1,
            "depth_perspective": 4,
            "visual_balance": 4,
            "emotional_impact": 2
        },
        "comments": {
            "composition": "Elements arranged but to what end? Composition requires a subject to compose around.",
            "lighting": "Light exists, competently handled, yet illuminating nothing of consequence.",
            "focus_sharpness": "Sharp focus on... what? Technical precision without purpose.",
            "color_harmony": "Tonal values properly managed yet saying nothing.",
            "subject_isolation": "No subject to isolate. The fundamental question—'what is this about?'—has no answer.",
            "depth_perspective": "Depth leading nowhere, perspective revealing nothing.",
            "visual_balance": "Balance without meaning. A well-arranged nothing.",
            "emotional_impact": "The viewer searches, finds nothing, moves on unmoved."
        },
        "advisor_notes": "Before visualization, before exposure, before any technical consideration, the photographer must answer one question: What is this photograph about? A technically perfect photograph of nothing is still nothing. Find your subject. Commit to it. Build everything around it."
    },
    "poor_exposure": {
        "scores": {
            "composition": 5,
            "lighting": 3,
            "focus_sharpness": 5,
            "color_harmony": 2,
            "subject_isolation": 4,
            "depth_perspective": 3,
            "visual_balance": 4,
            "emotional_impact": 3
        },
        "comments": {
            "composition": "Reasonable structure obscured by exposure failure.",
            "lighting": "The light may have been good, but exposure destroys its potential.",
            "focus_sharpness": "Focus is adequate though exposure problems dominate perception.",
            "color_harmony": "Overexposed highlights blow out to paper white, losing all tonal differentiation. Or shadows block up, crushing detail into featureless black.",
            "subject_isolation": "Extreme exposure makes separation impossible—everything compressed into narrow tonal range.",
            "depth_perspective": "Tonal compression from poor exposure flattens dimensional illusion.",
            "visual_balance": "Large areas of pure white or black dominate, overwhelming compositional intent.",
            "emotional_impact": "Technical failure distracts from any emotional content."
        },
        "advisor_notes": "The Zone System exists precisely to prevent this. Proper exposure places tonal values where you visualize them—not where the meter suggests. Learn to read the light. Expose for the shadows, develop for the highlights. In the digital realm, protect highlights absolutely. Underexposure or overexposure both destroy information that printing cannot recreate."
    }
}


def generate_negative_example(image_path: str, problem_type: str, grade: float = None) -> Dict:
    """Generate a negative training example based on common problems."""
    template = COMMON_PROBLEMS[problem_type]

    if grade is None:
        # Calculate grade from scores
        grade = sum(template['scores'].values()) / len(template['scores'])

    evaluation = {
        "dimensional_analysis": {
            dim: {
                "score": template['scores'][dim],
                "comment": template['comments'][dim]
            }
            for dim in template['scores'].keys()
        },
        "overall_grade": f"{grade:.1f}",
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
        "problem_type": problem_type
    }


def main():
    parser = argparse.ArgumentParser(description="Add negative training examples")
    parser.add_argument('--dir', required=True, help='Directory containing bad example photos')
    parser.add_argument('--output', default='negative_examples.jsonl', help='Output file')
    parser.add_argument('--quick', action='store_true', help='Use quick mode with templates')

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
    print("\nAvailable problem types:")
    for i, (key, _) in enumerate(COMMON_PROBLEMS.items(), 1):
        print(f"  {i}. {key.replace('_', ' ').title()}")

    training_data = []

    for img_path in image_files:
        print(f"\n{'='*80}")
        print(f"Image: {img_path.name}")
        print(f"{'='*80}")

        if args.quick:
            # Quick mode: auto-assign problem type
            print("Quick mode: Auto-assigning 'poor_composition'")
            problem_type = 'poor_composition'
        else:
            # Interactive mode
            print(f"\nOpen image: open {img_path}\n")

            while True:
                choice = input("Problem type (1-6) or 's' to skip: ").strip()
                if choice == 's':
                    print("Skipped.")
                    break

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(COMMON_PROBLEMS):
                        problem_type = list(COMMON_PROBLEMS.keys())[idx]
                        break
                except ValueError:
                    pass

                print("Invalid choice. Try again.")

            if choice == 's':
                continue

        # Generate the example
        entry = generate_negative_example(str(img_path), problem_type)
        training_data.append(entry)
        print(f"✓ Added as NEGATIVE example ({problem_type})")

    # Save
    with open(args.output, 'w') as f:
        for entry in training_data:
            f.write(json.dumps(entry) + '\n')

    print(f"\n✓ Saved {len(training_data)} negative examples to {args.output}")


if __name__ == '__main__':
    main()
