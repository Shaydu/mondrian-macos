# Where to Put Your Training Images

## Quick Answer

Put your images in these directories:

```
/Users/shaydu/dev/mondrian-macos/training/
├── ansel_ocr/extracted_photos/     # Your existing 17 Ansel photos (✅ already here)
├── user_images/                     # Create this for user photos to evaluate
│   ├── good/                        # Positive training examples (8-10 scores)
│   └── bad/                         # Negative training examples (2-6 scores)
└── datasets/                        # Training data files (.jsonl)
    └── (all your .jsonl files)
```

## Detailed Setup

### 1. Existing Ansel Photos (Already Set Up)

Your 17 extracted Ansel Adams photos are already in:
```
/Users/shaydu/dev/mondrian-macos/training/ansel_ocr/extracted_photos/
```

Scripts default to this directory. Use them with:
```bash
python review_images_interactive.py
# Defaults to --images-dir ../ansel_ocr/extracted_photos
```

### 2. Create Directories for Your Training Images

```bash
cd /Users/shaydu/dev/mondrian-macos/training

# Create directories for positive examples
mkdir -p user_images/good

# Create directories for negative examples
mkdir -p user_images/bad
```

### 3. Add Your Images

#### For Positive Examples (Good Photos):
```bash
# Copy or move good photos here
cp ~/Downloads/good_photo1.jpg user_images/good/
cp ~/Downloads/good_photo2.jpg user_images/good/
```

Then review them:
```bash
cd datasets
python review_images_interactive.py \
    --images-dir ../user_images/good \
    --output positive_user_examples.jsonl
```

#### For Negative Examples (Bad Photos):
```bash
# Copy bad/amateur photos here
cp ~/Downloads/bad_photo1.jpg user_images/bad/
cp ~/Downloads/bad_photo2.jpg user_images/bad/
```

Then auto-label them:
```bash
cd datasets
python add_negative_nuanced.py \
    --dir ../user_images/bad \
    --output negative_user_examples.jsonl
```

## Full Directory Structure

```
/Users/shaydu/dev/mondrian-macos/training/
│
├── ansel_ocr/
│   ├── extracted_photos/                    # 17 Ansel Adams photos ✅
│   │   ├── camera_003_sand_dunes.png
│   │   ├── camera_015_mt_williamson.png
│   │   └── ... (15 more)
│   └── (other OCR files)
│
├── user_images/                             # ⬅️ CREATE THIS
│   ├── good/                                # Positive training examples
│   │   ├── excellent_landscape_1.jpg
│   │   ├── excellent_landscape_2.jpg
│   │   └── ... (50-100 photos)
│   │
│   └── bad/                                 # Negative training examples
│       ├── poor_composition_1.jpg
│       ├── soft_focus_1.jpg
│       └── ... (50-100 photos)
│
└── datasets/                                # Training data files
    ├── ansel_print_filtered_train.jsonl    # Text training (174) ✅
    ├── ansel_image_training_nuanced.jsonl  # Ansel photos labeled
    ├── positive_user_examples.jsonl        # Your good photos labeled
    ├── negative_user_examples.jsonl        # Your bad photos labeled
    ├── ansel_complete_training.jsonl       # Everything combined
    │
    └── (Python scripts)
        ├── review_images_interactive.py
        ├── add_negative_nuanced.py
        ├── check_training_status.py
        └── ...
```

## One-Time Setup Commands

```bash
# Navigate to training directory
cd /Users/shaydu/dev/mondrian-macos/training

# Create user_images directories
mkdir -p user_images/good
mkdir -p user_images/bad

echo "✅ Directories created!"
echo ""
echo "Next steps:"
echo "1. Add photos to user_images/good/ (50-100 excellent photos)"
echo "2. Add photos to user_images/bad/ (50-100 flawed photos)"
echo "3. Run scripts from datasets/ directory"
```

## Where to Get Images

