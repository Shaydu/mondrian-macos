#!/usr/bin/env python3
"""
Diagnose Reference Image Selection Issues
==========================================
Analyzes the last job to understand why only one reference image appears
and why it's always the same one.
"""

import sqlite3
import json
import os
from typing import List, Dict, Any

DB_PATH = "mondrian.db"

def get_last_job():
    """Get the most recent job from the database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT job_id, image_path, advisor, mode, status, 
               created_at, completed_at, result
        FROM jobs
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("❌ No jobs found in database")
        return None
    
    return dict(row)

def extract_user_dimensions(result_json):
    """Extract dimensional scores from job result"""
    if not result_json:
        return None
    
    try:
        result = json.loads(result_json)
        dimensions = result.get('dimensions', [])
        
        user_dims = {}
        for dim in dimensions:
            name = dim.get('name', '').lower().replace(' ', '_').replace('&', '').replace('__', '_').strip('_')
            score = dim.get('score')
            if name and score is not None:
                user_dims[f"{name}_score"] = score
        
        return user_dims
    except Exception as e:
        print(f"⚠️  Failed to parse result JSON: {e}")
        return None

def get_weak_dimensions(user_dims):
    """Identify the 3 weakest dimensions"""
    if not user_dims:
        return []
    
    scores = [(k.replace('_score', ''), v) for k, v in user_dims.items() if k.endswith('_score')]
    scores.sort(key=lambda x: x[1])
    return [name for name, score in scores[:3]]

def check_embeddings_status(advisor_id):
    """Check how many reference images have embeddings"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) as with_clip,
            SUM(CASE WHEN text_embedding IS NOT NULL THEN 1 ELSE 0 END) as with_text,
            SUM(CASE WHEN composition_score IS NOT NULL THEN 1 ELSE 0 END) as with_scores
        FROM dimensional_profiles
        WHERE advisor_id = ?
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row)

def get_reference_images_by_score(advisor_id, top_k=10):
    """Get top reference images by average score"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, image_path, image_title, date_taken,
               composition_score, lighting_score, focus_sharpness_score,
               color_harmony_score, subject_isolation_score, 
               depth_perspective_score, visual_balance_score, 
               emotional_impact_score,
               (composition_score + lighting_score + focus_sharpness_score + color_harmony_score) / 4.0 as avg_score,
               CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END as has_embedding
        FROM dimensional_profiles
        WHERE advisor_id = ?
          AND composition_score IS NOT NULL
        ORDER BY avg_score DESC
        LIMIT ?
    """, (advisor_id, top_k))
    
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return rows

