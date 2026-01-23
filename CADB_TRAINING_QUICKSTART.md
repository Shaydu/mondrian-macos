# CADB Training Pipeline Quickstart

Complete pipeline to analyze 200 CADB images and fine-tune Qwen3-VL-4B with 6-dimension feedback.

## Prerequisites

1. **CADB Dataset** downloaded to `Image-Composition-Assessment-Dataset-CADB/`
2. **AI Advisor Service** running (provides 6-dimension analysis)
3. **RTX 3060** with PyTorch + CUDA installed

## Pipeline Steps

### Step 1: Select 10 Diverse CADB Images (1 minute)

Select images stratified by composition score (2 from each quintile for testing):

```bash
python scripts/training/select_cadb_images.py \
    --cadb-root Image-Composition-Assessment-Dataset-CADB \
    --output training/cadb_selected_images.json \
    --count 10 \
    --bins 5
```

**Output:** `training/cadb_selected_images.json` with 10 image paths and metadata

**Note:** Use `--count 200 --bins 5` for full production run (40 images per quintile)

---

### Step 2: Batch Analyze with AI Service (6-10 hours)

Send images to your AI advisor service to get full 6-dimension analysis:

```bash
# First, test with 3 images
python scripts/training/analyze_cadb_batch.py \
    --selected-images training/cadb_selected_images.json \
    --service-url http://localhost:5100/analyze \
    --advisor ansel \
    --output training/cadb_analyzed/cadb_training_data.jsonl \
    --test

# If test works, run full batch (takes 6-10 hours for 200 images)
python scripts/training/analyze_cadb_batch.py \
    --selected-images training/cadb_selected_images.json \
    --service-url http://localhost:5100/analyze \
    --advisor ansel \
    --output training/cadb_analyzed/cadb_training_data.jsonl \
    --delay 2.0
```

**Features:**
- Auto-resumes if interrupted (checks existing output)
- 2 second delay between requests (configurable)
- Generates diverse prompts for each image
- Saves immediately after each success

**Output:** `training/cadb_analyzed/cadb_training_data.jsonl` with 200 analyzed examples

**Monitor progress:**
```bash
# Count completed
wc -l training/cadb_analyzed/cadb_training_data.jsonl

# Watch in real-time
tail -f training/cadb_analyzed/cadb_training_data.jsonl
```

---

### Step 2.5: Review & Edit Training Data (Optional, 10-30 minutes)

Before training, review and modify the dimensional scores and feedback using the web interface:

```bash
python scripts/training/review_training_data_web.py \
    --data training/cadb_analyzed/cadb_training_data.json \
    --images training/cadb_selected_images.json \
    --port 8080
```

Then open http://localhost:8080 in your browser.

**Features:**
- View each image with its 6-dimensional analysis
- Edit individual dimension scores (1-10 scale) inline
- Modify comments and recommendations in real-time
- Recalculates overall score automatically
- Beautiful web interface with side-by-side image and analysis
- Progress tracking across all images
- Save changes only when ready

**Workflow:**
1. Start the web server (command above)
2. Open http://localhost:8080 in your browser
3. View each image with its dimensional feedback
4. Edit scores/comments as needed (changes auto-save)
5. Navigate through images with Previous/Next buttons
6. Click "Save Changes" to persist to JSON file

**Output:** Modified `cadb_training_data.json` ready for training

---

### Step 3: Merge with Existing Training Data (1 minute)

Combine CADB data with your curated dataset:

```bash
cat training/20260121-qwen3-vl-4b/augmented_training_data_train.jsonl \
    training/cadb_analyzed/cadb_training_data.jsonl \
    > training/cadb_merged/merged_training_data.jsonl

echo "Merged dataset size:"
wc -l training/cadb_merged/merged_training_data.jsonl
# Expected: ~492 lines (292 existing + 200 CADB)
```

---

### Step 4: Fine-Tune LoRA Adapter on RTX 3060 (4-6 hours)

Train the model with merged dataset:

```bash
python training/train_lora_qwen3vl.py \
    --base_model Qwen/Qwen3-VL-4B-Instruct \
    --data_dir training/cadb_merged/merged_training_data.jsonl \
    --output_dir adapters/ansel_cadb_v1 \
    --epochs 3 \
    --batch_size 1 \
    --gradient_accumulation_steps 8 \
    --learning_rate 2e-4 \
    --lora_r 16 \
    --lora_alpha 32 \
    --lora_dropout 0.05 \
    --warmup_steps 50 \
    --save_steps 100 \
    --logging_steps 10
```

**Training Config:**
- **Effective batch size:** 8 (1 × 8 gradient accumulation)
- **Memory usage:** ~10GB VRAM with 4-bit quantization
- **Time estimate:** 4-6 hours for 492 examples × 3 epochs
- **Checkpoints:** Saved every 100 steps to `adapters/ansel_cadb_v1/checkpoint-*/`

**Monitor training:**
```bash
# Watch logs
tail -f adapters/ansel_cadb_v1/logs/events.out.tfevents.*

# Check GPU usage
nvidia-smi -l 1
```

---

### Step 5: Test Fine-Tuned Adapter

Test the trained adapter on new images:

```bash
# TODO: Add inference script to test adapter
# Will load from adapters/ansel_cadb_v1/
```

---

## Expected Timeline

| Step | Duration | Can Run Overnight? |
|------|----------|-------------------|
| 1. Select images | 1 min | No |
| 2. Batch analyze | 6-10 hrs | **Yes** ✓ |
| 3. Merge data | 1 min | No |
| 4. Fine-tune | 4-6 hrs | **Yes** ✓ |
| 5. Test | 5 min | No |
| **Total** | **10-16 hrs** | |

---

## Troubleshooting

### Service URL Issues

If analyze_cadb_batch.py fails with connection errors:

```bash
# Test service manually
curl -X POST http://localhost:5100/analyze \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"

# Check if service is running
curl http://localhost:5100/health || echo "Service not responding"
```

### Out of Memory During Training

If RTX 3060 runs out of VRAM:

```bash
# Reduce batch size
python training/train_lora_qwen3vl.py \
    --batch_size 1 \
    --gradient_accumulation_steps 16  # Increase to maintain effective batch size
    # ... other args
```

### Resume Interrupted Analysis

The batch analyzer auto-resumes by default:

```bash
# Just re-run the same command - it skips completed images
python scripts/training/analyze_cadb_batch.py \
    --selected-images training/cadb_selected_images.json \
    --output training/cadb_analyzed/cadb_training_data.jsonl
    # Will resume from where it left off
```

---

## Data Format Reference

### Selected Images JSON
```json
[
  {
    "image_id": "000001",
    "image_path": "Image-Composition-Assessment-Dataset-CADB/images/000001.jpg",
    "cadb_score": 3.8,
    "score_bin": 3
  }
]
```

### Training Data JSONL
```json
{
  "messages": [
    {"role": "user", "content": "<image>\nAnalyze this photograph..."},
    {"role": "assistant", "content": "{\"dimensions\": [...], \"overall_score\": 7.5}"}
  ],
  "image_path": "path/to/image.jpg",
  "cadb_score": 3.8,
  "source": "CADB"
}
```

---

## Next Steps

After training completes:

1. **Evaluate on test set** - Compare base model vs fine-tuned on held-out images
2. **A/B test in production** - Deploy adapter and compare user feedback
3. **Iterate** - Analyze weak dimensions, add more training data if needed

---

## Files Created by This Pipeline

```
training/
├── cadb_selected_images.json              # Step 1 output
├── cadb_analyzed/
│   └── cadb_training_data.jsonl          # Step 2 output
├── cadb_merged/
│   └── merged_training_data.jsonl        # Step 3 output
└── train_lora_qwen3vl.py                 # Training script

adapters/
└── ansel_cadb_v1/                        # Step 4 output
    ├── adapter_config.json
    ├── adapter_model.bin
    ├── training_config.json
    └── checkpoint-*/                     # Checkpoints every 100 steps
```
