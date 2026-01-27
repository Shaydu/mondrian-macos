#!/usr/bin/env python3
"""
Interactive Camera Book Passage Tagger

Extracts meaningful passages from "The Camera" and lets you
review/tag them with dimensions, add notes, edit text, and approve for import.

Features:
- Edit passage text to fix OCR errors
- Auto-cleanup of common OCR issues
- Tag with dimensions
- Add notes

Usage:
    python scripts/interactive_camera_tagger.py
    python scripts/interactive_camera_tagger.py --input training/book_passages/camera_extracted.json
"""

import json
import re
import sys
import tempfile
import subprocess
import os
from pathlib import Path
from typing import List, Dict

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
OCR_FILE = PROJECT_ROOT / "training" / "ansel_ocr" / "ansel_adams_filtered_corpus.txt"
OUTPUT_FILE = PROJECT_ROOT / "training" / "book_passages" / "camera_pending.json"
INPUT_FILE = PROJECT_ROOT / "training" / "book_passages" / "camera_extracted.json"

# Available dimensions - matches dimensional_profiles schema (6 dimensions)
DIMENSIONS = [
    "composition",
    "lighting",
    "focus_sharpness",
    "depth_perspective",
    "visual_balance",
    "emotional_impact"
]


def show_dimensions_menu():
    """Display available dimensions."""
    print("\nAvailable dimensions:")
    for i, dim in enumerate(DIMENSIONS, 1):
        print(f"  {i}. {dim}")


def extract_camera_section(corpus_path: Path) -> List[str]:
    """Extract paragraphs from The Camera section (lines 1-8660)."""
    if not corpus_path.exists():
        print(f"❌ Corpus file not found: {corpus_path}")
        return []
    
    with open(corpus_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Camera section: lines 1-8660
    camera_lines = lines[:8660]
    camera_text = ''.join(camera_lines)
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in camera_text.split('\n\n') if p.strip()]
    return paragraphs


def score_passage_relevance(text: str) -> float:
    """Score passage relevance for photography instruction."""
    score = 0.0
    text_lower = text.lower()
    
    # High-value instructional keywords
    high_value_keywords = [
        'composition', 'exposure', 'light', 'lighting', 'visualization',
        'contrast', 'tonal', 'subject', 'technique', 'creative',
        'photographer', 'photograph', 'lens', 'camera', 'zone system'
    ]
    
    for keyword in high_value_keywords:
        if keyword in text_lower:
            score += 2.0
    
    # Avoid metadata/boilerplate
    avoid_phrases = [
        'copyright', 'published by', 'isbn', 'table of contents',
        'preface', 'acknowledgment', 'index', 'page'
    ]
    
    for phrase in avoid_phrases:
        if phrase in text_lower:
            score -= 5.0
    
    return score


def extract_camera_passages() -> List[str]:
    """Extract high-quality instructional passages from The Camera."""
    paragraphs = extract_camera_section(OCR_FILE)
    
    # Filter and score passages
    candidates = []
    for para in paragraphs:
        # Length filter: 150-800 chars
        if not (150 <= len(para) <= 800):
            continue
        
        score = score_passage_relevance(para)
        if score > 0:
            candidates.append((score, para))
    
    # Sort by score and take top 40
    candidates.sort(reverse=True, key=lambda x: x[0])
    passages = [text for score, text in candidates[:40]]
    
    return passages