def get_images_for_weak_dimensions(advisor_id, weak_dimensions, min_score=8.0):
    """Simulate the _get_images_for_weak_dimensions method"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
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
        'emotion': 'emotional_impact_score',
    }
    
    # Build SQL to find images that excel (>=8) in any of the weak dimensions
    conditions = []
    for dim in weak_dimensions:
        col = dim_to_col.get(dim.lower())
        if col:
            conditions.append(f"{col} >= {min_score}")
    
    if not conditions:
        print(f"⚠️  No matching columns found for weak dimensions: {weak_dimensions}")
        return []
    
    where_clause = f"({' OR '.join(conditions)})"
    
    query = f"""
        SELECT id, image_path, image_title, date_taken,
               composition_score, lighting_score, focus_sharpness_score,
               color_harmony_score, subject_isolation_score,
               depth_perspective_score, visual_balance_score,
               emotional_impact_score,
               CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END as has_embedding
        FROM dimensional_profiles
        WHERE advisor_id = ?
          AND composition_score IS NOT NULL
          AND {where_clause}
        ORDER BY (composition_score + lighting_score + focus_sharpness_score + color_harmony_score) / 4.0 DESC
        LIMIT 10
    """
    
    cursor.execute(query, (advisor_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return rows

def simulate_visual_embedding_retrieval(advisor_id, weak_dimensions, user_image_path):
    """Check what would be returned by visual embedding retrieval"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
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
    
    # Build score filters for weak dimensions
    score_filters = []
    if weak_dimensions:
        for dim in weak_dimensions:
            col = dim_to_col.get(dim.lower())
            if col:
                score_filters.append(f"{col} >= 8.0")
    
    where_clause = f"WHERE advisor_id = ? AND embedding IS NOT NULL AND composition_score IS NOT NULL"
    if score_filters:
        where_clause += f" AND ({' OR '.join(score_filters)})"
    
    query = f"""
        SELECT id, image_path, image_title, date_taken,
               composition_score, lighting_score, focus_sharpness_score,
               color_harmony_score, subject_isolation_score,
               depth_perspective_score, visual_balance_score,
               emotional_impact_score,
               1 as has_embedding
        FROM dimensional_profiles
        {where_clause}
    """
    
    cursor.execute(query, (advisor_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    return rows

def simulate_deduplication(images, used_paths=None, min_images=2):
    """Simulate the deduplication logic"""
    if used_paths is None:
        used_paths = set()
    
    original_count = len(images)
    deduplicated = []
    skipped = []
    
    for img in images:
        img_path = img.get('image_path')
        if img_path and img_path not in used_paths:
            used_paths.add(img_path)
            deduplicated.append(img)
        else:
            skipped.append(img)
    
    # Check if we need to add back duplicates
    added_back = []
    if len(deduplicated) < min_images and len(images) > len(deduplicated):
        for img in images:
            if len(deduplicated) >= min_images:
                break
            img_path = img.get('image_path')
            if img_path and img_path in used_paths:
                deduplicated.append(img)
                added_back.append(img)
    
    return {
        'original_count': original_count,
        'deduplicated': deduplicated,
        'skipped': skipped,
        'added_back': added_back,
        'final_count': len(deduplicated)
    }

def main():
    print("=" * 80)
    print("REFERENCE IMAGE SELECTION DIAGNOSTIC")
    print("=" * 80)
    print()
    
    # Get last job
    print("📋 STEP 1: Fetching last job from database...")
    print("-" * 80)
    job = get_last_job()
    
    if not job:
        return
    
    print(f"✓ Job ID: {job['job_id']}")
    print(f"✓ Image: {job['image_path']}")
    print(f"✓ Advisor: {job['advisor']}")
    print(f"✓ Mode: {job['mode']}")
    print(f"✓ Status: {job['status']}")
    print()
    
    # Extract dimensional scores
    print("📊 STEP 2: Extracting user dimensional scores...")
    print("-" * 80)
    user_dims = extract_user_dimensions(job['result'])
    
    if not user_dims:
        print("⚠️  No dimensional scores found in result")
        print()
    else:
        print("✓ User dimensional scores:")
        for dim, score in sorted(user_dims.items(), key=lambda x: x[1]):
            print(f"  - {dim}: {score}")
        print()
        
        weak_dimensions = get_weak_dimensions(user_dims)
        print(f"✓ User's 3 weakest dimensions: {weak_dimensions}")
        print()
    
    # Check embeddings status
    print("🔍 STEP 3: Checking embeddings status...")
    print("-" * 80)
    embedding_status = check_embeddings_status(job['advisor'])
    print(f"✓ Total reference images: {embedding_status['total']}")
    print(f"✓ With CLIP embeddings: {embedding_status['with_clip']}")
    print(f"✓ With text embeddings: {embedding_status['with_text']}")
    print(f"✓ With dimensional scores: {embedding_status['with_scores']}")
    print()
    
    if embedding_status['with_clip'] == 0:
        print("❌ NO EMBEDDINGS FOUND!")
        print("   This is why visual similarity retrieval is failing.")
        print("   Run: python3 scripts/compute_embeddings.py --advisor ansel")
        print()
    
    # Get top reference images by score
    print("🏆 STEP 4: Top 10 reference images (by average score)...")
    print("-" * 80)
    top_images = get_reference_images_by_score(job['advisor'], top_k=10)
    
    if not top_images:
        print("❌ No reference images found!")
        print()
    else:
        for i, img in enumerate(top_images, 1):
            title = img['image_title'] or os.path.basename(img['image_path'])
            print(f"{i}. {title} (avg: {img['avg_score']:.1f}, embedding: {'✓' if img['has_embedding'] else '✗'})")
            print(f"   C:{img['composition_score']} L:{img['lighting_score']} "
                  f"F:{img['focus_sharpness_score']} CH:{img['color_harmony_score']}")
        print()
    
    # Simulate score-based retrieval for weak dimensions
    if user_dims and weak_dimensions:
        print("🎯 STEP 5: Images that excel in weak dimensions (score >= 8.0)...")
        print("-" * 80)
        print(f"Looking for images with high scores in: {weak_dimensions}")
        print()
        
        weak_dim_images = get_images_for_weak_dimensions(job['advisor'], weak_dimensions)
        
        if not weak_dim_images:
            print("❌ NO IMAGES FOUND that score >= 8.0 in any weak dimension!")
            print("   This explains why you're not getting varied references.")
            print()
            print("   Possible causes:")
            print("   1. Reference images don't have high scores in these dimensions")
            print("   2. Threshold of 8.0 is too strict")
            print("   3. Not enough reference images indexed")
            print()
        else:
            print(f"✓ Found {len(weak_dim_images)} images:")
            for i, img in enumerate(weak_dim_images, 1):
                title = img['image_title'] or os.path.basename(img['image_path'])
                print(f"\n{i}. {title} (embedding: {'✓' if img['has_embedding'] else '✗'})")
                
                # Show scores for each weak dimension
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
                    'emotion': 'emotional_impact_score',
                }
                
                for weak_dim in weak_dimensions:
                    col = dim_to_col.get(weak_dim.lower())
                    if col:
                        score = img.get(col)
                        indicator = "✓" if score and score >= 8.0 else " "
                        print(f"   {indicator} {weak_dim}: {score}")
            print()
            
            # Simulate deduplication
            print("🔄 STEP 6: Simulating deduplication...")
            print("-" * 80)
            dedup_result = simulate_deduplication(weak_dim_images, used_paths=set(), min_images=2)
            
            print(f"✓ Original count: {dedup_result['original_count']}")
            print(f"✓ After deduplication: {dedup_result['final_count']}")
            print(f"✓ Skipped (duplicates): {len(dedup_result['skipped'])}")
            print(f"✓ Added back to meet minimum: {len(dedup_result['added_back'])}")
            print()
            
            if dedup_result['final_count'] <= 1:
                print("❌ PROBLEM IDENTIFIED: Only 1 unique image after deduplication!")
                print()
                print("   Reasons:")
                if dedup_result['original_count'] == 1:
                    print("   1. Only 1 image meets the criteria (score >= 8.0 in weak dims)")
                else:
                    print("   1. Multiple images retrieved but they're duplicates")
                    print(f"      Original: {dedup_result['original_count']}")
                    print(f"      Unique: {len(dedup_result['deduplicated'])}")
                print()
            
            print("📸 Final deduplicated images:")
            for i, img in enumerate(dedup_result['deduplicated'][:4], 1):
                title = img['image_title'] or os.path.basename(img['image_path'])
                print(f"  {i}. {title}")
            print()
    
    # Simulate visual embedding retrieval if embeddings exist
    if user_dims and weak_dimensions and embedding_status['with_clip'] > 0:
        print("🖼️  STEP 7: Simulating visual embedding retrieval...")
        print("-" * 80)
        print(f"Checking images with embeddings AND scores >= 8.0 in: {weak_dimensions}")
        print()
        
        embedding_images = simulate_visual_embedding_retrieval(
            job['advisor'], weak_dimensions, job['image_path']
        )
        
        if not embedding_images:
            print("❌ NO IMAGES with both embeddings AND high scores in weak dimensions!")
            print()
            print("   This means:")
            print("   1. Images with embeddings don't score >= 8.0 in weak dimensions")
            print("   2. OR images that score high don't have embeddings computed")
            print()
        else:
            print(f"✓ Found {len(embedding_images)} candidates for visual similarity:")
            for i, img in enumerate(embedding_images[:10], 1):
                title = img['image_title'] or os.path.basename(img['image_path'])
                print(f"  {i}. {title}")
            print()
            print("   Note: Visual similarity would then rank these by CLIP embedding cosine similarity")
            print()
    
    # Summary
    print("=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)
    print()
    
    if embedding_status['with_clip'] == 0:
        print("❌ PRIMARY ISSUE: No embeddings computed")
        print("   → Run: python3 scripts/compute_embeddings.py --advisor ansel")
        print()
    
    if user_dims and weak_dimensions:
        weak_dim_images = get_images_for_weak_dimensions(job['advisor'], weak_dimensions)
        if len(weak_dim_images) <= 1:
            print("❌ SECONDARY ISSUE: Only 1 image scores >= 8.0 in weak dimensions")
            print(f"   Weak dimensions: {weak_dimensions}")
            print("   → Need more diverse reference images with high scores")
            print("   → OR lower the threshold from 8.0 to 7.0")
            print()
    
    print("✓ Diagnostic complete")
    print()

if __name__ == "__main__":
    main()
