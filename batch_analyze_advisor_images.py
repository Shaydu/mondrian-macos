#!/usr/bin/env python3
"""
Batch Dimensional Analysis for Advisor Reference Images

This script:
1. Finds all advisor reference images
2. Analyzes each with AI Advisor Service (without RAG)
3. Dimensional profiles are automatically extracted and saved
4. Verifies scores are populated in database

Usage:
    python batch_analyze_advisor_images.py --advisor ansel
    python batch_analyze_advisor_images.py --advisor all
    python batch_analyze_advisor_images.py --advisor ansel --verify-only
"""

import os
import requests
import time
from pathlib import Path
import sqlite3
import argparse
import json

AI_ADVISOR_URL = "http://127.0.0.1:5100/analyze"
DB_PATH = "mondrian.db"

ADVISOR_DIRS = {
    "ansel": "mondrian/source/advisor/photographer/ansel",
    "okeefe": "mondrian/source/advisor/painter/okeefe",
    "mondrian": "mondrian/source/advisor/painter/mondrian",
    "gehry": "mondrian/source/advisor/architect/gehry",
    "vangogh": "mondrian/source/advisor/painter/vangogh"
}

def analyze_image(image_path, advisor_id):
    """Analyze image with AI Advisor Service"""
    # Convert to absolute path to avoid path resolution issues
    abs_path = str(image_path.resolve())
    payload = {
        "advisor": advisor_id,
        "image_path": abs_path,
        "enable_rag": "false"  # Don't use RAG when indexing reference images
    }
    
    try:
        print(f"  [INFO] Analyzing: {image_path.name}")
        resp = requests.post(AI_ADVISOR_URL, json=payload, timeout=120)
        
        if resp.status_code == 200:
            print(f"  [OK] Analysis complete: {image_path.name}")
            return True
        else:
            print(f"  [ERROR] Analysis failed: {resp.status_code}")
            print(f"  [ERROR] Response: {resp.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  [ERROR] Timeout analyzing {image_path.name} (>120s)")
        return False
    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] Connection failed - is AI Advisor Service running on port 5100?")
        return False
    except Exception as e:
        print(f"  [ERROR] Exception analyzing {image_path.name}: {e}")
        return False

def verify_dimensional_profile(image_path):
    """Verify that dimensional profile was created with valid scores"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Use absolute resolved path to match what was saved by AI service
    abs_path = str(image_path.resolve())
    
    cursor.execute("""
        SELECT composition_score, lighting_score, overall_grade, created_at
        FROM dimensional_profiles 
        WHERE image_path = ? 
        ORDER BY created_at DESC 
        LIMIT 1
    """, (abs_path,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print(f"  [WARN] No dimensional profile found for {image_path.name}")
        return False
    
    comp_score, light_score, overall, created_at = result
    
    if comp_score is None or light_score is None or overall is None:
        print(f"  [WARN] Dimensional profile has NULL scores for {image_path.name}")
        print(f"  [WARN] Created at: {created_at}")
        return False
    
    print(f"  [OK] Valid profile: comp={comp_score:.1f}, light={light_score:.1f}, overall={overall:.1f}")
    return True

def get_existing_profiles(advisor_id):
    """Get count of existing profiles for an advisor"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get profiles with valid scores
    cursor.execute("""
        SELECT COUNT(*) 
        FROM dimensional_profiles 
        WHERE advisor_id = ? 
        AND composition_score IS NOT NULL
    """, (advisor_id,))
    
    valid_count = cursor.fetchone()[0]
    
    # Get profiles with NULL scores
    cursor.execute("""
        SELECT COUNT(*) 
        FROM dimensional_profiles 
        WHERE advisor_id = ? 
        AND composition_score IS NULL
    """, (advisor_id,))
    
    null_count = cursor.fetchone()[0]
    
    conn.close()
    
    return valid_count, null_count

