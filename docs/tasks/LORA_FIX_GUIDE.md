# LoRA Adapter Fix Guide

## The Problem

Your LoRA adapter was trained on **philosophy text** instead of **image analysis data**, causing it to produce incomplete JSON output.

### What's Wrong

- **Current training**: `training/datasets/ansel_combined_train.jsonl` (1494 philosophy examples)
- **Should be**: `training/datasets/ansel_image_training_nuanced.jsonl` (21 image analysis examples)

**Result**: Model generates only `image_description` field, missing:
- `dimensional_analysis` (8 photography dimensions)
- `overall_grade`
- `advisor_notes`
- `techniques`

### Evidence

From logs:
```
[JSON PARSER] Response length: 492 chars  (should be 3000-5000+)
[JSON PARSER] First 100 chars: '{\n  "image_description": "..."'
[JSON PARSER] All parsing strategies failed
```

Training config shows 1478 examples (philosophy text count), not image analysis.

---

## Solution: Retrain with Correct Data

### Option 1: Automated Retraining (RECOMMENDED)

Run the automated fix script:

```bash
python3 retrain_lora_fix.py
```

This script will:
1. ✓ Verify correct training data exists
2. ✓ Train new adapter (10-30 minutes)
3. ✓ Backup old adapter automatically
4. ✓ Install new adapter
5. ✓ Display next steps

**That's it!** The script handles everything.

### Option 2: Manual Retraining

If you prefer to control each step:

```bash
# 1. Stop the AI Advisor Service (if running)
# (Ctrl+C or kill the process)

# 2. Train new adapter with correct data
python3 train_mlx_lora.py \
  --train_data training/datasets/ansel_image_training_nuanced.jsonl \
  --output_dir adapters/ansel_new \
  --epochs 3 \
  --batch_size 1 \
  --learning_rate 5e-05

# 3. Backup old adapter and install new one
mv adapters/ansel adapters/ansel_old_backup
mv adapters/ansel_new adapters/ansel

# 4. Restart services
python3 mondrian/start_services.py

# 5. Test
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

### Option 3: Bash Script

Alternatively, run the bash script:

```bash
bash retrain_lora_correct.sh
```

---

## Verification

After retraining, verify the fix:

### Test LoRA Mode

```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

Expected output:
- ✓ Completes successfully
- ✓ Creates `analysis_output/lora_e2e_lora_*` directory
- ✓ Generates `analysis_detailed.html` and `analysis_summary.html`
- ✓ Shows "Test PASSED" message

### Compare All Modes

```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare
```

This creates a side-by-side comparison of:
- LoRA (fine-tuned)
- Baseline (base model only)

### Check Raw Output

```bash
# See what LoRA model is actually producing
curl -X POST http://127.0.0.1:5100/analyze \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "mode=lora" 2>/dev/null | python3 -m json.tool | head -100
```

Should see full JSON with `dimensional_analysis`, not just `image_description`.

---

## Important Notes

### Training Data Size

The correct training data only has **21 examples**. This is very small for deep learning.

**Implications**:
- ✓ Will train quickly (5-10 minutes)
- ⚠ Model may not learn much semantic knowledge
- ⚠ Might still produce incomplete outputs initially

**If LoRA still fails after retraining**:
1. The 21 examples may be too few
2. You need to generate more training data from baseline model
3. See "Generating More Training Data" section below

### GPU Memory

Training requires GPU memory. If you get CUDA errors:
```bash
# Stop services first
# Reduce batch size
python3 train_mlx_lora.py \
  --train_data training/datasets/ansel_image_training_nuanced.jsonl \
  --batch_size 1 \  # Already minimum
  --epochs 1        # Reduce epochs temporarily
```

---

## Advanced: Generating More Training Data

If retraining with 21 examples doesn't work well, generate more:

```bash
# 1. Generate analysis outputs from baseline model
python3 scripts/generate_training_data.py \
  --advisor ansel \
  --input_dir source/ \
  --output training/datasets/ansel_full_training.jsonl \
  --use_baseline  # Generate using baseline model (not LoRA)

# 2. Check how many examples generated
wc -l training/datasets/ansel_full_training.jsonl

# 3. Retrain with full dataset
python3 train_mlx_lora.py \
  --train_data training/datasets/ansel_full_training.jsonl \
  --output_dir adapters/ansel_new \
  --epochs 3 \
  --batch_size 1

# 4. Install
mv adapters/ansel adapters/ansel_backup
mv adapters/ansel_new adapters/ansel

# 5. Test
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

---

## Troubleshooting

### Issue: Still getting incomplete JSON after retraining

**Check**:
```bash
tail -100 logs/ai_advisor_service_*.log | grep -A 10 "JSON PARSER"
```

**Solutions**:
1. Generate more training data (see above)
2. Train for more epochs: `--epochs 5` instead of 3
3. Use RAG or baseline mode instead (fully working)

### Issue: Out of memory during training

**Solutions**:
```bash
# Reduce batch size (already at 1, minimum)
# Reduce epochs
python3 train_mlx_lora.py \
  --train_data training/datasets/ansel_image_training_nuanced.jsonl \
  --epochs 1 \
  --batch_size 1

# Or clear GPU cache
# (Stop services and any other GPU processes)
```

### Issue: Training crashes with "No images found"

Check image paths in training data:
```bash
head -1 training/datasets/ansel_image_training_nuanced.jsonl | \
  python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('image_path'))"
```

The paths may be relative and need adjustment based on where you run the script.

---

## Rollback (If Something Goes Wrong)

If the new adapter is worse than before:

```bash
# Restore old adapter
rm -rf adapters/ansel
mv adapters/ansel_old_backup adapters/ansel

# Restart services
python3 mondrian/start_services.py
```

Or look for timestamped backups:
```bash
ls -lh adapters/ | grep backup
```

---

## FAQ

**Q: Will retraining take a long time?**
A: 5-30 minutes depending on your GPU. CPU-only training would be hours.

**Q: What if I don't have a GPU?**
A: Training will still work on CPU but be very slow. You can reduce epochs: `--epochs 1`

**Q: Should I retrain baseline or RAG modes?**
A: No, only LoRA needs retraining. Baseline and RAG modes work perfectly already.

**Q: Can I test without retraining?**
A: Yes, use baseline or RAG mode:
  ```bash
  python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
  python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag
  ```

**Q: What if 21 training examples still isn't enough?**
A: Generate more by running analysis with baseline model and saving outputs as JSONL.

---

## Summary

| Step | Command | Time |
|------|---------|------|
| **Fix** | `python3 retrain_lora_fix.py` | 10-30 min |
| **Verify** | `python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora` | 2 min |
| **Compare** | `python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare` | 5 min |

**That's all you need to fix the issue!**

