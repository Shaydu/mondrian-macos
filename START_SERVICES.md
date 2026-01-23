# Starting Services for CADB Human/Animal Image Analysis & Review

## Current Status
- **Total selected images**: 200 CADB images
- **Already analyzed**: 102 images (non-human/animal)
- **Remaining to analyze**: 98 images (human/animal categories)
- **Ready to review**: All 200 analyzed images

## Prerequisites Check
- ✅ CADB dataset downloaded: `Image-Composition-Assessment-Dataset-CADB/`
- ✅ Selected images prepared: `training/cadb_selected_images.json` (200 images)
- ✅ Analysis cache ready: `training/cadb_analyzed/cadb_training_data.json` (102 analyzed)
- ✅ Web UI ready: `scripts/training/review_training_data_web.py`
- ✅ Processing script ready: `analyze_cadb_human_animal.py`

---

## PART 1: Start AI Advisor Service (Port 5100)

The AI Advisor Service provides the 6-dimensional analysis (Composition, Lighting, Focus & Sharpness, Color Harmony, Depth & Perspective, Visual Balance).

### In Terminal 1:
```bash
cd /home/doo/dev/mondrian-macos

# Activate venv if needed
source venv/bin/activate

# Start the AI Advisor Service
python3 mondrian/ai_advisor_service_linux.py --port 5100
```

**Expected output:**
```
[INFO] Loading Qwen2-VL model...
[INFO] Model loaded successfully
[INFO] Starting Flask app on port 5100
[INFO] * Running on http://0.0.0.0:5100
```

**Test the service:**
```bash
curl -X POST http://localhost:5100/health
# Should return: {"status": "healthy"}
```

**Keep this terminal running while processing images.**

---

## PART 2: Process Remaining 98 Human/Animal Images (Terminal 2)

This will analyze the 98 images with human/animal categories that haven't been processed yet.

### In Terminal 2:
```bash
cd /home/doo/dev/mondrian-macos

# Activate venv
source venv/bin/activate

# Start batch processing of human/animal images
python3 analyze_cadb_human_animal.py \
  --selected-images training/cadb_selected_images.json \
  --cadb-root Image-Composition-Assessment-Dataset-CADB \
  --processed-file training/cadb_analyzed/cadb_training_data.json \
  --output training/cadb_analyzed/cadb_training_data.json \
  --service-url http://localhost:5100/analyze \
  --advisor ansel \
  --delay 2.0 \
  --timeout 600
```

**What this does:**
1. Loads all 200 selected images
2. Identifies the 98 with human/animal categories (not yet analyzed)
3. Analyzes each with the AI Advisor Service
4. Appends results to the existing `cadb_training_data.json`
5. Auto-resumes if interrupted

**Monitor progress:**
```bash
# In another terminal, watch the count grow
watch -n 5 'python3 -c "import json; print(f\"Analyzed: {len(json.load(open(\"training/cadb_analyzed/cadb_training_data.json\")))}\")"'

# Or tail the logs
tail -f mondrian/logs/ai_advisor_service_linux.log
```

**Expected time**: ~5-8 hours for 98 images at 2s delay per image

**Note**: Processing will pause if the service becomes unresponsive. Just restart Terminal 1 (AI service) and re-run the command in Terminal 2—it auto-resumes from where it left off.

---

## PART 3: Start Web Review UI (Terminal 3)

Once you have some analyzed images (can run while processing), start the review UI to rescores and edit the dimensional scores.

### In Terminal 3:
```bash
cd /home/doo/dev/mondrian-macos

# Activate venv
source venv/bin/activate

# Start the web review interface
python3 scripts/training/review_training_data_web.py \
  --data training/cadb_analyzed/cadb_training_data.json \
  --images training/cadb_selected_images.json \
  --port 8080 \
  --host 0.0.0.0
```

**Expected output:**
```
[INFO] Loaded 102 training examples
[INFO] Loaded metadata for 200 images
[INFO] Starting server at http://localhost:8080
```

**Then open in your browser:**
```
http://localhost:8080
```

---

## Web UI Features

Once open, you can:

### For Each Image:
1. **View the photograph** (left panel)
2. **View dimensional analysis** (right panel):
   - Composition (CADB-based)
   - Lighting
   - Focus & Sharpness
   - Color Harmony
   - Depth & Perspective
   - Visual Balance

3. **Edit scores**: Click on the score input box (1-10 scale)
4. **Edit comments**: Modify the comment text
5. **Edit recommendations**: Modify suggestions for improvement

