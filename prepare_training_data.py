#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare Training Data for LoRA Fine-tuning
Converts existing analysis data into training format

This script:
1. Scans analysis outputs and advisor prompts
2. Pairs images with prompts and responses
3. Creates JSON training dataset

Usage:
    python prepare_training_data.py \
        --analysis_dir ./analysis_output \
        --source_dir ./source \
        --prompts_dir ./mondrian/prompts \
        --output_dir ./training_data \
        --advisor ansel
"""

import os
import json
import argparse
import glob
from pathlib import Path
import re

def extract_image_id_from_filename(filename):
    """Extract image identifier from various filename formats"""
    # Try to extract UUID or other identifier
    patterns = [
        r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',  # UUID
        r'([a-zA-Z0-9_-]+)\.(jpg|jpeg|png)',  # Simple name
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def find_image_for_analysis(analysis_file, source_dir):
    """Find corresponding image file for an analysis"""
    # Extract identifier from analysis filename
    analysis_name = os.path.basename(analysis_file)
    image_id = extract_image_id_from_filename(analysis_name)
    
    if not image_id:
        return None
    
    # Search for image in source directory
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    for ext in extensions:
        pattern = os.path.join(source_dir, f"*{image_id}*{ext}")
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
        
        # Also try direct match
        direct_path = os.path.join(source_dir, f"{image_id}{ext}")
        if os.path.exists(direct_path):
            return direct_path
    
    return None


def extract_response_from_html(html_file):
    """Extract text response from HTML analysis file"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to extract JSON if present
        json_match = re.search(r'<script[^>]*>.*?({.*?})</script>', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if 'analysis' in data:
                    return json.dumps(data['analysis'], indent=2)
            except:
                pass
        
        # Extract text from HTML
        # Remove script and style tags
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Extract text from analysis divs
        analysis_match = re.search(r'<div[^>]*class="analysis"[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
        if analysis_match:
            text = analysis_match.group(1)
            # Clean HTML tags
            text = re.sub(r'<[^>]+>', '\n', text)
            text = re.sub(r'\n\s*\n', '\n', text)
            return text.strip()
        
        # Fallback: extract all text
        text = re.sub(r'<[^>]+>', '\n', content)
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()[:2000]  # Limit length
        
    except Exception as e:
        print(f"Error extracting from {html_file}: {e}")
        return None


def load_advisor_prompt(prompts_dir, advisor_name):
    """Load advisor-specific prompt"""
    prompt_file = os.path.join(prompts_dir, f"{advisor_name}.md")
    if os.path.exists(prompt_file):
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def load_system_prompt(prompts_dir):
    """Load system prompt"""
    system_file = os.path.join(prompts_dir, "system.md")
    if os.path.exists(system_file):
        with open(system_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def create_training_example(image_path, prompt, response):
    """Create a training example in the required format"""
    return {
        "image_path": image_path,
        "prompt": prompt,
        "response": response
    }


def prepare_training_data(
    analysis_dir,
    source_dir,
    prompts_dir,
    output_dir,
    advisor=None,
    min_examples=10
):
    """Prepare training data from analysis files"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load prompts
    system_prompt = load_system_prompt(prompts_dir)
    advisor_prompt = None
    if advisor:
        advisor_prompt = load_advisor_prompt(prompts_dir, advisor)
    
    # Find all analysis files
    analysis_files = []
    if os.path.isdir(analysis_dir):
        analysis_files = glob.glob(os.path.join(analysis_dir, "*.html"))
    elif os.path.isfile(analysis_dir):
        analysis_files = [analysis_dir]
    
    print(f"Found {len(analysis_files)} analysis files")
    
    # Process each analysis file
    training_examples = []
    skipped = 0
    
    for analysis_file in analysis_files:
        # Find corresponding image
        image_path = find_image_for_analysis(analysis_file, source_dir)
        if not image_path or not os.path.exists(image_path):
            print(f"  Skipping {os.path.basename(analysis_file)}: image not found")
            skipped += 1
            continue
        
        # Extract response
        response = extract_response_from_html(analysis_file)
        if not response or len(response) < 50:
            print(f"  Skipping {os.path.basename(analysis_file)}: invalid response")
            skipped += 1
            continue
        
        # Build prompt
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(system_prompt)
        if advisor_prompt:
            prompt_parts.append(f"\n\nAdvisor-specific guidance:\n{advisor_prompt}")
        prompt_parts.append("\n\nAnalyze the provided image and provide detailed feedback.")
        
        prompt = "\n".join(prompt_parts)
        
        # Create training example
        example = create_training_example(image_path, prompt, response)
        training_examples.append(example)
        print(f"  ✓ Processed {os.path.basename(analysis_file)}")
    
    print(f"\nPrepared {len(training_examples)} training examples (skipped {skipped})")
    
    if len(training_examples) < min_examples:
        print(f"Warning: Only {len(training_examples)} examples (minimum {min_examples} recommended)")
    
    # Save training data
    if advisor:
        output_file = os.path.join(output_dir, f"training_data_{advisor}.json")
    else:
        output_file = os.path.join(output_dir, "training_data.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_examples, f, indent=2, ensure_ascii=False)
    
    print(f"Saved training data to {output_file}")
    
    # Also save individual files for easier loading
    individual_dir = os.path.join(output_dir, "individual")
    os.makedirs(individual_dir, exist_ok=True)
    
    for i, example in enumerate(training_examples):
        individual_file = os.path.join(individual_dir, f"example_{i:04d}.json")
        with open(individual_file, 'w', encoding='utf-8') as f:
            json.dump(example, f, indent=2, ensure_ascii=False)
    
    print(f"Also saved {len(training_examples)} individual files to {individual_dir}/")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Prepare training data for LoRA fine-tuning")
    parser.add_argument("--analysis_dir", type=str, default="./analysis_output",
                        help="Directory containing analysis HTML files")
    parser.add_argument("--source_dir", type=str, default="./source",
                        help="Directory containing source images")
    parser.add_argument("--prompts_dir", type=str, default="./mondrian/prompts",
                        help="Directory containing prompt files")
    parser.add_argument("--output_dir", type=str, default="./training_data",
                        help="Output directory for training data")
    parser.add_argument("--advisor", type=str, default=None,
                        help="Specific advisor to prepare data for (e.g., 'ansel')")
    parser.add_argument("--min_examples", type=int, default=10,
                        help="Minimum number of examples required")
    
    args = parser.parse_args()
    
    prepare_training_data(
        analysis_dir=args.analysis_dir,
        source_dir=args.source_dir,
        prompts_dir=args.prompts_dir,
        output_dir=args.output_dir,
        advisor=args.advisor,
        min_examples=args.min_examples
    )


if __name__ == "__main__":
    main()





