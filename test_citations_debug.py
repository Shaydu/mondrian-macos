#!/usr/bin/env python3
"""Test script to debug citations pipeline."""

import logging
import sys
from pathlib import Path

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

from mondrian.rag_retrieval import get_top_reference_images

DB_PATH = "mondrian.db"

print("\n=== Testing get_top_reference_images() ===\n")
images = get_top_reference_images(DB_PATH, "ansel", max_total=5)

print(f"\n✓ Retrieved {len(images)} images")

if images:
    img = images[0]
    print(f"\nFirst image:")
    print(f"  Title: {img.get('image_title')}")
    print(f"  Has image_path: {'image_path' in img}")
    print(f"  Has composition_instructive: {'composition_instructive' in img}")
    print(f"  All keys: {list(img.keys())}")
    
    if 'composition_instructive' in img:
        text = img['composition_instructive']
        if text:
            print(f"  composition_instructive (first 100 chars): {text[:100]}...")
        else:
            print(f"  composition_instructive: (NULL/empty)")
    else:
        print(f"  composition_instructive: (NOT IN DICT)")