### Navigation:
- **Previous/Next buttons**: Move through images
- **Progress bar**: Shows where you are (e.g., 1 of 200)
- **Save Changes**: Persists all edits to JSON

### Important:
- Changes are tracked in memory as you edit
- Click **"💾 Save Changes"** button to persist to disk
- Edited fields get highlighted with orange border
- Can edit while images are still being processed

---

## Recommended Workflow

### Option A: Process First, Then Review
```
1. Start AI Service (Terminal 1)           ← Keep running
2. Start batch processing (Terminal 2)     ← Takes 5-8 hours
3. While processing, start Web UI (Terminal 3)
4. Review images as they're analyzed
5. Save changes after reviewing batch
```

### Option B: Review as You Go (Recommended)
```
1. Start AI Service (Terminal 1)           ← Keep running
2. Start batch processing (Terminal 2)     ← Auto-updates JSON
3. Start Web UI (Terminal 3)
4. Review and rescores in real-time
5. Refresh UI to see newly analyzed images
6. Save changes periodically
```

---

## File Locations

```
training/cadb_analyzed/
├── cadb_training_data.json           ← Main analysis file (grows as processing)
├── cadb_training_data_human_animal.json  ← Human/animal images only
└── cadb_training_data_recovery.jsonl ← Backup/recovery file

training/cadb_selected_images.json    ← 200 selected images (reference)

Image-Composition-Assessment-Dataset-CADB/
├── images/                           ← 10,000 CADB photos
├── annotations/
│   ├── composition_scores.json       ← CADB raw scores (0-5)
│   └── scene_categories.json         ← Image categories (human, animal, etc)
└── CADB_Dataset/
    └── composition_scores.json       ← Alternative scores file
```

---

## Troubleshooting

### AI Service won't start
```bash
# Check CUDA/GPU
nvidia-smi

# Check if port 5100 is in use
lsof -i :5100

# Kill any existing process
pkill -f "ai_advisor_service"
```

### Processing script fails with timeout
- Increase `--timeout` from 600 to 800
- Reduce `--delay` from 2.0 to 1.0 (more concurrent requests)
- Check if AI Service is responding: `curl http://localhost:5100/health`

### Web UI won't load images
- Ensure image paths in `cadb_training_data.json` are absolute paths
- Verify images exist in `Image-Composition-Assessment-Dataset-CADB/images/`

### Want to see raw analysis?
```bash
# Check what's been analyzed
python3 -c "import json; d=json.load(open('training/cadb_analyzed/cadb_training_data.json')); print(f'Analyzed: {len(d)} images'); print(f'Last: {d[-1].get(\"image_id\")}')"

# Get image categories
python3 -c "import json; d=json.load(open('training/cadb_selected_images.json')); print(f'Categories: {set([img.get(\"cadb_category\", \"?\") for img in d])}')"
```

---

## Next Steps After Review

Once you've reviewed and rescored all 200 images:

1. **Merge with Ansel Adams training data**:
   ```bash
   # Combine CADB + Ansel Adams
   cd training
   python3 merge_training_datasets.py
   ```

2. **Fine-tune LORA adapter**:
   ```bash
   python3 training/train_lora_qwen3vl.py \
     --data_path 20260121-qwen3-vl-4b/merged_training_data_train.jsonl \
     --output_dir ../adapters/merged_qwen3_4b_v2 \
     --epochs 3 \
     --batch_size 1 \
     --lora_r 16
   ```

3. **Test improved model** on new images

---

## Commands Summary

**Terminal 1 (AI Service):**
```bash
cd /home/doo/dev/mondrian-macos && source venv/bin/activate
python3 mondrian/ai_advisor_service_linux.py --port 5100
```

**Terminal 2 (Processing):**
```bash
cd /home/doo/dev/mondrian-macos && source venv/bin/activate
python3 analyze_cadb_human_animal.py --selected-images training/cadb_selected_images.json --cadb-root Image-Composition-Assessment-Dataset-CADB --output training/cadb_analyzed/cadb_training_data.json --service-url http://localhost:5100/analyze --timeout 600
```

**Terminal 3 (Review UI):**
```bash
cd /home/doo/dev/mondrian-macos && source venv/bin/activate
python3 scripts/training/review_training_data_web.py --data training/cadb_analyzed/cadb_training_data.json --port 8080
```

**Then open:** `http://localhost:8080`

---

## Questions?

Check the logs:
```bash
# AI Service logs
tail -f mondrian/logs/ai_advisor_service_linux.log

# Flask logs (web UI)
tail -f mondrian/logs/review_training_data_web.log
```
