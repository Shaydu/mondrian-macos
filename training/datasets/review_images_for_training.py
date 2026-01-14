#!/usr/bin/env python3
"""
Interactive Image Review Tool for LoRA Training Data

This script helps you:
1. Review existing training images
2. Add positive examples (good photos with praise)
3. Add negative examples (bad photos with constructive critique)
4. Generate Ansel Adams-style evaluations across 8 dimensions
5. Export to vision model training format (base64 encoded)

Usage:
    python review_images_for_training.py --mode review     # Review existing images
    python review_images_for_training.py --mode add        # Add new images
    python review_images_for_training.py --mode export     # Export to training format
"""

import json
import base64
import os
from pathlib import Path
from typing import Dict, List, Optional
import argparse


# Ansel's 8 evaluation dimensions
DIMENSIONS = [
    "composition",
    "lighting",
    "focus_sharpness",
    "color_harmony",
    "subject_isolation",
    "depth_perspective",
    "visual_balance",
    "emotional_impact"
]

# Example critiques for each dimension (negative examples)
NEGATIVE_CRITIQUES = {
    "composition": "The arrangement lacks intentionality. The eye wanders without purpose or clear visual hierarchy.",
    "lighting": "Flat, even illumination reveals no form. Light must sculpt and define—here it merely documents.",
    "focus_sharpness": "Soft focus undermines technical credibility. Sharpness where it matters is non-negotiable.",
    "color_harmony": "Tonal values compete rather than harmonize. The Zone System would reveal the chaos here.",
    "subject_isolation": "The subject drowns in visual clutter. What is the photograph about?",
    "depth_perspective": "Space collapses. No sense of near and far, no invitation to enter the frame.",
    "visual_balance": "Elements war for attention. Visual weight distributed without consideration.",
    "emotional_impact": "Technical execution without vision. The photograph says nothing."
}

# Example praise for each dimension (positive examples)
POSITIVE_CRITIQUES = {
    "composition": "Every element serves the whole. The eye travels exactly as the photographer intended.",
    "lighting": "Light reveals form and texture with precision. The Zone System's power is evident here.",
    "focus_sharpness": "Hyperfocal distance mastery—sharpness from foreground to infinity, technique in service of vision.",
    "color_harmony": "Tonal relationships sing. Each value carefully placed, each transition considered.",
    "subject_isolation": "The subject emerges with clarity and authority. Context enriches without distraction.",
    "depth_perspective": "Magnificent sense of space—the viewer stands within the frame, experiencing dimension.",
    "visual_balance": "Visual weight distributed with the sensitivity of a master composer.",
    "emotional_impact": "One stands before such an image and feels the presence of something greater."
}


def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_image_data_url(image_path: str) -> str:
    """Create data URL for image."""
    ext = Path(image_path).suffix.lower()
    mime_type = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif'
    }.get(ext, 'image/png')

    base64_data = encode_image_to_base64(image_path)
    return f"data:{mime_type};base64,{base64_data}"


def display_image_info(image_path: str):
    """Display image information."""
    print(f"\n{'='*80}")
    print(f"Image: {Path(image_path).name}")
    print(f"Path: {image_path}")
    print(f"Size: {os.path.getsize(image_path) / 1024:.1f} KB")
    print(f"{'='*80}\n")


def create_evaluation(
    scores: Dict[str, int],
    comments: Dict[str, str],
    overall_grade: float,
    advisor_notes: str,
    image_name: str
) -> Dict:
    """Create a complete evaluation structure."""
    dimensional_analysis = {}
    for dim in DIMENSIONS:
        dimensional_analysis[dim] = {
            "score": scores.get(dim, 5),
            "comment": comments.get(dim, "")
        }

    return {
        "dimensional_analysis": dimensional_analysis,
        "overall_grade": str(overall_grade),
        "advisor_notes": advisor_notes.format(image_name=image_name)
    }


