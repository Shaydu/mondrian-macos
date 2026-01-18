#!/usr/bin/env python3
"""
Import dimension-tagged book passages into database with embeddings.

Loads approved passages from training/book_passages/*.json,
computes embeddings, and inserts into book_passages table.

Usage:
    python3 scripts/import_book_passages.py
    python3 scripts/import_book_passages.py --dry-run  # Preview without importing
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict
import numpy as np

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "mondrian.db"
PASSAGES_DIR = PROJECT_ROOT / "training" / "book_passages"


def compute_text_embedding(text: str) -> np.ndarray:
    """Compute sentence-transformer embedding for text passage."""
    try:
        from sentence_transformers import SentenceTransformer
        
        # Use same model as image text embeddings for consistency
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.astype(np.float32)
    
    except ImportError:
        print("Error: sentence-transformers not installed")
        print("Install with: pip install sentence-transformers")
        sys.exit(1)
    except Exception as e:
        print(f"Error computing embedding: {e}")
        return None


def load_approved_passages() -> List[Dict]:
    """Load all approved passages from JSON files."""
    all_passages = []
    
    for book in ['print', 'camera']:
        approved_file = PASSAGES_DIR / f"{book}_approved.json"
        
        if approved_file.exists():
            with open(approved_file, 'r') as f:
                data = json.load(f)
                passages = data.get('passages', [])
                
                # Add book metadata
                book_title = f"The {book.title()}"
                for p in passages:
                    p['book_title'] = book_title
                    p['advisor_id'] = data.get('advisor', 'ansel')
                
                all_passages.extend(passages)
                print(f"Loaded {len(passages)} passages from {book_title}")
    
    return all_passages


def import_passages(passages: List[Dict], dry_run: bool = False):
    """Import passages into database with embeddings."""
    
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return False
    
    # Check if table exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='book_passages'
    """)
    
    if not cursor.fetchone():
        print("Error: book_passages table does not exist")
        print("Run: python3 scripts/add_book_passages_table.py first")
        conn.close()
        return False
    
    if dry_run:
        print("\n--- DRY RUN MODE ---")
        print("Passages that would be imported:\n")
        
        for p in passages[:5]:  # Show first 5
            dims = ', '.join(p['dimensions'])
            text_preview = p['text'][:100] + "..." if len(p['text']) > 100 else p['text']
            print(f"ID: {p['id']}")
            print(f"Book: {p['book_title']}")
            print(f"Dimensions: {dims}")
            print(f"Text: {text_preview}")
            print()
        
        if len(passages) > 5:
            print(f"... and {len(passages) - 5} more passages")
        
        conn.close()
        return True
    
    print(f"\nImporting {len(passages)} passages...")
    print("Computing embeddings (this may take a minute)...")
    
    imported = 0
    skipped = 0
    
    for i, passage in enumerate(passages):
        passage_id = passage['id']
        
        # Check if already exists
        cursor.execute("SELECT id FROM book_passages WHERE id = ?", (passage_id,))
        if cursor.fetchone():
            print(f"  Skip {i+1}/{len(passages)}: {passage_id} (already exists)")
            skipped += 1
            continue
        
        # Compute embedding
        embedding = compute_text_embedding(passage['text'])
        if embedding is None:
            print(f"  Skip {i+1}/{len(passages)}: {passage_id} (embedding failed)")
            skipped += 1
            continue
        
        # Prepare data
        dimension_tags_json = json.dumps(passage['dimensions'])
        embedding_blob = embedding.tobytes()
        
        # Insert
        cursor.execute("""
            INSERT INTO book_passages (
                id, advisor_id, book_title, passage_text,
                dimension_tags, embedding, relevance_score,
                source, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            passage_id,
            passage['advisor_id'],
            passage['book_title'],
            passage['text'],
            dimension_tags_json,
            embedding_blob,
            passage.get('relevance_score', 0),
            passage.get('source', ''),
            passage.get('notes', '')
        ))
        
        imported += 1
        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(passages)}...")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Import complete:")
    print(f"  Imported: {imported}")
    print(f"  Skipped:  {skipped}")
    
    return True


def verify_import():
    """Verify import by showing statistics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Count by book
    cursor.execute("""
        SELECT book_title, COUNT(*) as count
        FROM book_passages
        GROUP BY book_title
    """)
    
    print("\n📊 Database statistics:")
    for book, count in cursor.fetchall():
        print(f"  {book}: {count} passages")
    
    # Count by dimension (requires parsing JSON)
    cursor.execute("SELECT dimension_tags FROM book_passages")
    dimension_counts = {}
    
    for (tags_json,) in cursor.fetchall():
        dims = json.loads(tags_json)
        for dim in dims:
            dimension_counts[dim] = dimension_counts.get(dim, 0) + 1
    
    print("\n📊 By dimension:")
    for dim, count in sorted(dimension_counts.items(), key=lambda x: -x[1]):
        print(f"  {dim}: {count}")
    
    # Sample query
    print("\n📚 Sample passages:")
    cursor.execute("""
        SELECT id, book_title, dimension_tags, 
               SUBSTR(passage_text, 1, 80) as preview
        FROM book_passages
        LIMIT 3
    """)
    
    for passage_id, book, tags, preview in cursor.fetchall():
        dims = ', '.join(json.loads(tags))
        print(f"\n  {passage_id}")
        print(f"  {book} | Dimensions: {dims}")
        print(f"  {preview}...")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import tagged book passages into database"
    )
    parser.add_argument('--dry-run', action='store_true',
                        help="Preview import without modifying database")
    
    args = parser.parse_args()
    
    # Load passages
    passages = load_approved_passages()
    
    if not passages:
        print("No approved passages found!")
        print(f"Check: {PASSAGES_DIR}")
        return 1
    
    print(f"\nFound {len(passages)} approved passages")
    
    # Import
    success = import_passages(passages, dry_run=args.dry_run)
    
    if not success:
        return 1
    
    # Verify if not dry run
    if not args.dry_run:
        verify_import()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
