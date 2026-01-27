#!/usr/bin/env python3
"""
Interactive Book Passage Dimension Tagger

Reviews existing filtered book passages, auto-tags with dimensions,
and allows human review/approval for RAG integration.

This tool helps curate Ansel Adams' book content (The Print, The Camera)
into dimension-specific passages that can be used for:
1. RAG retrieval - cite relevant passages for weak dimensions
2. Training data - dimension-specific vocabulary for LoRA
3. Prompt augmentation - authentic Ansel voice per dimension

Usage:
    python scripts/tag_book_passages.py                    # Start fresh with The Print
    python scripts/tag_book_passages.py --book camera      # Process The Camera
    python scripts/tag_book_passages.py --resume           # Resume previous session
    python scripts/tag_book_passages.py --stats            # Show statistics
    python scripts/tag_book_passages.py --min-score 8      # Only high-quality passages
    python scripts/tag_book_passages.py --export           # Export for database import
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATASETS_DIR = PROJECT_ROOT / "training" / "datasets"
OUTPUT_DIR = PROJECT_ROOT / "training" / "book_passages"

# Source files - filtered JSONL from OCR processing
SOURCES = {
    "print": DATASETS_DIR / "ansel_print_filtered_train.jsonl",
    "camera": DATASETS_DIR / "ansel_text_train.jsonl",
}

# The 8 dimensions we use for photo evaluation
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

# Dimension-specific keyword patterns for auto-tagging
# These help identify which dimension(s) a passage is relevant to
DIMENSION_KEYWORDS = {
    "composition": [
        r'\bcomposit', r'\barrang', r'\bframe\b', r'\bframing', r'\brule of thirds',
        r'\bgolden', r'\bplacement', r'\borganiz', r'\bstructure', r'\bleading line',
        r'\bforeground', r'\bbackground', r'\bmiddle.?ground', r'\bformat\b',
        r'\bvertical', r'\bhorizontal', r'\bcrop', r'\bedge', r'\bborder',
        r'\bnegative space', r'\bvisual.?flow', r'\bwhere to stand', r'\bpoint of view',
        r'\bimage management', r'\boptical image',
    ],
    "lighting": [
        r'\bzone system', r'\bzone [IVX0-9]+', r'\btonal', r'\bexposure',
        r'\bhighlight', r'\bshadow', r'\bcontrast', r'\bluminan', r'\bbrillian',
        r'\blight\b', r'\blighting', r'\billuminat', r'\bmeter', r'\bf.?stop',
        r'\baperture', r'\bshutter', r'\bblack\b', r'\bwhite\b', r'\bgray',
        r'\bdensity', r'\bvalue[s]?\b', r'\brange\b', r'\bdynamic range',
        r'\bprevisuali', r'\bvisuali', r'\bnegative\b', r'\bprint.*tone',
        r'\bluminance', r'\breflectance', r'\bbrightness',
    ],
    "focus_sharpness": [
        r'\bfocus', r'\bsharp', r'\bsoft\b', r'\bblur', r'\bdepth of field',
        r'\bdof\b', r'\bhyperfocal', r'\bcircle of confusion', r'\bf/64', r'\bf\.?64',
        r'\btripod', r'\bcamera shake', r'\bresolution', r'\bacuity',
        r'\bplane of focus', r'\bcritical focus', r'\bdiffraction',
        r'\benlarg', r'\bacutance', r'\bdetail\b',
    ],
    "color_harmony": [
        r'\bcolor\b', r'\bhue\b', r'\bsaturat', r'\bwarm\b', r'\bcool\b',
        r'\btone\b', r'\btonal.?harmony', r'\bpalette', r'\bmonochrom',
        r'\bblack.?and.?white', r'\bgray.?scale', r'\bvalue.?scale',
        r'\bprint.*tone', r'\bpaper.*tone', r'\bsepia', r'\bsplit.?ton',
        r'\bprint color', r'\brelationship of values',
    ],
    "subject_isolation": [
        r'\bsubject\b', r'\bisolat', r'\bseparation', r'\bstand.?out',
        r'\bemphasi', r'\bdominant', r'\bfocal.?point', r'\bcenter of interest',
        r'\bhierarchy', r'\bsimplif', r'\bminimal', r'\bdistracti', r'\bclutter',
        r'\bselectiv', r'\bwhat.*photograph.*of',
    ],
    "depth_perspective": [
        r'\bdepth\b', r'\bperspectiv', r'\bthree.?dimension', r'\b3.?d\b',
        r'\bforeground', r'\breceding', r'\bdistance', r'\bnear.*far',
        r'\bplane[s]?\b', r'\blayer', r'\bconvergence', r'\bvanishing',
        r'\bwide.?angle', r'\btelephoto', r'\bcompression', r'\bscale\b',
        r'\bspatial', r'\boverlap', r'\batmospheric', r'\baerial',
    ],
    "visual_balance": [
        r'\bbalanc', r'\bweight\b', r'\bvisual.?weight', r'\bsymmetr',
        r'\basymmetr', r'\bequilibrium', r'\btension', r'\bharmony',
        r'\bunity', r'\bdistribution', r'\bproportion', r'\bratio',
        r'\bgolden.?ratio', r'\bgolden.?mean', r'\bdynamic.?symmetry',
    ],
    "emotional_impact": [
        r'\bemotion', r'\bfeel', r'\bmood', r'\batmospher', r'\bspirit',
        r'\bsoul', r'\bpower', r'\bimpact', r'\bmov(?:e|ing)\b', r'\btouch',
        r'\blove', r'\bbeaut', r'\bwonder', r'\bawe\b', r'\breverence',
        r'\bsublime', r'\btranscend', r'\bexpressive', r'\bexpression',
        r'\bintent', r'\bvision\b', r'\bpurpose', r'\bmeaning', r'\bsignifican',
        r'\bconnect', r'\bintimate', r'\bpersonal', r'\bexperience',
        r'\bartist', r'\bcreativ', r'\bfine print', r'\bsatisf',
    ],
}

# Dimension descriptions for the help menu
DIMENSION_DESCRIPTIONS = {
    "composition": "Arrangement, framing, rule of thirds, leading lines, foreground/background relationships",
    "lighting": "Zone System, exposure, tonal values, highlights/shadows, contrast, previsualization",
    "focus_sharpness": "Depth of field, hyperfocal distance, f/64, tripod use, critical focus, sharpness",
    "color_harmony": "Tonal harmony, B&W value relationships, gray scale, print tonality",
    "subject_isolation": "Subject emphasis, separation from background, visual hierarchy, simplification",
    "depth_perspective": "Spatial depth, foreground layers, perspective, wide-angle/telephoto effects",
    "visual_balance": "Visual weight distribution, symmetry/asymmetry, equilibrium, golden ratio",
    "emotional_impact": "Mood, feeling, expression, artistic intent, meaning, fine print philosophy",
}


def clean_ocr_text(text: str) -> str:
    """
    Clean common OCR artifacts to make passages readable for users.
    These passages will be cited in LLM output and displayed to users.
    """
    # Fix hyphenated line breaks: "pro- cess" -> "process"
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    # Fix common OCR spacing issues
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)  # Space before punctuation
    
    # Fix common OCR character substitutions
    text = text.replace('{', '(').replace('}', ')')  # {craft} -> (craft)
    text = text.replace('~', '-')
    text = text.replace('â€"', '—')  # Em dash encoding
    text = text.replace('â€™', "'")  # Apostrophe encoding
    text = text.replace('â€œ', '"').replace('â€', '"')  # Quote encoding
    
    # Remove multiple punctuation
    text = re.sub(r'([.,;:!?])\1+', r'\1', text)
    
    # Fix common number/letter OCR errors in common words
    text = re.sub(r'\b1oo\b', '100', text)  # 1oo -> 100
    text = re.sub(r'\b196o\b', '1960', text)  # 196o -> 1960
    
    # Remove metadata artifacts
    metadata_patterns = [
        r'ISBN[:\s]+[\d-]+',
        r'Copyright ©.*?\d{4}',
        r'All rights reserved.*?publisher\.',
        r'Library of Congress.*?catalog',
        r'Printed in \w+',
        r'Visit our Web site at.*?\.com',
        r'Time Warner Book Group',
        r'LITTLE, BROWN AND COMPANY',
    ]
    for pattern in metadata_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Clean up any resulting multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def auto_tag_dimensions(text: str) -> List[Tuple[str, int]]:
    """
    Auto-detect dimensions with relevance scores based on keyword matches.
    Returns list of (dimension, score) sorted by score descending.
    """
    text_lower = text.lower()
    scores = {}

    for dimension, patterns in DIMENSION_KEYWORDS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            score += len(matches)
        if score > 0:
            scores[dimension] = score

    # Sort by score descending
    sorted_dims = sorted(scores.items(), key=lambda x: -x[1])
    return sorted_dims


def load_jsonl(filepath: Path, min_score: float = 5.0) -> List[Dict]:
    """Load JSONL file and filter by relevance score."""
    passages = []

    if not filepath.exists():
        print(f"Warning: {filepath} not found")
        return []

    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            try:
                entry = json.loads(line.strip())
                score = entry.get('score', 0)

                if score >= min_score:
                    # Extract the assistant's response (Ansel's words)
                    messages = entry.get('messages', [])
                    text = ""
                    for msg in messages:
                        if msg.get('role') == 'assistant':
                            text = msg.get('content', '')
                            break

                    if text and len(text) > 50:
                        # Clean OCR artifacts before storing
                        cleaned_text = clean_ocr_text(text)
                        
                        # Skip if cleaning removed too much content
                        if len(cleaned_text) < 50:
                            continue
                        
                        passages.append({
                            'id': f"{filepath.stem}_{i:04d}",
                            'text': cleaned_text,
                            'original_text': text,  # Keep original for reference
                            'source': entry.get('source', filepath.stem),
                            'relevance_score': score,
                            'status': 'pending',
                            'dimensions': [],
                            'notes': '',
                        })
            except json.JSONDecodeError:
                continue

    return passages


def word_wrap(text: str, width: int = 78) -> str:
    """Word wrap text to specified width."""
    words = text.split()
    lines = []
    line = ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return "\n".join(lines)


def display_passage(passage: Dict, index: int, total: int):
    """Display a passage for review with auto-detected dimensions."""
    print("\n" + "=" * 80)
    print(f"PASSAGE {index + 1} of {total}  |  ID: {passage['id']}  |  Relevance: {passage['relevance_score']:.1f}")
    print(f"Source: {passage['source']}")
    print("=" * 80)

    # Auto-detect dimensions
    auto_dims = auto_tag_dimensions(passage['text'])

    if auto_dims:
        print("\n📊 AUTO-DETECTED DIMENSIONS (by keyword matches):")
        for dim, score in auto_dims[:5]:
            bar = "█" * min(score, 20)
            print(f"   {dim:20s} {bar} ({score})")
    else:
        print("\n📊 No dimensions auto-detected (general/philosophical content)")

    current = passage.get('dimensions', [])
    if current:
        print(f"\n📝 CURRENT TAGS: {', '.join(current)}")

    print("\n" + "-" * 80)
    print(word_wrap(passage['text']))
    print("-" * 80)


def display_dimension_menu():
    """Display dimension selection menu."""
    print("\nDIMENSIONS:")
    for i, dim in enumerate(DIMENSIONS, 1):
        print(f"  {i}. {dim}")
    print("  0. Clear all dimensions")
    print("\nEnter numbers separated by commas (e.g., '1,2,5')")
    print("Or press Enter to accept auto-detected dimensions")


def get_user_action() -> str:
    """Get user action for current passage."""
    print("\nACTIONS:")
    print("  [a] Approve with auto-detected dimensions")
    print("  [d] Set dimensions manually, then approve")
    print("  [e] Edit text to fix OCR errors")
    print("  [s] Skip (not relevant for any dimension)")
    print("  [n] Add notes to this passage")
    print("  [v] View passage again")
    print("  [b] Go back one passage")
    print("  [q] Quit and save progress")
    print("  [?] Show dimension descriptions")

    while True:
        action = input("\nAction: ").strip().lower()
        if action in ['a', 'd', 'e', 's', 'n', 'v', 'b', 'q', '?']:
            return action
        print("Invalid. Enter a, d, e, s, n, v, b, q, or ?")


def select_dimensions(passage: Dict) -> List[str]:
    """Let user select dimensions manually."""
    display_dimension_menu()

    # Get auto-detected as default
    auto_dims = auto_tag_dimensions(passage['text'])
    auto_list = [d[0] for d in auto_dims[:3]]  # Top 3

    default_str = ','.join(auto_list) if auto_list else 'none'

    while True:
        sel = input(f"\nDimensions [default: {default_str}]: ").strip()

        # Empty = accept auto-detected
        if sel == '':
            return auto_list

        # 'k' = keep auto-detected (legacy)
        if sel.lower() == 'k':
            return auto_list

        # '0' = clear all
        if sel == '0':
            return []

        try:
            indices = [int(x.strip()) for x in sel.split(',')]
            dims = []
            for idx in indices:
                if 1 <= idx <= len(DIMENSIONS):
                    dims.append(DIMENSIONS[idx - 1])
                else:
                    print(f"Invalid dimension number: {idx}")
            if dims:
                return dims
            print("No valid dimensions. Try again.")
        except ValueError:
            print("Invalid input. Enter numbers like '1,2,5' or press Enter for default")


def show_dimension_help():
    """Show dimension descriptions."""
    print("\n" + "=" * 80)
    print("DIMENSION REFERENCE - What content belongs to each dimension?")
    print("=" * 80)
    for i, dim in enumerate(DIMENSIONS, 1):
        print(f"\n{i}. {dim.upper()}")
        print(f"   {DIMENSION_DESCRIPTIONS[dim]}")
    print("\n" + "=" * 80)
    input("Press Enter to continue...")


def save_progress(passages: List[Dict], book: str):
    """Save current progress to JSON files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    approved = [p for p in passages if p['status'] == 'approved']
    pending = [p for p in passages if p['status'] == 'pending']
    skipped = [p for p in passages if p['status'] == 'skipped']

    # Save approved passages (main output)
    approved_file = OUTPUT_DIR / f"{book}_approved.json"
    with open(approved_file, 'w') as f:
        json.dump({
            'book': book,
            'advisor': 'ansel',
            'processed_date': datetime.now().isoformat(),
            'total_approved': len(approved),
            'passages': approved
        }, f, indent=2)

    # Save pending for resume capability
    pending_file = OUTPUT_DIR / f"{book}_pending.json"
    with open(pending_file, 'w') as f:
        json.dump({
            'pending': pending,
            'skipped_count': len(skipped),
        }, f, indent=2)

    print(f"\n✓ Progress saved:")
    print(f"  Approved: {len(approved)} → {approved_file.name}")
    print(f"  Pending:  {len(pending)}")
    print(f"  Skipped:  {len(skipped)}")

    return approved_file


