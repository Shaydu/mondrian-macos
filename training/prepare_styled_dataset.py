#!/usr/bin/env python3
"""
Prepare training dataset with authentic advisor voice/style.

This script creates training data where responses are written in the advisor's
distinctive voice and writing style, enabling the fine-tuned model to respond
authentically as that advisor.

Usage:
    python training/prepare_styled_dataset.py --advisor ansel
    python training/prepare_styled_dataset.py --advisor ansel --use-llm  # Use LLM to rewrite
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Paths
DB_PATH = PROJECT_ROOT / "mondrian" / "mondrian.db"
OUTPUT_DIR = PROJECT_ROOT / "training" / "datasets"
STYLES_DIR = PROJECT_ROOT / "training" / "advisor_styles"

DIMENSIONS = [
    "composition",
    "lighting",
    "focus_sharpness",
    "color_harmony",
    "subject_isolation",
    "depth_perspective",
    "visual_balance",
    "emotional_impact"
]


def load_advisor_style(advisor_id: str) -> Dict[str, Any]:
    """Load the style configuration for an advisor."""
    style_path = STYLES_DIR / f"{advisor_id}_style.json"
    if not style_path.exists():
        print(f"Warning: No style file found at {style_path}")
        return {}

    with open(style_path) as f:
        return json.load(f)


def get_dimensional_profiles(advisor_id: str) -> List[Dict[str, Any]]:
    """Fetch dimensional profiles from database for an advisor."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM dimensional_profiles
        WHERE advisor_id = ?
        AND image_path NOT LIKE '%temp%'
        AND image_path NOT LIKE '%analyze_image%'
        AND image_path LIKE '%' || ? || '%'
    """, (advisor_id, advisor_id))

    profiles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return profiles


def rewrite_comment_in_style(
    dimension: str,
    original_comment: str,
    score: int,
    style: Dict[str, Any],
    image_name: str
) -> str:
    """
    Rewrite a comment in the advisor's authentic voice.
    This is a template-based approach - for better results, use --use-llm.
    """
    vocab = style.get("dimension_vocabulary", {}).get(dimension, {})

    # Determine quality tier based on score
    if score >= 9:
        phrases = vocab.get("excellent", ["exceptional work"])
    elif score >= 7:
        phrases = vocab.get("good", ["solid execution"])
    else:
        phrases = vocab.get("needs_work", ["room for growth"])

    # Use the first phrase as a starting point
    style_phrase = phrases[0] if phrases else ""

    # Get signature phrases
    signatures = style.get("signature_phrases", [])

    # Build styled comment based on dimension
    if dimension == "lighting":
        if score >= 8:
            return f"{style_phrase}. The tonal values here demonstrate understanding of how light reveals form. {original_comment}"
        else:
            return f"The light serves its purpose, though one senses it could reveal more. {original_comment}"

    elif dimension == "composition":
        if score >= 8:
            return f"{style_phrase}. The arrangement speaks of careful visualization before the exposure was made. {original_comment}"
        else:
            return f"The composition functions, though I would counsel more deliberation. {original_comment}"

    elif dimension == "emotional_impact":
        if score >= 8:
            return f"Photography is a way of feeling, of touching, of loving—and this image demonstrates that truth. {original_comment}"
        else:
            return f"Technical competence must serve emotional truth. Here, one searches for deeper feeling. {original_comment}"

    elif dimension == "focus_sharpness":
        if score >= 8:
            return f"Crystalline precision throughout—every plane resolved with clear intention. {original_comment}"
        else:
            return f"Sharpness must serve the visualization. Here it is adequate but not inspired. {original_comment}"

    else:
        # Generic styling for other dimensions
        if score >= 8:
            return f"{style_phrase}. {original_comment}"
        else:
            return f"{original_comment} One might explore further possibilities here."


def rewrite_with_llm(
    profile: Dict[str, Any],
    style: Dict[str, Any],
    image_path: str
) -> Dict[str, Any]:
    """
    Use an LLM to rewrite the dimensional analysis in the advisor's voice.
    Returns the rewritten dimensional_analysis dict.
    """
    try:
        import anthropic
    except ImportError:
        print("Error: anthropic package required for --use-llm")
        print("Install with: pip install anthropic")
        sys.exit(1)

    client = anthropic.Anthropic()

    # Build the current analysis
    current_analysis = {}
    for dim in DIMENSIONS:
        score = profile.get(f"{dim}_score", 7)
        comment = profile.get(f"{dim}_comment", "")
        current_analysis[dim] = {"score": score, "comment": comment}

    # Create the prompt
    style_info = json.dumps({
        "full_name": style.get("full_name"),
        "signature_phrases": style.get("signature_phrases", []),
        "writing_samples": style.get("writing_samples", []),
        "critique_voice": style.get("critique_voice", {}),
        "scoring_philosophy": style.get("scoring_philosophy", ""),
        "example_critiques": style.get("example_critiques", [])
    }, indent=2)

    prompt = f"""You are rewriting photography critiques to sound authentically like {style.get('full_name', 'the advisor')}.

Here is information about their writing style and voice:
{style_info}

Here is the current dimensional analysis to rewrite:
{json.dumps(current_analysis, indent=2)}

The image being analyzed is: {Path(image_path).name}

