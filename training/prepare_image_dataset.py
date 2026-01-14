#!/usr/bin/env python3
"""
Prepare image training dataset from extracted Ansel Adams photos.

Creates image+text training examples using the curated photos from
The Camera and The Print volumes.

Usage:
    python training/prepare_image_dataset.py
"""

import json
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PHOTOS_DIR = PROJECT_ROOT / "training" / "ansel_ocr" / "extracted_photos"
METADATA_PATH = PHOTOS_DIR / "metadata.yaml"
OUTPUT_PATH = PROJECT_ROOT / "training" / "datasets" / "ansel_train.jsonl"

# Ansel Adams style responses for different image types
STYLE_TEMPLATES = {
    "sand_dunes": {
        "composition": {"score": 9, "comment": "The flowing lines of the dunes create a natural rhythm that guides the eye through the frame. This demonstrates the principle of previsualization—seeing the final print before making the exposure."},
        "lighting": {"score": 10, "comment": "Extraordinary use of side lighting reveals the sculptural quality of the sand. Each grain becomes a universe of tonal values, from deepest shadow to brilliant highlight."},
        "focus_sharpness": {"score": 9, "comment": "Edge-to-edge sharpness achieved through careful selection of aperture and focus point. The texture of sand rendered with crystalline clarity."},
        "color_harmony": {"score": 8, "comment": "The monochromatic palette emphasizes form over color, allowing the eye to appreciate pure tonal relationships."},
        "subject_isolation": {"score": 8, "comment": "The dunes stand as abstract forms, isolated from context yet universally evocative of nature's artistry."},
        "depth_perspective": {"score": 9, "comment": "The receding dune crests establish a powerful sense of depth, drawing the viewer into infinite space."},
        "visual_balance": {"score": 9, "comment": "Dynamic asymmetry creates tension and interest while maintaining overall harmony."},
        "emotional_impact": {"score": 10, "comment": "This image speaks to the eternal—the timeless dance of light and shadow across nature's canvas."}
    },
    "mountains": {
        "composition": {"score": 9, "comment": "The mountain mass anchors the composition with geological authority. Every element serves the whole."},
        "lighting": {"score": 9, "comment": "The Zone System reveals its power here—shadows retain detail while highlights sing with brilliance."},
        "focus_sharpness": {"score": 9, "comment": "Hyperfocal distance calculation ensures sharpness from foreground to infinity. Technical precision in service of vision."},
        "color_harmony": {"score": 8, "comment": "Tonal values speak louder than color. The grayscale reveals what color photography often obscures."},
        "subject_isolation": {"score": 8, "comment": "The mountain dominates yet does not overwhelm. Context enriches rather than distracts."},
        "depth_perspective": {"score": 10, "comment": "From immediate foreground to distant peak, the eye travels through space as the photographer intended."},
        "visual_balance": {"score": 9, "comment": "Earth and sky in careful proportion, each serving the other in visual dialogue."},
        "emotional_impact": {"score": 10, "comment": "One stands before such an image and feels the presence of something greater than oneself."}
    },
    "forest": {
        "composition": {"score": 8, "comment": "The vertical thrust of the trees creates a cathedral-like atmosphere. Nature's own architecture."},
        "lighting": {"score": 9, "comment": "Diffused light penetrates the canopy, creating a luminous quality that reveals texture without harshness."},
        "focus_sharpness": {"score": 8, "comment": "Selective focus guides attention while maintaining overall clarity of form."},
        "color_harmony": {"score": 8, "comment": "The monochrome treatment emphasizes the interplay of light and dark, bark and leaf."},
        "subject_isolation": {"score": 7, "comment": "The complexity of forest requires careful seeing. Each element must find its place."},
        "depth_perspective": {"score": 8, "comment": "Receding trees establish rhythm and depth. The eye finds pathways through the visual forest."},
        "visual_balance": {"score": 8, "comment": "Vertical elements balanced by horizontal ground plane. Stability within complexity."},
        "emotional_impact": {"score": 9, "comment": "The forest speaks of patience, of time measured in centuries. We are visitors in an ancient world."}
    },
    "waterfall": {
        "composition": {"score": 9, "comment": "The water's descent creates natural leading lines. The eye follows gravity's path."},
        "lighting": {"score": 8, "comment": "The interplay of mist and light creates ethereal atmosphere. Zone III shadows preserve mystery."},
        "focus_sharpness": {"score": 8, "comment": "The choice of shutter speed transforms moving water into silken flow—technique serving vision."},
        "color_harmony": {"score": 8, "comment": "Water, rock, and vegetation create natural tonal harmony."},
        "subject_isolation": {"score": 8, "comment": "The waterfall commands attention while environment provides essential context."},
        "depth_perspective": {"score": 8, "comment": "From near rock to distant cascade, depth is carefully constructed."},
        "visual_balance": {"score": 9, "comment": "The weight of falling water balanced by surrounding stillness."},
        "emotional_impact": {"score": 9, "comment": "Moving water speaks of impermanence and eternal return. Each moment unique yet part of endless flow."}
    },
    "default": {
        "composition": {"score": 8, "comment": "The arrangement of elements demonstrates thoughtful visualization—seeing the final image before exposure."},
        "lighting": {"score": 8, "comment": "Light has been observed carefully. The tonal relationships reveal form and texture."},
        "focus_sharpness": {"score": 8, "comment": "Technical precision serves the vision. Sharpness where needed, softness where appropriate."},
        "color_harmony": {"score": 7, "comment": "The tonal palette works in service of the image's mood and meaning."},
        "subject_isolation": {"score": 7, "comment": "The subject emerges from its context with clarity of purpose."},
        "depth_perspective": {"score": 8, "comment": "The sense of space is well established, inviting the viewer into the frame."},
        "visual_balance": {"score": 8, "comment": "Elements are arranged with consideration for visual weight and harmony."},
        "emotional_impact": {"score": 8, "comment": "The image communicates beyond mere documentation. It speaks to the viewer."}
    }
}


