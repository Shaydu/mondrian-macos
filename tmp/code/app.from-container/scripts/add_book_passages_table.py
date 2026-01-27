#!/usr/bin/env python3
"""
Add book_passages table to database for dimension-tagged Ansel Adams quotes.

This table stores passages from "The Print" and "The Camera" that have been:
1. Filtered for quality (relevance score >= 5)
2. OCR-cleaned for readability
3. Manually tagged by dimension
4. Embedded for semantic retrieval

Usage:
    python3 scripts/add_book_passages_table.py
"""

import sqlite3
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "mondrian.db"


def add_book_passages_table():
    """Add book_passages table to existing database."""
    
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return False
    
    print(f"Adding book_passages table to {DB_PATH}...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table already exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='book_passages'
    """)
    
    if cursor.fetchone():
        print("⚠ book_passages table already exists")
        response = input("Drop and recreate? (y/N): ").strip().lower()
        if response == 'y':
            cursor.execute("DROP TABLE book_passages")
            print("✓ Dropped existing table")
        else:
            print("Keeping existing table")
            conn.close()
            return True
    
    # Create table
    cursor.execute("""
        CREATE TABLE book_passages (
            id TEXT PRIMARY KEY,
            advisor_id TEXT NOT NULL,
            book_title TEXT NOT NULL,
            passage_text TEXT NOT NULL,
            dimension_tags TEXT NOT NULL,
            embedding BLOB,
            relevance_score REAL,
            source TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (advisor_id) REFERENCES advisors(id)
        )
    """)
    
    # Create indices for fast retrieval
    cursor.execute("""
        CREATE INDEX idx_book_passages_advisor 
        ON book_passages(advisor_id)
    """)
    
    cursor.execute("""
        CREATE INDEX idx_book_passages_book 
        ON book_passages(book_title)
    """)
    
    # Index for dimension filtering (JSON array stored as TEXT)
    # SQLite JSON support allows queries like: dimension_tags LIKE '%"lighting"%'
    cursor.execute("""
        CREATE INDEX idx_book_passages_dimensions 
        ON book_passages(dimension_tags)
    """)
    
    conn.commit()
    conn.close()
    
    print("✓ Created book_passages table with indices")
    print("\nTable schema:")
    print("  - id: Unique passage identifier")
    print("  - advisor_id: Links to advisors table (e.g., 'ansel')")
    print("  - book_title: 'The Print', 'The Camera', etc.")
    print("  - passage_text: Cleaned OCR text for display")
    print("  - dimension_tags: JSON array of dimensions (e.g., ['lighting', 'emotional_impact'])")
    print("  - embedding: 384-dim vector for semantic search")
    print("  - relevance_score: OCR filtering score")
    print("\nNext: Run import_book_passages.py to load tagged passages")
    
    return True


if __name__ == "__main__":
    success = add_book_passages_table()
    sys.exit(0 if success else 1)
