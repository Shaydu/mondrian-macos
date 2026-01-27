#!/usr/bin/env python3
"""
Compute CLIP Visual and Text Embeddings for Advisor Reference Images

This script:
1. Loads CLIP model for visual embeddings
2. Loads sentence-transformer for text embeddings
3. Computes embeddings for all advisor images in dimensional_profiles
4. Stores embeddings as BLOBs in the database

Usage:
    python scripts/compute_embeddings.py --advisor ansel
    python scripts/compute_embeddings.py --advisor all
    python scripts/compute_embeddings.py --advisor ansel --verify-only
"""

import os
import sys
import sqlite3
import argparse
import numpy as np
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "mondrian.db"

# Lazy load models to avoid import time
_clip_model = None
_clip_processor = None
_text_model = None


def get_clip_model():
    """Lazy load CLIP model"""
    global _clip_model, _clip_processor
    if _clip_model is None:
        print("[INFO] Loading CLIP model (clip-vit-base-patch32)...")
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            
            _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            
            # Try to use GPU, fall back to CPU if it fails
            try:
                if torch.cuda.is_available():
                    # Test if CUDA actually works
                    test_tensor = torch.zeros(1).cuda()
                    _clip_model = _clip_model.cuda()
                    print(f"[INFO] CLIP model loaded on CUDA (GPU: {torch.cuda.get_device_name(0)})")
                else:
                    print("[INFO] CLIP model loaded on CPU (CUDA not available)")
            except Exception as cuda_error:
                print(f"[WARN] CUDA failed ({cuda_error}), falling back to CPU")
                _clip_model = _clip_model.cpu()
                print(f"[WARN] CUDA error: {cuda_error}, falling back to CPU")
                # Model stays on CPU
        except ImportError as e:
            print(f"[ERROR] Failed to import transformers: {e}")
            print("[INFO] Install with: pip install transformers")
            sys.exit(1)
    return _clip_model, _clip_processor


def get_text_model():
    """Lazy load text embedding model"""
    global _text_model
    if _text_model is None:
        print("[INFO] Loading text embedding model (all-MiniLM-L6-v2)...")
        try:
            from sentence_transformers import SentenceTransformer
            _text_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[INFO] Text model loaded")
        except ImportError as e:
            print(f"[ERROR] Failed to import sentence_transformers: {e}")
            print("[INFO] Install with: pip install sentence-transformers")
            sys.exit(1)
    return _text_model


def compute_clip_embedding(image_path: str) -> np.ndarray:
    """Compute CLIP visual embedding for an image"""
    from PIL import Image
    import torch
    
    model, processor = get_clip_model()
    
    try:
        image = Image.open(image_path).convert('RGB')
        inputs = processor(images=image, return_tensors="pt")
        
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        # Normalize embedding
        embedding = image_features.cpu().numpy().flatten()
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding
    except Exception as e:
        print(f"[ERROR] Failed to compute CLIP embedding for {image_path}: {e}")
        return None


def compute_text_embedding(text: str) -> np.ndarray:
    """Compute text embedding for description/significance"""
    model = get_text_model()
    
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding
    except Exception as e:
        print(f"[ERROR] Failed to compute text embedding: {e}")
        return None


def get_advisor_images(advisor_id: str = None):
    """Get advisor images that need embeddings computed"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if advisor_id and advisor_id != 'all':
        cursor.execute("""
            SELECT rowid, image_path, image_title, image_description, image_significance,
                   embedding, text_embedding
            FROM dimensional_profiles
            WHERE advisor_id = ?
              AND composition_score IS NOT NULL
        """, (advisor_id,))
    else:
        cursor.execute("""
            SELECT rowid, image_path, image_title, image_description, image_significance,
                   embedding, text_embedding, advisor_id
            FROM dimensional_profiles
            WHERE composition_score IS NOT NULL
              AND advisor_id IS NOT NULL
        """)
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def save_embeddings(profile_id: str, clip_embedding: np.ndarray = None, text_embedding: np.ndarray = None):
    """Save embeddings to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if clip_embedding is not None and text_embedding is not None:
        cursor.execute("""
            UPDATE dimensional_profiles
            SET embedding = ?, text_embedding = ?
            WHERE rowid = ?
        """, (clip_embedding.tobytes(), text_embedding.tobytes(), profile_id))
        rows_affected = cursor.rowcount
    elif clip_embedding is not None:
        cursor.execute("""
            UPDATE dimensional_profiles
            SET embedding = ?
            WHERE rowid = ?
        """, (clip_embedding.tobytes(), profile_id))
        rows_affected = cursor.rowcount
    elif text_embedding is not None:
        cursor.execute("""
            UPDATE dimensional_profiles
            SET text_embedding = ?
            WHERE rowid = ?
        """, (text_embedding.tobytes(), profile_id))
        rows_affected = cursor.rowcount
    else:
        rows_affected = 0
    
    conn.commit()
    conn.close()
    
    if rows_affected == 0:
        print(f"  [WARN] No rows updated for profile_id={profile_id}")


