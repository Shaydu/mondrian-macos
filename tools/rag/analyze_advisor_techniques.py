#!/usr/bin/env python3
"""
Analyze Advisor Images for Photographic Techniques

This script uses the MLX vision model to detect VISUAL techniques in advisor images:
- Ansel Adams: Zone System, f/64 deep DOF, foreground anchoring, dramatic lighting
- Analyze actual image content, not just metadata
- Store detected techniques for comparison with user images

The crux of the app: Compare user's techniques to advisor's signature approaches
and grade/recommend based on how well they match the master's style.

Usage:
    python3 tools/rag/analyze_advisor_techniques.py --advisor ansel
"""

import os
import sys
import json
import requests
import argparse
from pathlib import Path

# Add mondrian to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mondrian'))

AI_SERVICE_URL = "http://localhost:5100/analyze"

# Technique detection prompts for each advisor
TECHNIQUE_PROMPTS = {
    'ansel': """Analyze this Ansel Adams photograph for these specific technical approaches:

1. **Zone System Tonal Range**: Does it show full tonal range from pure black (Zone 0) to pure white (Zone X) with rich midtones? Rate: none/moderate/strong

2. **f/64 Deep Depth of Field**: Is everything sharp from foreground to infinity? Or selective focus? Rate: shallow_dof/moderate/deep_dof_f64

3. **Foreground Anchoring**: Strong foreground element (rocks, plants, structures) in lower third that establishes scale? Rate: none/present/strong

4. **Compositional Technique**: Which applies?
   - rule_of_thirds
   - s_curve
   - triangular
   - leading_lines
   - centered

5. **Lighting Approach**: What type of lighting?
   - dramatic_sidelight (texture emphasis)
   - golden_hour (warm directional)
   - high_contrast (Zones II-IX separation)
   - overcast_diffused
   - backlight

6. **Subject Matter**: What is being photographed?
   - grand_landscape
   - intimate_scene
   - architectural
   - natural_detail
   - portrait

7. **Technical Precision**: Evidence of large format camera precision (corrected perspective, no distortion)? Rate: low/medium/high

Return ONLY a JSON object:
{
  "zone_system": "none" | "moderate" | "strong",
  "depth_of_field": "shallow_dof" | "moderate" | "deep_dof_f64",
  "foreground_anchor": "none" | "present" | "strong",
  "composition": "rule_of_thirds" | "s_curve" | "triangular" | "leading_lines" | "centered",
  "lighting": "dramatic_sidelight" | "golden_hour" | "high_contrast" | "overcast_diffused" | "backlight",
  "subject": "grand_landscape" | "intimate_scene" | "architectural" | "natural_detail" | "portrait",
  "technical_precision": "low" | "medium" | "high",
  "explanation": "Brief explanation of the dominant techniques used"
}
"""
}


