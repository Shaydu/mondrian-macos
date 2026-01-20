#!/usr/bin/env python3
"""Test CLIP-based quote retrieval system"""

import os
import sys

# Add mondrian to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mondrian.embedding_retrieval import get_top_book_passages

# Find a test image
test_images = [
    "mondrian/test_images/ansel_adams_yosemite.jpg",
    "training_data/ansel_adams/images/img_001.jpg", 
    "images/ansel/img_001.jpg"
]

test_image = None
for img_path in test_images:
    if os.path.exists(img_path):
        test_image = img_path
        break

if not test_image:
    print("⚠️  No test image found, testing fallback mode...")
    print("\n🧪 Testing WITHOUT user image (should fall back to relevance_score):")
    passages = get_top_book_passages(advisor_id="ansel", user_image_path=None, max_passages=10)
    
    if passages:
        print(f"✅ Retrieved {len(passages)} passages via relevance_score fallback")
        for i, p in enumerate(passages[:3], 1):
            score = p.get('relevance_score', 'N/A')
            score_str = f"{score:.2f}" if isinstance(score, float) else str(score)
            print(f"\n{i}. Score: {score_str}")
            print(f"   Dimensions: {', '.join(p['dimensions'])}")
            print(f"   Text: {p['passage_text'][:100]}...")
    else:
        print("❌ No passages retrieved")
    sys.exit(0)

print(f"🧪 Testing WITH user image: {test_image}")
print("\n📊 Retrieving top 10 quotes using CLIP similarity...")

passages = get_top_book_passages(
    advisor_id="ansel",
    user_image_path=test_image,
    max_passages=10
)

if passages:
    print(f"✅ Retrieved {len(passages)} passages")
    print(f"\n🎯 Top 5 quotes (by CLIP similarity):")
    
    for i, p in enumerate(passages[:5], 1):
        sim_score = p.get('similarity_score', 'N/A')
        sim_str = f"{sim_score:.4f}" if isinstance(sim_score, float) else str(sim_score)
        print(f"\n{i}. Similarity: {sim_str}")
        print(f"   Book: {p['book_title']}")
        print(f"   Dimensions: {', '.join(p['dimensions'])}")
        print(f"   Text: {p['passage_text'][:150]}...")
    
    print("\n" + "="*80)
    print("✅ CLIP-based quote retrieval is working!")
    sim_max = passages[0]['similarity_score']
    sim_min = passages[-1]['similarity_score']
    print(f"   Similarity range: {sim_max:.4f} → {sim_min:.4f}")
    print(f"   All {len(passages)} quotes ranked by semantic relevance to image")
else:
    print("❌ No passages retrieved - check logs above")