IMPORTANT GUIDELINES:
1. Rewrite each comment in {style.get('full_name')}'s authentic voice and style
2. Use their signature phrases and vocabulary naturally (don't force them)
3. The scores may need adjustment - {style.get('full_name')} had high standards:
   - Score 10: Transcendent, museum-worthy work (very rare)
   - Score 8-9: Excellent work showing mastery
   - Score 6-7: Good, competent work
   - Score 4-5: Needs improvement
4. Comments should be 2-3 sentences, not generic platitudes
5. Reference specific techniques when relevant (Zone System, visualization, etc.)

Return ONLY a valid JSON object with this structure:
{{
  "dimensional_analysis": {{
    "composition": {{"score": X, "comment": "..."}},
    "lighting": {{"score": X, "comment": "..."}},
    "focus_sharpness": {{"score": X, "comment": "..."}},
    "color_harmony": {{"score": X, "comment": "..."}},
    "subject_isolation": {{"score": X, "comment": "..."}},
    "depth_perspective": {{"score": X, "comment": "..."}},
    "visual_balance": {{"score": X, "comment": "..."}},
    "emotional_impact": {{"score": X, "comment": "..."}}
  }}
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse the response
    response_text = response.content[0].text.strip()

    # Handle markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    try:
        result = json.loads(response_text)
        return result.get("dimensional_analysis", current_analysis)
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse LLM response: {e}")
        return current_analysis


def create_styled_training_example(
    image_path: str,
    dimensional_analysis: Dict[str, Any],
    advisor_id: str,
    style: Dict[str, Any],
    overall_grade: Optional[str] = None
) -> Dict[str, Any]:
    """Create a training example with styled response."""

    # Calculate overall grade from scores if not provided
    if not overall_grade:
        scores = [dim.get("score", 7) for dim in dimensional_analysis.values()]
        avg_score = sum(scores) / len(scores) if scores else 7
        overall_grade = f"{avg_score:.1f}"

    response = {
        "dimensional_analysis": dimensional_analysis,
        "overall_grade": overall_grade
    }

    # Create the user prompt
    user_prompt = f"""<image>
As the photography advisor '{advisor_id}', analyze this photograph across all 8 dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact).

Respond in your authentic voice as {style.get('full_name', advisor_id)}. Provide scores from 0-10 and detailed comments reflecting your philosophy and expertise."""

    messages = [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": json.dumps(response, indent=2)}
    ]

    return {
        "messages": messages,
        "image_path": image_path
    }


def prepare_styled_dataset(
    advisor_id: str,
    use_llm: bool = False,
    output_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """Prepare training dataset with styled responses."""

    print(f"Preparing styled dataset for advisor: {advisor_id}")

    # Load style configuration
    style = load_advisor_style(advisor_id)
    if not style:
        print(f"Warning: No style configuration found for {advisor_id}")
        print("Using basic styling only.")
    else:
        print(f"Loaded style for: {style.get('full_name', advisor_id)}")

    # Get profiles from database
    profiles = get_dimensional_profiles(advisor_id)
    print(f"Found {len(profiles)} dimensional profiles")

    if not profiles:
        print("No profiles found. Please run analysis on reference images first.")
        return []

    examples = []

    for i, profile in enumerate(profiles):
        image_path = profile.get("image_path")

        if not image_path or not os.path.exists(image_path):
            print(f"Skipping missing image: {image_path}")
            continue

        print(f"\nProcessing {i+1}/{len(profiles)}: {Path(image_path).name}")

        if use_llm:
            # Use LLM to rewrite in authentic voice
            print("  Using LLM to rewrite in authentic voice...")
            dimensional_analysis = rewrite_with_llm(profile, style, image_path)
        else:
            # Use template-based styling
            dimensional_analysis = {}
            for dim in DIMENSIONS:
                score = profile.get(f"{dim}_score", 7)
                original_comment = profile.get(f"{dim}_comment", "")

                styled_comment = rewrite_comment_in_style(
                    dimension=dim,
                    original_comment=original_comment,
                    score=score,
                    style=style,
                    image_name=Path(image_path).name
                )

                dimensional_analysis[dim] = {
                    "score": score,
                    "comment": styled_comment
                }

        # Create training example
        example = create_styled_training_example(
            image_path=image_path,
            dimensional_analysis=dimensional_analysis,
            advisor_id=advisor_id,
            style=style,
            overall_grade=profile.get("overall_grade")
        )

        examples.append(example)
        print(f"  Added with styled comments")

    print(f"\nTotal training examples: {len(examples)}")

    # Save dataset
    if output_path:
        output_path.mkdir(parents=True, exist_ok=True)
        jsonl_path = output_path / f"{advisor_id}_train.jsonl"

        with open(jsonl_path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")

        print(f"\nSaved dataset to: {jsonl_path}")

    return examples


def main():
    parser = argparse.ArgumentParser(
        description="Prepare LoRA training dataset with authentic advisor voice"
    )
    parser.add_argument(
        "--advisor", "-a",
        type=str,
        default="ansel",
        help="Advisor ID (default: ansel)"
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM (Claude) to rewrite responses in authentic voice (recommended)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output directory (default: training/datasets)"
    )

    args = parser.parse_args()
    output_dir = Path(args.output) if args.output else OUTPUT_DIR

    examples = prepare_styled_dataset(
        advisor_id=args.advisor,
        use_llm=args.use_llm,
        output_path=output_dir
    )

    if not examples:
        print("No training examples created. Exiting.")
        sys.exit(1)

    print("\nDataset preparation complete!")
    print(f"\nNext step: Run training with:")
    print(f"  python training/train_lora.py --advisor {args.advisor}")


if __name__ == "__main__":
    main()
