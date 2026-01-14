#!/usr/bin/env python3
"""
Prepare training dataset from dimensional_profiles for LoRA fine-tuning.

This script reads existing dimensional profiles from the SQLite database
and converts them to HuggingFace dataset format required by mlx_vlm.

Usage:
    python training/prepare_dataset.py --advisor ansel
    python training/prepare_dataset.py --advisor ansel --augment
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Database path
DB_PATH = PROJECT_ROOT / "mondrian" / "mondrian.db"
OUTPUT_DIR = PROJECT_ROOT / "training" / "datasets"

# 8 dimensional fields
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


def get_dimensional_profiles(advisor_id: str) -> List[Dict[str, Any]]:
    """
    Fetch dimensional profiles from database for an advisor.
    Excludes temp/analyze files to get only reference image profiles.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get profiles for reference images only (exclude temp uploads)
    cursor.execute("""
        SELECT * FROM dimensional_profiles
        WHERE advisor_id = ?
        AND image_path NOT LIKE '%temp%'
        AND image_path NOT LIKE '%analyze_image%'
        AND image_path LIKE '%' || ? || '%'
    """, (advisor_id, advisor_id))

    profiles = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return profiles


def profile_to_dimensional_analysis(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a database profile row to dimensional_analysis JSON structure.
    """
    analysis = {}

    for dim in DIMENSIONS:
        score_key = f"{dim}_score"
        comment_key = f"{dim}_comment"

        score = profile.get(score_key)
        comment = profile.get(comment_key, "")

        if score is not None:
            analysis[dim] = {
                "score": int(score),
                "comment": comment or ""
            }

    return analysis


def create_training_example(
    image_path: str,
    dimensional_analysis: Dict[str, Any],
    advisor_id: str,
    overall_grade: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a single training example in HuggingFace format.

    Returns dict with:
    - messages: List of conversation turns
    - images: List of PIL Images
    """
    # Build the assistant response JSON
    response = {
        "dimensional_analysis": dimensional_analysis
    }
    if overall_grade:
        response["overall_grade"] = overall_grade

    # Format as conversation
    messages = [
        {
            "role": "user",
            "content": f"<image>\nAs the photography advisor '{advisor_id}', analyze this photograph across all 8 dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact). Provide scores from 0-10 and detailed comments for each dimension."
        },
        {
            "role": "assistant",
            "content": json.dumps(response, indent=2)
        }
    ]

    # Load the image
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Warning: Could not load image {image_path}: {e}")
        return None

    return {
        "messages": messages,
        "images": [image]
    }


def prepare_dataset(
    advisor_id: str,
    augment: bool = False,
    output_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    Prepare training dataset for an advisor.

    Args:
        advisor_id: The advisor to prepare data for (e.g., 'ansel')
        augment: Whether to apply data augmentation
        output_path: Where to save the dataset

    Returns:
        List of training examples
    """
    print(f"Preparing dataset for advisor: {advisor_id}")

    # Get profiles from database
    profiles = get_dimensional_profiles(advisor_id)
    print(f"Found {len(profiles)} dimensional profiles")

    if not profiles:
        print("No profiles found. Please run RAG analysis on reference images first.")
        return []

    examples = []

    for profile in profiles:
        image_path = profile.get("image_path")

        if not image_path or not os.path.exists(image_path):
            print(f"Skipping missing image: {image_path}")
            continue

        # Convert profile to dimensional analysis
        dimensional_analysis = profile_to_dimensional_analysis(profile)

        # Check we have all 8 dimensions
        if len(dimensional_analysis) < 8:
            print(f"Skipping incomplete profile for {image_path} ({len(dimensional_analysis)}/8 dimensions)")
            continue

        # Create the training example
        example = create_training_example(
            image_path=image_path,
            dimensional_analysis=dimensional_analysis,
            advisor_id=advisor_id,
            overall_grade=profile.get("overall_grade")
        )

        if example:
            examples.append(example)
            print(f"  Added: {Path(image_path).name}")

    print(f"\nTotal training examples: {len(examples)}")

    # Save dataset if output path provided
    if output_path:
        output_path.mkdir(parents=True, exist_ok=True)

        # Save as JSON Lines format (compatible with HuggingFace)
        jsonl_path = output_path / f"{advisor_id}_train.jsonl"

        with open(jsonl_path, "w") as f:
            for ex in examples:
                # Convert PIL Image to path for serialization
                record = {
                    "messages": ex["messages"],
                    "image_path": profiles[examples.index(ex)]["image_path"]
                }
                f.write(json.dumps(record) + "\n")

        print(f"\nSaved dataset to: {jsonl_path}")

    return examples


def save_as_hf_dataset(examples: List[Dict[str, Any]], output_dir: Path, advisor_id: str):
    """
    Save examples as a HuggingFace Dataset.
    Requires: pip install datasets
    """
    try:
        from datasets import Dataset as HFDataset
    except ImportError:
        print("Warning: 'datasets' package not installed. Run: pip install datasets")
        return None

    # For HuggingFace Dataset, we keep images as PIL objects
    hf_dataset = HFDataset.from_list(examples)

    dataset_path = output_dir / advisor_id
    hf_dataset.save_to_disk(str(dataset_path))
    print(f"Saved HuggingFace dataset to: {dataset_path}")

    return hf_dataset


def main():
    parser = argparse.ArgumentParser(
        description="Prepare LoRA training dataset from dimensional profiles"
    )
    parser.add_argument(
        "--advisor", "-a",
        type=str,
        default="ansel",
        help="Advisor ID to prepare dataset for (default: ansel)"
    )
    parser.add_argument(
        "--augment",
        action="store_true",
        help="Apply data augmentation (not yet implemented)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output directory (default: training/datasets)"
    )
    parser.add_argument(
        "--hf-format",
        action="store_true",
        help="Also save in HuggingFace Dataset format"
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else OUTPUT_DIR

    # Prepare the dataset
    examples = prepare_dataset(
        advisor_id=args.advisor,
        augment=args.augment,
        output_path=output_dir
    )

    if not examples:
        print("No training examples created. Exiting.")
        sys.exit(1)

    # Optionally save as HuggingFace format
    if args.hf_format:
        save_as_hf_dataset(examples, output_dir, args.advisor)

    print("\nDataset preparation complete!")
    print(f"Next step: Run training with:")
    print(f"  python training/train_lora.py --advisor {args.advisor}")


if __name__ == "__main__":
    main()
