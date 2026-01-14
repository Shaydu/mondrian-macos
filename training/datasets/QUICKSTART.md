# Quick Start: Add Images to Your Training Data

You have 174 text-only training examples. Now let's add images!

## ⚡ Fast Track (30 minutes)

### Step 1: Review Your 17 Existing Images (15 min)

```bash
cd /Users/shaydu/dev/mondrian-macos/training/datasets

# Start the interactive review
python review_images_for_training.py --mode review \
    --images-dir ../ansel_ocr/extracted_photos \
    --output ansel_image_training.jsonl
```

**What to do:**
- For each image that opens in Preview, press:
  - `p` = positive (good photo, scores 8-10)
  - `n` = negative (needs work, scores 3-6)
  - `s` = skip it
- Enter overall grade (0-10)
- Type `q` for quick mode (uses templates)
- Press Enter to use default advisor notes

**Pro tip:** Most of Ansel's extracted photos are good examples, so label most as `p` with grades 8-10.

### Step 2: Get Negative Examples (15 min)

You need bad photos for the model to learn what NOT to do.

**Easy sources:**
1. Go to Unsplash.com and search "amateur photography"
2. Download 50 images to a folder like `~/Downloads/bad_photos`
3. Or use your own rejected photos

```bash
# Label all your bad photos
python add_negative_examples.py \
    --dir ~/Downloads/bad_photos \
    --output negative_examples.jsonl \
    --quick
```

**Quick mode** auto-labels everything as "poor composition" - perfect for getting started!

### Step 3: Check Status

```bash
python check_training_status.py
```

You should see:
- ✅ Text-only training: 174 entries
- ✅ Positive image examples: ~15 entries
- ✅ Negative image examples: ~50 entries

### Step 4: Export for Training

```bash
# Export positive examples with base64 images
python review_images_for_training.py --mode export \
    --input ansel_image_training.jsonl \
    --export-output ansel_images_base64.jsonl

# Export negative examples with base64 images
python review_images_for_training.py --mode export \
    --input negative_examples.jsonl \
    --export-output negative_examples_base64.jsonl

# Combine everything
cat ansel_print_filtered_train.jsonl \
    ansel_image_training.jsonl \
    negative_examples.jsonl \
    > ansel_complete_training.jsonl
```

### Done! 🎉

You now have:
- **~240 training examples** (174 text + ~65 images)
- **Balanced positive/negative** image examples
- **Ready for LoRA training**

## 📊 What You Get

### Text Training (174 entries)
Teaches the model Ansel's voice and philosophy from his book "The Print"

### Positive Image Examples (~15-20)
- Your 17 extracted Ansel Adams photos
- Scores 8-10 across dimensions
- Shows what excellent photography looks like

### Negative Image Examples (~50)
- Amateur/flawed photos
- Scores 3-6 across dimensions
- Teaches constructive critique

## 🎯 Tips for Better Results

### Labeling Positive Examples
- Be selective - not every photo is a 10
- Look for: strong composition, good lighting, full tonal range
- Ansel's teaching examples might score 7-8 (good but not masterworks)

### Choosing Negative Examples
- Variety is key - different problems (composition, lighting, focus)
- Don't use professional photos with minor flaws
- Use clearly flawed amateur work
- Think: "What would Ansel critique here?"

### Time Savers
- Use **quick mode** (`q`) for templates - they're high quality
- Use `--quick` flag for batch labeling negative examples
- Press Enter to accept default advisor notes

## 📁 Files You'll Create

```
ansel_image_training.jsonl          # Your labeled images (with file paths)
negative_examples.jsonl             # Negative examples (with file paths)
ansel_images_base64.jsonl          # Positive examples (base64 encoded)
negative_examples_base64.jsonl     # Negative examples (base64 encoded)
ansel_complete_training.jsonl      # Everything combined
```

## 🚀 Next: LoRA Training

Once you have your complete dataset, you can start LoRA fine-tuning:

```bash
# Your training file is ready:
# /Users/shaydu/dev/mondrian-macos/training/datasets/ansel_complete_training.jsonl

# For vision models, use the base64 versions:
# - ansel_images_base64.jsonl (positive examples with images)
# - negative_examples_base64.jsonl (negative examples with images)
# - ansel_print_filtered_train.jsonl (text-only for voice)
```

## 💡 Need More?

**Want 100+ negative examples?** Run add_negative_examples.py multiple times on different folders:

```bash
python add_negative_examples.py --dir ~/Downloads/bad_photos_1 --output neg1.jsonl --quick
python add_negative_examples.py --dir ~/Downloads/bad_photos_2 --output neg2.jsonl --quick
cat neg1.jsonl neg2.jsonl > negative_examples.jsonl
```

**Want more positive examples?** Point review script at any folder of good photos:

```bash
python review_images_for_training.py --mode review \
    --images-dir ~/Photos/best_landscapes \
    --output more_positive.jsonl
```

## 🆘 Troubleshooting

**Script won't run?**
```bash
chmod +x *.py
python3 review_images_for_training.py --help
```

**Images won't open?**
Use `open` command manually:
```bash
open ../ansel_ocr/extracted_photos/camera_003_sand_dunes.png
```

**Need to see progress?**
```bash
python check_training_status.py
```
