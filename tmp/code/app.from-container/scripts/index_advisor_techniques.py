#!/usr/bin/env python3
"""
Index Advisor Techniques

Analyzes advisor images and tags them with photographic techniques.
This creates the knowledge base for technique-based RAG matching.
"""

import sqlite3
import sys
import os
import json
import base64
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MLX imports
try:
    import mlx.core as mx
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_image
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    print("[ERROR] MLX not available. Install with: pip install mlx-vlm")
    sys.exit(1)


def get_technique_detection_prompt(techniques):
    """
    Build prompt for detecting techniques in an image.
    
    Args:
        techniques: List of technique dicts from database
        
    Returns:
        Prompt string
    """
    prompt = """Analyze this Ansel Adams photograph and identify which photographic techniques are present.

These are reference/exemplar images from Ansel Adams' body of work, so focus on techniques that ARE present and well-executed.

For each technique listed below, determine:
1. Is it present? (yes/no)
2. If yes, what is the strength score? (0-10 scale)
   - 0-2: barely detectable, very subtle
   - 3-4: subtle but noticeable
   - 5-6: moderately used
   - 7-8: prominently featured
   - 9-10: dominant, central to the image
3. Evidence: 1-2 sentences describing how it appears in THIS specific image
4. Region: where in the frame it's most evident (e.g., "lower third", "left side", "throughout")

These are master works, so most techniques will be present with high scores (7-10). Only include techniques that are clearly present.

TECHNIQUES TO DETECT:

"""
    
    # Group by category
    by_category = {}
    for tech in techniques:
        cat = tech['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tech)
    
    # Format techniques by category
    for category, techs in sorted(by_category.items()):
        prompt += f"\n{category.upper()} TECHNIQUES:\n"
        for tech in techs:
            prompt += f"\n- {tech['name']} (ID: {tech['id']})\n"
            prompt += f"  Description: {tech['description']}\n"
            prompt += f"  Detection: {tech['detection_criteria']}\n"
    
    prompt += """

OUTPUT FORMAT (JSON):
{
  "techniques": [
    {
      "id": "foreground_anchoring",
      "present": true,
      "score": 8,
      "evidence": "Large boulder in lower left third creates strong foreground anchor, establishing scale against distant mountains",
      "region": "lower left third"
    },
    {
      "id": "deep_dof_landscape",
      "present": true,
      "score": 9,
      "evidence": "Sharp focus from foreground rocks to distant peaks, characteristic f/64 sharpness throughout",
      "region": "throughout frame"
    },
    ...
  ]
}

IMPORTANT:
- Only include techniques where present=true (these are exemplar images)
- Score should be an integer from 0-10 reflecting prominence/strength
- Be specific in evidence - reference actual elements in THIS image
- These are Ansel Adams master works - focus on well-executed techniques
- Output ONLY valid JSON, no other text
"""
    
    return prompt


def analyze_image_techniques(image_path, techniques, model, processor):
    """
    Analyze an image and detect techniques present.
    
    Args:
        image_path: Path to image file
        techniques: List of technique dicts from database
        model: MLX model
        processor: MLX processor
        
    Returns:
        List of detected techniques with metadata
    """
    print(f"[INFO] Analyzing: {os.path.basename(image_path)}")
    
    try:
        # Load image
        image = load_image(image_path)
        
        # Build prompt
        prompt = get_technique_detection_prompt(techniques)
        
        # Format for model
        formatted_prompt = apply_chat_template(
            processor,
            config=model.config,
            prompt=prompt
        )
        
        # Generate response
        print(f"[INFO] Running technique detection...")
        output = generate(
            model,
            processor,
            formatted_prompt,
            image=image,
            max_tokens=2000,
            temp=0.3,  # Lower temperature for more consistent JSON
            verbose=False
        )
        
        # Convert GenerationResult to string if needed
        if hasattr(output, 'text'):
            output_text = output.text
        elif hasattr(output, '__str__'):
            output_text = str(output)
        else:
            output_text = output
        
        print(f"[DEBUG] Raw output: {output_text[:500]}...")
        
        # Parse JSON response
        detected = parse_technique_response(output_text)
        
        if detected:
            print(f"[OK] Detected {len(detected)} techniques")
            for tech in detected:
                score = tech.get('score', tech.get('strength'))  # Handle both numeric and string formats
                print(f"  - {tech['id']}: {score}/10" if isinstance(score, int) else f"  - {tech['id']}: {score}")
        else:
            print(f"[WARN] No techniques detected")
        
        return detected
        
    except Exception as e:
        print(f"[ERROR] Failed to analyze {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return []


def parse_technique_response(response_text):
    """
    Parse JSON response from technique detection.
    
    Args:
        response_text: Raw response from model
        
    Returns:
        List of detected technique dicts with numeric scores
    """
    try:
        # Remove markdown code blocks if present
        text = response_text.strip()
        
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        
        if text.endswith('```'):
            text = text[:-3]
        
        text = text.strip()
        
        # Find JSON object
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            print(f"[ERROR] No JSON object found in response")
            return []
        
        json_text = text[start_idx:end_idx + 1]
        data = json.loads(json_text)
        
        # Extract techniques where present=true (for advisor exemplar images)
        techniques = data.get('techniques', [])
        detected = [t for t in techniques if t.get('present', False)]
        
        # Normalize score field (handle both 'score' and 'strength')
        for tech in detected:
            if 'score' not in tech and 'strength' in tech:
                # Convert old strength values to numeric scores
                strength = tech['strength']
                if isinstance(strength, int):
                    tech['score'] = strength
                else:
                    score_map = {'strong': 8, 'moderate': 5, 'subtle': 2}
                    tech['score'] = score_map.get(strength, 5)
        
        return detected
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parsing failed: {e}")
        print(f"[ERROR] Attempted to parse: {text[:500]}...")
        return []
    except Exception as e:
        print(f"[ERROR] Failed to parse response: {e}")
        return []


def save_image_techniques(db_path, advisor_id, image_path, detected_techniques):
    """
    Save detected techniques to database.
    
    Args:
        db_path: Path to database
        advisor_id: Advisor ID
        image_path: Path to image
        detected_techniques: List of detected technique dicts
        
    Returns:
        Number of techniques saved
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        saved = 0
        for tech in detected_techniques:
            # Handle both numeric scores and old string strengths
            score = tech.get('score', tech.get('strength'))
            
            # Convert numeric score to string strength for backward compatibility
            if isinstance(score, int):
                if score >= 7:
                    strength = 'strong'
                elif score >= 4:
                    strength = 'moderate'
                else:
                    strength = 'subtle'
            else:
                strength = score
            
            cursor.execute("""
                INSERT INTO advisor_image_techniques 
                (advisor_id, image_path, technique_id, strength, evidence, example_region)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                advisor_id,
                image_path,
                tech['id'],
                strength,
                tech.get('evidence', ''),
                tech.get('region', '')
            ))
            saved += 1
        
        conn.commit()
        conn.close()
        
        print(f"[OK] Saved {saved} techniques for {os.path.basename(image_path)}")
        return saved
        
    except Exception as e:
        print(f"[ERROR] Failed to save techniques: {e}")
        return 0


