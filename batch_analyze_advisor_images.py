#!/usr/bin/env python3
"""
Batch Dimensional Analysis for Training Dataset Images + Advisor Reference Images

This script:
1. Finds all training dataset images (new 24 + existing from augmented set)
2. Analyzes each with AI Advisor Service (without RAG)
3. Dimensional profiles are automatically extracted and saved
4. Exports profiles to JSON index for dimension-aware RAG
5. Tags book passages by dimension relevance
6. Verifies scores are populated in database

Usage:
    python batch_analyze_advisor_images.py --source training
    python batch_analyze_advisor_images.py --source advisor --advisor ansel
    python batch_analyze_advisor_images.py --source all
    python batch_analyze_advisor_images.py --source training --verify-only
    python batch_analyze_advisor_images.py --source training --export-index
"""

import os
import requests
import time
from pathlib import Path
import sqlite3
import argparse
import json
import re

AI_ADVISOR_URL = "http://127.0.0.1:5100/analyze"
DB_PATH = "mondrian.db"

# Training dataset locations
TRAINING_IMAGE_DIR = "training/20260121-qwen3-vl-4b"
TRAINING_ANALYSIS_FILE = "training/20260121-qwen3-vl-4b/analysis/all_images_analysis.json"
TRAINING_JSONL_TRAIN = "training/20260121-qwen3-vl-4b/augmented_training_data_train.jsonl"

# Legacy advisor directories
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

def load_training_analysis():
    """Load pre-analyzed dimensional profiles from training dataset"""
    analysis_file = Path(TRAINING_ANALYSIS_FILE)
    
    if not analysis_file.exists():
        print(f"[ERROR] Training analysis file not found: {analysis_file}")
        return None
    
    try:
        with open(analysis_file, 'r') as f:
            analysis = json.load(f)
        print(f"[OK] Loaded analysis for {sum(len(v) for v in analysis.values())} images")
        return analysis
    except Exception as e:
        print(f"[ERROR] Failed to load training analysis: {e}")
        return None

def extract_quotes_from_jsonl(jsonl_file):
    """Extract quotes/passages from training JSONL file"""
    quotes = {}
    try:
        with open(jsonl_file, 'r') as f:
            for i, line in enumerate(f):
                try:
                    example = json.loads(line)
                    # Assuming assistant response contains passages
                    assistant_content = example.get('messages', [{}])[-1].get('content', '')
                    if assistant_content and len(assistant_content) > 50:
                        quotes[f"passage_{i}"] = {
                            "text": assistant_content[:200],  # First 200 chars
                            "source": example.get('photographer', 'Unknown'),
                            "image": example.get('image_path', 'Unknown')
                        }
                except json.JSONDecodeError:
                    continue
        print(f"[OK] Extracted {len(quotes)} passages from JSONL")
        return quotes
    except Exception as e:
        print(f"[ERROR] Failed to extract quotes: {e}")
        return {}

def tag_quotes_by_dimension(quotes, dimensions_map):
    """Tag extracted quotes by which dimensions they address"""
    dimension_keywords = {
        "Composition": ["composition", "framing", "leading line", "balance", "placement"],
        "Lighting": ["lighting", "light", "shadow", "exposure", "tonal", "zone system", "metering"],
        "Focus & Sharpness": ["focus", "sharpness", "depth of field", "aperture", "f-stop"],
        "Color Harmony": ["color", "tone", "monochrome", "harmony", "saturation"],
        "Depth & Perspective": ["depth", "perspective", "foreground", "background", "distance"],
        "Visual Balance": ["balance", "weight", "visual", "symmetry"],
        "Emotional Impact": ["emotion", "impact", "mood", "feeling", "resonance"],
        "Technical Execution": ["technical", "execution", "craft", "mastery"],
        "Subject Matter": ["subject", "matter", "content", "theme"]
    }
    
    tagged_quotes = []
    for quote_id, quote_data in quotes.items():
        text = quote_data['text'].lower()
        matching_dims = []
        
        for dim, keywords in dimension_keywords.items():
            if any(kw in text for kw in keywords):
                matching_dims.append(dim)
        
        if matching_dims:
            tagged_quotes.append({
                "id": quote_id,
                "text": quote_data['text'],
                "source": quote_data['source'],
                "image": quote_data['image'],
                "primary_dimension": matching_dims[0] if matching_dims else None,
                "secondary_dimensions": matching_dims[1:] if len(matching_dims) > 1 else []
            })
    
    return tagged_quotes

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

def batch_analyze_training_dataset(skip_existing=True):
    """Batch analyze all images from the training dataset"""
    
    # Check if analysis file exists
    analysis_file = Path(TRAINING_ANALYSIS_FILE)
    if not analysis_file.exists():
        print(f"[ERROR] Training analysis file not found: {analysis_file}")
        print(f"[ERROR] Please run phase2_generate_training_data.py first")
        return
    
    # Load existing analysis
    analysis = load_training_analysis()
    if not analysis:
        return
    
    # Flatten all images from analysis
    all_images = {}
    for category, images in analysis.items():
        for img_data in images:
            img_path = f"training/20260121-qwen3-vl-4b/photos/{category}/{img_data['filename']}"
            all_images[img_path] = img_data
    
    print(f"\n{'='*70}")
    print(f"Batch Analysis: Training Dataset")
    print(f"{'='*70}")
    print(f"Total images: {len(all_images)}")
    print(f"{'='*70}\n")
    
    # Export dimensional index (pre-analyzed)
    export_dimensional_index(analysis)
    
    # Extract and tag quotes
    extract_and_tag_quotes()

