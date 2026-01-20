# Instructions for updating the code to use CLIP-based quote retrieval

## File 1: mondrian/embedding_retrieval.py
### Replace the get_top_book_passages function (lines 420-465) with:

```python
def get_top_book_passages(advisor_id: str, user_image_path: str = None, max_passages: int = 10, db_path: str = None) -> List[Dict]:
    """
    Retrieve top book passages using CLIP semantic similarity to user's image.
    Ranks ALL passages by image-to-text CLIP similarity and returns top-K.
    
    Args:
        advisor_id: ID of the advisor (e.g., "ansel")
        user_image_path: Path to user's image for CLIP similarity matching
        max_passages: Maximum passages to return (default 10)
        db_path: Path to database (default: mondrian.db)
    
    Returns:
        List of dicts with keys: passage_text, book_title, dimensions, similarity_score
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mondrian.db')
    
    logger.info(f"Retrieving top {max_passages} book passages for advisor {advisor_id} using CLIP similarity")
    
    # If no user image provided, fall back to relevance score
    if user_image_path is None:
        logger.warning("No user image provided, falling back to relevance_score ranking")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT passage_text, book_title, dimension_tags, relevance_score
            FROM book_passages
            WHERE advisor_id = ?
            ORDER BY relevance_score DESC
            LIMIT ?
        """
        
        cursor.execute(query, (advisor_id, max_passages))
        rows = cursor.fetchall()
        conn.close()
        
        passages = []
        for row in rows:
            import json
            passages.append({
                'passage_text': row['passage_text'],
                'book_title': row['book_title'],
                'dimensions': json.loads(row['dimension_tags']),
                'relevance_score': row['relevance_score']
            })
        
        return passages
    
    # Compute CLIP image embedding for user's image
    try:
        from PIL import Image
        user_image = Image.open(user_image_path).convert('RGB')
        user_embedding = compute_image_embedding(user_image)
    except Exception as e:
        logger.error(f"Failed to compute image embedding: {e}")
        # Fall back to relevance score
        return get_top_book_passages(advisor_id, None, max_passages, db_path)
    
    # Get all passages with CLIP embeddings
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT id, passage_text, book_title, dimension_tags, clip_text_embedding
        FROM book_passages
        WHERE advisor_id = ? AND clip_text_embedding IS NOT NULL
        ORDER BY id
    """
    
    cursor.execute(query, (advisor_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        logger.error(f"No passages with CLIP embeddings found for advisor {advisor_id}")
        logger.error("Run: python scripts/compute_clip_quote_embeddings.py")
        return []
    
    # Compute similarities
    passages_with_similarity = []
    for row in rows:
        import json
        
        # Load CLIP text embedding
        text_embedding_blob = row['clip_text_embedding']
        text_embedding = np.frombuffer(text_embedding_blob, dtype=np.float32)
        
        # Compute cosine similarity
        similarity = cosine_similarity(user_embedding, text_embedding)
        
        passages_with_similarity.append({
            'passage_text': row['passage_text'],
            'book_title': row['book_title'],
            'dimensions': json.loads(row['dimension_tags']),
            'similarity_score': float(similarity)
        })
    
    # Sort by similarity (highest first) and return top-K
    passages_with_similarity.sort(key=lambda x: x['similarity_score'], reverse=True)
    top_passages = passages_with_similarity[:max_passages]
    
    logger.info(f"Retrieved {len(top_passages)} passages (similarity range: {top_passages[0]['similarity_score']:.3f} - {top_passages[-1]['similarity_score']:.3f})")
    
    return top_passages
```

## File 2: mondrian/ai_advisor_service_linux.py
### Update 1: Lines 922-927, change from:
```python
                    book_passages = get_top_book_passages(
                        advisor_id=advisor,
                        max_passages=6
                    )
```

### To:
```python
                    book_passages = get_top_book_passages(
                        advisor_id=advisor,
                        user_image_path=image_path,
                        max_passages=10
                    )
```

### Update 2: Line 993, change from:
```python
            rag_context += "You may cite UP TO 3 of these quotes total across all dimensions. Each dimension may cite ONE quote maximum. Never reuse quote IDs.\n\n"
```

### To:
```python
            rag_context += "You may cite UP TO 3 of these quotes total across all dimensions. Each dimension may cite ONE quote maximum. Never reuse quote IDs. These quotes are semantically matched to your image.\n\n"
```

## Summary of changes:
1. ✅ Database backup created
2. ✅ CLIP text embedding column added
3. ✅ All 62 quotes processed with CLIP embeddings
4. ⏳ Update get_top_book_passages() function to use CLIP similarity
5. ⏳ Update service to pass user_image_path and use max_passages=10
6. ⏳ Update prompt text to indicate semantic matching

The embeddings are now computed and stored. Apply the code changes above to complete the implementation.