def get_style_for_image(filename: str, title: str) -> dict:
    """Determine which style template to use based on filename/title."""
    lower = (filename + " " + title).lower()

    if "dune" in lower or "sand" in lower:
        return STYLE_TEMPLATES["sand_dunes"]
    elif "mountain" in lower or "teton" in lower or "williamson" in lower or "half dome" in lower:
        return STYLE_TEMPLATES["mountains"]
    elif "redwood" in lower or "forest" in lower or "tree" in lower:
        return STYLE_TEMPLATES["forest"]
    elif "waterfall" in lower or "cascade" in lower:
        return STYLE_TEMPLATES["waterfall"]
    else:
        return STYLE_TEMPLATES["default"]


def create_training_example(image_path: str, metadata: dict) -> dict:
    """Create a single training example for an image."""

    title = metadata.get("title", "Untitled")
    year = metadata.get("year", "unknown")
    source = metadata.get("source", "")

    # Get appropriate style template
    style = get_style_for_image(metadata.get("filename", ""), title)

    # Calculate overall grade
    scores = [dim["score"] for dim in style.values()]
    overall_grade = sum(scores) / len(scores)

    # Create the response in Ansel Adams' voice
    response = {
        "dimensional_analysis": style,
        "overall_grade": f"{overall_grade:.1f}",
        "advisor_notes": f"This image, '{title}' ({year}), exemplifies principles I have long advocated. "
                        f"The photograph must be visualized before exposure—every tonal value, every "
                        f"relationship of light and shadow, anticipated and controlled."
    }

    # Create user prompt
    user_prompt = """<image>
As Ansel Adams, analyze this photograph across all 8 dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact).

Respond in your authentic voice, drawing on your philosophy of previsualization, the Zone System, and your deep connection to the natural world. Provide scores from 0-10 and detailed comments."""

    return {
        "messages": [
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": json.dumps(response, indent=2)}
        ],
        "image_path": image_path
    }


def main():
    print(f"Reading metadata from: {METADATA_PATH}")

    if not METADATA_PATH.exists():
        print(f"Error: Metadata not found at {METADATA_PATH}")
        return

    with open(METADATA_PATH) as f:
        metadata = yaml.safe_load(f)

    photos = metadata.get("photos", [])
    print(f"Found {len(photos)} photos in metadata")

    examples = []
    for photo in photos:
        filename = photo.get("filename")
        image_path = str(PHOTOS_DIR / filename)

        if not (PHOTOS_DIR / filename).exists():
            print(f"  Warning: Image not found: {filename}")
            continue

        example = create_training_example(image_path, photo)
        examples.append(example)
        print(f"  Added: {filename} - {photo.get('title', 'Untitled')[:40]}...")

    print(f"\nGenerated {len(examples)} image training examples")

    # Write to JSONL
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"Saved to: {OUTPUT_PATH}")

    # Now update combined dataset
    text_dataset = PROJECT_ROOT / "training" / "datasets" / "ansel_text_train.jsonl"
    combined_path = PROJECT_ROOT / "training" / "datasets" / "ansel_combined_train.jsonl"

    with open(combined_path, "w") as out_f:
        # Add image examples first
        for example in examples:
            out_f.write(json.dumps(example) + "\n")

        # Add text examples
        if text_dataset.exists():
            with open(text_dataset) as txt_f:
                for line in txt_f:
                    out_f.write(line)
            print(f"Combined with text dataset from: {text_dataset}")

    with open(combined_path) as f:
        combined_count = sum(1 for _ in f)

    print(f"\nCombined dataset: {combined_count} examples")
    print(f"  - {len(examples)} image examples")
    print(f"  - {combined_count - len(examples)} text examples")
    print(f"Saved to: {combined_path}")


if __name__ == "__main__":
    main()
