# Quick LoRA Fix - 2 Commands

## The Problem (In 10 seconds)

Your LoRA adapter was trained on philosophy text, not image analysis. That's why it produces empty JSON output.

## The Fix (In 5 steps)

### Step 1: Run the fix script (hands-off, 10-30 minutes)

```bash
python3 retrain_lora_fix.py
```

That's it! The script will:
- Stop services if needed ✓
- Train new adapter with correct image analysis data ✓
- Backup old adapter ✓
- Install new adapter ✓
- Tell you what to do next ✓

### Step 2: Start services

```bash
python3 mondrian/start_services.py
```

### Step 3: Test LoRA

```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

### Step 4: Compare all modes (optional)

```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare
```

### Step 5: Done!

If tests pass, you're done. If not, check the detailed guide: `LORA_FIX_GUIDE.md`

---

## What Went Wrong

**Current adapter**: Trained on `ansel_combined_train.jsonl` (philosophy text)
**Should be**: Trained on `ansel_image_training_nuanced.jsonl` (image analysis)

Result: Model only outputs `{"image_description": "..."}` instead of full JSON with:
- `dimensional_analysis`
- `overall_grade`
- `advisor_notes`

---

## If Automatic Fix Doesn't Work

See: `LORA_FIX_GUIDE.md` for manual retraining and advanced troubleshooting.

---

## Workaround (If You Need Results Now)

Use baseline or RAG mode - they work perfectly:

```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag
```

Then retrain LoRA in the background.

