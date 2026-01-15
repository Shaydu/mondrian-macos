# LoRA Fix Checklist

Use this checklist to track your progress through the fix.

## Pre-Fix Verification

- [ ] Read `QUICK_LORA_FIX.md` (2 min)
- [ ] Understand the problem: Wrong training data
- [ ] Know the solution: Retrain with correct data
- [ ] Have 20-40 minutes available
- [ ] Can access `/Users/shaydu/dev/mondrian-macos/`

## Run the Fix

- [ ] Open terminal in project directory
- [ ] Run: `python3 retrain_lora_fix.py`
- [ ] Wait for script to complete (10-30 min)
- [ ] See message: "RETRAINING COMPLETE!" ✓
- [ ] Confirm: Old adapter backed up
- [ ] Confirm: New adapter installed

## Post-Fix Setup

- [ ] Run: `python3 mondrian/start_services.py`
- [ ] Wait for startup messages
- [ ] See: "AI Advisor Service ready on http://0.0.0.0:5100"
- [ ] See: "Job Service v2.3-DB-FIXED on port 5005"

## Verification Testing

### Test 1: LoRA Mode
- [ ] Run: `python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora`
- [ ] Wait for completion (2-3 min)
- [ ] See message: "✓ End-to-End Test PASSED"
- [ ] Check output directory created: `analysis_output/lora_e2e_lora_*/`
- [ ] Files exist:
  - [ ] `analysis_summary.html` (should be 3+ KB)
  - [ ] `analysis_detailed.html` (should be 10+ KB)
  - [ ] Both files have visible content (not empty)

### Test 2: Compare Modes (Optional)
- [ ] Run: `python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare`
- [ ] Wait for completion (5-10 min)
- [ ] Output shows:
  - [ ] LoRA results with recommendations
  - [ ] Baseline results with recommendations
  - [ ] Comparison HTML generated

### Test 3: Baseline Mode (Should Still Work)
- [ ] Run: `python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline`
- [ ] Completes successfully
- [ ] Produces full output (should already work)

## Log Verification

- [ ] Check logs: `tail -50 logs/ai_advisor_service_*.log`
- [ ] Should NOT see:
  - [ ] `[JSON PARSER] All parsing strategies failed`
  - [ ] `[STRATEGY ERROR] Could not parse model response`
  - [ ] `ValueError: Could not parse model response as JSON`
- [ ] Should see:
  - [ ] `[JSON PARSER] Strategy 1 (as-is) succeeded`
  - [ ] `[STRATEGY] Analysis complete`
  - [ ] Mode used: `lora`

## Success Indicators

Check all of these:

- [ ] Test output says: "✓ End-to-End Test PASSED"
- [ ] HTML files are generated (not empty)
- [ ] No JSON parsing errors in logs
- [ ] Mode confirmed as "lora" (not fallback)
- [ ] All three tests pass (LoRA, baseline, comparison)

## Troubleshooting

If any test fails, check:

### If LoRA test still produces empty output:

- [ ] Verify services are running:
  ```bash
  curl http://127.0.0.1:5005/health
  curl http://127.0.0.1:5100/health
  ```
- [ ] Check latest logs:
  ```bash
  tail -100 logs/ai_advisor_service_*.log | grep -E "ERROR|FAIL|JSON PARSER"
  ```
- [ ] If still incomplete, may need more training data
  - See: LORA_FIX_GUIDE.md → "Advanced: Generating More Training Data"

### If services won't start:

- [ ] Kill any existing processes: `pkill -f ai_advisor_service` or `pkill -f job_service`
- [ ] Check ports are free: 5005 and 5100
- [ ] Restart: `python3 mondrian/start_services.py`

### If retraining failed:

- [ ] Check GPU memory available
- [ ] Try with reduced epochs: `--epochs 1`
- [ ] Check training data exists: `ls -l training/datasets/ansel_image_training_nuanced.jsonl`

## Completion

- [ ] All tests passed
- [ ] No errors in logs
- [ ] Full JSON output generated
- [ ] Ready to use LoRA mode

## Additional Notes

**What was fixed:**
- Old adapter (trained on philosophy text) → Backed up
- New adapter (trained on image analysis) → Installed

**Time spent:**
- Fix script: ___ minutes
- Services startup: ___ minutes
- Testing: ___ minutes
- Total: ___ minutes

**Issues encountered:**
(list any problems and how you fixed them)
- [ ] None
- [ ] (describe issues here)

## Next Steps After Fix

- [ ] Consider generating more training data if output quality is low
- [ ] Run periodic tests to ensure LoRA stays working
- [ ] Monitor logs for any issues
- [ ] Document any customizations made

---

## Quick Reference

If you need to run commands again later:

```bash
# Run the fix (next time)
python3 retrain_lora_fix.py

# Start services
python3 mondrian/start_services.py

# Test LoRA
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora

# Test all modes
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare

# Check health
curl http://127.0.0.1:5005/health && echo "Job Service OK"
curl http://127.0.0.1:5100/health && echo "AI Service OK"

# View logs
tail -50 logs/ai_advisor_service_*.log
tail -50 logs/job_service_v2.3_*.log
```

---

**Estimated total time: 30-50 minutes**

Good luck! 🚀