def interactive_review_mode(images_dir: str, output_file: str):
    """Interactive mode to review and label images."""
    images_dir = Path(images_dir)
    image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))

    if not image_files:
        print(f"No images found in {images_dir}")
        return

    print(f"\nFound {len(image_files)} images to review")
    print("\nFor each image, you'll provide:")
    print("  - Label: positive (good) or negative (bad)")
    print("  - Overall grade: 0-10")
    print("  - Scores for 8 dimensions: 0-10")
    print("  - Comments for each dimension\n")

    training_data = []

    for img_path in image_files:
        display_image_info(str(img_path))

        print(f"Open this image in Preview to view it:")
        print(f"  open {img_path}\n")

        # Get label
        while True:
            label = input("Label [p=positive, n=negative, s=skip]: ").lower()
            if label in ['p', 'n', 's']:
                break
            print("Invalid input. Use 'p', 'n', or 's'")

        if label == 's':
            print("Skipped.\n")
            continue

        is_positive = label == 'p'

        # Get overall grade
        while True:
            try:
                overall_grade = float(input("Overall grade (0-10): "))
                if 0 <= overall_grade <= 10:
                    break
                print("Grade must be between 0 and 10")
            except ValueError:
                print("Please enter a number")

        # Quick mode or detailed mode
        mode = input("\nQuick mode (use templates) or Detailed? [q/d]: ").lower()

        scores = {}
        comments = {}

        if mode == 'q':
            # Use templates
            base_score = int(overall_grade)
            if is_positive:
                for dim in DIMENSIONS:
                    scores[dim] = base_score
                    comments[dim] = POSITIVE_CRITIQUES[dim]
            else:
                for dim in DIMENSIONS:
                    scores[dim] = base_score
                    comments[dim] = NEGATIVE_CRITIQUES[dim]
        else:
            # Detailed input
            print("\nEnter scores (0-10) for each dimension:")
            for dim in DIMENSIONS:
                while True:
                    try:
                        score = int(input(f"  {dim}: "))
                        if 0 <= score <= 10:
                            scores[dim] = score
                            break
                    except ValueError:
                        pass
                    print("    Invalid. Enter 0-10")

            print("\nEnter comments for each dimension (or press Enter for template):")
            for dim in DIMENSIONS:
                comment = input(f"  {dim}: ").strip()
                if not comment:
                    comment = POSITIVE_CRITIQUES[dim] if is_positive else NEGATIVE_CRITIQUES[dim]
                comments[dim] = comment

        # Get advisor notes
        print("\nAdvisor notes (overall assessment):")
        advisor_notes = input("> ").strip()
        if not advisor_notes:
            if is_positive:
                advisor_notes = f"This image, '{img_path.stem}', exemplifies principles I have long advocated. The photograph must be visualized before exposure—every tonal value, every relationship of light and shadow, anticipated and controlled."
            else:
                advisor_notes = f"This image, '{img_path.stem}', demonstrates common pitfalls. Study what's missing: intentionality in composition, mastery of light, technical precision in service of vision."

        # Create training entry
        evaluation = create_evaluation(
            scores=scores,
            comments=comments,
            overall_grade=overall_grade,
            advisor_notes=advisor_notes,
            image_name=img_path.stem
        )

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
            "image_path": str(img_path),
            "label": "positive" if is_positive else "negative"
        }

        training_data.append(entry)
        print(f"\n✓ Added as {'POSITIVE' if is_positive else 'NEGATIVE'} example\n")

    # Save to file
    with open(output_file, 'w') as f:
        for entry in training_data:
            f.write(json.dumps(entry) + '\n')

    print(f"\n✓ Saved {len(training_data)} training examples to {output_file}")
    print(f"  Positive: {sum(1 for e in training_data if e['label'] == 'positive')}")
    print(f"  Negative: {sum(1 for e in training_data if e['label'] == 'negative')}")


def export_with_base64(input_file: str, output_file: str):
    """Export training data with base64-encoded images for vision model training."""
    print(f"\nExporting {input_file} with base64-encoded images...")

    exported_data = []

    with open(input_file, 'r') as f:
        for line in f:
            entry = json.loads(line)

            if 'image_path' not in entry:
                continue

            image_path = entry['image_path']

            if not os.path.exists(image_path):
                print(f"  ⚠ Image not found: {image_path}")
                continue

            # Create base64 data URL
            try:
                data_url = get_image_data_url(image_path)
            except Exception as e:
                print(f"  ⚠ Error encoding {image_path}: {e}")
                continue

            # Convert to vision model format
            vision_entry = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url
                                }
                            },
                            {
                                "type": "text",
                                "text": "As Ansel Adams, analyze this photograph across all 8 dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact).\n\nRespond in your authentic voice, drawing on your philosophy of previsualization, the Zone System, and your deep connection to the natural world. Provide scores from 0-10 and detailed comments."
                            }
                        ]
                    },
                    {
                        "role": "assistant",
                        "content": entry['messages'][1]['content']
                    }
                ]
            }

            exported_data.append(vision_entry)
            print(f"  ✓ Exported: {Path(image_path).name}")

    with open(output_file, 'w') as f:
        for entry in exported_data:
            f.write(json.dumps(entry) + '\n')

    print(f"\n✓ Exported {len(exported_data)} entries to {output_file}")
    print(f"Ready for vision model LoRA training!")


def list_existing_data(input_file: str):
    """List existing training data."""
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return

    entries = []
    with open(input_file, 'r') as f:
        for line in f:
            entries.append(json.loads(line))

    print(f"\nExisting training data in {input_file}:")
    print(f"Total entries: {len(entries)}")

    positive = [e for e in entries if e.get('label') == 'positive']
    negative = [e for e in entries if e.get('label') == 'negative']

    print(f"  Positive: {len(positive)}")
    print(f"  Negative: {len(negative)}")

    if entries:
        print("\nSample entries:")
        for i, entry in enumerate(entries[:3], 1):
            label = entry.get('label', 'unknown')
            img_path = entry.get('image_path', 'no path')
            print(f"  {i}. {label:8} | {Path(img_path).name}")


def main():
    parser = argparse.ArgumentParser(description="Review images for LoRA training")
    parser.add_argument(
        '--mode',
        choices=['review', 'export', 'list'],
        default='review',
        help='Mode: review images, export with base64, or list existing data'
    )
    parser.add_argument(
        '--images-dir',
        default='../ansel_ocr/extracted_photos',
        help='Directory containing images to review'
    )
    parser.add_argument(
        '--input',
        default='ansel_image_training.jsonl',
        help='Input JSONL file (for export mode)'
    )
    parser.add_argument(
        '--output',
        default='ansel_image_training.jsonl',
        help='Output JSONL file'
    )
    parser.add_argument(
        '--export-output',
        default='ansel_image_training_base64.jsonl',
        help='Output file for base64 export'
    )

    args = parser.parse_args()

    if args.mode == 'review':
        interactive_review_mode(args.images_dir, args.output)
    elif args.mode == 'export':
        export_with_base64(args.input, args.export_output)
    elif args.mode == 'list':
        list_existing_data(args.output)


if __name__ == '__main__':
    main()