def load_progress(book: str) -> Optional[List[Dict]]:
    """Load previous session if it exists."""
    pending_file = OUTPUT_DIR / f"{book}_pending.json"
    approved_file = OUTPUT_DIR / f"{book}_approved.json"

    passages = []

    # Load approved first (to preserve them)
    if approved_file.exists():
        with open(approved_file) as f:
            data = json.load(f)
            passages.extend(data.get('passages', []))

    # Load pending
    if pending_file.exists():
        with open(pending_file) as f:
            data = json.load(f)
            passages.extend(data.get('pending', []))

    return passages if passages else None


def interactive_review(passages: List[Dict], book: str):
    """Main interactive review loop."""
    pending = [p for p in passages if p['status'] == 'pending']

    if not pending:
        approved = len([p for p in passages if p['status'] == 'approved'])
        print(f"\n✅ All done! {approved} passages approved for '{book}'")
        print(f"   Output: {OUTPUT_DIR / f'{book}_approved.json'}")
        return

    print(f"\n📚 Reviewing {len(pending)} passages from '{book.upper()}'")
    print("Each passage will be auto-tagged. You approve, modify, or skip.\n")
    print("TIP: Press 'a' to quickly approve with auto-detected dimensions")
    print("     Press 'd' to manually select dimensions")
    print("     Press '?' for dimension descriptions\n")

    i = 0
    while i < len(pending):
        passage = pending[i]
        display_passage(passage, i, len(pending))

        action = get_user_action()

        if action == 'a':  # Approve with auto-detected
            auto_dims = [d[0] for d in auto_tag_dimensions(passage['text'])[:3]]
            passage['dimensions'] = auto_dims if auto_dims else ['emotional_impact']
            passage['status'] = 'approved'
            print(f"✓ Approved: {', '.join(passage['dimensions'])}")
            i += 1

        elif action == 'd':  # Manual dimensions
            passage['dimensions'] = select_dimensions(passage)
            if passage['dimensions']:
                passage['status'] = 'approved'
                print(f"✓ Approved: {', '.join(passage['dimensions'])}")
                i += 1
            else:
                print("No dimensions selected. Marking as skipped.")
                passage['status'] = 'skipped'
                i += 1
        
        elif action == 'e':  # Edit text (for fixing OCR issues)
            print("\nCurrent text:")
            print(word_wrap(passage['text']))
            print("\nEnter corrected text (or 'k' to keep):")
            print("(Press Ctrl+D or enter blank line twice to finish)")
            
            lines = []
            try:
                while True:
                    line = input()
                    if line.lower() == 'k':
                        break
                    if line == '' and lines and lines[-1] == '':
                        break
                    lines.append(line)
            except EOFError:
                pass
            
            if lines and lines != ['k']:
                new_text = ' '.join(lines).strip()
                if new_text:
                    passage['text'] = new_text
                    print("✓ Text updated")
            else:
                print("Text unchanged")

        elif action == 's':  # Skip
            passage['status'] = 'skipped'
            print("⨉ Skipped (not dimension-relevant)")
            i += 1

        elif action == 'n':  # Notes
            passage['notes'] = input("Notes: ").strip()
            print(f"Added notes: {passage['notes']}")

        elif action == 'v':  # View again
            continue  # Will redisplay

        elif action == 'b':  # Back
            if i > 0:
                i -= 1
                # Reset previous passage to pending
                pending[i]['status'] = 'pending'
                pending[i]['dimensions'] = []
                print("← Going back one passage")
            else:
                print("Already at first passage")

        elif action == '?':  # Help
            show_dimension_help()

        elif action == 'q':  # Quit
            save_progress(passages, book)
            print("\nProgress saved. Run with --resume to continue.")
            return

        # Auto-save every 10 passages
        if i > 0 and i % 10 == 0:
            save_progress(passages, book)

    # Final save
    save_progress(passages, book)

    approved = len([p for p in passages if p['status'] == 'approved'])
    skipped = len([p for p in passages if p['status'] == 'skipped'])
    print(f"\n🎉 Review complete!")
    print(f"   Approved: {approved}")
    print(f"   Skipped:  {skipped}")
    print(f"   Output:   {OUTPUT_DIR / f'{book}_approved.json'}")


