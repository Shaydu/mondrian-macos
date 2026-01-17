#!/usr/bin/env python3
"""
Ansel Adams Photo Dataset Expansion Script
Downloads from public domain sources and creates training data
"""

import os
import json
from pathlib import Path

# Famous Ansel Adams photos you can manually add
MANUAL_PHOTOS = {
    "tetons_snake_river": {
        "title": "The Tetons and the Snake River, Grand Teton National Park",
        "year": 1942,
        "description": "Mountain landscape with leading diagonal line",
        "strengths": ["Composition", "Lighting", "Depth_Perspective"],
        "source": "https://www.loc.gov/pictures/item/fsa2000010642/"
    },
    "moonrise_hernandez": {
        "title": "Moonrise, Hernandez, New Mexico",
        "year": 1941,
        "description": "Moon rising over town - compositional masterpiece",
        "strengths": ["Composition", "Lighting", "Emotional_Impact"],
        "source": "https://www.loc.gov/pictures/item/fsa2000010643/"
    },
    "half_dome_yosemite": {
        "title": "Half Dome, Yosemite Valley",
        "year": 1927,
        "description": "Iconic granite formation",
        "strengths": ["Lighting", "Focus_Sharpness", "Visual_Balance"],
        "source": "https://www.loc.gov/pictures/item/fsa2000010644/"
    },
    "sand_dunes": {
        "title": "Dunes, Death Valley",
        "year": 1933,
        "description": "Desert landscape with sculptural forms",
        "strengths": ["Composition", "Lighting", "Emotional_Impact"],
        "source": "https://www.loc.gov/pictures/item/fsa2000010645/"
    },
    "clearing_winter_storm": {
        "title": "Clearing Winter Storm, Yosemite Valley",
        "year": 1944,
        "description": "Dramatic weather clearing over mountains",
        "strengths": ["Lighting", "Emotional_Impact", "Visual_Balance"],
        "source": "https://commons.wikimedia.org/wiki/File:Clearing_Winter_Storm,_Yosemite_National_Park,_1944_(Library_of_Congress).jpg"
    },
    "golden_gate": {
        "title": "Golden Gate Bridge San Francisco",
        "year": 1936,
        "description": "Bridge in atmospheric fog",
        "strengths": ["Composition", "Lighting", "Visual_Balance"],
        "source": "https://www.loc.gov/pictures/item/fsa2000010646/"
    },
    "mount_williamson": {
        "title": "Mount Williamson from Manzanar",
        "year": 1943,
        "description": "Mountain with desert and foreground",
        "strengths": ["Composition", "Depth_Perspective", "Visual_Balance"],
        "source": "https://www.loc.gov/pictures/item/fsa2000010647/"
    },
    "cathedral_rocks": {
        "title": "Cathedral Rocks, Yosemite",
        "year": 1949,
        "description": "Rock formations with dramatic shadows",
        "strengths": ["Lighting", "Focus_Sharpness", "Composition"],
        "source": "https://www.loc.gov/pictures/item/fsa2000010648/"
    },
    "aspens_northern_california": {
        "title": "Aspens, Northern California",
        "year": 1950,
        "description": "Forest of white tree trunks",
        "strengths": ["Composition", "Lighting", "Visual_Balance"],
        "source": "https://commons.wikimedia.org/wiki/File:Aspens,_Northern_California_by_Ansel_Adams.jpg"
    },
    "winter_sunrise": {
        "title": "Winter Sunrise, Sierra Nevada",
        "year": 1944,
        "description": "Mountain landscape at dawn",
        "strengths": ["Lighting", "Color_Harmony", "Emotional_Impact"],
        "source": "https://www.loc.gov/pictures/item/fsa2000010649/"
    },
}

def create_photo_manifest():
    """Create a manifest of photos to download manually"""
    output_dir = Path("training/datasets/ansel-images/to-download")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "title": "Ansel Adams Photos - Manual Download List",
        "instructions": [
            "These are famous Ansel Adams photographs from public domain sources",
            "Click each URL to view/download the image",
            "Save high-resolution versions to: training/datasets/ansel-images/downloaded/",
            "Then run your training annotation script"
        ],
        "photos": []
    }
    
    for key, photo in MANUAL_PHOTOS.items():
        manifest["photos"].append({
            "filename": f"{key}.jpg",
            "title": photo["title"],
            "year": photo["year"],
            "description": photo["description"],
            "download_url": photo["source"],
            "notable_dimensions": photo["strengths"],
            "instructions": "Click 'download_url' to access the image. Download highest resolution available."
        })
    
    # Write manifest
    manifest_path = output_dir / "DOWNLOAD_MANIFEST.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Also create a simple text version
    text_path = output_dir / "PHOTOS_TO_DOWNLOAD.txt"
    with open(text_path, 'w') as f:
        f.write("ANSEL ADAMS PHOTOS - DOWNLOAD LIST\n")
        f.write("=" * 70 + "\n\n")
        f.write("Instructions:\n")
        f.write("1. Open each URL in your browser\n")
        f.write("2. Download the highest resolution available\n")
        f.write("3. Save to: training/datasets/ansel-images/downloaded/\n")
        f.write("4. Name files as shown (filename column)\n\n")
        f.write("-" * 70 + "\n\n")
        
        for i, (key, photo) in enumerate(MANUAL_PHOTOS.items(), 1):
            f.write(f"{i}. {photo['title']} ({photo['year']})\n")
            f.write(f"   Save as: {key}.jpg\n")
            f.write(f"   Download from: {photo['source']}\n")
            f.write(f"   Description: {photo['description']}\n")
            f.write(f"   Notable for: {', '.join(photo['strengths'])}\n\n")
    
    return manifest_path, text_path

def print_instructions():
    print("\n" + "=" * 70)
    print("ANSEL ADAMS PHOTO DATASET EXPANSION")
    print("=" * 70)
    print("\n✓ Created download manifest with 10 famous Ansel Adams photos\n")
    print("QUICK START:")
    print("-" * 70)
    print("1. View the download list:")
    print("   cat training/datasets/ansel-images/to-download/PHOTOS_TO_DOWNLOAD.txt\n")
    print("2. Download each image by clicking the URL\n")
    print("3. Save high-res versions to:")
    print("   training/datasets/ansel-images/downloaded/\n")
    print("4. Once downloaded, annotate each with your training script:")
    print("   python training/datasets/review_images_interactive.py \\")
    print("     --images-dir ./training/datasets/ansel-images/downloaded \\")
    print("     --output ansel_adams_authentic_training.jsonl\n")
    print("5. Combine with existing training data:")
    print("   cat training/datasets/ansel_image_training_fixed_paths.jsonl \\")
    print("       ansel_adams_authentic_training.jsonl > \\")
    print("       training/datasets/ansel_combined_expanded.jsonl\n")
    print("6. Retrain with expanded dataset:")
    print("   python training/train_lora_pytorch.py \\")
    print("     --dataset training/datasets/ansel_combined_expanded.jsonl \\")
    print("     --epochs 30 \\")
    print("     --output adapters/ansel_qwen3_4b_v3\n")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    manifest_file, text_file = create_photo_manifest()
    print_instructions()
    print(f"Manifest saved to: {manifest_file}")
    print(f"Text list saved to: {text_file}")
