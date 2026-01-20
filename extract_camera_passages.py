#!/usr/bin/env python3
"""
Extract unique passages from "The Camera" book for citation/RAG.

This extracts ~30-50 meaningful passages from The Camera section of the corpus,
ensuring they're completely distinct from The Print passages.

Usage:
    python3 extract_camera_passages.py
    python3 extract_camera_passages.py --count 50  # Extract more passages
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Dict

# Project paths
PROJECT_ROOT = Path(__file__).parent
CORPUS_FILE = PROJECT_ROOT / "training" / "ansel_ocr" / "ansel_adams_filtered_corpus.txt"
OUTPUT_FILE = PROJECT_ROOT / "training" / "book_passages" / "camera_extracted.json"

# Keywords indicating relevant instructional content
INSTRUCTIONAL_KEYWORDS = [
    r'\bvisuali',
    r'\bcomposit',
    r'\blighting',
    r'\bexposure',
    r'\bfocus',
    r'\bdepth\s+of\s+field',
    r'\bsharpness',
    r'\blens',
    r'\baperture',
    r'\bsubject',
    r'\bperspective',
    r'\bbalance',
    r'\bemotional',
    r'\bimpact',
    r'\bexpression',
    r'\binterpret',
    r'\bevaluat',
    r'\bquality',
    r'\bconcept',
    r'\bprinciple',
    r'\btechnique',
    r'\bapproach',
]

def extract_camera_section(corpus_text: str) -> str:
    """Extract just The Camera book section from corpus, skipping preamble."""
    # The Camera appears first in the corpus (lines 1-8660 approx)
    # Skip preamble and start from Chapter 1 (around line 450)
    # The Print starts around line 8661
    lines = corpus_text.split('\n')
    
    camera_start = None
    chapter_start = None
    print_start = None
    
    for i, line in enumerate(lines):
        if line.strip() == 'The Camera' and camera_start is None:
            camera_start = i
        # Find Chapter 1 to skip preamble
        if line.strip() == 'Chapter 1' and camera_start is not None and chapter_start is None:
            chapter_start = i
        if line.strip() == 'The Print' and print_start is None:
            print_start = i
            break
    
    if camera_start is None:
        raise ValueError("Could not find 'The Camera' section in corpus")
    
    if chapter_start is None:
        # Fall back to camera_start if no Chapter 1 found
        chapter_start = camera_start
    
    if print_start is None:
        # Take everything after Chapter 1
        camera_lines = lines[chapter_start:]
    else:
        # Take only Camera chapters (skip preamble, stop before Print)
        camera_lines = lines[chapter_start:print_start]
    
    return '\n'.join(camera_lines)


def score_passage_relevance(text: str) -> float:
    """Score how relevant a passage is for instructional purposes."""
    text_lower = text.lower()
    
    # Priority keywords from user: Visualization, Composition, Lighting
    priority_boost = 0
    if 'visualiz' in text_lower:
        priority_boost += 5
    if 'composit' in text_lower:
        priority_boost += 5
    if 'lighting' in text_lower or 'light and' in text_lower or 'illuminat' in text_lower:
        priority_boost += 5
    
    # Count instructional keywords
    keyword_matches = sum(1 for kw in INSTRUCTIONAL_KEYWORDS if re.search(kw, text_lower))
    
    # Penalize if it's mostly technical specs or equipment
    technical_penalty = 0
    if any(x in text_lower for x in ['page ', 'figure ', 'plate ', 'chapter ', 'index']):
        technical_penalty = 5
    
    if any(x in text_lower for x in ['copyright', 'isbn', 'publisher', 'library of congress']):
        technical_penalty = 10
    
    return priority_boost + keyword_matches - technical_penalty


def extract_passages(camera_text: str, target_count: int = 40) -> List[str]:
    """Extract meaningful instructional passages from Camera text."""
    # Split into paragraphs
    paragraphs = camera_text.split('\n\n')
    
    # Filter and score paragraphs
    candidates = []
    
    for para in paragraphs:
        para = para.strip()
        para = re.sub(r'\s+', ' ', para)  # Normalize whitespace
        
        # Filter criteria
        if len(para) < 150:  # Too short
            continue
        if len(para) > 800:  # Too long (likely OCR error or multiple merged)
            continue
        
        # Check for meaningful content
        score = score_passage_relevance(para)
        if score < 1:  # Not instructional enough
            continue
        
        candidates.append({
            'text': para,
            'score': score,
            'length': len(para)
        })
    
    # Sort by relevance score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Take top N passages
    top_passages = [c['text'] for c in candidates[:target_count]]
    
    return top_passages


def create_output_json(passages: List[str]) -> Dict:
    """Create JSON structure for passages."""
    return {
        "book": "camera",
        "advisor": "ansel",
        "extracted_date": "2026-01-20",
        "total_extracted": len(passages),
        "status": "needs_tagging",
        "note": "Extracted from The Camera. Ready for dimension tagging.",
        "passages": [
            {
                "id": f"ansel_camera_extract_{i:04d}",
                "text": passage,
                "source": "the_camera",
                "status": "pending",
                "dimensions": [],
                "notes": "",
                "relevance_score": 0.0
            }
            for i, passage in enumerate(passages, 1)
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="Extract Camera book passages")
    parser.add_argument('--count', type=int, default=40,
                       help='Number of passages to extract (default: 40)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without saving')
    args = parser.parse_args()
    
    print("=" * 70)
    print("CAMERA PASSAGE EXTRACTOR")
    print("=" * 70)
    
    # Load corpus
    if not CORPUS_FILE.exists():
        print(f"❌ Error: Corpus file not found: {CORPUS_FILE}")
        return 1
    
    print(f"\n📖 Loading corpus from: {CORPUS_FILE}")
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        corpus_text = f.read()
    
    print(f"   Corpus size: {len(corpus_text):,} characters")
    
    # Extract Camera section
    print("\n🔍 Extracting Camera book section...")
    camera_text = extract_camera_section(corpus_text)
    print(f"   Camera section: {len(camera_text):,} characters")
    
    # Extract passages
    print(f"\n📝 Extracting top {args.count} instructional passages...")
    passages = extract_passages(camera_text, target_count=args.count)
    
    if not passages:
        print("❌ No passages extracted!")
        return 1
    
    print(f"   ✓ Extracted {len(passages)} passages")
    
    # Show samples
    print("\n" + "=" * 70)
    print("SAMPLE PASSAGES")
    print("=" * 70)
    
    for i, passage in enumerate(passages[:3], 1):
        print(f"\n[Passage {i}]")
        print(f"Length: {len(passage)} chars")
        print(f"Preview: {passage[:200]}...")
        print("-" * 70)
    
    if args.dry_run:
        print("\n✓ DRY RUN - No files written")
        print(f"\nWould save {len(passages)} passages to: {OUTPUT_FILE}")
        return 0
    
    # Create output
    output_data = create_output_json(passages)
    
    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(passages)} passages to: {OUTPUT_FILE}")
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("\n1. Review extracted passages:")
    print(f"   cat {OUTPUT_FILE}")
    print("\n2. Tag passages with dimensions:")
    print("   python3 scripts/interactive_camera_tagger.py")
    print("\n3. Once tagged, import to database:")
    print("   python3 scripts/import_book_passages.py")
    
    return 0


if __name__ == '__main__':
    exit(main())
