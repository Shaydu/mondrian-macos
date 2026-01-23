# Interactive Training Quick Start

**You now have everything needed to download, score, and train on your data!**

---

## What Was Created

### 🎬 Interactive Scripts (in `scripts/training/`)

1. **`interactive_image_scorer.py`** - Manually rate images
   ```bash
   python scripts/training/interactive_image_scorer.py --source training/cadb/images
   ```
   - View image in viewer
   - Rate all 9 dimensions (1-10)
   - Add comments
   - Save progress
   - Resume sessions

2. **`scores_to_training_data.py`** - Convert manual scores to training format
   ```bash
   python scripts/training/scores_to_training_data.py \
     --scores scored_images.json \
     --images training/cadb/images \
     --output training_data.jsonl
   ```

3. **`download_cadb_dataset.py`** - Download CADB (1,000 images)
   ```bash
   python scripts/training/download_cadb_dataset.py
   ```

4. **`download_wikimedia_photographers.py`** - Download more masterworks
   ```bash
   python scripts/training/download_wikimedia_photographers.py
   ```

5. **`run_training_pipeline.py`** - Orchestrate entire pipeline (NEW!)
   ```bash
   python scripts/training/run_training_pipeline.py
   ```

### 📚 Documentation (in `docs/phases/`)

1. **`07_interactive_image_scoring.md`** - Complete guide to manual scoring
   - When to use
   - Scoring examples for each dimension
   - Workflows (validation, curation)
   - Troubleshooting

2. **`08_complete_training_pipeline.md`** - Full end-to-end training guide
   - Step-by-step execution
   - Expected outputs
   - Quality assurance
   - Performance metrics

---

## Three Approaches

### Approach 1: Automated (Recommended)
**Time: ~9 hours | Effort: Minimal | Scale: 1,000+ examples**

```bash
# One command does everything!
python scripts/training/run_training_pipeline.py

# Outputs:
# - 1,000+ analyzed images
# - Merged dataset (train/val/test)
# - Fine-tuned adapter
# - Evaluation report
```

### Approach 2: Manual Validation + Automated
**Time: ~12 hours | Effort: Medium | Scale: 900+ examples + 10 validated**

```bash
# Step 1: Score 10 images manually (2 hours)
python scripts/training/interactive_image_scorer.py \
  --source training/cadb/images \
  --output validation_scores.json

# Step 2: Convert to training
python scripts/training/scores_to_training_data.py \
  --scores validation_scores.json \
  --images training/cadb/images \
  --output validation_training.jsonl

# Step 3: Run automated pipeline with validation set
python scripts/training/run_training_pipeline.py

# This creates:
# - 1,000 from CADB
# - 10 manually validated
# - 24 existing
# = 1,034 total examples
```

### Approach 3: Full Manual Curation
**Time: Variable | Effort: High | Scale: Custom dataset**

```bash
# Score exactly the images you want (10 min per image)
python scripts/training/interactive_image_scorer.py \
  --source training/cadb/images \
  --output my_curated_scores.json \
  --resume  # Can pause and resume

# Convert to training format
python scripts/training/scores_to_training_data.py \
  --scores my_curated_scores.json \
  --images training/cadb/images \
  --output my_curated_training.jsonl

# Fine-tune on your curated data
python train_lora_qwen3vl.py \
  --train-jsonl my_curated_training.jsonl
```

---

## Quick Start: Pick One

### Option A: Set It and Forget It (9 hours unattended)

```bash
# Download
python scripts/training/download_cadb_dataset.py

# Then walk away for 9 hours
python scripts/training/run_training_pipeline.py

# Check results tomorrow
cat evaluation_report.json
```

### Option B: Quick Validation First (4 hours)

```bash
# Download
python scripts/training/download_cadb_dataset.py

# Score 5-10 sample images (30 minutes interactive)
python scripts/training/interactive_image_scorer.py \
  --source training/cadb/images \
  --output sample_validation.json

# Let pipeline run with validation
python scripts/training/run_training_pipeline.py
```