### Positive Examples (user_images/good/)
- Your best photography
- Ansel Adams photos (from books, public domain)
- Master photographers: Edward Weston, Henri Cartier-Bresson
- Stock sites filtered for "professional landscape photography"
- **Tip**: Search "award winning photography" on Unsplash

### Negative Examples (user_images/bad/)
- Your rejected photos (learning from mistakes)
- Amateur photography from Reddit r/photocritique
- Beginner photography from Instagram #beginnerphotography
- Intentionally flawed examples (out of focus, poor composition)
- Stock sites filtered for "amateur photography"

## Using the Scripts

### Review Ansel's Photos (Already Have These)
```bash
cd /Users/shaydu/dev/mondrian-macos/training/datasets

python review_images_interactive.py \
    --images-dir ../ansel_ocr/extracted_photos \
    --output ansel_image_training_nuanced.jsonl
```

### Review Your Good Photos
```bash
python review_images_interactive.py \
    --images-dir ../user_images/good \
    --output positive_user_examples.jsonl
```

### Auto-Label Your Bad Photos
```bash
# Nuanced scoring (recommended - more realistic)
python add_negative_nuanced.py \
    --dir ../user_images/bad \
    --output negative_user_examples.jsonl

# Or with specific problem type
python add_negative_nuanced.py \
    --dir ../user_images/bad \
    --problem good_comp_bad_focus \
    --output negative_user_examples.jsonl
```

### Check Status
```bash
python check_training_status.py
```

### Combine Everything
```bash
cat ansel_print_filtered_train.jsonl \
    ansel_image_training_nuanced.jsonl \
    positive_user_examples.jsonl \
    negative_user_examples.jsonl \
    > ansel_complete_training.jsonl
```

## Important Notes

### About File Paths
- Images can be anywhere on your computer
- The .jsonl files store the full path to each image
- For training, images will be base64-encoded (no path needed)

### About Image Formats
- Supported: .png, .jpg, .jpeg
- Recommended size: 1024px max dimension
- Scripts handle all formats automatically

### About Backups
```bash
# Backup your training data
cp ansel_complete_training.jsonl ansel_complete_training_backup_$(date +%Y%m%d).jsonl
```

## Quick Start Example

```bash
# 1. Create directories
cd /Users/shaydu/dev/mondrian-macos/training
mkdir -p user_images/good user_images/bad

# 2. Download/copy 50 good photos to user_images/good/
# 3. Download/copy 50 bad photos to user_images/bad/

# 4. Navigate to datasets
cd datasets

# 5. Review Ansel's photos
python review_images_interactive.py

# 6. Review your good photos
python review_images_interactive.py \
    --images-dir ../user_images/good \
    --output positive_user_examples.jsonl

# 7. Auto-label bad photos
python add_negative_nuanced.py \
    --dir ../user_images/bad \
    --output negative_user_examples.jsonl

# 8. Check status
python check_training_status.py

# 9. Combine everything
cat ansel_print_filtered_train.jsonl \
    ansel_image_training_nuanced.jsonl \
    positive_user_examples.jsonl \
    negative_user_examples.jsonl \
    > ansel_complete_training.jsonl

# Done! 🎉
```

## FAQ

**Q: Can I use images from anywhere on my computer?**
A: Yes! Use `--images-dir /any/path/to/images` with any script.

**Q: What if I already have images in different folders?**
A: No need to move them! Just point the scripts at each folder:
```bash
python review_images_interactive.py --images-dir ~/Photos/landscapes
python review_images_interactive.py --images-dir ~/Photos/portraits
```

**Q: Can I add more images later?**
A: Yes! Just run the scripts on new folders and append to your .jsonl files:
```bash
python add_negative_nuanced.py --dir ~/more_bad_photos --output more_neg.jsonl
cat negative_user_examples.jsonl more_neg.jsonl > combined_negative.jsonl
```

**Q: How many images do I need?**
A: Recommended:
- Text training: 174 ✅ (you have this)
- Positive images: 50-100
- Negative images: 50-100
- **Total: 274-374 examples**
