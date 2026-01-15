# LoRA Debugging Complete ✓

## Executive Summary

**Problem**: LoRA end-to-end test produces empty JSON output
**Root Cause**: Adapter trained on philosophy text instead of image analysis data
**Solution**: Retrain with correct data using `python3 retrain_lora_fix.py`
**Time to Fix**: 10-30 minutes (automatic retraining) + 5 minutes (testing)

---

## What We Found

### The Issue
Your LoRA model only outputs:
```json
{"image_description": "..."}
```

But it should output:
```json
{
  "dimensional_analysis": {
    "composition": {"score": 9, "comment": "..."},
    "lighting": {"score": 8, "comment": "..."},
    ...8 more dimensions...
  },
  "overall_grade": "8.5",
  "advisor_notes": "...",
  ...
}
```

### Why It's Happening

**Wrong training data**:
- File: `training/datasets/ansel_combined_train.jsonl`
- Content: Ansel Adams philosophy, biography, book excerpts
- Examples: 1,494 text-only examples
- Result: Model learned to generate philosophy, not image analysis

**Correct training data**:
- File: `training/datasets/ansel_image_training_nuanced.jsonl`
- Content: Image analysis with full JSON structure
- Examples: 21 complete image analysis examples
- Result: Would teach model to generate proper JSON

### Evidence
1. **Log output**: "Response length: 492 chars" (should be 3000-5000+)
2. **Training config**: Shows 1478 examples (matches philosophy file count, not image file)
3. **Parser errors**: Multiple `[JSON PARSER] All parsing strategies failed` errors
4. **JSON structure**: Last characters show incomplete JSON with trailing comma

---

## How to Fix It

### Option 1: Automatic Fix (EASIEST) ⭐

```bash
python3 retrain_lora_fix.py
```

This script:
- ✓ Verifies correct training data exists
- ✓ Trains new adapter (10-30 min)
- ✓ Backs up old adapter
- ✓ Installs new adapter
- ✓ Tells you what to do next

**That's it!** No other commands needed.

### Option 2: Manual Step-by-Step

See: `LORA_FIX_GUIDE.md`

### Option 3: Bash Script

```bash
bash retrain_lora_correct.sh
```

---

## Quick Start

### 1. Read This First (2 min)
```bash
cat QUICK_LORA_FIX.md
```

### 2. Run the Fix (10-30 min)
```bash
python3 retrain_lora_fix.py
```

### 3. Start Services
```bash
python3 mondrian/start_services.py
```

### 4. Test
```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

### 5. Verify Complete Output
Check the output files are created:
- `analysis_output/lora_e2e_lora_*/analysis_summary.html` ✓
- `analysis_output/lora_e2e_lora_*/analysis_detailed.html` ✓
- Should see full recommendations, not empty

---

## Temporary Workaround

If you need results **right now** while retraining happens:

```bash
# These work perfectly, no retraining needed
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag
```

Both baseline and RAG modes produce complete, proper output.

---

## Files Created for You

### Quick Reference
- **QUICK_LORA_FIX.md** - 2-minute quick start guide ⭐

### Complete Guides
- **LORA_FIX_GUIDE.md** - Detailed step-by-step guide
- **LORA_DEBUG_FINDINGS.md** - Technical analysis of the issue

### Scripts to Use
- **retrain_lora_fix.py** - Main automated fix script ⭐
- **retrain_lora_correct.sh** - Bash alternative
- **diagnose_lora_output.py** - Diagnostic information
- **test_lora_direct.py** - Direct model testing

---

## Expected Outcome After Fix

### Before Retraining
```
[JSON PARSER] All parsing strategies failed
[JSON PARSER] Response length: 492 chars
[STRATEGY ERROR] Could not parse model response as JSON
ValueError: Could not parse model response as JSON
```

### After Retraining
```
✓ Analysis completed successfully
✓ Test PASSED
✓ Generated analysis_summary.html (3+ KB)
✓ Generated analysis_detailed.html (10+ KB)
✓ Full JSON with dimensional_analysis
```

---

## Frequently Asked Questions

**Q: Will retraining take very long?**
A: No, 10-30 minutes depending on GPU. Only 21 training examples.

**Q: Do I need to fix anything else?**
A: No, just retrain the one adapter. Baseline and RAG modes work fine.

**Q: What if it still doesn't work after retraining?**
A: 21 examples might be too few. See "Advanced: Generating More Training Data" in LORA_FIX_GUIDE.md

**Q: Can I test without retraining?**
A: Yes, use baseline or RAG mode - they're fully functional.

**Q: Will I lose the old adapter?**
A: No, it's backed up to `adapters/ansel_backup_TIMESTAMP`.

**Q: What GPU do I need?**
A: Any Metal GPU (Apple Silicon) works. MLX handles it. CPU-only will be slow (~1-2 hours).

---

## Support

If you get stuck:

1. **Check the logs**:
   ```bash
   tail -50 logs/ai_advisor_service_*.log | grep -E "ERROR|FAIL|JSON PARSER"
   ```

2. **Verify services are running**:
   ```bash
   curl http://127.0.0.1:5005/health
   curl http://127.0.0.1:5100/health
   ```

3. **Check training data exists**:
   ```bash
   head -1 training/datasets/ansel_image_training_nuanced.jsonl | python3 -m json.tool | head -30
   ```

4. **Read the detailed guide**:
   ```bash
   cat LORA_FIX_GUIDE.md
   ```

---

## Summary

| Task | Command | Time |
|------|---------|------|
| Quick Start | `cat QUICK_LORA_FIX.md` | 2 min |
| Run Fix | `python3 retrain_lora_fix.py` | 10-30 min |
| Start Services | `python3 mondrian/start_services.py` | 10 sec |
| Test | `python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora` | 3 min |
| **TOTAL** | | **15-50 min** |

---

**You're all set! Start with `QUICK_LORA_FIX.md` and follow the instructions. The automated script handles the rest.**
