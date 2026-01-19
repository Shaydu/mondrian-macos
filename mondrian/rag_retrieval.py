#!/usr/bin/env python3
"""
RAG Retrieval Module for AI Advisor Service
Handles reference image retrieval, case study computation, and RAG context augmentation.
"""

import os
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Database path - project root
DB_PATH = str(Path(__file__).parent.parent / 'mondrian.db')

# Standard dimension ordering (indexed 0-7)
DIMENSIONS = [
    'composition',
    'lighting',
    'focus_sharpness',
    'color_harmony',
    'subject_isolation',
    'depth_perspective',
    'visual_balance',
    'emotional_impact'
]

# Map dimension names to database column names
DIMENSION_TO_DB_COLUMN = {
    'composition': 'composition_score',
    'lighting': 'lighting_score',
    'focus_sharpness': 'focus_sharpness_score',
    'focus': 'focus_sharpness_score',
    'sharpness': 'focus_sharpness_score',
    'color_harmony': 'color_harmony_score',
    'color': 'color_harmony_score',
    'subject_isolation': 'subject_isolation_score',
    'isolation': 'subject_isolation_score',
    'depth_perspective': 'depth_perspective_score',
    'depth': 'depth_perspective_score',
    'perspective': 'depth_perspective_score',
    'visual_balance': 'visual_balance_score',
    'balance': 'visual_balance_score',
    'emotional_impact': 'emotional_impact_score',
    'emotion': 'emotional_impact_score',
    'impact': 'emotional_impact_score'
}


def get_dimension_index(name: str) -> Optional[int]:
    """
    Get the dimension index (0-7) from a dimension name.
    Examples:
      "Composition" → 0
      "Focus & Sharpness" → 2
      "Depth & Perspective" → 5
    
    Returns None if dimension is not recognized.
    """
    if not name:
        return None
    
    # Convert to lowercase and replace & (and surrounding spaces) with just underscore
    normalized = (
        name.lower()
        .replace(' & ', '_')  # "Focus & Sharpness" → "focus_sharpness"
        .replace(' ', '_')    # "Color Harmony" → "color_harmony"
    )
    
    # Check if it matches a known dimension
    if normalized in DIMENSIONS:
        return DIMENSIONS.index(normalized)
    
    # Check dimension_to_db_column for variations
    if normalized in DIMENSION_TO_DB_COLUMN:
        # Get the canonical form by looking up what column it maps to
        col = DIMENSION_TO_DB_COLUMN[normalized]
        # Convert "focus_sharpness_score" → "focus_sharpness"
        canonical = col.replace('_score', '')
        if canonical in DIMENSIONS:
            return DIMENSIONS.index(canonical)
    
    logger.debug(f"Could not normalize dimension name: {name}")
    return None


