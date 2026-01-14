#!/usr/bin/env python3
"""
Convert Ansel Adams OCR text corpus into training examples for LoRA fine-tuning.

Creates text-only training examples that teach the model to respond in
Ansel Adams' voice and philosophy about photography.

Usage:
    python training/prepare_text_dataset.py
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CORPUS_PATH = PROJECT_ROOT / "training" / "ansel_ocr" / "ansel_adams_training_corpus.txt"
OUTPUT_PATH = PROJECT_ROOT / "training" / "datasets" / "ansel_text_train.jsonl"


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks of roughly chunk_size words."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def clean_text(text: str) -> str:
    """Clean OCR artifacts from text."""
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    # Remove lines that are just numbers (page numbers)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    # Clean up common OCR errors
    text = text.replace('|', 'l')
    text = text.replace('0', 'o') if 'f/0' not in text else text  # Don't replace in f-stops
    return text.strip()


def create_qa_examples(chunk: str) -> list[dict]:
    """
    Create Q&A style training examples from a text chunk.

    Returns list of message dicts in the format expected by train_lora.py
    """
    examples = []

    # Skip chunks that are too short or likely not content
    if len(chunk.split()) < 50:
        return []

    # Template 1: Philosophy question
    examples.append({
        "messages": [
            {
                "role": "user",
                "content": "What is your philosophy on photography and the creative process?"
            },
            {
                "role": "assistant",
                "content": chunk
            }
        ]
    })

    # Template 2: Technical advice
    if any(term in chunk.lower() for term in ['exposure', 'focus', 'lens', 'aperture', 'shutter', 'film', 'print', 'develop']):
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": "Can you share your technical insights on achieving quality in photography?"
                },
                {
                    "role": "assistant",
                    "content": chunk
                }
            ]
        })

    # Template 3: Composition advice
    if any(term in chunk.lower() for term in ['composition', 'frame', 'balance', 'light', 'shadow', 'tone', 'contrast']):
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": "How do you approach composition and visual elements in your work?"
                },
                {
                    "role": "assistant",
                    "content": chunk
                }
            ]
        })

    # Template 4: General teaching
    examples.append({
        "messages": [
            {
                "role": "user",
                "content": "As a photography advisor, what guidance would you offer?"
            },
            {
                "role": "assistant",
                "content": chunk
            }
        ]
    })

    return examples


def main():
    print(f"Reading corpus from: {CORPUS_PATH}")

    if not CORPUS_PATH.exists():
        print(f"Error: Corpus not found at {CORPUS_PATH}")
        print("Run OCR first to generate the corpus.")
        return

    # Read and clean the corpus
    with open(CORPUS_PATH, 'r') as f:
        raw_text = f.read()

    cleaned_text = clean_text(raw_text)
    print(f"Corpus size: {len(cleaned_text):,} characters, {len(cleaned_text.split()):,} words")

    # Split into chunks
    chunks = chunk_text(cleaned_text, chunk_size=300, overlap=30)
    print(f"Created {len(chunks)} text chunks")

    # Generate training examples
    all_examples = []
    for chunk in chunks:
        examples = create_qa_examples(chunk)
        all_examples.extend(examples)

    print(f"Generated {len(all_examples)} training examples")

    # Write to JSONL
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        for example in all_examples:
            f.write(json.dumps(example) + '\n')

    print(f"Saved to: {OUTPUT_PATH}")

    # Also create combined dataset (text + image examples)
    combined_path = PROJECT_ROOT / "training" / "datasets" / "ansel_combined_train.jsonl"
    image_dataset = PROJECT_ROOT / "training" / "datasets" / "ansel_train.jsonl"

    with open(combined_path, 'w') as out_f:
        # Add text examples
        for example in all_examples:
            out_f.write(json.dumps(example) + '\n')

        # Add image examples if they exist
        if image_dataset.exists():
            with open(image_dataset, 'r') as img_f:
                for line in img_f:
                    out_f.write(line)
            print(f"Combined with image dataset from: {image_dataset}")

    # Count combined examples
    with open(combined_path, 'r') as f:
        combined_count = sum(1 for _ in f)

    print(f"Combined dataset: {combined_count} examples")
    print(f"Saved to: {combined_path}")


if __name__ == "__main__":
    main()
