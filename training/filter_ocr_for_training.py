#!/usr/bin/env python3
"""
Filter OCR text to extract content relevant for training a photography evaluator.

This script reads OCR output files and filters them to keep only content
that's relevant for teaching the model to evaluate photographs in Ansel Adams' voice.

Relevant content includes:
- Visualization and interpretation philosophy
- Image quality and expressive elements
- Evaluating/critiquing photographs
- Tonal values and their emotional impact
- Compositional considerations
- What makes a "fine print"

Excluded content:
- Pure equipment specifications
- Chemical formulas and processing steps
- Darkroom equipment setup
- Page numbers, figure references only
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Tuple

# Keywords indicating relevant content (evaluation, interpretation, quality)
POSITIVE_KEYWORDS = [
    # Visualization and interpretation
    r'\bvisualiz',
    r'\binterpret',
    r'\bexpressive',
    r'\bexpression',
    r'\bcreativ',
    r'\bemotion',
    r'\baesthetic',
    r'\bartistic',
    r'\bbeauty',
    r'\bbeautiful',

    # Evaluation and quality
    r'\bfine print',
    r'\bquality',
    r'\bevaluat',
    r'\bcritiqu',
    r'\bjudg',
    r'\bassess',
    r'\bexcellen',
    r'\bsatisf',

    # Tonal and value discussion
    r'\btonal',
    r'\bvalue[s]?\b',
    r'\bcontrast',
    r'\bhighlight',
    r'\bshadow',
    r'\bblack[s]?\b',
    r'\bwhite[s]?\b',
    r'\bluminan',
    r'\bbrillian',
    r'\brichness',
    r'\bdepth\b',

    # Composition and form
    r'\bcomposit',
    r'\bform\b',
    r'\bshape',
    r'\btexture',
    r'\bdetail',
    r'\bbalance',
    r'\bharmony',
    r'\bunity',

    # Mood and feeling
    r'\bmood',
    r'\bfeeling',
    r'\batmospher',
    r'\bimpact',
    r'\bpower',
    r'\bsubtle',
    r'\bdelicate',
    r'\bdramatic',

    # Photographer's intent
    r'\bintent',
    r'\bvision',
    r'\bpurpose',
    r'\bmeaning',
    r'\bsignifican',
    r'\bmessage',

    # Self-reflection on his work
    r'\bI made',
    r'\bI used',
    r'\bI wanted',
    r'\bI felt',
    r'\bI tried',
    r'\bmy visuali',
    r'\bmy intent',
]

# Keywords indicating purely technical/equipment content to exclude
NEGATIVE_KEYWORDS = [
    # Equipment specs
    r'\bmilliliter',
    r'\bml\b',
    r'\bgram[s]?\b',
    r'\bounce[s]?\b',
    r'\bcc\b',
    r'\bformula',
    r'\bsolution',
    r'\bchemical',
    r'\bdeveloper\b',  # the chemical, not person
    r'\bfixer',
    r'\bhypo',
    r'\bpotassium',
    r'\bsodium',
    r'\bthiosulfate',

    # Processing steps only
    r'\bagitat',
    r'\btimer',
    r'\bthermometer',
    r'\btemperature.*degrees',
    r'\bwash.*minutes',
    r'\brinse',

    # Pure equipment
    r'\benlarg.*lens',
    r'\bsafelight',
    r'\btray[s]?\b',
    r'\btank[s]?\b',
    r'\beasel',
    r'\btrimmer',
    r'\bcutter',
    r'\bmanufacturer',
    r'\bmodel\s+\d',
    r'\bserial',
    r'\bwarranty',
    r'\bprice',
    r'\bdollar',

    # Page/figure references only
    r'^Figure \d',
    r'^See page',
    r'^See Figure',
    r'^Chapter \d+$',
    r'^\d+$',  # Just a number
]

# Strongly positive - paragraphs with these are almost always relevant
STRONG_POSITIVE = [
    r'fine print',
    r'expressive',
    r'visualiz',
    r'interpret.*image',
    r'emotional.*response',
    r'beauty.*photograph',
    r'quality.*print',
    r'tonal.*value',
    r'creative.*control',
]


def score_paragraph(text: str) -> Tuple[float, List[str]]:
    """
    Score a paragraph for relevance to photography evaluation training.

    Returns:
        Tuple of (score, list of matched keywords)
    """
    text_lower = text.lower()
    score = 0.0
    matches = []

    # Check strong positives first
    for pattern in STRONG_POSITIVE:
        if re.search(pattern, text_lower):
            score += 3.0
            matches.append(f"+3: {pattern}")

    # Check positive keywords
    for pattern in POSITIVE_KEYWORDS:
        if re.search(pattern, text_lower):
            score += 1.0
            matches.append(f"+1: {pattern}")

    # Check negative keywords
    for pattern in NEGATIVE_KEYWORDS:
        if re.search(pattern, text_lower):
            score -= 2.0
            matches.append(f"-2: {pattern}")

    # Bonus for first-person reflection (Adams speaking directly)
    if re.search(r'\bI\s+(have|had|made|used|felt|wanted|tried|think|believe)', text):
        score += 1.5
        matches.append("+1.5: first-person reflection")

    # Penalty for very short paragraphs (likely figure captions or fragments)
    if len(text) < 150:
        score -= 3.0
        matches.append("-3: short paragraph (<150 chars)")
    elif len(text) < 250:
        score -= 1.0
        matches.append("-1: short paragraph (<250 chars)")

    # Bonus for substantial paragraphs with good content
    if len(text) > 300 and score > 0:
        score += 1.0
        matches.append("+1: substantial length")

    return score, matches


def clean_text(text: str) -> str:
    """Clean OCR artifacts from text."""
    # Fix common OCR errors
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'["""]', '"', text)  # Normalize quotes
    text = re.sub(r"[''']", "'", text)  # Normalize apostrophes
    text = re.sub(r'—|–', '-', text)  # Normalize dashes
    text = text.strip()
    return text


