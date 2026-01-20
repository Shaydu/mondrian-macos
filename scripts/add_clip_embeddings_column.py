#!/usr/bin/env python3
"""
Add CLIP Text Embedding Column to book_passages Table

Adds a new column 'clip_text_embedding' to store 512-dim CLIP embeddings.
Usage: python scripts/add_clip_embeddings_column.py
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "mondrian.db"

def add_clip_column():
    """Add clip_text_embedding column to book_passages table"""
    
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(book_passages)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'clip_text_embedding' in columns:
            print("ℹ️  Column 'clip_text_embedding' already exists")
            conn.close()
            return True
        
        # Add new column
        print("📝 Adding 'clip_text_embedding' column to book_passages table...")
        cursor.execute("""
            ALTER TABLE book_passages 
            ADD COLUMN clip_text_embedding BLOB
        """)
        
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(book_passages)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'clip_text_embedding' in columns:
            print("✅ Column added successfully")
            print(f"   Table now has {len(columns)} columns")
            conn.close()
            return True
        else:
            print("❌ Column addition verification failed")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Failed to add column: {e}")
        return False

if __name__ == "__main__":
    success = add_clip_column()
    exit(0 if success else 1)
