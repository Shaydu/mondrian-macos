#!/usr/bin/env python3
"""
Embedding-Based Reference Image Retrieval

This module provides functions to retrieve advisor reference images
using visual (CLIP) and text embeddings for semantic similarity.

Used by ai_advisor_service_linux.py for RAG modes.
"""

import os
import sqlite3
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Embedding dimensions
CLIP_DIM = 512  # clip-vit-base-patch32
TEXT_DIM = 384  # all-MiniLM-L6-v2

# Lazy loaded models
_clip_model = None
_clip_processor = None
_text_model = None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)


def load_embedding_from_blob(blob: bytes, dim: int) -> Optional[np.ndarray]:
    """Load numpy array from database BLOB"""
    if blob is None:
        return None
    try:
        return np.frombuffer(blob, dtype=np.float32).reshape(-1)
    except Exception as e:
        logger.warning(f"Failed to load embedding: {e}")
        return None


def get_clip_model():
    """Lazy load CLIP model"""
    global _clip_model, _clip_processor
    if _clip_model is None:
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            
            logger.info("Loading CLIP model...")
            _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            
            if torch.cuda.is_available():
                _clip_model = _clip_model.cuda()
                logger.info("CLIP model loaded on CUDA")
            else:
                logger.info("CLIP model loaded on CPU")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            return None, None
    return _clip_model, _clip_processor


def get_text_model():
    """Lazy load text embedding model"""
    global _text_model
    if _text_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading text embedding model...")
            _text_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Text model loaded")
        except Exception as e:
            logger.error(f"Failed to load text model: {e}")
            return None
    return _text_model


def compute_image_embedding(image_path: str) -> Optional[np.ndarray]:
    """Compute CLIP embedding for an image at runtime"""
    from PIL import Image
    import torch
    
    model, processor = get_clip_model()
    if model is None:
        return None
    
    try:
        image = Image.open(image_path).convert('RGB')
        inputs = processor(images=image, return_tensors="pt")
        
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        with torch.no_grad():
            image_features = model.get_image_features(**inputs)
        
        embedding = image_features.cpu().numpy().flatten()
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.astype(np.float32)
    except Exception as e:
        logger.error(f"Failed to compute CLIP embedding: {e}")
        return None


def compute_text_embedding(text: str) -> Optional[np.ndarray]:
    """Compute text embedding at runtime"""
    model = get_text_model()
    if model is None:
        return None
    
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.astype(np.float32)
    except Exception as e:
        logger.error(f"Failed to compute text embedding: {e}")
        return None


