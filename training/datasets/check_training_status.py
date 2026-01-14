#!/usr/bin/env python3
"""
Quick training data status checker

Shows you what you have and what you need.
"""

import json
import os
from pathlib import Path
from collections import Counter


def check_file(filepath):
    """Check a JSONL training file."""
    if not os.path.exists(filepath):
        return None

    entries = []
    with open(filepath, 'r') as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except:
                pass

    stats = {
        'total': len(entries),
        'has_images': sum(1 for e in entries if 'image_path' in e),
        'has_base64': sum(1 for e in entries if 'messages' in e and
                          any('image_url' in str(m.get('content', '')) for m in e['messages'])),
        'labels': Counter(e.get('label', 'unlabeled') for e in entries)
    }

    return stats


def main():
    print("\n" + "="*80)
    print("TRAINING DATA STATUS CHECK")
    print("="*80 + "\n")

    datasets_dir = Path('.')

    files_to_check = {
        'Text Training (Ansel\'s voice)': 'ansel_print_filtered_train.jsonl',
        'Image Training (with paths)': 'ansel_image_training.jsonl',
        'Negative Examples (with paths)': 'negative_examples.jsonl',
        'Image Training (base64)': 'ansel_images_base64.jsonl',
        'Negative Examples (base64)': 'negative_examples_base64.jsonl',
        'Combined Dataset': 'ansel_complete_training.jsonl'
    }

    results = {}

    for name, filename in files_to_check.items():
        filepath = datasets_dir / filename
        stats = check_file(filepath)
        results[name] = (filepath, stats)

    # Print results
    for name, (filepath, stats) in results.items():
        print(f"📄 {name}")
        print(f"   File: {filepath.name}")

        if stats is None:
            print(f"   Status: ❌ NOT FOUND\n")
            continue

        print(f"   Status: ✅ EXISTS")
        print(f"   Total entries: {stats['total']}")

        if stats['has_images'] > 0:
            print(f"   With image paths: {stats['has_images']}")

        if stats['has_base64'] > 0:
            print(f"   With base64 images: {stats['has_base64']}")

        if stats['labels']:
            for label, count in stats['labels'].items():
                if label != 'unlabeled':
                    print(f"   {label.capitalize()}: {count}")

        print()

    # Summary and recommendations
    print("="*80)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*80 + "\n")

    text_training = results['Text Training (Ansel\'s voice)'][1]
    image_training = results['Image Training (with paths)'][1]
    negative_training = results['Negative Examples (with paths)'][1]

    total_text = text_training['total'] if text_training else 0
    total_images_pos = image_training['labels'].get('positive', 0) if image_training else 0
    total_images_neg = (image_training['labels'].get('negative', 0) if image_training else 0) + \
                       (negative_training['total'] if negative_training else 0)

    print(f"✅ Text-only training: {total_text} entries")
    print(f"{'✅' if total_images_pos >= 20 else '⚠️ '} Positive image examples: {total_images_pos} " +
          f"{'(good!)' if total_images_pos >= 50 else '(aim for 50-100)'}")
    print(f"{'✅' if total_images_neg >= 20 else '⚠️ '} Negative image examples: {total_images_neg} " +
          f"{'(good!)' if total_images_neg >= 50 else '(aim for 50-100)'}")

    print(f"\nTotal training examples: {total_text + total_images_pos + total_images_neg}")

    # Next steps
    print("\n" + "-"*80)
    print("NEXT STEPS:")
    print("-"*80 + "\n")

    if not image_training:
        print("1. ⚠️  Review your existing images:")
        print("   python review_images_for_training.py --mode review")
    elif total_images_pos < 50:
        print(f"1. ⚠️  Add more positive examples (need {50 - total_images_pos} more)")

    if total_images_neg < 50:
        print(f"2. ⚠️  Add negative examples (need {50 - total_images_neg} more):")
        print("   python add_negative_examples.py --dir /path/to/bad/photos")

    if image_training and not results['Image Training (base64)'][1]:
        print("3. ⚠️  Export to base64 format:")
        print("   python review_images_for_training.py --mode export")

    if all([text_training, image_training, total_images_pos >= 20, total_images_neg >= 20]):
        if not results['Combined Dataset'][1]:
            print("4. ✅ Combine all datasets:")
            print("   cat ansel_print_filtered_train.jsonl ansel_image_training.jsonl negative_examples.jsonl > ansel_complete_training.jsonl")
        else:
            print("4. ✅ Dataset ready for training!")
            print(f"   Use: ansel_complete_training.jsonl ({total_text + total_images_pos + total_images_neg} total examples)")

    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()