def verify_only(advisor_id):
    """Verify existing profiles without re-analyzing"""
    if advisor_id not in ADVISOR_DIRS:
        print(f"[ERROR] Unknown advisor: {advisor_id}")
        return
    
    advisor_dir = Path(ADVISOR_DIRS[advisor_id])
    
    if not advisor_dir.exists():
        print(f"[ERROR] Directory not found: {advisor_dir}")
        return
    
    # Find all images
    img_exts = {".jpg", ".jpeg", ".png"}
    image_files = [p for p in advisor_dir.rglob("*") if p.suffix.lower() in img_exts]
    
    print(f"\n{'='*70}")
    print(f"Verification Report: {advisor_id}")
    print(f"{'='*70}")
    print(f"Directory: {advisor_dir}")
    print(f"Images found: {len(image_files)}")
    
    valid_count, null_count = get_existing_profiles(advisor_id)
    print(f"Profiles with valid scores: {valid_count}")
    print(f"Profiles with NULL scores: {null_count}")
    print(f"{'='*70}\n")
    
    verified_count = 0
    missing_count = 0
    null_score_count = 0
    
    for img_path in image_files:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Use absolute resolved path to match what was saved by AI service
        abs_path = str(img_path.resolve())
        
        cursor.execute("""
            SELECT composition_score, lighting_score, overall_grade 
            FROM dimensional_profiles 
            WHERE image_path = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (abs_path,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            print(f"❌ MISSING: {img_path.name}")
            missing_count += 1
        elif result[0] is None or result[1] is None or result[2] is None:
            print(f"⚠️  NULL SCORES: {img_path.name}")
            null_score_count += 1
        else:
            print(f"✅ VALID: {img_path.name} (comp={result[0]:.1f}, light={result[1]:.1f}, overall={result[2]:.1f})")
            verified_count += 1
    
    print(f"\n{'='*70}")
    print(f"Verification Summary: {advisor_id}")
    print(f"{'='*70}")
    print(f"✅ Valid profiles:   {verified_count}/{len(image_files)}")
    print(f"⚠️  NULL scores:      {null_score_count}/{len(image_files)}")
    print(f"❌ Missing profiles: {missing_count}/{len(image_files)}")
    print(f"{'='*70}\n")
    
    if null_score_count > 0 or missing_count > 0:
        print(f"⚠️  Re-run without --verify-only to analyze missing/NULL images")

def batch_analyze_advisor(advisor_id, skip_existing=True):
    """Batch analyze all images for an advisor"""
    
    if advisor_id not in ADVISOR_DIRS:
        print(f"[ERROR] Unknown advisor: {advisor_id}")
        return
    
    advisor_dir = Path(ADVISOR_DIRS[advisor_id])
    
    if not advisor_dir.exists():
        print(f"[ERROR] Directory not found: {advisor_dir}")
        return
    
    # Find all images
    img_exts = {".jpg", ".jpeg", ".png"}
    image_files = [p for p in advisor_dir.rglob("*") if p.suffix.lower() in img_exts]
    
    # Filter out images that already have valid profiles
    if skip_existing:
        images_to_analyze = []
        for img_path in image_files:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # Use absolute resolved path to match what was saved by AI service
            abs_path = str(img_path.resolve())
            cursor.execute("""
                SELECT composition_score 
                FROM dimensional_profiles 
                WHERE image_path = ? 
                AND composition_score IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
            """, (abs_path,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                images_to_analyze.append(img_path)
        
        skipped_count = len(image_files) - len(images_to_analyze)
    else:
        images_to_analyze = image_files
        skipped_count = 0
    
    print(f"\n{'='*70}")
    print(f"Batch Dimensional Analysis: {advisor_id}")
    print(f"{'='*70}")
    print(f"Directory: {advisor_dir}")
    print(f"Total images: {len(image_files)}")
    print(f"Already analyzed: {skipped_count}")
    print(f"To analyze: {len(images_to_analyze)}")
    print(f"{'='*70}\n")
    
    if not images_to_analyze:
        print("✅ All images already have valid dimensional profiles!")
        return
    
    success_count = 0
    failed_count = 0
    verified_count = 0
    
    for i, img_path in enumerate(images_to_analyze, 1):
        print(f"\n[{i}/{len(images_to_analyze)}] {img_path.name}")
        print(f"{'─'*70}")
        
        # Analyze image
        if analyze_image(img_path, advisor_id):
            success_count += 1
            
            # Verify dimensional profile
            if verify_dimensional_profile(img_path):
                verified_count += 1
        else:
            failed_count += 1
    
    print(f"\n{'='*70}")
    print(f"Batch Analysis Complete: {advisor_id}")
    print(f"{'='*70}")
    print(f"✅ Analysis succeeded: {success_count}/{len(images_to_analyze)}")
    print(f"❌ Analysis failed:    {failed_count}/{len(images_to_analyze)}")
    print(f"✅ Profiles verified:  {verified_count}/{len(images_to_analyze)}")
    print(f"{'='*70}\n")
    
    if verified_count < success_count:
        print(f"⚠️  Warning: {success_count - verified_count} profiles were not verified")
        print(f"⚠️  Run with --verify-only to check all profiles")

def main():
    parser = argparse.ArgumentParser(
        description="Batch analyze advisor reference images for dimensional RAG"
    )
    parser.add_argument(
        "--advisor",
        type=str,
        required=True,
        choices=list(ADVISOR_DIRS.keys()) + ["all"],
        help="Advisor to analyze (or 'all' for all advisors)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing profiles, don't analyze new images"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-analyze all images, even if they already have profiles"
    )
    args = parser.parse_args()
    
    if args.verify_only:
        if args.advisor == "all":
            for advisor_id in ADVISOR_DIRS.keys():
                verify_only(advisor_id)
        else:
            verify_only(args.advisor)
    else:
        if args.advisor == "all":
            for advisor_id in ADVISOR_DIRS.keys():
                batch_analyze_advisor(advisor_id, skip_existing=not args.force)
        else:
            batch_analyze_advisor(args.advisor, skip_existing=not args.force)

if __name__ == "__main__":
    main()