def get_similar_images_by_visual_embedding(
    db_path: str,
    user_image_path: str,
    advisor_id: str,
    weak_dimensions: List[str] = None,
    top_k: int = 4,
    min_score: float = 8.0
) -> List[Dict[str, Any]]:
    """
    Find advisor images visually similar to user's image that excel in weak dimensions.
    
    Args:
        db_path: Path to SQLite database
        user_image_path: Path to user's image
        advisor_id: Advisor to search
        weak_dimensions: User's weak dimensions to filter by (optional)
        top_k: Number of results to return
        min_score: Minimum score in weak dimensions
    
    Returns:
        List of reference images sorted by visual similarity
        
    Raises:
        RuntimeError: If no embeddings found in database
    """
    # First check if embeddings exist in database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM dimensional_profiles 
        WHERE advisor_id = ? AND embedding IS NOT NULL
    """, (advisor_id,))
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        raise RuntimeError(
            f"Embedding system not initialized: No image embeddings found for advisor '{advisor_id}'. "
            "Run: python scripts/compute_embeddings.py --advisor ansel"
        )
    
    # Compute user image embedding
    user_embedding = compute_image_embedding(user_image_path)
    if user_embedding is None:
        raise RuntimeError(
            "Could not compute user image embedding. "
            "Check that the image file exists and is valid."
        )
    
    # Map dimension names to columns
    dim_to_col = {
        'composition': 'composition_score',
        'lighting': 'lighting_score',
        'focus': 'focus_sharpness_score',
        'focus_sharpness': 'focus_sharpness_score',
        'color': 'color_harmony_score',
        'color_harmony': 'color_harmony_score',
        'subject_isolation': 'subject_isolation_score',
        'depth': 'depth_perspective_score',
        'depth_perspective': 'depth_perspective_score',
        'visual_balance': 'visual_balance_score',
        'balance': 'visual_balance_score',
        'emotional_impact': 'emotional_impact_score',
    }
    
    # Build score filter
    score_filters = []
    if weak_dimensions:
        for dim in weak_dimensions[:3]:
            col = dim_to_col.get(dim.lower().replace(' ', '_').replace('&', ''))
            if col:
                score_filters.append(f"{col} >= {min_score}")
    
    where_clause = f"WHERE advisor_id = ? AND embedding IS NOT NULL AND composition_score IS NOT NULL"
    if score_filters:
        where_clause += f" AND ({' OR '.join(score_filters)})"
    
    # Fetch candidates
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT id, image_path, image_title, date_taken, image_description,
               composition_score, lighting_score, focus_sharpness_score,
               depth_perspective_score,
               visual_balance_score, emotional_impact_score, overall_grade,
               embedding
        FROM dimensional_profiles
        {where_clause}
    """, (advisor_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        logger.info(f"No images with embeddings found for advisor {advisor_id}")
        return []
    
    # Compute similarities
    results = []
    for row in rows:
        ref_embedding = load_embedding_from_blob(row['embedding'], CLIP_DIM)
        if ref_embedding is None:
            continue
        
        similarity = cosine_similarity(user_embedding, ref_embedding)
        
        img_dict = dict(row)
        del img_dict['embedding']  # Don't include raw embedding in result
        img_dict['visual_similarity'] = float(similarity)
        results.append(img_dict)
    
    # Sort by similarity descending
    results.sort(key=lambda x: x['visual_similarity'], reverse=True)
    
    logger.info(f"Found {len(results)} visually similar images, returning top {top_k}")
    return results[:top_k]


def get_similar_images_by_text_embedding(
    db_path: str,
    query_text: str,
    advisor_id: str,
    top_k: int = 4,
    min_score: float = 8.0
) -> List[Dict[str, Any]]:
    """
    Find advisor images whose descriptions are semantically similar to query text.
    
    Args:
        db_path: Path to SQLite database
        query_text: Text to match (e.g., recommendation text)
        advisor_id: Advisor to search
        top_k: Number of results to return
        min_score: Minimum overall score
    
    Returns:
        List of reference images sorted by text similarity
        
    Raises:
        RuntimeError: If no text embeddings found in database
    """
    # First check if text embeddings exist in database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM dimensional_profiles 
        WHERE advisor_id = ? AND text_embedding IS NOT NULL
    """, (advisor_id,))
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        raise RuntimeError(
            f"Embedding system not initialized: No text embeddings found for advisor '{advisor_id}'. "
            "Run: python scripts/compute_embeddings.py --advisor ansel"
        )
    
    # Compute query embedding
    query_embedding = compute_text_embedding(query_text)
    if query_embedding is None:
        raise RuntimeError(
            "Could not compute text embedding for query. "
            "Check that sentence-transformers is installed."
        )
    
    # Fetch candidates
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, image_path, image_title, date_taken, image_description,
               composition_score, lighting_score, focus_sharpness_score,
               depth_perspective_score,
               visual_balance_score, emotional_impact_score, overall_grade,
               text_embedding
        FROM dimensional_profiles
        WHERE advisor_id = ?
          AND text_embedding IS NOT NULL
          AND composition_score IS NOT NULL
    """, (advisor_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        logger.info(f"No images with text embeddings found for advisor {advisor_id}")
        return []
    
    # Compute similarities
    results = []
    for row in rows:
        ref_embedding = load_embedding_from_blob(row['text_embedding'], TEXT_DIM)
        if ref_embedding is None:
            continue
        
        similarity = cosine_similarity(query_embedding, ref_embedding)
        
        img_dict = dict(row)
        del img_dict['text_embedding']
        img_dict['text_similarity'] = float(similarity)
        results.append(img_dict)
    
    # Sort by similarity descending
    results.sort(key=lambda x: x['text_similarity'], reverse=True)
    
    logger.info(f"Found {len(results)} text-similar images, returning top {top_k}")
    return results[:top_k]


def get_images_hybrid_retrieval(
    db_path: str,
    user_image_path: str,
    advisor_id: str,
    weak_dimensions: List[str],
    user_scores: Dict[str, float],
    top_k: int = 4,
    visual_weight: float = 0.6,
    score_weight: float = 0.4
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: combine visual similarity with dimensional gap scores.
    
    Args:
        db_path: Path to SQLite database
        user_image_path: Path to user's image
        advisor_id: Advisor to search
        weak_dimensions: User's weak dimensions
        user_scores: Dict of user's scores per dimension
        top_k: Number of results to return
        visual_weight: Weight for visual similarity (0-1)
        score_weight: Weight for gap score (0-1)
    
    Returns:
        List of reference images sorted by hybrid score
        
    Raises:
        RuntimeError: If embeddings not initialized
    """
    # Get visually similar images (will raise RuntimeError if no embeddings)
    visual_results = get_similar_images_by_visual_embedding(
        db_path, user_image_path, advisor_id, weak_dimensions, top_k=20
    )
    
    if not visual_results:
        raise RuntimeError(
            "No visual similarity results found. This may indicate corrupted embeddings."
        )
    
    # Map dimension names to columns
    dim_to_col = {
        'composition': 'composition_score',
        'lighting': 'lighting_score',
        'focus': 'focus_sharpness_score',
        'focus_sharpness': 'focus_sharpness_score',
        'depth': 'depth_perspective_score',
        'depth_perspective': 'depth_perspective_score',
        'visual_balance': 'visual_balance_score',
        'balance': 'visual_balance_score',
        'emotional_impact': 'emotional_impact_score',
    }
    
    # Calculate hybrid score for each result
    for img in visual_results:
        # Calculate max gap across weak dimensions
        max_gap = 0
        for dim in weak_dimensions:
            col = dim_to_col.get(dim.lower().replace(' ', '_').replace('&', ''))
            if col and col.replace('_score', '') in user_scores:
                user_score = user_scores.get(col.replace('_score', ''), 5)
                ref_score = img.get(col, 0) or 0
                gap = ref_score - user_score
                max_gap = max(max_gap, gap)
        
        # Normalize gap to 0-1 (assuming max gap of 10)
        normalized_gap = min(max_gap / 10.0, 1.0)
        
        # Hybrid score
        visual_sim = img.get('visual_similarity', 0)
        hybrid_score = (visual_weight * visual_sim) + (score_weight * normalized_gap)
        
        img['max_gap'] = max_gap
        img['hybrid_score'] = hybrid_score
    
    # Sort by hybrid score
    visual_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
    
    logger.info(f"Hybrid retrieval: returning top {top_k} images")
    return visual_results[:top_k]


def get_top_book_passages(advisor_id: str, user_image_path: str, max_passages: int = 10, db_path: str = None) -> List[Dict]:
    """
    Retrieve top book passages using CLIP semantic similarity to user's image.
    Ranks ALL passages by image-to-text CLIP similarity and returns top-K.
    
    Args:
        advisor_id: ID of the advisor (e.g., "ansel")
        user_image_path: Path to user's image for CLIP similarity matching (REQUIRED)
        max_passages: Maximum passages to return (default 10)
        db_path: Path to database (default: mondrian.db)
    
    Returns:
        List of dicts with keys: passage_text, book_title, dimensions, similarity_score
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mondrian.db')
    
    logger.info(f"Retrieving top {max_passages} book passages for advisor {advisor_id} using CLIP similarity")
    
    # Compute CLIP image embedding for user's image
    try:
        user_embedding = compute_image_embedding(user_image_path)
        if user_embedding is None:
            raise RuntimeError("compute_image_embedding returned None")
    except Exception as e:
        logger.error(f"Failed to compute image embedding from {user_image_path}: {e}")
        raise RuntimeError(f"Cannot retrieve quotes without valid image embedding: {e}") from e
    
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


def get_book_passages_for_dimensions(advisor_id, weak_dimensions, max_passages=2, db_path=None):
    """
    [DEPRECATED - use get_top_book_passages for single-pass]
    Retrieve book passages tagged with weak dimensions for prompt augmentation.
    
    Args:
        advisor_id: ID of the advisor (e.g., "ansel")
        weak_dimensions: List of dimension names (e.g., ["lighting", "composition"])
        max_passages: Maximum passages to return (default 2, user constraint)
        db_path: Path to database (default: mondrian.db)
    
    Returns:
        List of dicts with keys: passage_text, book_title, dimensions, relevance_score
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mondrian.db')
    
    if not weak_dimensions:
        logger.info("No weak dimensions specified, returning empty passages")
        return []
    
    logger.info(f"Retrieving book passages for advisor {advisor_id}, dimensions: {weak_dimensions}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Build query to find passages matching any of the weak dimensions
    # dimension_tags is stored as JSON array
    dimension_conditions = []
    params = [advisor_id]
    
    for dim in weak_dimensions:
        # Match dimension in JSON array (SQLite JSON functions)
        dimension_conditions.append("json_extract(dimension_tags, '$') LIKE ?")
        params.append(f'%"{dim}"%')
    
    where_clause = f"advisor_id = ? AND ({' OR '.join(dimension_conditions)})"
    
    query = f"""
        SELECT passage_text, book_title, dimension_tags, relevance_score
        FROM book_passages
        WHERE {where_clause}
        ORDER BY relevance_score DESC
        LIMIT ?
    """
    params.append(max_passages)
    
    cursor.execute(query, params)
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
    
    logger.info(f"Retrieved {len(passages)} book passages for weak dimensions")
    return passages


# Export functions for use in ai_advisor_service
__all__ = [
    'compute_image_embedding',
    'compute_text_embedding',
    'get_similar_images_by_visual_embedding',
    'get_similar_images_by_text_embedding',
    'get_images_hybrid_retrieval',
    'get_book_passages_for_dimensions',
    'get_top_book_passages',  # Single-pass RAG
    'cosine_similarity',
    'load_embedding_from_blob'
]
