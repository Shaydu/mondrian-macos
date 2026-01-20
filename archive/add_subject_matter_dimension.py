#!/usr/bin/env python3
"""
Add Subject Matter Alignment dimension to training data.

This script adds a 9th dimension "subject_matter" to the training JSONL files.
For Ansel Adams reference images (landscapes, nature), subject_matter scores 9-10.
The model will learn to penalize non-landscape/nature images when trained.
"""

import json
import re
from pathlib import Path


def add_subject_matter_to_example(example: dict) -> dict:
    """Add subject_matter dimension to a training example."""
    
    # Parse the assistant's response content
    messages = example.get('messages', [])
    if len(messages) < 2:
        return example
    
    assistant_content = messages[1].get('content', '')
    
    try:
        # Parse the JSON response
        response_data = json.loads(assistant_content)
        
        # Check if it has dimensional_analysis structure
        if 'dimensional_analysis' in response_data:
            dim_analysis = response_data['dimensional_analysis']
            
            # Add subject_matter dimension - for Ansel's images, they align perfectly (10)
            # This teaches the model what "good" subject matter looks like
            # The model will learn to give 1-3 for non-landscape/nature images
            dim_analysis['subject_matter'] = {
                "score": 10,
                "comment": "Perfect alignment with Ansel Adams' artistic domain - this wilderness/nature photograph exemplifies the landscape mastery that defined his life's work."
            }
            
            # Update the assistant content
            messages[1]['content'] = json.dumps(response_data, indent=2)
        
        # Also check for dimensions array format (newer format)
        elif 'dimensions' in response_data:
            dimensions = response_data['dimensions']
            
            # Check if subject_matter already exists
            has_subject_matter = any(d.get('name', '').lower() == 'subject matter' for d in dimensions)
            
            if not has_subject_matter:
                # Add subject_matter dimension - score 10 for Ansel's reference images
                dimensions.append({
                    "name": "Subject Matter",
                    "score": 10,
                    "comment": "Perfect alignment with Ansel Adams' artistic domain - wilderness landscape photography.",
                    "recommendation": "Continue pursuing landscapes, nature, mountains, and environmental subjects. Portraits, snapshots, urban scenes, or event photography would score 1-3 as they fall completely outside this advisor's expertise."
                })
                
                # Update the assistant content
                messages[1]['content'] = json.dumps(response_data, indent=2)
        
        # Update scores dict if present
        if 'scores' in example:
            example['scores']['subject_matter'] = 10
            
    except json.JSONDecodeError:
        # If content isn't valid JSON, skip
        pass
    
    # Update user prompt to mention 9 dimensions
    user_content = messages[0].get('content', '')
    user_content = user_content.replace(
        'all 8 dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact)',
        'all 9 dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact, subject_matter)'
    )
    messages[0]['content'] = user_content
    
    return example


def process_jsonl_file(input_path: Path, output_path: Path):
    """Process a JSONL file and add subject_matter dimension."""
    
    examples = []
    with open(input_path, 'r') as f:
        for line in f:
            if line.strip():
                example = json.loads(line)
                updated = add_subject_matter_to_example(example)
                examples.append(updated)
    
    # Write updated examples
    with open(output_path, 'w') as f:
        for example in examples:
            f.write(json.dumps(example) + '\n')
    
    print(f"Processed {len(examples)} examples")
    print(f"Output: {output_path}")


def main():
    base_dir = Path('/home/doo/dev/mondrian-macos/training/datasets')
    
    # Process the main training file
    input_file = base_dir / 'ansel_image_training_nuanced.jsonl'
    output_file = base_dir / 'ansel_image_training_9dim.jsonl'
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return
    
    print(f"Adding Subject Matter dimension to training data...")
    print(f"Input: {input_file}")
    
    process_jsonl_file(input_file, output_file)
    
    # Also process the absolute paths version if it exists
    abs_input = base_dir / 'ansel_image_training_nuanced_abs.jsonl'
    if abs_input.exists():
        abs_output = base_dir / 'ansel_image_training_9dim_abs.jsonl'
        print(f"\nProcessing absolute paths version...")
        process_jsonl_file(abs_input, abs_output)
    
    print("\n✓ Done! New training files created with 9 dimensions.")
    print(f"\nTo retrain, update retrain_lora_correct.sh to use:")
    print(f"  TRAINING_DATA=\"training/datasets/ansel_image_training_9dim.jsonl\"")


if __name__ == '__main__':
    main()
