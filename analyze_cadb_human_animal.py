#!/usr/bin/env python3
"""
Analyze ONLY the human/animal category CADB images.

This script:
1. Loads all 200 selected images
2. Loads the scene categories from CADB
3. Identifies which images have 'human' or 'animal' categories
4. Excludes images already in cadb_training_data.json
5. Only analyzes the remaining human/animal images
6. Saves them to a separate file

This prevents reprocessing the 102 already-analyzed images.

Usage:
    python analyze_cadb_human_animal.py
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Set

# Import the batch analyzer functions
import sys
sys.path.insert(0, str(Path(__file__).parent / 'scripts' / 'training'))
from analyze_cadb_batch import (
    load_cadb_scene_categories,
    load_cadb_composition_scores,
    load_cadb_composition_attributes,
    batch_analyze
)


def get_already_processed_ids(processed_file: Path) -> Set[str]:
    """Get set of image IDs already processed"""
    if not processed_file.exists():
        return set()

    with open(processed_file) as f:
        data = json.load(f)

    return {item.get('image_id', '') for item in data}


def filter_to_human_animal_only(
    selected_images: List[Dict],
    categories: Dict[str, str],
    already_processed: Set[str]
) -> List[Dict]:
    """
    Filter images to only human/animal categories that haven't been processed.

    Args:
        selected_images: All selected images
        categories: Dict mapping image_id -> category
        already_processed: Set of image_ids already processed

    Returns:
        List of images with human/animal categories not yet processed
    """
    human_animal_images = []

    for img_meta in selected_images:
        image_id = img_meta.get('image_id', '')

        # Skip if already processed
        if image_id in already_processed:
            continue

        # Get category
        category = categories.get(image_id, 'unknown').lower()

        # Include if human or animal
        if category in ['human', 'animal']:
            human_animal_images.append(img_meta)

    return human_animal_images


def main():
    parser = argparse.ArgumentParser(
        description="Analyze only human/animal CADB images (skip already-processed)"
    )
    parser.add_argument(
        "--selected-images",
        type=Path,
        default="training/cadb_selected_images.json",
        help="JSON file with all 200 selected CADB images"
    )
    parser.add_argument(
        "--cadb-root",
        type=Path,
        default="Image-Composition-Assessment-Dataset-CADB",
        help="Path to CADB root"
    )
    parser.add_argument(
        "--processed-file",
        type=Path,
        default="training/cadb_analyzed/cadb_training_data.json",
        help="File with already-processed images"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default="training/cadb_analyzed/cadb_training_data_human_animal.json",
        help="Output file for human/animal images"
    )
    parser.add_argument(
        "--service-url",
        default="http://localhost:5100/analyze",
        help="AI advisor service URL"
    )
    parser.add_argument(
        "--advisor",
        default="ansel",
        help="Advisor ID"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests (seconds)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout per image (seconds)"
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"Analyze Human/Animal CADB Images (Skip Already-Processed)")
    print(f"{'='*70}")

    # Load already processed
    already_processed = get_already_processed_ids(args.processed_file)
    print(f"\n[INFO] Already processed: {len(already_processed)} images")

    # Load all selected images
    print(f"[INFO] Loading selected images...")
    with open(args.selected_images) as f:
        all_images = json.load(f)
    print(f"[INFO] Total selected: {len(all_images)} images")

    # Load CADB categories
    print(f"[INFO] Loading CADB scene categories...")
    categories = load_cadb_scene_categories(args.cadb_root)

    # Filter to human/animal only
    print(f"[INFO] Filtering to human/animal categories...")
    human_animal_images = filter_to_human_animal_only(
        all_images,
        categories,
        already_processed
    )

    print(f"[INFO] Images to analyze: {len(human_animal_images)}")

    if not human_animal_images:
        print(f"[INFO] No human/animal images to process. All done!")
        return

    # Load CADB scores and attributes
    print(f"[INFO] Loading CADB composition scores...")
    cadb_scores = load_cadb_composition_scores(args.cadb_root)

    print(f"[INFO] Loading CADB composition attributes...")
    cadb_attributes = load_cadb_composition_attributes(args.cadb_root)

    print(f"\n{'='*70}\n")

    # Run batch analysis
    batch_analyze(
        human_animal_images,
        args.service_url,
        args.advisor,
        args.output,
        cadb_scores,
        cadb_attributes=cadb_attributes,
        delay=args.delay,
        resume=True,
        timeout=args.timeout
    )

    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