def split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs."""
    # Split on double newlines or clear paragraph breaks
    paragraphs = re.split(r'\n\s*\n|\n(?=[A-Z])', text)
    # Clean each paragraph
    paragraphs = [clean_text(p) for p in paragraphs]
    # Filter empty paragraphs
    paragraphs = [p for p in paragraphs if p and len(p) > 20]
    return paragraphs


def process_file(filepath: Path, threshold: float = 2.0, verbose: bool = False) -> List[dict]:
    """
    Process a single OCR file and extract relevant paragraphs.

    Args:
        filepath: Path to the OCR text file
        threshold: Minimum score to include a paragraph
        verbose: Print scoring details

    Returns:
        List of dicts with 'text' and 'score' keys
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    paragraphs = split_into_paragraphs(content)
    results = []

    for para in paragraphs:
        score, matches = score_paragraph(para)

        if verbose and score != 0:
            print(f"\n--- Score: {score:.1f} ---")
            print(f"Text: {para[:100]}...")
            for m in matches[:5]:
                print(f"  {m}")

        # Only include paragraphs with substantial content (at least 200 chars)
        if score >= threshold and len(para) >= 200:
            results.append({
                'text': para,
                'score': score,
                'source': filepath.name
            })

    return results


def create_training_examples(paragraphs: List[dict]) -> List[dict]:
    """
    Convert filtered paragraphs into training examples.

    Creates Q&A pairs where Adams responds to photography questions.
    """
    questions = [
        "How do you evaluate the quality of a photograph?",
        "What makes a fine print?",
        "How should I think about tonal values in my work?",
        "What role does visualization play in photography?",
        "How do you interpret the emotional content of an image?",
        "What distinguishes an expressive photograph from a merely technical one?",
        "How do you approach the creative process in printing?",
        "What should I look for when critiquing my own work?",
        "How do contrast and tonal range affect the mood of a photograph?",
        "What is the relationship between technical quality and artistic expression?",
    ]

    examples = []
    for i, para in enumerate(paragraphs):
        # Rotate through questions
        question = questions[i % len(questions)]

        example = {
            "messages": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": para['text']}
            ],
            "source": para['source'],
            "score": para['score']
        }
        examples.append(example)

    return examples


def main():
    parser = argparse.ArgumentParser(
        description="Filter OCR text for photography evaluation training"
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="Directory containing OCR text files"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output JSONL file path"
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=2.0,
        help="Minimum score threshold (default: 2.0)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print scoring details"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only print statistics, don't write output"
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: Directory not found: {input_dir}")
        return 1

    # Process all text files
    all_paragraphs = []
    txt_files = sorted(input_dir.glob("*.txt"))

    print(f"Processing {len(txt_files)} files...")

    for filepath in txt_files:
        paragraphs = process_file(filepath, args.threshold, args.verbose)
        all_paragraphs.extend(paragraphs)

    print(f"\nFound {len(all_paragraphs)} relevant paragraphs (threshold={args.threshold})")

    if all_paragraphs:
        scores = [p['score'] for p in all_paragraphs]
        print(f"Score range: {min(scores):.1f} - {max(scores):.1f}")
        print(f"Average score: {sum(scores)/len(scores):.1f}")

    if args.stats_only:
        # Print sample of highest-scoring paragraphs
        print("\n--- Top 5 highest-scoring paragraphs ---")
        sorted_paras = sorted(all_paragraphs, key=lambda x: x['score'], reverse=True)
        for p in sorted_paras[:5]:
            print(f"\n[Score: {p['score']:.1f}] {p['source']}")
            print(p['text'][:300] + "...")
        return 0

    # Create training examples
    examples = create_training_examples(all_paragraphs)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_dir.parent / f"{input_dir.parent.name}_filtered_train.jsonl"

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nWrote {len(examples)} training examples to {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