def analyze_image_techniques(image_path, advisor_id):
    """
    Analyze an image to detect photographic techniques.
    
    Uses the MLX vision model with a specialized prompt to identify
    the specific techniques the advisor uses in this image.
    
    Returns:
        Dict with detected techniques and confidence levels
    """
    try:
        abs_path = str(Path(image_path).resolve())
        
        print(f"    [→] Detecting techniques in {Path(image_path).name}...")
        
        # Get technique detection prompt for this advisor
        technique_prompt = TECHNIQUE_PROMPTS.get(advisor_id, TECHNIQUE_PROMPTS['ansel'])
        
        # Send to AI service with technique detection prompt
        data = {
            "advisor": advisor_id,
            "image_path": abs_path,
            "enable_rag": "false",
            "custom_prompt": technique_prompt  # Override with technique detection
        }
        
        response = requests.post(
            AI_SERVICE_URL,
            json=data,
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"    [✗] Analysis failed: {response.status_code}")
            return None
        
        # Parse response to extract technique JSON
        response_text = response.text
        
        # Try to extract JSON from response
        try:
            # Look for JSON object in response
            import re
            json_match = re.search(r'\{[^{}]*"zone_system"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                techniques = json.loads(json_match.group(0))
                print(f"    [✓] Detected techniques:")
                print(f"        Zone System: {techniques.get('zone_system')}")
                print(f"        DOF: {techniques.get('depth_of_field')}")
                print(f"        Composition: {techniques.get('composition')}")
                return techniques
            else:
                print(f"    [!] Could not parse techniques from response")
                return None
        except Exception as e:
            print(f"    [!] Error parsing techniques: {e}")
            return None
        
    except Exception as e:
        print(f"    [✗] Error: {e}")
        return None


def save_techniques_to_db(db_path, image_path, techniques, advisor_id):
    """
    Update dimensional_profiles table with detected techniques.
    
    This allows RAG queries to compare user techniques to advisor techniques.
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Convert techniques to JSON string
        techniques_json = json.dumps(techniques)
        
        # Update the profile for this image
        cursor.execute('''
            UPDATE dimensional_profiles 
            SET techniques_json = ?
            WHERE image_path = ? AND advisor_id = ?
        ''', (techniques_json, str(Path(image_path).resolve()), advisor_id))
        
        conn.commit()
        conn.close()
        
        if cursor.rowcount > 0:
            print(f"    [✓] Saved techniques to database")
            return True
        else:
            print(f"    [!] No profile found to update (index image first)")
            return False
        
    except Exception as e:
        print(f"    [✗] Database error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Analyze advisor images for techniques")
    parser.add_argument('--advisor', type=str, required=True, help='Advisor ID (e.g., ansel)')
    parser.add_argument('--image-dir', type=str, help='Directory containing images')
    parser.add_argument('--db', type=str, default='mondrian.db', help='Database path')
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"Analyzing {args.advisor.title()} Techniques")
    print("=" * 70)
    print()
    print("This analyzes the VISUAL content of advisor images to detect:")
    print("  - Photographic techniques used")
    print("  - Compositional approaches")
    print("  - Lighting methods")
    print("  - Technical characteristics")
    print()
    print("These techniques will be used to compare with user images")
    print("and provide advisor-specific recommendations.")
    print()
    
    # Check AI service
    try:
        health_resp = requests.get("http://localhost:5100/health", timeout=5)
        if health_resp.status_code == 200:
            print("[✓] AI Advisor Service is running")
        else:
            print("[✗] AI service not responding")
            sys.exit(1)
    except Exception as e:
        print(f"[✗] Cannot connect to AI service: {e}")
        print(f"    Start with: python3 mondrian/ai_advisor_service.py --port 5100")
        sys.exit(1)
    
    # Determine image directory
    if args.image_dir:
        image_dir = Path(args.image_dir)
    else:
        image_dir = Path('mondrian') / 'source' / 'advisor' / 'photographer' / args.advisor
    
    if not image_dir.exists():
        print(f"[✗] Directory not found: {image_dir}")
        sys.exit(1)
    
    print(f"[✓] Image directory: {image_dir}")
    print()
    
    # Find images
    IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
    images = [f for f in image_dir.iterdir() 
              if f.is_file() and f.suffix in IMG_EXTENSIONS]
    
    if not images:
        print(f"[✗] No images found in {image_dir}")
        sys.exit(1)
    
    print(f"Found {len(images)} images to analyze")
    print()
    
    # Analyze each image
    results = []
    for i, image_path in enumerate(images, 1):
        print(f"[{i}/{len(images)}] {image_path.name}")
        
        techniques = analyze_image_techniques(image_path, args.advisor)
        
        if techniques:
            # Save to database
            save_techniques_to_db(args.db, image_path, techniques, args.advisor)
            results.append({
                'image': image_path.name,
                'techniques': techniques
            })
        
        print()
    
    # Summary
    print("=" * 70)
    print("Analysis Complete")
    print("=" * 70)
    print(f"Analyzed: {len(results)}/{len(images)} images")
    print()
    
    if results:
        print("Technique Summary:")
        
        # Count techniques
        from collections import Counter
        zone_systems = Counter(r['techniques'].get('zone_system') for r in results)
        dof_types = Counter(r['techniques'].get('depth_of_field') for r in results)
        compositions = Counter(r['techniques'].get('composition') for r in results)
        
        print(f"  Zone System usage: {dict(zone_systems)}")
        print(f"  Depth of Field: {dict(dof_types)}")
        print(f"  Compositions: {dict(compositions)}")
        print()
        print(f"✓ Techniques stored in database")
        print(f"✓ RAG can now compare user techniques to {args.advisor}'s approach")
        print()
        print("Next: Upload an image with enable_rag=true to get technique-based feedback!")


if __name__ == "__main__":
    main()

