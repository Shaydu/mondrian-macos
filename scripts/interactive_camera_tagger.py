#!/usr/bin/env python3
"""
Interactive Camera Book Passage Tagger

Extracts meaningful passages from "The Camera" and lets you
review/tag them with dimensions, add notes, and approve for import.

Usage:
    python scripts/interactive_camera_tagger.py
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OCR_FILE = PROJECT_ROOT / "training" / "ansel_ocr" / "ansel_adams_filtered_corpus.txt"
OUTPUT_FILE = PROJECT_ROOT / "training" / "book_passages" / "camera_pending.json"

DIMENSIONS = [
    "composition",
    "lighting",
    "focus_sharpness",
    "color_harmony",
    "depth_perspective",
    "visual_balance",
    "emotional_impact",
]

DIMENSION_DESCRIPTIONS = {
    "composition": "Arrangement, framing, rule of thirds, leading lines",
    "lighting": "Zone System, exposure, tonal values, contrast, previsualization",
    "focus_sharpness": "Depth of field, hyperfocal distance, f/64, critical focus",
    "color_harmony": "B&W value relationships, tonal harmony, gray scale, print tonality",
    "depth_perspective": "Spatial depth, foreground layers, perspective effects",
    "visual_balance": "Visual weight, symmetry/asymmetry, equilibrium",
    "emotional_impact": "Mood, feeling, expression, artistic intent, meaning",
}


def extract_camera_passages() -> List[str]:
    """Extract meaningful paragraphs from The Camera book."""
    if not OCR_FILE.exists():
        print(f"Error: {OCR_FILE} not found")
        return []
    
    with open(OCR_FILE, 'r') as f:
        text = f.read()
    
    # Find Camera book content
    if "The Camera" not in text:
        print("Error: 'The Camera' not found in OCR corpus")
        return []
    
    # Split into paragraphs and filter for meaningful ones
    paragraphs = text.split('\n\n')
    camera_start = None
    
    for i, para in enumerate(paragraphs):
        if "The Camera" in para and "Ansel Adams" in para:
            camera_start = i
            break
    
    if camera_start is None:
        print("Could not find Camera book section")
        return []
    
    # Extract passages (paragraphs that are substantive)
    passages = []
    for para in paragraphs[camera_start:]:
        # Clean up
        para = para.strip()
        para = re.sub(r'\s+', ' ', para)
        
        # Filter: meaningful length, not headers/metadata
        if (len(para) > 100 and 
            len(para) < 1000 and
            not para[0].isupper() or any(c.islower() for c in para[:50]),
            not any(x in para.lower() for x in ['page', 'chapter', 'contents', 'index', 'copyright'])):
            
            passages.append(para)
    
    return passages[:50]  # Limit to first 50 for review


def show_dimensions_menu():
    """Show available dimensions."""
    print("\n📊 Available Dimensions:")
    for i, dim in enumerate(DIMENSIONS, 1):
        print(f"  {i}. {dim}")
        print(f"     → {DIMENSION_DESCRIPTIONS[dim]}")


def get_user_dimensions() -> List[str]:
    """Let user select dimensions for a passage."""
    show_dimensions_menu()
    print("\nSelect dimensions (e.g., 1,3,7 or leave blank to skip):")
    
    while True:
        user_input = input("  > ").strip().lower()
        
        if user_input == '':
            return []
        
        try:
            indices = [int(x.strip()) - 1 for x in user_input.split(',')]
            dims = [DIMENSIONS[i] for i in indices if 0 <= i < len(DIMENSIONS)]
            if dims:
                return dims
        except (ValueError, IndexError):
            pass
        
        print("  Invalid input, try again")


def tag_passages():
    """Interactively tag Camera passages."""
    passages = extract_camera_passages()
    
    if not passages:
        print("No passages extracted from The Camera book")
        return
    
    print(f"\n📖 Found {len(passages)} passages from The Camera")
    print("=" * 80)
    
    approved = []
    skipped = 0
    
    for i, passage in enumerate(passages, 1):
        print(f"\n[{i}/{len(passages)}] " + "=" * 70)
        print(f"\nPassage text:")
        print(f"  {passage[:200]}..." if len(passage) > 200 else f"  {passage}")
        
        print(f"\nOptions:")
        print(f"  1. Approve with dimensions")
        print(f"  2. Add note and approve")
        print(f"  3. Skip this passage")
        print(f"  4. Quit")
        
        while True:
            choice = input("\nChoice (1-4): ").strip()
            
            if choice == '1':
                dims = get_user_dimensions()
                if dims:
                    approved.append({
                        "id": f"ansel_camera_passages_{i:04d}",
                        "passage_text": passage,
                        "dimensions": dims,
                        "notes": ""
                    })
                    print(f"✓ Approved with dimensions: {', '.join(dims)}")
                    break
                else:
                    print("No dimensions selected, skipping...")
                    skipped += 1
                    break
            
            elif choice == '2':
                dims = get_user_dimensions()
                if dims:
                    notes = input("\nAdd a note (optional): ").strip()
                    approved.append({
                        "id": f"ansel_camera_passages_{i:04d}",
                        "passage_text": passage,
                        "dimensions": dims,
                        "notes": notes
                    })
                    print(f"✓ Approved with note: {notes[:50]}...")
                    break
                else:
                    skipped += 1
                    break
            
            elif choice == '3':
                print("⊘ Skipped")
                skipped += 1
                break
            
            elif choice == '4':
                print("\n" + "=" * 80)
                print(f"\n✓ Tagged {len(approved)} passages, skipped {skipped}")
                save_approved(approved)
                return
            
            else:
                print("Invalid choice")


def save_approved(passages: List[Dict]):
    """Save approved passages to JSON file."""
    output = {
        "book": "camera",
        "advisor": "ansel",
        "passages": passages
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Saved {len(passages)} approved passages to:")
    print(f"  {OUTPUT_FILE}")
    print(f"\nNext step: Import to database with:")
    print(f"  python3 scripts/import_book_passages.py {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        tag_passages()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
