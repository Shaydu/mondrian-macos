#!/usr/bin/env python3
"""
Compute CLIP Text Embeddings for Book Passages

Computes 512-dim CLIP text embeddings for all book passages and stores them
in the clip_text_embedding column.

Usage: python scripts/compute_clip_quote_embeddings.py
"""

import sqlite3
import numpy as np
from pathlib import Path
from transformers import CLIPProcessor, CLIPModel
import torch

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "mondrian.db"

def get_clip_model():
    """Load CLIP model (same one used for images)"""
    print("📦 Loading CLIP model...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    
    # Use GPU if available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    model.eval()
    
    print(f"✅ CLIP model loaded on {device}")
    return model, processor, device

def compute_text_embedding(text, model, processor, device):
    """Compute CLIP text embedding for a passage"""
    with torch.no_grad():
        inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        text_features = model.get_text_features(**inputs)
        # Normalize embedding
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        # Convert to numpy and return
        embedding = text_features.cpu().numpy().flatten()
        return embedding

def compute_all_embeddings():
    """Compute CLIP embeddings for all book passages"""
    
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return False
    
    try:
        # Load CLIP model
        model, processor, device = get_clip_model()
        
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(book_passages)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'clip_text_embedding' not in columns:
            print("❌ Column 'clip_text_embedding' does not exist")
            print("   Run: python scripts/add_clip_embeddings_column.py")
            conn.close()
            return False
        
        # Get all passages
        cursor.execute("""
            SELECT id, passage_text, advisor_id, book_title
            FROM book_passages
            ORDER BY id
        """)
        passages = cursor.fetchall()
        
        print(f"\n📊 Found {len(passages)} passages to process")
        
        # Process each passage
        updated_count = 0
        skipped_count = 0
        
        for idx, (passage_id, text, advisor_id, book_title) in enumerate(passages, 1):
            # Check if already has embedding
            cursor.execute("""
                SELECT clip_text_embedding 
                FROM book_passages 
                WHERE id = ?
            """, (passage_id,))
            result = cursor.fetchone()
            
            if result[0] is not None:
                print(f"[{idx}/{len(passages)}] ⏭️  Skipping {passage_id} (already has embedding)")
                skipped_count += 1
                continue
            
            # Compute embedding
            print(f"[{idx}/{len(passages)}] 🔄 Processing {passage_id}...")
            print(f"   Book: {book_title}")
            print(f"   Text preview: {text[:80]}...")
            
            embedding = compute_text_embedding(text, model, processor, device)
            
            # Store in database
            embedding_blob = embedding.astype(np.float32).tobytes()
            cursor.execute("""
                UPDATE book_passages 
                SET clip_text_embedding = ?
                WHERE id = ?
            """, (embedding_blob, passage_id))
            
            conn.commit()
            updated_count += 1
            print(f"   ✅ Embedding stored (dim: {embedding.shape[0]})")
        
        print(f"\n✅ Processing complete!")
        print(f"   Updated: {updated_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total: {len(passages)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to compute embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = compute_all_embeddings()
    exit(0 if success else 1)