def get_similar_images_from_db(db_path: str, advisor_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve similar reference images from the dimensional_profiles table.
    This provides RAG context by finding reference images with similar dimensional scores.
    
    Args:
        db_path: Path to the SQLite database
        advisor_id: Advisor to search (e.g., 'ansel')
        top_k: Number of similar images to return
        
    Returns:
        List of similar image records with their dimensional scores
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get reference images for this advisor
        # For now, just get the best-rated images as context
        query = """
            SELECT id, image_path, composition_score, lighting_score, 
                   focus_sharpness_score, color_harmony_score, overall_grade,
                   image_description, image_title, date_taken,
                   subject_isolation_score, depth_perspective_score,
                   visual_balance_score, emotional_impact_score
            FROM dimensional_profiles
            WHERE advisor_id = ?
              AND composition_score IS NOT NULL
            ORDER BY (
                composition_score + lighting_score + focus_sharpness_score + 
                color_harmony_score
            ) / 4.0 DESC
            LIMIT ?
        """
        
        cursor.execute(query, (advisor_id, top_k))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            logger.warning(f"No reference images found for advisor: {advisor_id}")
            return []
        
        result_images = []
        for row in rows:
            img_dict = dict(row)
            image_path = img_dict.get('image_path')
            
            # Serve image via endpoint instead of base64
            if image_path and os.path.exists(image_path):
                try:
                    img_filename = os.path.basename(image_path)
                    img_dict['image_url'] = f"/api/reference-image/{img_filename}"
                    img_dict['image_filename'] = img_filename
                    result_images.append(img_dict)
                except Exception as e:
                    logger.warning(f"Failed to process image {image_path}: {e}")
                    continue
            else:
                logger.warning(f"Image path not found: {image_path}")
        
        logger.info(f"Retrieved and prepared {len(result_images)} similar reference images for RAG context")
        
        return result_images
        
    except Exception as e:
        logger.error(f"Failed to retrieve similar images: {e}")
        return []


def get_top_reference_images(db_path: str, advisor_id: str, max_total: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve top-quality reference images across ALL dimensions (single-pass RAG).
    Does NOT filter by weak dimensions - returns best overall exemplars for LLM to choose from.
    
    Args:
        db_path: Path to the SQLite database
        advisor_id: Advisor to search (e.g., 'ansel')
        max_total: Maximum number of images to return (default 10)
        
    Returns:
        List of top reference images sorted by overall quality
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get top images by average dimensional score (no weak dimension filter)
        query = """
            SELECT id, image_path, composition_score, lighting_score, 
                   focus_sharpness_score, color_harmony_score,
                   subject_isolation_score, depth_perspective_score,
                   visual_balance_score, emotional_impact_score,
                   overall_grade, image_description, image_title, date_taken
            FROM dimensional_profiles
            WHERE advisor_id = ?
              AND composition_score IS NOT NULL
            ORDER BY (
                COALESCE(composition_score, 0) + COALESCE(lighting_score, 0) + 
                COALESCE(focus_sharpness_score, 0) + COALESCE(color_harmony_score, 0) +
                COALESCE(subject_isolation_score, 0) + COALESCE(depth_perspective_score, 0) +
                COALESCE(visual_balance_score, 0) + COALESCE(emotional_impact_score, 0)
            ) / 8.0 DESC
            LIMIT ?
        """
        
        cursor.execute(query, (advisor_id, max_total))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            logger.warning(f"No reference images found for advisor: {advisor_id}")
            return []
        
        result_images = []
        for row in rows:
            img_dict = dict(row)
            image_path = img_dict.get('image_path')
            
            # Construct image URL if image_path exists
            if image_path and os.path.exists(image_path):
                try:
                    img_filename = os.path.basename(image_path)
                    img_dict['image_url'] = f"/api/reference-image/{img_filename}"
                    img_dict['image_filename'] = img_filename
                    result_images.append(img_dict)
                except Exception as e:
                    logger.warning(f"Failed to process image {image_path}: {e}")
                    continue
            else:
                result_images.append(img_dict)
        
        logger.info(f"Retrieved {len(result_images)} top reference images for single-pass RAG")
        return result_images
        
    except Exception as e:
        logger.error(f"Failed to retrieve top reference images: {e}")
        return []


def get_images_for_weak_dimensions(db_path: str, advisor_id: str, weak_dimensions: List[str], max_images: int = 4) -> List[Dict[str, Any]]:
    """
    [DEPRECATED - use get_top_reference_images for single-pass]
    Retrieve reference images that excel in the user's weakest dimensions.
    This helps provide specific examples showing how to improve in areas where the user needs the most help.
    
    Args:
        db_path: Path to the SQLite database
        advisor_id: Advisor to search (e.g., 'ansel')
        weak_dimensions: List of dimension names where user needs improvement (e.g., ['composition', 'lighting'])
        max_images: Maximum number of reference images to return (default 4)
        
    Returns:
        List of reference images that excel in the specified dimensions
    """
    try:
        if not weak_dimensions:
            return []
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query to find images that excel in the weak dimensions
        score_columns = []
        for dim in weak_dimensions[:3]:  # Limit to top 3 weak dimensions
            dim_col = DIMENSION_TO_DB_COLUMN.get(dim.lower().replace(' ', '_').replace('&', ''))
            if dim_col:
                score_columns.append(dim_col)
        
        if not score_columns:
            logger.warning(f"Could not map weak dimensions {weak_dimensions} to database columns")
            return []
        
        # Calculate average score across weak dimensions and get images that excel
        # Prioritize images with highest scores in the specific weak dimensions the user needs to improve
        avg_calc = " + ".join(score_columns)
        
        query = f"""
            SELECT id, image_path, composition_score, lighting_score, 
                   focus_sharpness_score, color_harmony_score,
                   subject_isolation_score, depth_perspective_score,
                   visual_balance_score, emotional_impact_score,
                   overall_grade, image_description, image_title, date_taken
            FROM dimensional_profiles
            WHERE advisor_id = ?
              AND composition_score IS NOT NULL
              AND ({" AND ".join([f"{col} >= 8.0" for col in score_columns])})
            ORDER BY ({avg_calc}) / {len(score_columns)} DESC
            LIMIT ?
        """
        
        cursor.execute(query, (advisor_id, max_images))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            logger.warning(f"No reference images found with high scores (>= 8.0) in target dimensions: {weak_dimensions}")
            return []
        
        result_images = []
        for row in rows:
            img_dict = dict(row)
            image_path = img_dict.get('image_path')
            
            # Construct image URL if image_path exists
            if image_path and os.path.exists(image_path):
                try:
                    img_filename = os.path.basename(image_path)
                    img_dict['image_url'] = f"/api/reference-image/{img_filename}"
                    img_dict['image_filename'] = img_filename
                    result_images.append(img_dict)
                except Exception as e:
                    logger.warning(f"Failed to process image {image_path}: {e}")
                    continue
            else:
                # If image doesn't exist but we have the dict, still add it (without image_url)
                result_images.append(img_dict)
        
        # Log selected images and their scores in weak dimensions for debugging
        if result_images:
            score_summary = []
            for img in result_images[:min(3, len(result_images))]:  # Show first 3
                title = img.get('image_title', 'untitled')
                dim_scores = {weak_dimensions[i]: img.get(score_columns[i]) for i in range(min(len(weak_dimensions), len(score_columns)))}
                score_summary.append(f"{title}: {dim_scores}")
            logger.info(f"Selected {len(result_images)} reference images excelling in {weak_dimensions}: {score_summary}")
        
        return result_images
        
    except Exception as e:
        logger.error(f"Failed to retrieve images for weak dimensions: {e}")
        return []


def deduplicate_reference_images(images: List[Dict[str, Any]], used_paths: set, min_images: int = 1) -> List[Dict[str, Any]]:
    """
    Remove duplicate images based on image_path to ensure each reference is used only once.
    
    Args:
        images: List of reference image dictionaries
        used_paths: Set of already used image paths
        min_images: Minimum number of images to return (will add back best images if needed)
        
    Returns:
        List of unique reference images
    """
    deduplicated = []
    for img in images:
        img_path = img.get('image_path')
        if img_path and img_path not in used_paths:
            used_paths.add(img_path)
            deduplicated.append(img)
            logger.debug(f"Added unique reference: {img.get('image_title', img_path.split('/')[-1])}")
        else:
            logger.debug(f"Skipped duplicate reference: {img.get('image_title', img_path.split('/')[-1] if img_path else 'Unknown')}")
    
    # If we have too few unique images, add back the best duplicates
    if len(deduplicated) < min_images and len(images) > len(deduplicated):
        logger.info(f"Only {len(deduplicated)} unique images found, adding back best duplicates to reach minimum of {min_images}")
        for img in images:
            if len(deduplicated) >= min_images:
                break
            img_path = img.get('image_path')
            if img_path and img_path in used_paths:
                # Add it back but mark it as a duplicate in the log
                deduplicated.append(img)
                logger.debug(f"Re-added duplicate reference: {img.get('image_title', img_path.split('/')[-1])}")
    
    return deduplicated


def get_best_image_per_dimension(db_path: str, advisor_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Retrieve the single best reference image for EACH dimension separately.
    This ensures diversity - each dimension gets its own best exemplar.
    
    Args:
        db_path: Path to the SQLite database
        advisor_id: Advisor to search (e.g., 'ansel')
        
    Returns:
        Dict mapping dimension name to best image for that dimension
        e.g., {'composition': {...}, 'lighting': {...}, ...}
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        result = {}
        
        for dim_name in DIMENSIONS:
            db_column = DIMENSION_TO_DB_COLUMN.get(dim_name)
            if not db_column:
                continue
            
            # Get the single best image for this dimension (score >= 8.0, ordered by score DESC)
            query = f"""
                SELECT id, image_path, composition_score, lighting_score, 
                       focus_sharpness_score, color_harmony_score,
                       subject_isolation_score, depth_perspective_score,
                       visual_balance_score, emotional_impact_score,
                       overall_grade, image_description, image_title, date_taken, embedding
                FROM dimensional_profiles
                WHERE advisor_id = ?
                  AND {db_column} >= 8.0
                  AND {db_column} IS NOT NULL
                ORDER BY {db_column} DESC
                LIMIT 1
            """
            
            cursor.execute(query, (advisor_id,))
            row = cursor.fetchone()
            
            if row:
                img_dict = dict(row)
                # Don't include raw embedding in dict to avoid log clutter
                if 'embedding' in img_dict:
                    img_dict['has_embedding'] = img_dict['embedding'] is not None
                    del img_dict['embedding']
                result[dim_name] = img_dict
        
        conn.close()
        
        logger.info(f"[CaseStudy] Retrieved best images for {len(result)}/{len(DIMENSIONS)} dimensions")
        return result
        
    except Exception as e:
        logger.error(f"Failed to retrieve best images per dimension: {e}")
        return {}


def compute_visual_relevance(user_image_path: str, ref_image_path: str) -> float:
    """
    Compute CLIP embedding similarity between user image and reference image.
    Higher similarity = more relevant reference for the user's photo.
    
    Args:
        user_image_path: Path to user's uploaded image
        ref_image_path: Path to reference image
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    try:
        from mondrian.embedding_retrieval import compute_image_embedding, cosine_similarity
        
        user_emb = compute_image_embedding(user_image_path)
        ref_emb = compute_image_embedding(ref_image_path)
        
        if user_emb is None or ref_emb is None:
            logger.warning(f"Could not compute embeddings for relevance check")
            return 0.5  # Default to moderate relevance if we can't compute
        
        similarity = cosine_similarity(user_emb, ref_emb)
        return float(similarity)
        
    except Exception as e:
        logger.warning(f"Failed to compute visual relevance: {e}")
        return 0.5  # Default to moderate relevance on error


def compute_case_studies(
    db_path: str,
    advisor_id: str,
    user_dimensions: List[Dict[str, Any]], 
    user_image_path: str = None,
    max_case_studies: int = 3,
    relevance_threshold: float = 0.25
) -> List[Dict[str, Any]]:
    """
    Compute which dimensions should get case studies based on:
    1. Gap between reference score and user score (larger = more learning opportunity)
    2. Visual relevance between user image and reference image
    3. Unique images only (first match wins for tie-breaking)
    
    Args:
        db_path: Path to the SQLite database
        advisor_id: Advisor to use for reference images
        user_dimensions: List of user's dimension scores from LLM analysis
        user_image_path: Path to user's image for relevance scoring
        max_case_studies: Maximum number of case studies to include (1-3)
        relevance_threshold: Minimum visual similarity to include (0.0-1.0)
        
    Returns:
        List of case study dicts, each containing:
        - dimension_name: Which dimension this case study is for
        - user_score: User's score in this dimension
        - ref_image: Reference image dict
        - ref_score: Reference image's score in this dimension
        - gap: ref_score - user_score
        - relevance: Visual similarity score (if computed)
    """
    # Get best reference image for each dimension
    best_per_dim = get_best_image_per_dimension(db_path, advisor_id)
    
    if not best_per_dim:
        logger.warning("[CaseStudy] No reference images found for any dimension")
        return []
    
    # Build user score lookup (normalize dimension names)
    user_scores = {}
    for dim in user_dimensions:
        dim_name = dim.get('name', '').lower().strip()
        # Normalize common variations
        dim_name = dim_name.replace(' & ', '_').replace(' and ', '_').replace(' ', '_')
        if 'focus' in dim_name:
            dim_name = 'focus_sharpness'
        elif 'color' in dim_name:
            dim_name = 'color_harmony'
        elif 'depth' in dim_name:
            dim_name = 'depth_perspective'
        elif 'balance' in dim_name:
            dim_name = 'visual_balance'
        elif 'emotion' in dim_name or 'impact' in dim_name:
            dim_name = 'emotional_impact'
        elif 'isolation' in dim_name:
            dim_name = 'subject_isolation'
        user_scores[dim_name] = dim.get('score', 10)
    
    logger.info(f"[CaseStudy] User scores: {user_scores}")
    
    # Calculate gaps and relevance for each dimension
    candidates = []
    used_image_paths = set()
    
    for dim_name, ref_img in best_per_dim.items():
        db_column = DIMENSION_TO_DB_COLUMN.get(dim_name)
        if not db_column:
            continue
            
        ref_score = ref_img.get(db_column, 0)
        user_score = user_scores.get(dim_name, 10)
        ref_path = ref_img.get('image_path', '')
        
        # Skip if this image path already used (ensures uniqueness, first match wins)
        if ref_path in used_image_paths:
            logger.info(f"[CaseStudy] Skipping {dim_name}: image '{ref_img.get('image_title')}' already used")
            continue
        
        gap = ref_score - user_score
        
        # Only consider if there's a meaningful gap (user can learn something)
        if gap <= 0:
            logger.info(f"[CaseStudy] Skipping {dim_name}: no gap (user={user_score}, ref={ref_score})")
            continue
        
        # Compute visual relevance if user image provided
        relevance = 1.0  # Default to high relevance if no user image
        if user_image_path and ref_path and os.path.exists(ref_path):
            relevance = compute_visual_relevance(user_image_path, ref_path)
            logger.info(f"[CaseStudy] {dim_name}: gap={gap:.1f}, relevance={relevance:.2f}, ref='{ref_img.get('image_title')}'")
        else:
            logger.info(f"[CaseStudy] {dim_name}: gap={gap:.1f}, relevance=N/A, ref='{ref_img.get('image_title')}'")
        
        # Filter by relevance threshold
        if relevance < relevance_threshold:
            logger.info(f"[CaseStudy] Skipping {dim_name}: relevance {relevance:.2f} below threshold {relevance_threshold}")
            continue
        
        # Mark this image as used (first match wins for tie-breaking)
        used_image_paths.add(ref_path)
        
        candidates.append({
            'dimension_name': dim_name,
            'user_score': user_score,
            'ref_image': ref_img,
            'ref_score': ref_score,
            'gap': gap,
            'relevance': relevance
        })
    
    # Sort by gap descending (largest learning opportunity first)
    candidates.sort(key=lambda x: x['gap'], reverse=True)
    
    # Take top N case studies
    selected = candidates[:max_case_studies]
    
    if selected:
        selected_info = [(c['dimension_name'], f"gap={c['gap']:.1f}", c['ref_image'].get('image_title')) for c in selected]
        logger.info(f"[CaseStudy] Selected {len(selected)} case studies: {selected_info}")
    else:
        logger.info(f"[CaseStudy] No case studies selected (no gaps or low relevance)")
    
    return selected


def get_user_dimensional_profile(db_path: str, image_path: str) -> Optional[Dict[str, float]]:
    """
    Retrieve user's dimensional profile from database if it exists.
    This allows us to do gap analysis on re-analysis or second-pass RAG.
    
    Args:
        db_path: Path to the SQLite database
        image_path: Path to the user's image
        
    Returns:
        Dictionary of dimensional scores, or None if not found
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get most recent profile for this image
        cursor.execute("""
            SELECT composition_score, lighting_score, focus_sharpness_score,
                   color_harmony_score, subject_isolation_score, depth_perspective_score,
                   visual_balance_score, emotional_impact_score
            FROM dimensional_profiles
            WHERE image_path = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (image_path,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Convert to dictionary
        user_dims = dict(row)
        logger.info(f"Retrieved user dimensional profile for {image_path}")
        return user_dims
        
    except Exception as e:
        logger.error(f"Failed to retrieve user dimensional profile: {e}")
        return None


def get_images_with_embedding_retrieval(
    db_path: str,
    advisor_id: str, 
    user_image_path: str, 
    weak_dimensions: List[str] = None, 
    user_scores: Dict[str, float] = None,
    max_images: int = 4
) -> List[Dict[str, Any]]:
    """
    Retrieve reference images using CLIP visual embeddings for semantic similarity.
    Falls back to score-based retrieval if embeddings are not available.
    
    Args:
        db_path: Path to the SQLite database
        advisor_id: Advisor to search
        user_image_path: Path to user's image for visual similarity
        weak_dimensions: User's weak dimensions for filtering
        user_scores: User's dimensional scores for gap calculation
        max_images: Maximum number of images to return
        
    Returns:
        List of reference images with base64 encoded thumbnails
    """
    try:
        # Try embedding-based retrieval first
        from mondrian.embedding_retrieval import get_images_hybrid_retrieval, get_similar_images_by_visual_embedding
        
        if user_scores and weak_dimensions:
            # Hybrid retrieval: visual similarity + dimensional gaps
            logger.info("Using hybrid embedding retrieval (visual + gap scores)")
            results = get_images_hybrid_retrieval(
                db_path, user_image_path, advisor_id,
                weak_dimensions, user_scores, top_k=max_images
            )
        else:
            # Pure visual similarity
            logger.info("Using visual embedding retrieval")
            results = get_similar_images_by_visual_embedding(
                db_path, user_image_path, advisor_id,
                weak_dimensions, top_k=max_images
            )
        
        if not results:
            logger.info("No embedding results, falling back to score-based retrieval")
            return get_images_for_weak_dimensions(db_path, advisor_id, weak_dimensions, max_images)
        
        # Encode images as URLs instead of base64
        encoded_results = []
        for img in results:
            image_path = img.get('image_path')
            if image_path and os.path.exists(image_path):
                try:
                    img_filename = os.path.basename(image_path)
                    img['image_url'] = f"/api/reference-image/{img_filename}"
                    img['image_filename'] = img_filename
                    encoded_results.append(img)
                except Exception as e:
                    logger.warning(f"Failed to process image {image_path}: {e}")
        
        logger.info(f"Retrieved {len(encoded_results)} images via embedding retrieval with URLs")
        return encoded_results
        
    except ImportError as e:
        logger.warning(f"Embedding retrieval not available: {e}")
        logger.info("Falling back to score-based retrieval")
        return get_images_for_weak_dimensions(db_path, advisor_id, weak_dimensions, max_images)
    except Exception as e:
        logger.error(f"Embedding retrieval failed: {e}")
        return get_images_for_weak_dimensions(db_path, advisor_id, weak_dimensions, max_images)


def augment_prompt_with_rag_context(
    prompt: str, 
    db_path: str,
    advisor_id: str, 
    user_dimensions: Dict[str, float] = None, 
    user_image_path: str = None
) -> tuple:
    """
    Augment the prompt with RAG context from reference images.
    If user_dimensions are provided, finds images that excel in the user's weakest areas.
    Otherwise, uses top-rated reference images.
    
    Args:
        prompt: Original prompt
        db_path: Path to the SQLite database
        advisor_id: Advisor to search for reference images
        user_dimensions: Optional dict of user's dimensional scores for gap analysis
        user_image_path: Path to user's image for visual similarity
        
    Returns:
        Tuple of (augmented_prompt, reference_images)
    """
    
    # Track used images to prevent duplicates
    used_image_paths = set()
    reference_images = []
    
    # If user dimensions are provided, do gap-based analysis
    if user_dimensions:
        # Find the user's 3 weakest dimensions
        dimension_scores = []
        for dim_name, score in user_dimensions.items():
            if score is not None and dim_name.endswith('_score'):
                clean_name = dim_name.replace('_score', '')
                dimension_scores.append((clean_name, score))
        
        # Sort by score ascending (weakest first)
        dimension_scores.sort(key=lambda x: x[1])
        weak_dimensions = [name for name, score in dimension_scores[:3]]
        
        logger.info(f"User's weakest dimensions: {weak_dimensions}")
        
        # Try embedding-based retrieval if user image path is available
        if user_image_path:
            logger.info("Using embedding-based retrieval for visually similar references")
            reference_images = get_images_with_embedding_retrieval(
                db_path, advisor_id, user_image_path, weak_dimensions, user_dimensions, max_images=4
            )
        else:
            # Fall back to score-based retrieval
            reference_images = get_images_for_weak_dimensions(db_path, advisor_id, weak_dimensions, max_images=4)
        
        # Log what we got before deduplication
        logger.info(f"Retrieved {len(reference_images)} reference images before deduplication")
        if reference_images:
            titles = [img.get('image_title', 'Unknown') for img in reference_images]
            logger.info(f"Images before dedup: {titles}")
        
        # Deduplicate images
        reference_images = deduplicate_reference_images(reference_images, used_image_paths, min_images=2)
        
        # Log after deduplication
        logger.info(f"After deduplication: {len(reference_images)} unique images")
        if reference_images:
            titles = [img.get('image_title', 'Unknown') for img in reference_images]
            logger.info(f"Images after dedup: {titles}")
        
        if not reference_images:
            logger.info("No targeted reference images found for weak dimensions - skipping RAG augmentation")
            return prompt, []
        
        # Build targeted RAG context
        rag_context = "\n\n### TARGETED REFERENCE IMAGES FOR IMPROVEMENT:\n"
        rag_context += f"Based on the analysis, here are reference images that excel in the weakest areas ({', '.join(weak_dimensions)}).\n"
        
        # Add note about visual similarity if embedding retrieval was used
        if user_image_path and any('visual_similarity' in img or 'hybrid_score' in img for img in reference_images):
            rag_context += "These images are also visually similar to your photograph, making them excellent study references.\n"
        else:
            rag_context += "Study how these master works demonstrate excellence in the dimensions where improvement is most needed.\n"
        
    else:
        # No user dimensions yet - try visual embedding retrieval first
        if user_image_path:
            logger.info("Using visual embedding retrieval for first-time analysis")
            reference_images = get_images_with_embedding_retrieval(
                db_path, advisor_id, user_image_path, weak_dimensions=None, 
                user_scores=None, max_images=3
            )
        
        # Fall back to score-based if no embedding results
        if not reference_images:
            reference_images = get_similar_images_from_db(db_path, advisor_id, top_k=3)
        
        # Deduplicate images
        reference_images = deduplicate_reference_images(reference_images, used_image_paths, min_images=2)
        
        if not reference_images:
            logger.info("No unique reference images found after deduplication - skipping RAG augmentation")
            return prompt, []
        
        # Build RAG context with reference image names and dimensional comparisons
        rag_context = "\n\n### REFERENCE IMAGES FOR COMPARATIVE ANALYSIS:\n"
        if user_image_path and any('visual_similarity' in img for img in reference_images):
            rag_context += "These master works are visually similar to your photograph and provide dimensional benchmarks.\n"
        else:
            rag_context += "These master works from the advisor's portfolio provide dimensional benchmarks.\n"
    
    # Add reference image details with case study containers
    for i, img in enumerate(reference_images, 1):
        # Use image_title (metadata name) if available, otherwise extract filename
        img_title = img.get('image_title')
        if not img_title:
            img_path = img.get('image_path', '')
            img_title = img_path.split('/')[-1] if img_path else f"Reference {i}"
        
        # Add year if available
        year = img.get('date_taken')
        if year and str(year).strip():
            img_title_with_year = f"{img_title} ({year})"
        else:
            img_title_with_year = img_title
        
        # Get image URL for inline display
        img_filename = os.path.basename(img.get('image_path', ''))
        img_url = f"/api/reference-image/{img_filename}" if img_filename else ""
        
        # Build case study container with inline image
        rag_context += f"""
<div class="case-study-container" style="
    background: #1c1c1e; 
    border-radius: 12px; 
    padding: 20px; 
    margin: 20px 0;
    border-left: 4px solid #30b0c0;
">
    <h3 style="color: #ffffff; margin-top: 0; margin-bottom: 16px; font-size: 18px;">
        Case Study #{i}: {img_title_with_year}
    </h3>
    
    <div style="display: flex; flex-direction: column; gap: 16px;">
"""
        
        # Add image if available
        if img_url:
            rag_context += f"""
        <img src="{img_url}" style="
            width: 100%; 
            max-width: 100%; 
            height: auto; 
            border-radius: 8px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        " alt="{img_title}" />
"""
        
        rag_context += """
        <div style="color: #d1d1d6; line-height: 1.6;">
"""
        
        # Add description
        if img.get('image_description'):
            rag_context += f"<p style='margin: 0 0 12px 0;'><strong>Description:</strong> {img['image_description']}</p>"
        
        # Add dimensional profile with ALL 8 dimensions
        all_dims = ['composition_score', 'lighting_score', 'focus_sharpness_score', 
                   'color_harmony_score', 'subject_isolation_score', 'depth_perspective_score',
                   'visual_balance_score', 'emotional_impact_score']
        
        if any(img.get(k) is not None for k in all_dims):
            rag_context += "<p style='margin: 0;'><strong>Technical Excellence:</strong> "
            scores = []
            
            dim_labels = {
                'composition_score': 'Composition',
                'lighting_score': 'Lighting',
                'focus_sharpness_score': 'Focus & Sharpness',
                'color_harmony_score': 'Color Harmony',
                'subject_isolation_score': 'Subject Isolation',
                'depth_perspective_score': 'Depth & Perspective',
                'visual_balance_score': 'Visual Balance',
                'emotional_impact_score': 'Emotional Impact'
            }
            
            for dim_key, dim_label in dim_labels.items():
                if img.get(dim_key) is not None:
                    scores.append(f"{dim_label} {img[dim_key]}/10")
            
            rag_context += ", ".join(scores)
            if img.get('overall_grade'):
                rag_context += f" (Grade: {img['overall_grade']})"
            rag_context += "</p>"
        
        rag_context += """
        </div>
    </div>
</div>
"""
        rag_context += "\n"
    
    # Add structured list of available reference images for case_studies field
    if reference_images:
        rag_context += "\n### AVAILABLE REFERENCE IMAGES FOR case_studies FIELD:\n"
        rag_context += "Use ONLY these images in your case_studies output (select 0-3 that are strong in user's weak areas):\n\n"
        
        dim_map = {
            'composition_score': 'Composition',
            'lighting_score': 'Lighting', 
            'focus_sharpness_score': 'Focus & Sharpness',
            'color_harmony_score': 'Color Harmony',
            'subject_isolation_score': 'Subject Isolation',
            'depth_perspective_score': 'Depth & Perspective',
            'visual_balance_score': 'Visual Balance',
            'emotional_impact_score': 'Emotional Impact'
        }
        
        for img in reference_images[:3]:  # Limit to 3 max
            img_title = img.get('image_title') or img.get('image_path', '').split('/')[-1]
            year = img.get('date_taken', 'Unknown')
            
            # List dimensions where this image excels (score >= 8)
            strong_dims = []
            for dim_key, dim_name in dim_map.items():
                score = img.get(dim_key)
                if score is not None and score >= 8:
                    strong_dims.append(f"{dim_name}({score})")
            
            if strong_dims:
                rag_context += f"- \"{img_title}\" ({year}): Excels in [{', '.join(strong_dims)}]\n"
    
    rag_context += "\n**FOR case_studies OUTPUT:** Only cite images from the list above. Match reference strengths (>=8) to user weaknesses (<=5).\n"
    
    # Augment prompt
    augmented_prompt = f"{prompt}\n{rag_context}"
    logger.info(f"Augmented prompt with RAG context ({len(rag_context)} chars, {len(reference_images)} unique references)")
    
    # Log image titles for debugging duplication
    if reference_images:
        image_titles = [img.get('image_title', img.get('image_path', '').split('/')[-1]) for img in reference_images]
        logger.info(f"Reference images used: {image_titles}")
    
    return augmented_prompt, reference_images


def augment_prompt_for_pass2(prompt: str, weak_dimensions: List[Dict],
                             reference_images: List[Dict], 
                             book_passages: List[Dict]) -> str:
    """
    Augment the full analysis prompt with targeted RAG context for Pass 2.
    
    Args:
        prompt: Base prompt to augment
        weak_dimensions: List of weak dimension dicts with 'name' and 'score'
        reference_images: List of reference image dicts
        book_passages: List of book passage dicts
        
    Returns:
        Augmented prompt string
    """
    rag_context = "\n\n### TARGETED GUIDANCE FOR YOUR WEAKEST AREAS:\n"
    
    weak_names = [d['name'] for d in weak_dimensions]
    rag_context += f"Focus your feedback on these dimensions where improvement is most needed: **{', '.join(weak_names)}**\n"
    
    # Add book passages
    if book_passages:
        rag_context += "\n#### TECHNICAL GUIDANCE FROM MY WRITINGS:\n"
        for passage in book_passages:
            book_title = passage['book_title']
            text = passage['passage_text']
            dims = passage['dimensions']
            rag_context += f"\n**From \"{book_title}\" (relevant to: {', '.join(dims)}):**\n"
            rag_context += f"> {text}\n"
        
        rag_context += "\n**CRITICAL INSTRUCTION:** Reference these passages ONLY when discussing their tagged dimensions. "
        rag_context += "Zone System references MUST ONLY appear in Lighting dimension feedback. "
        rag_context += "Cite as: 'As I wrote in The Print...' or 'In The Camera, I discussed...'\n"
    
    # Add reference images
    if reference_images:
        rag_context += "\n#### REFERENCE IMAGES THAT EXCEL IN YOUR WEAK AREAS:\n"
        rag_context += "Study how these master works demonstrate excellence:\n\n"
        
        for i, img in enumerate(reference_images[:3], 1):
            img_title = img.get('image_title') or img.get('image_path', '').split('/')[-1]
            year = img.get('date_taken', '')
            
            # Find which weak dimensions this image excels in
            excels_in = []
            for weak in weak_dimensions:
                dim_col = f"{weak['name']}_score"
                score = img.get(dim_col, 0)
                if score and score >= 8:
                    excels_in.append(f"{weak['name']}({score})")
            
            if excels_in:
                rag_context += f"- **\"{img_title}\"** ({year}): Excels in {', '.join(excels_in)}\n"
                if img.get('image_description'):
                    rag_context += f"  {img['image_description'][:150]}...\n"
        
        rag_context += "\n**INSTRUCTION:** Reference these images as examples of excellence. "
        rag_context += "Mention them by name when discussing how to improve the weak dimensions.\n"
    
    # Add final reminder about dimension-specific techniques
    rag_context += "\n**CRITICAL REMINDER:** Zone System is ONLY for Lighting dimension. "
    rag_context += "Do NOT mention Zone System in recommendations for Composition, Focus, Color, Balance, or other non-lighting dimensions.\n"
    
    return prompt + rag_context