def verify_embeddings(advisor_id: str = None):
    """Verify embedding status for advisor images"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if advisor_id and advisor_id != 'all':
        where_clause = "WHERE advisor_id = ? AND composition_score IS NOT NULL"
        params = (advisor_id,)
    else:
        where_clause = "WHERE composition_score IS NOT NULL AND advisor_id IS NOT NULL"
        params = ()
    
    # Total images
    cursor.execute(f"SELECT COUNT(*) FROM dimensional_profiles {where_clause}", params)
    total = cursor.fetchone()[0]
    
    # With CLIP embeddings
    cursor.execute(f"SELECT COUNT(*) FROM dimensional_profiles {where_clause} AND embedding IS NOT NULL", params)
    with_clip = cursor.fetchone()[0]
    
    # With text embeddings
    cursor.execute(f"SELECT COUNT(*) FROM dimensional_profiles {where_clause} AND text_embedding IS NOT NULL", params)
    with_text = cursor.fetchone()[0]
    
    # With both
    cursor.execute(f"SELECT COUNT(*) FROM dimensional_profiles {where_clause} AND embedding IS NOT NULL AND text_embedding IS NOT NULL", params)
    with_both = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"Embedding Status: {advisor_id or 'all advisors'}")
    print("=" * 60)
    print(f"Total images:        {total}")
    print(f"With CLIP embedding: {with_clip} ({100*with_clip/total:.1f}%)" if total > 0 else "With CLIP embedding: 0")
    print(f"With text embedding: {with_text} ({100*with_text/total:.1f}%)" if total > 0 else "With text embedding: 0")
    print(f"With BOTH:           {with_both} ({100*with_both/total:.1f}%)" if total > 0 else "With BOTH: 0")
    print("=" * 60 + "\n")
    
    return with_both == total


def compute_all_embeddings(advisor_id: str = None, force: bool = False):
    """Compute embeddings for all advisor images"""
    images = get_advisor_images(advisor_id)
    
    print(f"\n[INFO] Processing {len(images)} images for {advisor_id or 'all advisors'}")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, img in enumerate(images):
        profile_id = img['rowid']
        image_path = img['image_path']
        title = img.get('image_title', 'Unknown')
        description = img.get('image_description', '')
        significance = img.get('image_significance', '')
        
        # Check if already computed
        has_clip = img.get('embedding') is not None
        has_text = img.get('text_embedding') is not None
        
        if has_clip and has_text and not force:
            skip_count += 1
            continue
        
        print(f"\n[{i+1}/{len(images)}] {title}")
        
        # Compute CLIP embedding if needed
        clip_emb = None
        if not has_clip or force:
            if os.path.exists(image_path):
                print(f"  Computing CLIP embedding...")
                clip_emb = compute_clip_embedding(image_path)
                if clip_emb is not None:
                    print(f"  ✓ CLIP embedding: {clip_emb.shape}")
            else:
                print(f"  ✗ Image not found: {image_path}")
                error_count += 1
                continue
        
        # Compute text embedding if needed
        text_emb = None
        if not has_text or force:
            # Combine description and significance for richer embedding
            text_content = f"{title}. {description} {significance}".strip()
            if text_content:
                print(f"  Computing text embedding...")
                text_emb = compute_text_embedding(text_content)
                if text_emb is not None:
                    print(f"  ✓ Text embedding: {text_emb.shape}")
        
        # Save to database
        if clip_emb is not None or text_emb is not None:
            save_embeddings(profile_id, clip_emb, text_emb)
            success_count += 1
            print(f"  ✓ Saved to database")
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Processed: {success_count}")
    print(f"Skipped:   {skip_count}")
    print(f"Errors:    {error_count}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Compute CLIP and text embeddings for advisor images")
    parser.add_argument('--advisor', type=str, default='ansel',
                        help='Advisor ID (ansel, okeefe, mondrian, all)')
    parser.add_argument('--verify-only', action='store_true',
                        help='Only verify embedding status, do not compute')
    parser.add_argument('--force', action='store_true',
                        help='Recompute even if embeddings exist')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Advisor Image Embedding Computation")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Advisor:  {args.advisor}")
    print(f"Mode:     {'Verify only' if args.verify_only else 'Compute'}")
    
    if args.verify_only:
        verify_embeddings(args.advisor)
    else:
        compute_all_embeddings(args.advisor, force=args.force)
        verify_embeddings(args.advisor)


if __name__ == "__main__":
    main()
