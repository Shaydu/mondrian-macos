#!/usr/bin/env python3
"""
Ingest .npy embedding files into image_captions table.

This script bridges the gap between compute_image_embeddings.py (which generates .npy files)
and the RAG service (which queries the database).

Usage:
    python ingest_npy_embeddings.py --advisor_dir mondrian/source/advisor/photographer/ansel/ --advisor_id ansel
    
    # Or for multiple advisors:
    python ingest_npy_embeddings.py --advisor_dir mondrian/source/advisor/ --advisor_id all
"""

import os
import argparse
from pathlib import Path
import numpy as np
import sqlite3
import uuid
import json
from datetime import datetime

DB_PATH = "mondrian.db"

def ensure_table():
    """Ensure image_captions table exists"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS image_captions (
            id TEXT PRIMARY KEY,
            job_id TEXT,
            image_path TEXT NOT NULL,
            caption TEXT NOT NULL,
            caption_type TEXT DEFAULT 'detailed',
            embedding BLOB,
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def ingest_npy_embeddings(advisor_dir, advisor_id):
    """
    Load .npy embeddings and insert into database.
    
    Args:
        advisor_dir: Directory containing images and their .npy embedding files
        advisor_id: Advisor identifier (e.g., 'ansel', 'okeefe')
    """
    advisor_dir = Path(advisor_dir)
    
    if not advisor_dir.exists():
        print(f"[ERROR] Directory not found: {advisor_dir}")
        return
    
    # Find all .npy files
    npy_files = list(advisor_dir.rglob("*.npy"))
    
    if not npy_files:
        print(f"[WARN] No .npy files found in {advisor_dir}")
        return
    
    print(f"[INFO] Found {len(npy_files)} .npy files in {advisor_dir}")
    
    ensure_table()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for npy_path in npy_files:
        try:
            # Get corresponding image path (remove .npy extension)
            # Handle both .jpg.npy and .jpeg.npy
            image_path_str = str(npy_path)
            if image_path_str.endswith('.jpg.npy'):
                image_path = Path(image_path_str[:-4])  # Remove .npy
            elif image_path_str.endswith('.jpeg.npy'):
                image_path = Path(image_path_str[:-4])  # Remove .npy
            elif image_path_str.endswith('.png.npy'):
                image_path = Path(image_path_str[:-4])  # Remove .npy
            else:
                print(f"[WARN] Unexpected .npy filename format: {npy_path}")
                error_count += 1
                continue
            
            if not image_path.exists():
                print(f"[WARN] Image not found for {npy_path}: {image_path}")
                error_count += 1
                continue
            
            # Check if already in database
            cursor.execute("""
                SELECT id FROM image_captions 
                WHERE image_path = ? AND caption_type = 'clip_embedding'
            """, (str(image_path),))
            
            if cursor.fetchone():
                print(f"[SKIP] Already in database: {image_path.name}")
                skip_count += 1
                continue
            
            # Load embedding
            embedding = np.load(npy_path)
            
            # Validate embedding
            if embedding.ndim != 1:
                print(f"[ERROR] Invalid embedding shape for {npy_path}: {embedding.shape}")
                error_count += 1
                continue
            
            # Create metadata
            metadata = {
                "embedding_dim": len(embedding),
                "embedding_source": "compute_image_embeddings.py",
                "npy_path": str(npy_path),
                "ingested_at": datetime.now().isoformat()
            }
            
            # Insert into database
            cursor.execute("""
                INSERT INTO image_captions
                (id, job_id, image_path, caption, caption_type, embedding, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                f"{advisor_id}-{image_path.stem}",
                str(image_path),
                f"CLIP embedding for {image_path.name}",  # Placeholder caption
                'clip_embedding',
                embedding.tobytes(),
                json.dumps(metadata),
                datetime.now().isoformat()
            ))
            
            print(f"[OK] Ingested: {image_path.name} (dim={len(embedding)})")
            success_count += 1
            
        except Exception as e:
            print(f"[ERROR] Failed to ingest {npy_path}: {e}")
            error_count += 1
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*60)
    print(f"[SUMMARY] Ingestion complete:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ⏭️  Skipped: {skip_count}")
    print(f"  ❌ Errors:  {error_count}")
    print(f"  📊 Total:   {len(npy_files)}")
    print("="*60)

def verify_database():
    """Verify embeddings are in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT caption_type, COUNT(*) as count 
        FROM image_captions 
        GROUP BY caption_type
    """)
    
    print("\n[INFO] Database contents:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} records")
    
    cursor.execute("""
        SELECT COUNT(*) FROM image_captions 
        WHERE embedding IS NOT NULL
    """)
    
    embedding_count = cursor.fetchone()[0]
    print(f"\n[INFO] Total embeddings in database: {embedding_count}")
    
    conn.close()

def main():
    parser = argparse.ArgumentParser(
        description="Ingest .npy embedding files into image_captions database table"
    )
    parser.add_argument(
        "--advisor_dir", 
        type=str, 
        required=True,
        help="Directory containing images and .npy embedding files"
    )
    parser.add_argument(
        "--advisor_id", 
        type=str, 
        required=True,
        help="Advisor identifier (e.g., 'ansel', 'okeefe', 'all')"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify database contents after ingestion"
    )
    args = parser.parse_args()
    
    print("="*60)
    print("NPY Embedding Ingestion Script")
    print("="*60)
    print(f"Advisor Directory: {args.advisor_dir}")
    print(f"Advisor ID: {args.advisor_id}")
    print(f"Database: {DB_PATH}")
    print("="*60 + "\n")
    
    ingest_npy_embeddings(args.advisor_dir, args.advisor_id)
    
    if args.verify:
        verify_database()

if __name__ == "__main__":
    main()
