# Image Training Data for LoRA Fine-Tuning

This guide explains how to review images and create training data for your Ansel Adams photography evaluation model.

## Current Status

- **Text training**: [ansel_print_filtered_train.jsonl](ansel_print_filtered_train.jsonl) (174 entries) ✅
- **Image training**: Need to create positive and negative examples
- **Available images**: 17 photos in `../ansel_ocr/extracted_photos/`

## Workflow Overview

```
1. Review existing images → Label positive/negative → Generate evaluations
2. Add negative examples → Point to bad photos → Auto-generate critiques
3. Combine datasets → Merge text + images → Export for LoRA training
4. Export with base64 → Convert images → Ready for vision model training
```

## Step 1: Review Your Existing Images

Use the interactive review tool to label your 17 extracted photos:

```bash
cd /Users/shaydu/dev/mondrian-macos/training/datasets

# Review and label images interactively
python review_images_for_training.py --mode review \
    --images-dir ../ansel_ocr/extracted_photos \
    --output ansel_image_training.jsonl
```

### What You'll Do:

For each image, you'll:
1. **View the image** (it will open in Preview automatically)
2. **Label it**: `p` for positive (good), `n` for negative (needs improvement), `s` to skip
3. **Give overall grade**: 0-10 scale
4. **Choose mode**:
   - `q` = Quick mode (uses templates)
   - `d` = Detailed mode (customize each dimension)

### Quick Mode Example:

```
Image: camera_003_sand_dunes.png
================================================================================

Open this image in Preview to view it:
  open ../ansel_ocr/extracted_photos/camera_003_sand_dunes.png

Label [p=positive, n=negative, s=skip]: p
Overall grade (0-10): 9.5

Quick mode (use templates) or Detailed? [q/d]: q
Advisor notes (overall assessment):
> This demonstrates mastery of form, light, and tonal range. The Zone System's power is evident.

✓ Added as POSITIVE example
```

## Step 2: Add Negative Examples

You need negative examples (bad photos) to teach the model what NOT to do.

### Option A: Add from a Directory of Bad Photos

```bash
# Point to a folder of bad/amateur photos
python add_negative_examples.py --dir /path/to/bad/photos \
    --output negative_examples.jsonl
```

The script will categorize each photo by common problems:
1. **Poor composition** - cluttered, no visual hierarchy
2. **Flat lighting** - no dimensional light, muddy tones
3. **Soft focus** - blurry, out of focus
4. **Cluttered frame** - too much visual noise
5. **No subject** - unclear what the photo is about
6. **Poor exposure** - blown highlights or blocked shadows

### Option B: Quick Mode (Auto-Label)

```bash
# Automatically label all as "poor_composition"
python add_negative_examples.py --dir /path/to/bad/photos --quick
```

### Where to Get Negative Examples:

1. **Your own rejected photos** - photos you took but didn't keep
2. **Stock photo sites** - search for "amateur photography" or "beginner mistakes"
3. **Reddit** - r/photocritique has many photos needing improvement
4. **Instagram** - search #beginnerphotography
5. **Free photo sites** - Unsplash, Pexels (filter for lower quality)

**Target**: 50-100 negative examples

## Step 3: Combine Everything

Merge your text training, positive images, and negative images:

```bash
# Combine all training data
cat ansel_print_filtered_train.jsonl \
    ansel_image_training.jsonl \
    negative_examples.jsonl \
    > ansel_complete_training.jsonl
```

## Step 4: Export for Vision Model Training

Convert to base64-encoded format required by vision models:

```bash
python review_images_for_training.py --mode export \
    --input ansel_image_training.jsonl \
    --export-output ansel_images_base64.jsonl

python review_images_for_training.py --mode export \
    --input negative_examples.jsonl \
    --export-output negative_examples_base64.jsonl
```

## Final Dataset Structure

Your complete training set should have:

| Type | Count | Purpose |
|------|-------|---------|
| Text-only (Ansel's voice) | 174 | Learn his writing style and philosophy |
| Positive images | 50-100 | Learn what makes great photography |
| Negative images | 50-100 | Learn what to critique and how |
| **Total** | **224-374** | **Balanced training set** |

## File Formats

### Text + Image Reference Format (ansel_image_training.jsonl)
```json
{
  "messages": [
    {
      "role": "user",
      "content": "<image>\nAs Ansel Adams, analyze this photograph..."
    },
    {
      "role": "assistant",
      "content": "{\"dimensional_analysis\": {...}, \"overall_grade\": \"9.0\", ...}"
    }
  ],
  "image_path": "/full/path/to/image.png",
  "label": "positive"
}
```

### Vision Model Format (ansel_images_base64.jsonl)
```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,iVBORw0KGgoAAAANS..."
          }
        },
        {
          "type": "text",
          "text": "As Ansel Adams, analyze this photograph..."
        }
      ]
    },
    {
      "role": "assistant",
      "content": "{\"dimensional_analysis\": {...}}"
    }
  ]
}
```

## Quality Guidelines

### Positive Examples Should Have:
- ✅ Strong composition (clear subject, visual hierarchy)
- ✅ Dimensional lighting (form-revealing)
- ✅ Full tonal range (Zone III to Zone VIII visible)
- ✅ Sharp focus on key elements
- ✅ Balanced visual weight
- ✅ Emotional impact
- ✅ Scores: 8-10 across dimensions

### Negative Examples Should Show:
- ❌ Common beginner mistakes
- ❌ Technical problems (soft focus, poor exposure)
- ❌ Compositional issues (clutter, no subject)
- ❌ Flat lighting (no tonal range)
- ❌ Scores: 2-6 across dimensions
- ❌ Constructive critique in Ansel's voice

## Next Steps

1. **Review your 17 existing images** (30-60 min)
2. **Collect 50-100 negative examples** from online sources
3. **Label negative examples** using the script (1-2 hours)
4. **Export everything to base64** format
5. **Start LoRA training** with complete dataset

## Checking Your Progress

```bash
# See what you have so far
python review_images_for_training.py --mode list --output ansel_image_training.jsonl

# Output shows:
# Total entries: 15
#   Positive: 12
#   Negative: 3
```

## Tips

- **Be honest with labels** - Not every Ansel photo is a 10. Some were teaching examples.
- **Use quick mode** for speed - Templates are high quality
- **Vary your critiques** for negative examples - Don't use the same problem type for everything
- **Balance positive/negative** - Aim for roughly 50/50 split in image training data
- **Keep text training separate** - The 174 text entries teach his voice without images

## Troubleshooting

**Q: Images are too large for training?**
A: The base64 export will work, but consider resizing images to max 1024px if needed.

**Q: Where do I get permission for negative examples?**
A: Use CC0/public domain images from Unsplash, Pexels, or your own rejected photos.

**Q: How do I know if my critiques are "Ansel-like"?**
A: The templates are based on his actual writing. Use them as guides.

**Q: Can I mix this with the text training?**
A: Yes! Combine them for the final dataset. Text teaches voice, images teach evaluation.