def clean_ocr_text(text: str) -> str:
    """Auto-clean common OCR errors."""
    # Remove stray hyphens at line breaks
    text = re.sub(r'-\s+', '', text)
    
    # Fix common OCR mistakes
    text = text.replace('ﬁ', 'fi')
    text = text.replace('ﬂ', 'fl')
    text = text.replace('—', '-')
    text = text.replace('"', '"')
    text = text.replace('"', '"')
    text = text.replace(''', "'")
    text = text.replace(''', "'")
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    text = re.sub(r'([.,;:!?])([A-Z])', r'\1 \2', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def edit_text_in_editor(text: str) -> str:
    """Open text in user's editor for manual corrections."""
    # Get editor from environment or use nano as default
    editor = os.environ.get('EDITOR', 'nano')
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        temp_path = f.name
        f.write(text)
    
    try:
        # Open in editor
        subprocess.call([editor, temp_path])
        
        # Read back edited text
        with open(temp_path, 'r') as f:
            edited_text = f.read().strip()
        
        return edited_text
    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)


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
    # Check if we have an input file to load from
    if INPUT_FILE.exists():
        print(f"📂 Loading passages from: {INPUT_FILE}")
        with open(INPUT_FILE, 'r') as f:
            data = json.load(f)
            passages_data = data.get('passages', [])
            passages = [p['text'] for p in passages_data]
            print(f"   Loaded {len(passages)} passages")
    else:
        passages = extract_camera_passages()
        if not passages:
            print("No passages extracted from The Camera book")
            return
    
    print(f"\n📖 Found {len(passages)} passages from The Camera")
    print("=" * 80)
    
    approved = []
    skipped = 0
    
    for i, passage in enumerate(passages, 1):
        # Auto-clean OCR errors first
        cleaned_passage = clean_ocr_text(passage)
        current_text = cleaned_passage
        
        print(f"\n[{i}/{len(passages)}] " + "=" * 70)
        print(f"\nPassage text ({len(current_text)} chars):")
        print(f"\n{current_text}\n")
        
        print(f"\nOptions:")
        print(f"  1. Edit text (opens in editor)")
        print(f"  2. Auto-clean and continue")
        print(f"  3. Use as-is")
        print(f"  4. Skip this passage")
        print(f"  5. Save progress and quit")
        
        while True:
            choice = input("\nChoice (1-5): ").strip()
            
            if choice == '1':
                # Edit in text editor
                print(f"\n📝 Opening in editor (${os.environ.get('EDITOR', 'nano')})...")
                edited_text = edit_text_in_editor(current_text)
                if edited_text and edited_text != current_text:
                    current_text = edited_text
                    print(f"\n✓ Text updated ({len(current_text)} chars)")
                    print(f"\nEdited text:")
                    print(f"\n{current_text}\n")
                else:
                    print("\n⚠ No changes made")
                # Stay in options menu to allow dimension tagging
                
            elif choice == '2':
                # Already auto-cleaned, just proceed to dimensions
                print("\n✓ Using auto-cleaned text")
                break
                
            elif choice == '3':
                # Use original text
                current_text = passage
                print("\n✓ Using original text")
                break
            
            elif choice == '4':
                print("⊘ Skipped")
                skipped += 1
                break
            
            elif choice == '5':
                print("\n" + "=" * 80)
                print(f"\n✓ Progress saved: {len(approved)} passages tagged, {skipped} skipped")
                if approved:
                    save_approved(approved)
                return
            
            else:
                print("Invalid choice, try again")
                continue
        
        # If skipped or quit, continue to next
        if choice in ['4', '5']:
            continue
        
        # Now tag with dimensions
        dims = get_user_dimensions()
        if not dims:
            print("No dimensions selected, skipping...")
            skipped += 1
            continue
        
        # Optional note
        print("\nAdd a note? (press Enter to skip)")
        notes = input("  Note: ").strip()
        
        approved.append({
            "id": f"ansel_camera_filtered_train_{i:04d}",
            "text": current_text,
            "original_text": passage if current_text != passage else None,
            "source": "the_camera",
            "relevance_score": 10.0,
            "status": "approved",
            "dimensions": dims,
            "notes": notes
        })
        print(f"✓ Approved with dimensions: {', '.join(dims)}")
    
    # Save final results
    print("\n" + "=" * 80)
    print(f"\n✓ Completed: {len(approved)} passages tagged, {skipped} skipped")
    if approved:
        save_approved(approved)


def save_approved(passages: List[Dict]):
    """Save approved passages to JSON file."""
    output = {
        "book": "camera",
        "advisor": "ansel",
        "processed_date": "2026-01-20",
        "total_approved": len(passages),
        "passages": passages
    }
    
    # Save to camera_approved.json (ready for import)
    approved_file = PROJECT_ROOT / "training" / "book_passages" / "camera_approved.json"
    with open(approved_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(passages)} approved passages to:")
    print(f"  {approved_file}")
    print(f"\nNext steps:")
    print(f"  1. Review: cat {approved_file}")
    print(f"  2. Import: python3 scripts/import_book_passages.py")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tag Camera book passages")
    parser.add_argument('--input', type=str, help='Input JSON file with extracted passages')
    args = parser.parse_args()
    
    if args.input:
        INPUT_FILE = Path(args.input)
    
    try:
        tag_passages()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        print("Progress has been saved if you chose option 5")
        sys.exit(0)
