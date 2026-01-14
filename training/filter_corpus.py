#!/usr/bin/env python3
"""
Filter Ansel Adams corpus to keep only content applicable to both digital and film.

Keeps content about:
- Composition, framing, visual design
- Lighting, exposure concepts (not film-specific exposure)
- Sharpness, focus, depth of field
- Lens optics
- Subject isolation, perspective
- Emotional impact, artistic vision

Removes content about:
- Film development, darkroom chemistry
- Specific film stocks, developers
- Enlarger techniques
- Zone System specifics for film
- Print washing, fixing, toning
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CORPUS_PATH = PROJECT_ROOT / "training" / "ansel_ocr" / "ansel_adams_training_corpus.txt"
OUTPUT_PATH = PROJECT_ROOT / "training" / "ansel_ocr" / "ansel_adams_filtered_corpus.txt"

# Keywords that indicate film-specific content to remove
FILM_SPECIFIC_KEYWORDS = [
    r'\bdeveloper\b', r'\bdevelopment\b', r'\bdeveloping\b',
    r'\bfixer\b', r'\bfixing\b', r'\bhypo\b',
    r'\benlarg(er|ing|ement)\b',
    r'\bdarkroom\b', r'\bsafelight\b',
    r'\bnegative\b', r'\bnegatives\b',
    r'\bprint\s+wash', r'\bwashing\b.*\bprint',
    r'\btoning\b', r'\bselenium\b', r'\bgold\s+toner\b',
    r'\bchemistry\b', r'\bchemical\b',
    r'\b(d-76|hc-110|rodinal|xtol)\b',
    r'\bgrain\b.*\bfilm\b', r'\bfilm\s+grain\b',
    r'\bast\s*\d+\b',  # ASA film speeds
    r'\biso\s+\d+\s+film\b',
    r'\bpanchromatic\b', r'\borthochromatic\b',
    r'\bemulsion\b',
    r'\bcontact\s+print\b', r'\bcontact\s+sheet\b',
    r'\beasel\b',  # enlarger easel
    r'\bdodging\b', r'\bburning\b',  # darkroom techniques
    r'\btest\s+strip\b',
    r'\bsilver\s+(gelatin|halide)\b',
    r'\bresin[- ]coated\b', r'\brc\s+paper\b',
    r'\bfiber[- ]based?\b',
]

# Keywords that indicate content we WANT to keep
KEEP_KEYWORDS = [
    r'\bcomposition\b', r'\bcompose\b', r'\bframing\b',
    r'\blighting\b', r'\blight\b', r'\bshadow\b', r'\bhighlight\b',
    r'\bsharpness\b', r'\bfocus\b', r'\bdepth\s+of\s+field\b',
    r'\blens\b', r'\baperture\b', r'\bf[/-]?\d', r'\bf\s*stop\b',
    r'\bshutter\b', r'\bexposure\b',
    r'\bsubject\b', r'\bisolation\b',
    r'\bperspective\b', r'\bdepth\b',
    r'\bbalance\b', r'\bharmony\b', r'\bcontrast\b',
    r'\bemotional\b', r'\bimpact\b', r'\bexpression\b',
    r'\bvisualization\b', r'\bprevisualization\b',
    r'\bscale\b', r'\btone\b', r'\btonal\b',
    r'\bcamera\b', r'\btripod\b', r'\bviewfinder\b',
    r'\blandscape\b', r'\bportrait\b', r'\bnature\b',
    r'\bartist\b', r'\bphotograph\b', r'\bimage\b',
]


def is_film_specific(text: str) -> bool:
    """Check if text contains primarily film-specific content."""
    text_lower = text.lower()

    # Count film-specific keywords
    film_count = sum(1 for kw in FILM_SPECIFIC_KEYWORDS if re.search(kw, text_lower))

    # Count universal/keep keywords
    keep_count = sum(1 for kw in KEEP_KEYWORDS if re.search(kw, text_lower))

    # If more film-specific than universal keywords, it's probably film-specific
    # Also filter if any strong film indicators even with other content
    strong_film = any(re.search(kw, text_lower) for kw in [
        r'\bdeveloper\b', r'\bdarkroom\b', r'\benlarg', r'\bfixer\b',
        r'\btoning\b', r'\bwashing\s+(print|film)', r'\bchemistry\b'
    ])

    if strong_film and keep_count < 3:
        return True

    if film_count > keep_count and film_count >= 2:
        return True

    return False


def filter_corpus():
    """Filter the corpus to remove film-specific content."""
    print(f"Reading corpus from: {CORPUS_PATH}")

    with open(CORPUS_PATH) as f:
        lines = f.readlines()

    print(f"Original corpus: {len(lines)} lines")

    # Process in chunks (paragraphs separated by blank lines)
    chunks = []
    current_chunk = []

    for line in lines:
        if line.strip():
            current_chunk.append(line)
        else:
            if current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = []
            chunks.append("\n")  # Keep paragraph breaks

    if current_chunk:
        chunks.append("".join(current_chunk))

    print(f"Identified {len([c for c in chunks if c.strip()])} text chunks")

    # Filter chunks
    kept_chunks = []
    removed_count = 0

    for chunk in chunks:
        if not chunk.strip():
            kept_chunks.append(chunk)
            continue

        if is_film_specific(chunk):
            removed_count += 1
        else:
            kept_chunks.append(chunk)

    print(f"Removed {removed_count} film-specific chunks")

    # Write filtered corpus
    filtered_text = "".join(kept_chunks)
    filtered_lines = filtered_text.count('\n')

    with open(OUTPUT_PATH, 'w') as f:
        f.write(filtered_text)

    print(f"Filtered corpus: ~{filtered_lines} lines")
    print(f"Saved to: {OUTPUT_PATH}")

    # Also update the main corpus
    with open(CORPUS_PATH, 'w') as f:
        f.write(filtered_text)
    print(f"Updated main corpus at: {CORPUS_PATH}")

    return filtered_text


if __name__ == "__main__":
    filter_corpus()
