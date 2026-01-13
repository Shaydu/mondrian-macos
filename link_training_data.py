#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Link Training Data - Maps Analysis Files to Source Images via Database

This script uses the mondrian.db job records to create a mapping between:
  - Source images (from filename column)
  - Analysis markdown files (from analysis_markdown column)
  - Advisor information (from advisor column)

The key insight: The jobs table contains the authoritative mapping of which
image was analyzed by which advisor, and where the output was stored.

Usage:
    python link_training_data.py \
        --db_path ./mondrian/mondrian.db \
        --advisor ansel \
        --output_dir ./training_data \
        --output_file training_data_manifest.json

Output:
    training_data_manifest.json - Maps all image-analysis pairs by advisor
"""

import sqlite3
import json
import os
import argparse
from pathlib import Path
from typing import Dict, List, Optional


def query_job_records(db_path: str, advisor: Optional[str] = None) -> List[Dict]:
    """
    Query mondrian.db for completed job records.
    
    Returns records with:
    - id: Job ID
    - filename: Source image filename (relative to mondrian/source/)
    - advisor: Advisor name (e.g., "ansel")
    - status: Job status (should be "completed")
    - analysis_markdown: Path where markdown analysis was stored
    - completed_at: Completion timestamp
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query completed jobs
    if advisor:
        query = """
            SELECT id, filename, advisor, status, analysis_markdown, 
                   completed_at, created_at
            FROM jobs
            WHERE status = 'completed' 
              AND advisor = ?
            ORDER BY completed_at DESC
        """
        cursor.execute(query, (advisor,))
    else:
        query = """
            SELECT id, filename, advisor, status, analysis_markdown, 
                   completed_at, created_at
            FROM jobs
            WHERE status = 'completed'
            ORDER BY advisor, completed_at DESC
        """
        cursor.execute(query)
    
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return records


def resolve_paths(record: Dict, source_dir: str, analysis_dir: str) -> Dict:
    """
    Resolve relative paths to absolute paths.
    
    Args:
        record: Job record from database
        source_dir: Base directory for source images (e.g., mondrian/source)
        analysis_dir: Base directory for analysis files (e.g., mondrian/analysis_md)
    
    Returns:
        Updated record with absolute paths and validation status
    """
    # Construct absolute paths
    image_filename = record['filename']
    image_path = os.path.join(source_dir, image_filename)
    
    # Analysis markdown file - use stored path or construct from pattern
    if record['analysis_markdown']:
        analysis_path = record['analysis_markdown']
        if not os.path.isabs(analysis_path):
            analysis_path = os.path.join(analysis_dir, os.path.basename(analysis_path))
    else:
        # Fallback: construct from pattern if not stored
        # Pattern: analysis-{advisor}-{job_id}.md
        analysis_filename = f"analysis-{record['advisor']}-{record['id']}.md"
        analysis_path = os.path.join(analysis_dir, analysis_filename)
    
    # Validate paths exist
    image_exists = os.path.exists(image_path)
    analysis_exists = os.path.exists(analysis_path)
    
    return {
        'job_id': record['id'],
        'advisor': record['advisor'],
        'image_filename': image_filename,
        'image_path': os.path.abspath(image_path),
        'image_exists': image_exists,
        'analysis_path': os.path.abspath(analysis_path),
        'analysis_exists': analysis_exists,
        'status': record['status'],
        'completed_at': record['completed_at'],
        'created_at': record['created_at']
    }