### Option C: Curated Quality Dataset (2-3 days)

```bash
# Download
python scripts/training/download_cadb_dataset.py

# Spend time manually scoring best images
python scripts/training/interactive_image_scorer.py \
  --source training/cadb/images \
  --output curated_scores.json --resume

# Fine-tune on what you scored
python scripts/training/scores_to_training_data.py \
  --scores curated_scores.json \
  --images training/cadb/images \
  --output curated_training.jsonl

python train_lora_qwen3vl.py --train-jsonl curated_training.jsonl
```

---

## Feature Breakdown

### Interactive Image Scorer

**What it does:**
- Opens image in your default viewer
- Prompts for score on each dimension
- Collects comments and feedback
- Builds JSON database as you go
- Can resume anytime

**Perfect for:**
- Validating AI advisor (compare your scores vs AI)
- Building ground-truth dataset
- Learning dimensional scoring
- Quality-checking CADB images

**Time investment:**
- 10-15 minutes per image
- 50 images = 10 hours (split across days)
- 10 images = 2 hours (good validation sample)

**Keyboard shortcuts:**
```
[s] Score next image
[r] Review previous score
[j] Jump to image number
[q] Save and quit
[h] Show scoring guide
```

**Example output:**
```json
{
  "photo_001.jpg": {
    "dimensions": {
      "Composition": {"score": 8, "comment": "Strong rule of thirds"},
      "Lighting": {"score": 9, "comment": "Beautiful tonal control"},
      ...
    },
    "overall_score": 8,
    "key_strengths": ["Composition", "Lighting"],
    "priority_improvements": ["Minor color tone"]
  }
}
```

### Automated Pipeline

**What it does:**
- Downloads CADB (1,000+ images)
- Analyzes all with AI advisor
- Merges with your existing data
- Creates train/val/test splits
- Fine-tunes LoRA adapter
- Evaluates results

**Time:**
- Download: 10 min
- Analysis: 4 hours (GPU)
- Training: 4-6 hours (GPU)
- Total: ~9 hours (mostly automated)

**Outputs:**
```
adapters/qwen3vl-dimensional-v2/
├── adapter_model.bin          ← Your fine-tuned adapter
├── adapter_config.json
└── training.log

evaluation_report.json         ← Performance metrics

training/20260121-combined/
├── training_data_merged_train.jsonl
├── training_data_merged_val.jsonl
└── training_data_merged_test.jsonl
```

---

## Common Workflows

### Workflow 1: Quick Start
```bash
# 10 minutes setup + 9 hours unattended
python scripts/training/download_cadb_dataset.py
python scripts/training/run_training_pipeline.py
# Done! Check results tomorrow
```

### Workflow 2: Validate Before Training
```bash
# 2 hours manual + 9 hours automated
python scripts/training/download_cadb_dataset.py

# Manually score 10 images
python scripts/training/interactive_image_scorer.py \
  --source training/cadb/images --output validation.json

# Compare your scores with AI's
python scripts/training/compare_scores.py \
  --manual validation.json \
  --automated training/cadb/augmented_training_data_cadb.jsonl

# If satisfied, run pipeline
python scripts/training/run_training_pipeline.py
```

### Workflow 3: High-Quality Curation
```bash
# Multiple days of careful annotation
python scripts/training/download_cadb_dataset.py

# Score 50-100 images carefully
python scripts/training/interactive_image_scorer.py \
  --source training/cadb/images \
  --output my_scores.json --resume

# Convert to training
python scripts/training/scores_to_training_data.py \
  --scores my_scores.json \
  --images training/cadb/images \
  --output curated_training.jsonl

# Fine-tune only on curated data
python train_lora_qwen3vl.py \
  --train-jsonl curated_training.jsonl \
  --epochs 10  # More epochs for smaller dataset
```