def show_stats():
    """Show statistics of processed passages."""
    print("\n" + "=" * 60)
    print("BOOK PASSAGE TAGGING STATISTICS")
    print("=" * 60)

    total_approved = 0
    total_by_dim = {d: 0 for d in DIMENSIONS}

    for book in ['print', 'camera']:
        approved_file = OUTPUT_DIR / f"{book}_approved.json"
        pending_file = OUTPUT_DIR / f"{book}_pending.json"

        if approved_file.exists():
            with open(approved_file) as f:
                data = json.load(f)
                passages = data.get('passages', [])
                total_approved += len(passages)

                print(f"\n📚 {book.upper()}: {len(passages)} approved")

                dim_counts = {d: 0 for d in DIMENSIONS}
                for p in passages:
                    for d in p.get('dimensions', []):
                        if d in dim_counts:
                            dim_counts[d] += 1
                            total_by_dim[d] += 1

                print("   By dimension:")
                for dim, count in sorted(dim_counts.items(), key=lambda x: -x[1]):
                    if count > 0:
                        bar = "█" * min(count, 30)
                        print(f"     {dim:20s} {bar} ({count})")

                # Show pending count if exists
                if pending_file.exists():
                    with open(pending_file) as pf:
                        pdata = json.load(pf)
                        pending = len(pdata.get('pending', []))
                        if pending > 0:
                            print(f"   Pending: {pending}")

    if total_approved > 0:
        print(f"\n{'=' * 60}")
        print(f"TOTAL APPROVED: {total_approved}")
        print("\nCombined by dimension:")
        for dim, count in sorted(total_by_dim.items(), key=lambda x: -x[1]):
            if count > 0:
                pct = count / total_approved * 100
                bar = "█" * min(int(pct / 2), 30)
                print(f"  {dim:20s} {bar} ({count}, {pct:.0f}%)")
    else:
        print("\nNo passages have been processed yet.")
        print("Run: python scripts/tag_book_passages.py --book print")


