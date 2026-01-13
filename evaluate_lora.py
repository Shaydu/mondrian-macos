#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LoRA Model Evaluation Framework

Compares outputs from base model vs fine-tuned model on held-out validation data.

Metrics:
  - Format Compliance: Valid JSON with expected fields
  - Score Consistency: Scores within expected ranges
  - Response Quality: Qualitative assessment via sample outputs
  - Inference Performance: Speed and throughput metrics

Usage:
    python evaluate_lora.py \
        --base_model "Qwen/Qwen3-VL-4B-Instruct" \
        --lora_path ./models/qwen3-vl-4b-lora-ansel \
        --val_data ./training_data/training_data_ansel_val.json \
        --output_report ./evaluation/comparison_report.json

Output:
    comparison_report.json - Detailed comparison metrics and sample outputs
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

from PIL import Image
import numpy as np

try:
    import mlx_vlm
except ImportError:
    print("[ERROR] mlx_vlm not installed. Install with: pip install mlx-vlm")
    raise


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class ModelComparator:
    """Compare base and fine-tuned models on evaluation data."""
    
    def __init__(
        self,
        base_model_id: str,
        lora_path: Optional[str] = None
    ):
        """
        Initialize comparator with base and fine-tuned models.
        
        Args:
            base_model_id: Hugging Face model ID for base model
            lora_path: Path to LoRA adapter (if None, only uses base model)
        """
        self.base_model_id = base_model_id
        self.lora_path = lora_path
        
        logger.info(f"Loading base model: {base_model_id}")
        self.base_model, self.processor = mlx_vlm.load(base_model_id)
        
        # Load fine-tuned model if LoRA path provided
        self.fine_tuned_model = None
        if lora_path:
            logger.info(f"Loading LoRA adapter from {lora_path}")
            # TODO: Load LoRA weights and apply to a copy of base model
            # For now, we'll use base model for both
            logger.warning("[TODO] LoRA adapter loading not yet implemented")
    
    def generate_output(
        self,
        model,
        image_path: str,
        prompt: str,
        max_tokens: int = 512
    ) -> Tuple[str, float]:
        """
        Generate model output for an image and prompt.
        
        Args:
            model: The model to use for generation
            image_path: Path to input image
            prompt: Text prompt for the model
            max_tokens: Maximum tokens to generate
        
        Returns:
            (generated_text, inference_time_seconds)
        """
        try:
            # Load image
            image = Image.open(image_path).convert('RGB')
            
            # Format as conversation
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            # Apply chat template
            text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Generate with timing
            start_time = time.time()
            output = mlx_vlm.generate(
                model,
                self.processor,
                prompt,
                image,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9
            )
            inference_time = time.time() - start_time
            
            return output, inference_time
        
        except Exception as e:
            logger.error(f"Error generating output for {image_path}: {str(e)}")
            return f"[ERROR: {str(e)}]", 0.0
    
    def validate_json_format(self, text: str) -> Dict:
        """
        Validate that text contains valid JSON with expected structure.
        
        Returns:
            Dict with:
            - is_valid: bool
            - has_json: bool
            - json_content: Dict or None
            - missing_fields: List[str]
            - error: str or None
        """
        result = {
            'is_valid': False,
            'has_json': False,
            'json_content': None,
            'missing_fields': [],
            'error': None
        }
        
        try:
            # Try to parse as JSON directly
            data = json.loads(text)
            result['has_json'] = True
            result['json_content'] = data
        except json.JSONDecodeError:
            # Try to extract from code blocks or other formats
            import re
            json_match = re.search(r'```json\s*({.*?})\s*```', text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    result['has_json'] = True
                    result['json_content'] = data
                except json.JSONDecodeError as e:
                    result['error'] = f"Invalid JSON in code block: {str(e)}"
                    return result
            else:
                result['error'] = "No valid JSON found"
                return result
        
        if not result['has_json']:
            return result
        
        # Validate required fields
        expected_fields = {
            'image_description': str,
            'dimensions': list,
            'overall_score': (int, float),
            'key_strengths': list,
            'priority_improvements': list
        }
        
        for field, expected_type in expected_fields.items():
            if field not in result['json_content']:
                result['missing_fields'].append(field)
        
        # Check score ranges
        if 'overall_score' in result['json_content']:
            score = result['json_content']['overall_score']
            if not (0 <= score <= 10):
                result['error'] = f"Overall score {score} out of valid range [0-10]"
                return result
        
        if not result['missing_fields']:
            result['is_valid'] = True
        else:
            result['error'] = f"Missing fields: {result['missing_fields']}"
        
        return result
    
    def evaluate_example(self, example: Dict) -> Dict:
        """
        Evaluate a single example with both models.
        
        Args:
            example: Dict with 'image_path', 'prompt', 'response'
        
        Returns:
            Dict with evaluation results
        """
        image_path = example['image_path']
        prompt = example['prompt']
        expected_response = example.get('response', '')
        
        # Generate outputs
        logger.info(f"Evaluating {os.path.basename(image_path)}")
        
        base_output, base_time = self.generate_output(
            self.base_model,
            image_path,
            prompt
        )
        
        fine_tuned_output = None
        fine_tuned_time = None
        if self.fine_tuned_model:
            fine_tuned_output, fine_tuned_time = self.generate_output(
                self.fine_tuned_model,
                image_path,
                prompt
            )
        
        # Validate outputs
        base_validation = self.validate_json_format(base_output)
        fine_tuned_validation = None
        if fine_tuned_output:
            fine_tuned_validation = self.validate_json_format(fine_tuned_output)
        
        # Extract scores if valid
        base_score = None
        if base_validation['is_valid'] and base_validation['json_content']:
            base_score = base_validation['json_content'].get('overall_score')
        
        fine_tuned_score = None
        if fine_tuned_validation and fine_tuned_validation['is_valid'] and fine_tuned_validation['json_content']:
            fine_tuned_score = fine_tuned_validation['json_content'].get('overall_score')
        
        result = {
            'image': os.path.basename(image_path),
            'image_path': image_path,
            'base_model': {
                'output': base_output[:500] + "..." if len(base_output) > 500 else base_output,
                'full_output': base_output,
                'inference_time': base_time,
                'format_valid': base_validation['is_valid'],
                'score': base_score,
                'validation_error': base_validation.get('error')
            }
        }
        
        if fine_tuned_validation:
            result['fine_tuned_model'] = {
                'output': fine_tuned_output[:500] + "..." if len(fine_tuned_output) > 500 else fine_tuned_output,
                'full_output': fine_tuned_output,
                'inference_time': fine_tuned_time,
                'format_valid': fine_tuned_validation['is_valid'],
                'score': fine_tuned_score,
                'validation_error': fine_tuned_validation.get('error')
            }
        
        return result
    
    def evaluate_dataset(self, data_path: str, max_examples: Optional[int] = None) -> Dict:
        """
        Evaluate entire dataset with both models.
        
        Args:
            data_path: Path to validation data JSON
            max_examples: Maximum number of examples to evaluate (for speed)
        
        Returns:
            Dict with comprehensive evaluation results
        """
        # Load validation data
        logger.info(f"Loading validation data from {data_path}")
        
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            data = [data]
        
        if max_examples:
            data = data[:max_examples]
        
        logger.info(f"Evaluating {len(data)} examples")
        
        # Evaluate all examples
        results = []
        for i, example in enumerate(data):
            logger.info(f"  Example {i+1}/{len(data)}")
            result = self.evaluate_example(example)
            results.append(result)
        
        return {
            'examples': results,
            'total': len(results)
        }
    
    def compute_metrics(self, evaluation_results: Dict) -> Dict:
        """
        Compute aggregate metrics from evaluation results.
        
        Metrics:
        - Format Compliance: % of valid JSON outputs
        - Inference Time: Mean time per image
        - Score Statistics: Mean, std of overall scores
        """
        examples = evaluation_results['examples']
        
        base_valid = 0
        base_scores = []
        base_times = []
        
        fine_tuned_valid = 0
        fine_tuned_scores = []
        fine_tuned_times = []
        
        for ex in examples:
            # Base model metrics
            if ex['base_model']['format_valid']:
                base_valid += 1
            if ex['base_model']['score'] is not None:
                base_scores.append(ex['base_model']['score'])
            if ex['base_model']['inference_time'] > 0:
                base_times.append(ex['base_model']['inference_time'])
            
            # Fine-tuned model metrics
            if 'fine_tuned_model' in ex:
                if ex['fine_tuned_model']['format_valid']:
                    fine_tuned_valid += 1
                if ex['fine_tuned_model']['score'] is not None:
                    fine_tuned_scores.append(ex['fine_tuned_model']['score'])
                if ex['fine_tuned_model']['inference_time'] > 0:
                    fine_tuned_times.append(ex['fine_tuned_model']['inference_time'])
        
        # Compute statistics
        base_format_compliance = base_valid / len(examples) if examples else 0
        fine_tuned_format_compliance = fine_tuned_valid / len(examples) if examples else 0
        
        metrics = {
            'base_model': {
                'format_compliance': round(base_format_compliance, 3),
                'valid_outputs': base_valid,
                'total_outputs': len(examples),
                'avg_score': round(np.mean(base_scores), 2) if base_scores else None,
                'std_score': round(np.std(base_scores), 2) if base_scores else None,
                'avg_inference_time': round(np.mean(base_times), 3) if base_times else None,
                'total_inference_time': round(sum(base_times), 2) if base_times else None
            }
        }
        
        if fine_tuned_scores or fine_tuned_times:
            metrics['fine_tuned_model'] = {
                'format_compliance': round(fine_tuned_format_compliance, 3),
                'valid_outputs': fine_tuned_valid,
                'total_outputs': len(examples),
                'avg_score': round(np.mean(fine_tuned_scores), 2) if fine_tuned_scores else None,
                'std_score': round(np.std(fine_tuned_scores), 2) if fine_tuned_scores else None,
                'avg_inference_time': round(np.mean(fine_tuned_times), 3) if fine_tuned_times else None,
                'total_inference_time': round(sum(fine_tuned_times), 2) if fine_tuned_times else None
            }
            
            # Compute deltas
            metrics['improvements'] = {
                'format_compliance_delta': f"+{round((fine_tuned_format_compliance - base_format_compliance) * 100, 1)}%",
                'score_delta': f"+{round(np.mean(fine_tuned_scores) - np.mean(base_scores), 2)}" if fine_tuned_scores and base_scores else "N/A",
                'inference_time_delta': f"{round((np.mean(fine_tuned_times) / np.mean(base_times) - 1) * 100, 1)}%" if fine_tuned_times and base_times else "N/A"
            }
        
        return metrics


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate and compare base vs fine-tuned models"
    )
    parser.add_argument(
        "--base_model",
        type=str,
        default="Qwen/Qwen3-VL-4B-Instruct",
        help="Base model ID"
    )
    parser.add_argument(
        "--lora_path",
        type=str,
        default=None,
        help="Path to LoRA adapter (optional)"
    )
    parser.add_argument(
        "--val_data",
        type=str,
        required=True,
        help="Path to validation data JSON"
    )
    parser.add_argument(
        "--output_report",
        type=str,
        default="./evaluation/comparison_report.json",
        help="Output file for evaluation report"
    )
    parser.add_argument(
        "--max_examples",
        type=int,
        default=None,
        help="Maximum number of examples to evaluate (for testing)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(os.path.dirname(args.output_report), exist_ok=True)
    
    # Initialize comparator
    comparator = ModelComparator(args.base_model, args.lora_path)
    
    # Evaluate dataset
    logger.info("Starting evaluation...")
    evaluation_results = comparator.evaluate_dataset(
        args.val_data,
        max_examples=args.max_examples
    )
    
    # Compute metrics
    logger.info("Computing metrics...")
    metrics = comparator.compute_metrics(evaluation_results)
    
    # Prepare report
    report = {
        'evaluation_date': datetime.now().isoformat(),
        'base_model': args.base_model,
        'lora_path': args.lora_path,
        'validation_data': args.val_data,
        'metrics': metrics,
        'summary': {
            'total_examples': evaluation_results['total'],
            'base_format_compliance': f"{metrics['base_model']['format_compliance']*100:.1f}%"
        },
        'sample_results': evaluation_results['examples'][:5]  # Include first 5 samples
    }
    
    if 'fine_tuned_model' in metrics:
        report['summary']['fine_tuned_format_compliance'] = f"{metrics['fine_tuned_model']['format_compliance']*100:.1f}%"
        if 'improvements' in metrics:
            report['summary']['improvements'] = metrics['improvements']
    
    # Save report
    with open(args.output_report, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Report saved to {args.output_report}")
    
    # Print summary
    logger.info("=" * 80)
    logger.info("EVALUATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total examples: {evaluation_results['total']}")
    logger.info(f"\nBase Model:")
    logger.info(f"  Format Compliance: {metrics['base_model']['format_compliance']*100:.1f}%")
    logger.info(f"  Avg Score: {metrics['base_model']['avg_score']}")
    logger.info(f"  Avg Inference Time: {metrics['base_model']['avg_inference_time']}s")
    
    if 'fine_tuned_model' in metrics:
        logger.info(f"\nFine-tuned Model:")
        logger.info(f"  Format Compliance: {metrics['fine_tuned_model']['format_compliance']*100:.1f}%")
        logger.info(f"  Avg Score: {metrics['fine_tuned_model']['avg_score']}")
        logger.info(f"  Avg Inference Time: {metrics['fine_tuned_model']['avg_inference_time']}s")
        
        if 'improvements' in metrics:
            logger.info(f"\nImprovements:")
            for key, value in metrics['improvements'].items():
                logger.info(f"  {key}: {value}")
    
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
