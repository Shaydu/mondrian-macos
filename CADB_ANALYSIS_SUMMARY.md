# CADB Analysis & Merge Summary

## Changes Made

### 1. Updated analyze_cadb_batch.py Script
- **Timeout increased**: 300s → **600s per image** (to handle slower requests)
- **Added timeout parameter**: Can be configured via `--timeout` CLI argument
- **Updated signature**: batch_analyze() now accepts and passes timeout to analyze_image()

## Current Status

### Datasets Available
1. **Ansel Adams Training Data**: 292 examples
   - Location: `training/20260121-qwen3-vl-4b/augmented_training_data_train.jsonl`
   
2. **CADB Previously Analyzed**: 102 examples  
   - Location: `training/cadb_analyzed/cadb_training_data.json`
   - Source: Earlier analysis run (not from current selected images)
   
3. **Merged Dataset**: 394 examples (292 Ansel + 102 CADB)
   - Location: `training/20260121-qwen3-vl-4b/merged_training_data*.jsonl`
   - Status: **Ready to train with immediately**

### What Needs Analysis
- **Total selected images**: 200
- **Filtered (excluding human/animal)**: 100
- **Already analyzed (from earlier run)**: 99
- **Remaining to analyze**: **101 images**
  - 100 non-human/animal from selected list
  - 1 that failed in previous attempt

## Analysis History

### First Run (analysis_200.log)
- Started with 200 selected images
- Filtered to 100 (excluded human/animal)
- Completed: ~6 images
- Failed: Multiple 300s timeouts

### Continued Run (analysis_200_continued.log)
- Resumed from 98 previously analyzed
- Attempted 2 more images
- Failed with 4 timeouts + 1 connection drop
- Reason: AI Advisor service became unresponsive

## To Analyze Remaining 101 Images

Run this command:

```bash
cd /home/doo/dev/mondrian-macos

python3 scripts/training/analyze_cadb_batch.py \
  --selected-images training/cadb_selected_images.json \
  --cadb-root Image-Composition-Assessment-Dataset-CADB \
  --service-url http://localhost:5100/analyze \
  --advisor ansel \
  --output training/cadb_analyzed/cadb_training_data_no_people_animals.json \
  --timeout 600 \
  --exclude-categories "human,animal"
```

### What This Does
1. Loads the 200 selected images
2. Filters to 100 non-human/animal
3. Analyzes the ones not yet completed
4. Saves to new file: `cadb_training_data_no_people_animals.json`
5. Uses 600s timeout per image (doubled from 300s)

### After Analysis Completes
1. Convert new analysis to JSONL:
   ```bash
   cd training
   python3 merge_training_datasets.py
   ```

2. This will automatically:
   - Merge the new CADB analysis with Ansel Adams data
   - Create train/val/test splits
   - Update `merged_training_data*.jsonl` files

3. Train with expanded dataset:
   ```bash
   python3 train_lora_qwen3vl.py \
     --data_path 20260121-qwen3-vl-4b/merged_training_data_train.jsonl \
     --output_dir ../adapters/merged_qwen3_4b_v2 \
     --num_epochs 20
   ```

## Files Modified

- `scripts/training/analyze_cadb_batch.py`:
  - Line 236: timeout default 300 → 600
  - Line 504: Added timeout parameter
  - Line 560: Pass timeout to analyze_image()
  - Lines 665-669: Added --timeout CLI argument
  - Line 717: Pass timeout to batch_analyze()

## Expected Results When Complete

- **Total training data**: ~495 examples (292 Ansel + 203 CADB)
- **Data diversity**: Mix of classic and modern composition assessment
- **Training ready**: JSONL format with proper train/val/test splits