def validate_analysis_json(analysis_path: str) -> Dict:
    """
    Validate that analysis file contains valid JSON.
    
    Args:
        analysis_path: Path to analysis markdown file
    
    Returns:
        Dict with is_valid and error details
    """
    try:
        if not os.path.exists(analysis_path):
            return {'is_valid': False, 'error': 'File not found'}
        
        with open(analysis_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract JSON from markdown code block
        # Format: ```json\n{...}\n```
        import re
        json_match = re.search(r'```json\s*({.*?})\s*```', content, re.DOTALL)
        
        if not json_match:
            return {'is_valid': False, 'error': 'No JSON code block found'}
        
        json_str = json_match.group(1)
        data = json.loads(json_str)
        
        # Validate required fields
        required_fields = ['image_description', 'dimensions', 'overall_score']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            return {
                'is_valid': False,
                'error': f'Missing fields: {missing}',
                'has_json': True
            }
        
        return {
            'is_valid': True,
            'size': len(json_str),
            'score': data.get('overall_score', None)
        }
    
    except json.JSONDecodeError as e:
        return {'is_valid': False, 'error': f'JSON decode error: {str(e)}'}
    except Exception as e:
        return {'is_valid': False, 'error': f'Unexpected error: {str(e)}'}


def link_training_data(
    db_path: str,
    source_dir: str,
    analysis_dir: str,
    advisor: Optional[str] = None,
    output_dir: str = './training_data',
    min_valid_examples: int = 10
) -> str:
    """
    Main function to link training data.
    
    Creates a manifest JSON file mapping images to analysis files.
    
    Returns:
        Path to generated manifest file
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[INFO] Querying job records from {db_path}")
    if advisor:
        print(f"[INFO] Filtering for advisor: {advisor}")
    
    # Query database
    records = query_job_records(db_path, advisor)
    print(f"[INFO] Found {len(records)} job records")
    
    if not records:
        print("[WARN] No job records found!")
        return None
    
    # Process records
    manifest = {
        'timestamp': str(Path(db_path).stat().st_mtime),
        'total_records': len(records),
        'by_advisor': {}
    }
    
    advisors_found = {}
    valid_by_advisor = {}
    
    for record in records:
        advisor_name = record['advisor']
        
        if advisor_name not in advisors_found:
            advisors_found[advisor_name] = []
            valid_by_advisor[advisor_name] = []
        
        # Resolve paths
        resolved = resolve_paths(record, source_dir, analysis_dir)
        
        # Quick validation
        if not resolved['image_exists']:
            print(f"  [SKIP] Image not found: {resolved['image_filename']}")
            continue
        
        if not resolved['analysis_exists']:
            print(f"  [SKIP] Analysis not found: {resolved['analysis_path']}")
            continue
        
        # Deep validation of JSON
        json_validation = validate_analysis_json(resolved['analysis_path'])
        if not json_validation['is_valid']:
            print(f"  [SKIP] Invalid JSON in {os.path.basename(resolved['analysis_path'])}: "
                  f"{json_validation.get('error', 'Unknown error')}")
            continue
        
        # Add to manifest
        entry = {
            'job_id': resolved['job_id'],
            'image_path': resolved['image_path'],
            'analysis_path': resolved['analysis_path'],
            'completed_at': resolved['completed_at'],
            'json_size': json_validation.get('size', 0),
            'overall_score': json_validation.get('score', None)
        }
        
        advisors_found[advisor_name].append(resolved)
        valid_by_advisor[advisor_name].append(entry)
    
    # Build final manifest
    for adv_name, entries in valid_by_advisor.items():
        if entries:
            manifest['by_advisor'][adv_name] = {
                'count': len(entries),
                'records': entries
            }
            print(f"[OK] {adv_name}: {len(entries)} valid training examples")
        else:
            print(f"[WARN] {adv_name}: 0 valid training examples")
    
    # Validate we have enough data
    total_valid = sum(len(entries) for entries in valid_by_advisor.values())
    if total_valid < min_valid_examples:
        print(f"\n[WARN] Only {total_valid} valid examples (minimum {min_valid_examples} recommended)")
    
    # Save manifest
    output_file = os.path.join(output_dir, 'training_data_manifest.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n[SUCCESS] Manifest saved to {output_file}")
    print(f"[SUMMARY]")
    print(f"  Total records queried: {len(records)}")
    print(f"  Total valid records: {total_valid}")
    print(f"  Advisors found: {list(valid_by_advisor.keys())}")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Link training data: Map analysis files to source images via database"
    )
    parser.add_argument(
        "--db_path",
        type=str,
        default="./mondrian/mondrian.db",
        help="Path to mondrian.db database"
    )
    parser.add_argument(
        "--source_dir",
        type=str,
        default="./mondrian/source",
        help="Directory containing source images"
    )
    parser.add_argument(
        "--analysis_dir",
        type=str,
        default="./mondrian/analysis_md",
        help="Directory containing analysis markdown files"
    )
    parser.add_argument(
        "--advisor",
        type=str,
        default=None,
        help="Filter by advisor name (e.g., 'ansel'). If not specified, links all advisors"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./training_data",
        help="Output directory for manifest file"
    )
    parser.add_argument(
        "--min_examples",
        type=int,
        default=10,
        help="Minimum number of valid examples (warning only)"
    )
    
    args = parser.parse_args()
    
    link_training_data(
        db_path=args.db_path,
        source_dir=args.source_dir,
        analysis_dir=args.analysis_dir,
        advisor=args.advisor,
        output_dir=args.output_dir,
        min_valid_examples=args.min_examples
    )


if __name__ == "__main__":
    main()