def index_advisor_images(advisor_id, db_path="mondrian.db", limit=None, skip_existing=True, source_dir=None):
    """
    Index all images for an advisor.
    
    Args:
        advisor_id: Advisor ID (e.g., "ansel")
        db_path: Path to database
        limit: Optional limit on number of images to process
        skip_existing: Skip images that already have techniques indexed
        source_dir: Optional specific directory to use (defaults to mondrian/source/advisor/photographer/{advisor_id})
    """
    print(f"\n[INFO] Indexing techniques for advisor: {advisor_id}")
    print(f"[INFO] Database: {db_path}")
    
    # Load MLX model
    print(f"[INFO] Loading MLX model...")
    model_name = "Qwen/Qwen2-VL-2B-Instruct"
    model, processor = load(model_name)
    print(f"[OK] Model loaded")
    
    # Get techniques from database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM photographer_techniques ORDER BY category, name")
    techniques = [dict(row) for row in cursor.fetchall()]
    print(f"[INFO] Loaded {len(techniques)} techniques to detect")
    
    # Find advisor images
    if source_dir:
        advisor_dir = source_dir
    else:
        advisor_dir = f"mondrian/source/advisor/photographer/{advisor_id}"
    
    if not os.path.exists(advisor_dir):
        print(f"[ERROR] Advisor directory not found: {advisor_dir}")
        return
    
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.PNG']:
        image_files.extend(Path(advisor_dir).glob(ext))
    
    # Remove duplicates and sort
    image_files = sorted(set(image_files))
    
    print(f"[INFO] Found {len(image_files)} images")
    
    if limit:
        image_files = image_files[:limit]
        print(f"[INFO] Processing first {limit} images")
    
    # Process each image
    total_techniques = 0
    processed = 0
    skipped = 0
    
    for img_path in image_files:
        img_path_str = str(img_path)
        
        # Check if already indexed
        if skip_existing:
            cursor.execute("""
                SELECT COUNT(*) FROM advisor_image_techniques 
                WHERE advisor_id = ? AND image_path = ?
            """, (advisor_id, img_path_str))
            
            if cursor.fetchone()[0] > 0:
                print(f"[SKIP] Already indexed: {img_path.name}")
                skipped += 1
                continue
        
        # Analyze image
        detected = analyze_image_techniques(img_path_str, techniques, model, processor)
        
        if detected:
            # Save to database
            saved = save_image_techniques(db_path, advisor_id, img_path_str, detected)
            total_techniques += saved
            processed += 1
        
        print()  # Blank line between images
    
    conn.close()
    
    print(f"\n[SUCCESS] Indexing complete!")
    print(f"[INFO] Processed: {processed} images")
    print(f"[INFO] Skipped: {skipped} images")
    print(f"[INFO] Total techniques indexed: {total_techniques}")
    print(f"[INFO] Average techniques per image: {total_techniques / processed if processed > 0 else 0:.1f}")


