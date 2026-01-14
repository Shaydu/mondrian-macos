# START HERE - Quick Start for Your Images

## Your Images Are Ready! ✅

You have **27 images** in: `/Users/shaydu/dev/mondrian-macos/training/datasets/ansel-images/`

Including:
- **22 Ansel Adams photos** (positive examples)
- **5 negative examples** (neg.jpg, neg2-5.jpg)
- Mix of famous works and teaching examples

## Start Reviewing RIGHT NOW (30 minutes)

```bash
cd /Users/shaydu/dev/mondrian-macos/training/datasets

# Review all 27 images with nuanced dimension scoring
python review_images_interactive.py \
    --images-dir ./ansel-images \
    --output ansel_images_reviewed.jsonl
```

### What Will Happen:

1. Each image opens in Preview
2. You label it: `p` (positive 8-10) or `n` (negative 0-6)
3. Choose scoring mode (recommend **Mode 3: Mixed**)
4. Score 2-3 standout dimensions, auto-fill rest
5. Done! Move to next image

### Recommended Approach:

**For Ansel's masterworks** (Tetons, Sand Dunes, etc.):
- Label: `p`
- Mode: `3` (Mixed)
- Pick dimensions: `2,3,8` (lighting, focus, emotional_impact)
- Score those: `10`
- Base score for rest: `9`

**For teaching examples** (camera_175_tidal_beach.png):
- Label: `p` or `n` (depending on quality)
- Mode: `3` (Mixed)
- Pick weak dimensions (e.g., composition, lighting)
- Score those: `4-6`
- Base score for rest: `6-7`

**For negative examples** (neg.jpg, neg2-5.jpg):
- Label: `n`
- Mode: `1` (Quick)
- Overall grade: `3-5`
- Auto-applies with variation

## After Reviewing (5 minutes)

### Check your progress:
```bash
python check_training_status.py
```

### You should see:
- ✅ Text training: 174 entries
- ✅ Image training: 27 entries (your new file!)

### Combine with text training:
```bash
cat ansel_print_filtered_train.jsonl \
    ansel_images_reviewed.jsonl \
    > ansel_combined_nuanced.jsonl
```

## Your Training Dataset

After combining:
- **174 text entries** - Ansel's voice from "The Print"
- **~22 positive images** - Ansel's photos with nuanced scoring
- **~5 negative images** - Critique examples
- **Total: ~201 examples** - Ready for LoRA training!

## Want More Negative Examples?

### Option 1: Download from Unsplash (15 min)
```bash
# Create a directory for more bad photos
mkdir -p bad_photos

# Download 20-50 amateur photos to bad_photos/
# Then auto-label them:
python add_negative_nuanced.py \
    --dir ./bad_photos \
    --output more_negative.jsonl

# Combine everything:
cat ansel_print_filtered_train.jsonl \
    ansel_images_reviewed.jsonl \
    more_negative.jsonl \
    > ansel_complete_training.jsonl
```

### Option 2: Keep It Simple
Your current 201 examples are sufficient for initial LoRA training!
You can always add more later.

## The Three Scoring Modes

### Mode 1: Quick (1 min per image)
- Set one overall grade (0-10)
- Auto-applies to all dimensions with ±1 variation
- **Use for:** Batch processing, simple evaluations

### Mode 2: Dimension by Dimension (3 min per image)
- Score all 8 dimensions independently
- Full control, most realistic
- **Use for:** Critical teaching examples

### Mode 3: Mixed ⭐ **RECOMMENDED** (2 min per image)
- Pick 2-3 standout dimensions (strengths or weaknesses)
- Score those carefully (0-10)
- Auto-fill rest with base score
- **Use for:** Most images - best balance of speed and nuance

## Example Session

```bash
$ python review_images_interactive.py --images-dir ./ansel-images

Found 27 images to review

================================================================================
Image: Adams_The_Tetons_and_the_Snake_River.jpg
================================================================================

Opening image...

Label [p=positive (8-10), n=negative (0-6), s=skip]: p

Scoring modes:
  1. Quick - Auto-assign scores based on overall grade
  2. Dimension by dimension - Score each independently
  3. Mixed - Set 2-3 key dimensions, auto-fill rest
Mode (1/2/3): 3

Set key dimensions that stand out (good or bad):
Available dimensions:
  1. composition
  2. lighting
  3. focus_sharpness
  4. color_harmony
  5. subject_isolation
  6. depth_perspective
  7. visual_balance
  8. emotional_impact

Enter dimension numbers to customize (e.g., '2,3,7'): 1,2,8

  COMPOSITION
  Arrangement of elements, visual hierarchy, rule of thirds
  Score (0-10, or 'a' for auto-comment): 10
  Comment (or Enter for auto): [Press Enter]

  LIGHTING
  Quality of light, tonal range, Zone System application
  Score (0-10, or 'a' for auto-comment): 10
  Comment (or Enter for auto): [Press Enter]

  EMOTIONAL_IMPACT
  Emotional resonance, connection, meaning beyond documentation
  Score (0-10, or 'a' for auto-comment): 10
  Comment (or Enter for auto): [Press Enter]

Base score for other dimensions (0-10): 9

Overall grade: 9.6
Advisor notes (or Enter for auto): [Press Enter]

✓ Added as POSITIVE example

[Next image...]
```

## Tips for Speed

1. **Press Enter to accept defaults** - Auto-comments are high quality
2. **Use Mode 3** for most images
3. **Batch similar images** - Review all masterworks, then teaching examples, then negatives
4. **Don't overthink scores** - 8-10 range for good photos, 3-6 for teaching moments
5. **Skip if unsure** - Press `s` to skip an image

## After Training

Your final file for LoRA training:
```
ansel_combined_nuanced.jsonl
```

Contains:
- Ansel's voice and philosophy (text)
- Nuanced photo evaluations (images)
- Mixed positive/negative examples
- Independent dimension scoring

Ready for vision model fine-tuning! 🎉

## Questions?

- **See all images first?** `open ansel-images/`
- **Check progress?** `python check_training_status.py`
- **Need help?** See [NUANCED_TRAINING.md](NUANCED_TRAINING.md)
- **Directory setup?** See [DIRECTORY_SETUP.md](DIRECTORY_SETUP.md)

## One Command to Start

```bash
cd /Users/shaydu/dev/mondrian-macos/training/datasets && \
python review_images_interactive.py --images-dir ./ansel-images --output ansel_images_reviewed.jsonl
```

That's it! Start reviewing your images now. ⚡