def export_for_database():
    """Export approved passages in format ready for database import."""
    all_passages = []

    for book in ['print', 'camera']:
        approved_file = OUTPUT_DIR / f"{book}_approved.json"
        if approved_file.exists():
            with open(approved_file) as f:
                data = json.load(f)
                for p in data.get('passages', []):
                    all_passages.append({
                        'id': p['id'],
                        'advisor_id': 'ansel',
                        'book_title': f"The {book.title()}",
                        'passage_text': p['text'],
                        'dimension_tags': json.dumps(p['dimensions']),
                        'relevance_score': p.get('relevance_score', 0),
                        'notes': p.get('notes', ''),
                    })

    if all_passages:
        export_file = OUTPUT_DIR / "ansel_passages_for_db.json"
        with open(export_file, 'w') as f:
            json.dump(all_passages, f, indent=2)
        print(f"\n✓ Exported {len(all_passages)} passages to {export_file}")
        print("  Ready for database import with embeddings computation")
    else:
        print("\nNo approved passages to export. Run tagging first.")


def main():
    parser = argparse.ArgumentParser(
        description="Tag Ansel Adams book passages by dimension for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/tag_book_passages.py                  # Start with The Print
  python scripts/tag_book_passages.py --book camera    # Process The Camera
  python scripts/tag_book_passages.py --resume         # Continue previous session
  python scripts/tag_book_passages.py --min-score 8    # Only high-quality passages
  python scripts/tag_book_passages.py --stats          # View progress statistics
  python scripts/tag_book_passages.py --export         # Export for database
        """
    )
    parser.add_argument('--book', choices=['print', 'camera'], default='print',
                        help="Which book to process (default: print)")
    parser.add_argument('--resume', action='store_true',
                        help="Resume previous tagging session")
    parser.add_argument('--stats', action='store_true',
                        help="Show tagging statistics")
    parser.add_argument('--export', action='store_true',
                        help="Export approved passages for database import")
    parser.add_argument('--min-score', type=float, default=5.0,
                        help="Minimum relevance score filter (default: 5.0)")

    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.stats:
        show_stats()
        return

    if args.export:
        export_for_database()
        return

    book = args.book
    source_file = SOURCES.get(book)

    if not source_file or not source_file.exists():
        print(f"Error: Source file not found: {source_file}")
        print(f"Available sources: {list(SOURCES.keys())}")
        return

    if args.resume:
        passages = load_progress(book)
        if passages:
            pending = len([p for p in passages if p['status'] == 'pending'])
            approved = len([p for p in passages if p['status'] == 'approved'])
            print(f"Resuming session: {approved} approved, {pending} pending")
        else:
            print("No saved progress found. Starting fresh.")
            passages = load_jsonl(source_file, args.min_score)
    else:
        passages = load_jsonl(source_file, args.min_score)
        print(f"Loaded {len(passages)} passages from {source_file.name}")
        print(f"(filtered to relevance score >= {args.min_score})")

    if not passages:
        print("No passages to review!")
        return

    interactive_review(passages, book)


if __name__ == "__main__":
    main()
