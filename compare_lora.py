#!/usr/bin/env python3
"""
Compare baseline vs LoRA fine-tuned model responses.
"""
import sys
from mondrian.strategies.context import AnalysisContext

def compare_models(image_path: str, advisor_id: str = "ansel"):
    """Compare baseline vs LoRA responses for the same image."""

    print("=" * 80)
    print(f"Comparing models on: {image_path}")
    print("=" * 80)

    # Test baseline (untrained)
    print("\n🔵 BASELINE MODEL (Untrained)")
    print("-" * 80)
    context_baseline = AnalysisContext()
    context_baseline.set_strategy("baseline", advisor_id)
    result_baseline = context_baseline.analyze(image_path, advisor_id)

    print(f"\nOverall Grade: {result_baseline.overall_grade}")
    print(f"Mode Used: {result_baseline.mode_used}")
    print("\nDimensional Analysis:")
    for dimension, data in result_baseline.dimensional_analysis.items():
        if isinstance(data, dict):
            score = data.get('score', 'N/A')
            comment = data.get('comment', '')
            print(f"  {dimension}: {score} - {comment}")

    advisor_notes = result_baseline.dimensional_analysis.get('advisor_notes', '')
    if advisor_notes:
        print(f"\nAdvisor Notes: {advisor_notes}")

    # Test LoRA (fine-tuned)
    print("\n🟢 LORA MODEL (Fine-tuned)")
    print("-" * 80)
    context_lora = AnalysisContext()
    context_lora.set_strategy("lora", advisor_id)
    result_lora = context_lora.analyze(image_path, advisor_id)

    print(f"\nOverall Grade: {result_lora.overall_grade}")
    print(f"Mode Used: {result_lora.mode_used}")
    print("\nDimensional Analysis:")
    for dimension, data in result_lora.dimensional_analysis.items():
        if isinstance(data, dict):
            score = data.get('score', 'N/A')
            comment = data.get('comment', '')
            print(f"  {dimension}: {score} - {comment}")

    advisor_notes = result_lora.dimensional_analysis.get('advisor_notes', '')
    if advisor_notes:
        print(f"\nAdvisor Notes: {advisor_notes}")

    print("\n" + "=" * 80)
    print("Comparison complete!")
    print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python compare_lora.py <image_path>")
        print("\nExample:")
        print("  python compare_lora.py training/ansel_ocr/extracted_photos/camera_003_sand_dunes.png")
        sys.exit(1)

    image_path = sys.argv[1]
    compare_models(image_path)