### Workflow 4: Progressive Expansion
```bash
# Build dataset over time
python scripts/training/download_cadb_dataset.py
python scripts/training/download_wikimedia_photographers.py

# Day 1: Train on 16 existing examples
python train_lora_qwen3vl.py \
  --train-jsonl training/20260121-qwen3-vl-4b/training_data_train.jsonl

# Day 2: Add 100 Wikimedia, retrain
python train_lora_qwen3vl.py \
  --train-jsonl merged_with_wikimedia.jsonl

# Week 1: Analyze CADB, retrain with 1,000+
python train_lora_qwen3vl.py \
  --train-jsonl training_merged_cadb_plus.jsonl
```

---

## Dimensions Explained

When using interactive scorer, here's what each dimension means:

**Composition (7-8 typical)**
- How well elements are arranged
- Rule of thirds, leading lines
- Visual hierarchy and balance
- "Does the frame work?"

**Lighting (8-9 typical)**
- Quality and direction of light
- Tonal range and contrast
- How light shapes the subject
- "Is the lighting masterful?"

**Focus & Sharpness (8-9 typical)**
- Technical sharpness where needed
- Depth of field control
- "Is focus executed well?"

**Color Harmony (7-8 typical)**
- Color palette cohesion
- Color relationships
- "Do colors work together?"

**Depth & Perspective (7-9 typical)**
- Three-dimensionality
- Foreground/middle/background layers
- "Is space used effectively?"

**Visual Balance (7-8 typical)**
- Weight distribution
- Symmetry vs asymmetry
- "Is the image stable?"

**Emotional Impact (5-9 variable)**
- Does it evoke feeling?
- Story potential
- Viewer connection
- "Does it move you?"

**Technical Execution (7-9 typical)**
- Exposure, noise, artifacts
- Overall technical quality
- "Is it technically excellent?"

**Subject Matter (5-9 variable)**
- Interest of subject
- Uniqueness
- "Is subject interesting?"

---

## Files Organization

Everything is organized in standard folders:

```
scripts/training/
├── download_cadb_dataset.py              ← Download data
├── download_wikimedia_photographers.py   ← Download data
├── interactive_image_scorer.py           ← Manual scoring
├── scores_to_training_data.py            ← Convert scores to JSONL
└── run_training_pipeline.py              ← Automated everything

docs/phases/
├── 07_interactive_image_scoring.md       ← Detailed manual scoring guide
└── 08_complete_training_pipeline.md      ← Detailed training guide

training/
├── 20260121-qwen3-vl-4b/                 ← Your existing data
├── cadb/                                 ← CADB download & analysis
├── wikimedia_expanded/                   ← Wikimedia download & analysis
└── 20260121-combined/                    ← Merged training data

adapters/
└── qwen3vl-dimensional-v2/               ← Your fine-tuned adapter
```

---

## Next Steps

1. **Start with download:**
   ```bash
   python scripts/training/download_cadb_dataset.py
   ```

2. **Choose your approach (A, B, or C) above**

3. **Run pipeline:**
   ```bash
   python scripts/training/run_training_pipeline.py
   ```

4. **Deploy adapter:**
   ```bash
   python mondrian/job_service_v2.3.py \
     --adapter adapters/qwen3vl-dimensional-v2
   ```

5. **Test with sample images**

---

## Documentation Reference

- **Manual Scoring**: [docs/phases/07_interactive_image_scoring.md](docs/phases/07_interactive_image_scoring.md)
- **Full Pipeline**: [docs/phases/08_complete_training_pipeline.md](docs/phases/08_complete_training_pipeline.md)
- **Data Sources**: [TRAINING_DATA_SOURCES.md](TRAINING_DATA_SOURCES.md)
- **Quick Start**: [TRAINING_DATA_QUICK_START.txt](TRAINING_DATA_QUICK_START.txt)

---

## Need Help?

- See interactive scorer guide: `docs/phases/07_interactive_image_scoring.md`
- See complete pipeline: `docs/phases/08_complete_training_pipeline.md`
- Check logs: `training_pipeline.log` (created during pipeline run)

**You're all set! Pick an approach and start training! 🚀**