def show_statistics(advisor_id, db_path="mondrian.db"):
    """Show statistics about indexed techniques"""
    print(f"\n[INFO] Technique Statistics for {advisor_id}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Total images indexed
    cursor.execute("""
        SELECT COUNT(DISTINCT image_path) 
        FROM advisor_image_techniques 
        WHERE advisor_id = ?
    """, (advisor_id,))
    total_images = cursor.fetchone()[0]
    print(f"Total images indexed: {total_images}")
    
    # Total techniques
    cursor.execute("""
        SELECT COUNT(*) 
        FROM advisor_image_techniques 
        WHERE advisor_id = ?
    """, (advisor_id,))
    total_techniques = cursor.fetchone()[0]
    print(f"Total technique instances: {total_techniques}")
    
    # Techniques by strength
    cursor.execute("""
        SELECT strength, COUNT(*) 
        FROM advisor_image_techniques 
        WHERE advisor_id = ?
        GROUP BY strength
    """, (advisor_id,))
    print(f"\nBy strength:")
    for strength, count in cursor.fetchall():
        print(f"  {strength}: {count}")
    
    # Most common techniques
    cursor.execute("""
        SELECT pt.name, COUNT(*) as count
        FROM advisor_image_techniques ait
        JOIN photographer_techniques pt ON ait.technique_id = pt.id
        WHERE ait.advisor_id = ?
        GROUP BY ait.technique_id
        ORDER BY count DESC
        LIMIT 10
    """, (advisor_id,))
    print(f"\nMost common techniques:")
    for name, count in cursor.fetchall():
        print(f"  {name}: {count} images")
    
    conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Index advisor images with photographic techniques")
    parser.add_argument("--advisor", type=str, default="ansel", help="Advisor ID to index")
    parser.add_argument("--db", type=str, default="mondrian.db", help="Database path")
    parser.add_argument("--source-dir", type=str, help="Custom source directory for images (defaults to mondrian/source/advisor/photographer/{advisor})")
    parser.add_argument("--limit", type=int, help="Limit number of images to process")
    parser.add_argument("--reindex", action="store_true", help="Reindex images that already have techniques")
    parser.add_argument("--stats-only", action="store_true", help="Only show statistics, don't index")
    args = parser.parse_args()
    
    if args.stats_only:
        show_statistics(args.advisor, args.db)
    else:
        index_advisor_images(
            args.advisor,
            db_path=args.db,
            limit=args.limit,
            skip_existing=not args.reindex,
            source_dir=args.source_dir
        )
        show_statistics(args.advisor, args.db)