def extract_and_tag_quotes():
    """Extract quotes from training data and tag by dimension"""
    jsonl_file = Path(TRAINING_JSONL_TRAIN)
    
    if not jsonl_file.exists():
        print(f"[WARN] Training JSONL not found: {jsonl_file}")
        return
    
    print(f"\n[INFO] Extracting quotes from {jsonl_file.name}...")
    quotes = extract_quotes_from_jsonl(str(jsonl_file))
    
    if not quotes:
        print(f"[WARN] No quotes extracted from training data")
        return
    
    # Tag quotes by dimension
    print(f"[INFO] Tagging quotes by dimension relevance...")
    tagged_quotes = tag_quotes_by_dimension(quotes, None)
    
    # Save tagged quotes
    output_file = Path(TRAINING_IMAGE_DIR) / "quotes_dimension_tagged.json"
    with open(output_file, 'w') as f:
        json.dump({
            "total_quotes": len(tagged_quotes),
            "quotes": tagged_quotes
        }, f, indent=2)
    print(f"[OK] Saved {len(tagged_quotes)} tagged quotes to {output_file}")

def export_dimensional_index(analysis):
    """Export dimensional analysis to JSON index for RAG"""
    
    index = {
        "metadata": {
            "created": str(Path.cwd()),
            "total_images": sum(len(v) for v in analysis.values()),
            "source": "training_dataset"
        },
        "images": []
    }
    
    # Flatten analysis structure
    for category, images in analysis.items():
        for img_data in images:
            image_entry = {
                "filename": img_data['filename'],
                "category": category,
                "photographer": img_data['photographer'],
                "overall_score": img_data['overall'],
                "dimensions": img_data['scores'],
                "strengths": [dim for dim, score in img_data['scores'].items() if score >= 8],
                "weaknesses": [dim for dim, score in img_data['scores'].items() if score < 7]
            }
            index["images"].append(image_entry)
    
    # Save index
    output_file = Path(TRAINING_IMAGE_DIR) / "image_index.json"
    with open(output_file, 'w') as f:
        json.dump(index, f, indent=2)
    print(f"[OK] Exported dimensional index: {output_file}")
    print(f"[OK] Index contains {index['metadata']['total_images']} images")

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

def verify_only(source, advisor_id=None):
    """Verify existing profiles without re-analyzing"""
    
    if source == "training":
        # Verify training dataset
        analysis = load_training_analysis()
        if not analysis:
            return
        
        total_images = sum(len(v) for v in analysis.values())
        print(f"\n{'='*70}")
        print(f"Verification Report: Training Dataset")
        print(f"{'='*70}")
        print(f"Total images found: {total_images}")
        
        # Check for index files
        index_file = Path(TRAINING_IMAGE_DIR) / "image_index.json"
        quotes_file = Path(TRAINING_IMAGE_DIR) / "quotes_dimension_tagged.json"
        
        print(f"Index file exists: {'✅' if index_file.exists() else '❌'}")
        print(f"Quotes file exists: {'✅' if quotes_file.exists() else '❌'}")
        print(f"{'='*70}\n")
        
    elif source == "advisor" and advisor_id:
        # Verify legacy advisor directory
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
        description="Analyze training dataset and advisor reference images for dimensional RAG"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["training", "advisor", "all"],
        help="Image source: training dataset, advisor references, or both"
    )
    parser.add_argument(
        "--advisor",
        type=str,
        choices=list(ADVISOR_DIRS.keys()),
        help="Specific advisor (required when --source=advisor)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing profiles, don't analyze new images"
    )
    parser.add_argument(
        "--export-index",
        action="store_true",
        help="Export dimensional index and quote tags from training data"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-analyze all images, even if they already have profiles"
    )
    args = parser.parse_args()
    
    # Validate arguments
    if args.source == "advisor" and not args.advisor:
        parser.error("--advisor is required when --source=advisor")
    
    if args.verify_only:
        if args.source == "training":
            verify_only("training")
        elif args.source == "advisor":
            verify_only("advisor", args.advisor)
        elif args.source == "all":
            verify_only("training")
            for advisor_id in ADVISOR_DIRS.keys():
                verify_only("advisor", advisor_id)
    else:
        if args.source == "training":
            batch_analyze_training_dataset(skip_existing=not args.force)
        elif args.source == "advisor":
            batch_analyze_advisor(args.advisor, skip_existing=not args.force)
        elif args.source == "all":
            batch_analyze_training_dataset(skip_existing=not args.force)
            for advisor_id in ADVISOR_DIRS.keys():
                batch_analyze_advisor(advisor_id, skip_existing=not args.force)

if __name__ == "__main__":
    main()

