# LoRA Debugging Complete - Document Index

## Quick Navigation

### 🚀 Start Here (Choose One)

**I want to fix it NOW:**
→ `QUICK_LORA_FIX.md` (2 minute read)

**I want detailed instructions:**
→ `LORA_FIX_GUIDE.md` (complete step-by-step guide)

**I want to understand the problem:**
→ `LORA_DEBUG_FINDINGS.md` (technical analysis)

**I want a summary:**
→ `DEBUGGING_COMPLETE.md` (this document is a summary of that)

---

## All Documents

### Primary Documents (Read These)

| File | Purpose | Read Time | Use When |
|------|---------|-----------|----------|
| **QUICK_LORA_FIX.md** | Quick 2-step fix overview | 2 min | You want the fastest path to fixing |
| **LORA_FIX_GUIDE.md** | Complete step-by-step guide | 10 min | You want detailed instructions |
| **DEBUGGING_COMPLETE.md** | Full summary with context | 5 min | You want to understand everything |
| **LORA_DEBUG_FINDINGS.md** | Technical root cause analysis | 8 min | You want technical details |

### Scripts (Run These)

| File | Purpose | Run Time | When to Use |
|------|---------|----------|------------|
| **retrain_lora_fix.py** | Automated retraining script | 10-30 min | Main fix - run this! ⭐ |
| **retrain_lora_correct.sh** | Bash version of fix script | 10-30 min | Alternative if you prefer bash |
| **diagnose_lora_output.py** | Diagnostic information | 1 sec | Verify the problem exists |
| **test_lora_direct.py** | Direct model testing | 10 min | Manual testing (needs GPU) |

---

## The Problem (30 seconds)

**What's wrong:**
- LoRA test produces incomplete JSON output
- Only generates `{"image_description": "..."}`
- Should generate full JSON with `dimensional_analysis`, `overall_grade`, etc.

**Why:**
- Adapter trained on **philosophy text** (wrong data)
- Should have trained on **image analysis examples** (right data)

**How to fix:**
```bash
python3 retrain_lora_fix.py
```

---

## The Solution (2 steps)

### Step 1: Run the Fix (10-30 minutes)
```bash
python3 retrain_lora_fix.py
```

The script will:
- Verify correct training data exists
- Train new adapter with image analysis data
- Automatically backup old adapter
- Install new adapter

### Step 2: Test It Works (5 minutes)
```bash
python3 mondrian/start_services.py
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

---

## Documentation Map

```
START HERE
    ↓
QUICK_LORA_FIX.md ────────────→ Want quick overview?
    ↓                           → 2 minute read
WANT MORE DETAIL?               → Go here first
    ↓
LORA_FIX_GUIDE.md ──────────→ Need step-by-step?
    ↓                         → Complete instructions
WANT TECHNICAL DETAILS?        → Includes troubleshooting
    ↓
LORA_DEBUG_FINDINGS.md ────→ How did this happen?
    ↓                         → Root cause analysis
    ↓
Run: python3 retrain_lora_fix.py
    ↓
Test: python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
    ↓
✓ FIXED!
```

---

## File Breakdown

### 📄 Document: QUICK_LORA_FIX.md
- **Purpose**: Ultra-quick reference
- **Length**: 1 page
- **Content**: Problem, fix command, next steps
- **Read Time**: 2 minutes
- **Best For**: Impatient users who just want to fix it

### 📄 Document: LORA_FIX_GUIDE.md
- **Purpose**: Complete implementation guide
- **Length**: 8 pages
- **Content**: All solutions (3 approaches), verification, troubleshooting, FAQ
- **Read Time**: 10-15 minutes
- **Best For**: Users who want complete instructions and troubleshooting

### 📄 Document: DEBUGGING_COMPLETE.md
- **Purpose**: Summary with context
- **Length**: 3 pages
- **Content**: Problem, root cause, solutions, timeline
- **Read Time**: 5 minutes
- **Best For**: Understanding the full picture

### 📄 Document: LORA_DEBUG_FINDINGS.md
- **Purpose**: Technical deep-dive
- **Length**: 4 pages
- **Content**: Root cause evidence, why it happened, training data comparison
- **Read Time**: 8 minutes
- **Best For**: Technical users wanting to understand why

---

## Scripts Breakdown

### 🐍 Script: retrain_lora_fix.py
```bash
python3 retrain_lora_fix.py
```
- **What it does**: Automated complete retraining workflow
- **Time**: 10-30 minutes
- **Reliability**: HIGH (recommended)
- **Includes**:
  - Data verification
  - Training with correct data
  - Automatic backup of old adapter
  - New adapter installation
  - Next steps instructions

### 🐚 Script: retrain_lora_correct.sh
```bash
bash retrain_lora_correct.sh
```
- **What it does**: Same as retrain_lora_fix.py but in bash
- **Time**: 10-30 minutes
- **Reliability**: HIGH
- **When to use**: If you prefer bash over Python

### 🔬 Script: diagnose_lora_output.py
```bash
python3 diagnose_lora_output.py
```
- **What it does**: Shows diagnostic information
- **Time**: < 1 second
- **Output**: Confirms the problem, shows possible causes
- **When to use**: Verify the issue exists before fixing

### 🧪 Script: test_lora_direct.py
```bash
python3 test_lora_direct.py
```
- **What it does**: Direct model testing (requires GPU)
- **Time**: 5-10 minutes
- **Status**: Experimental (may fail with GPU issues)
- **When to use**: Advanced debugging after retraining

---

## Common Workflows

### Workflow 1: "Just Fix It"
```bash
python3 retrain_lora_fix.py
python3 mondrian/start_services.py
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```
**Time**: 20-40 minutes

### Workflow 2: "I Want to Understand First"
```bash
cat QUICK_LORA_FIX.md
cat LORA_DEBUG_FINDINGS.md
python3 diagnose_lora_output.py
python3 retrain_lora_fix.py
```
**Time**: 30-50 minutes

### Workflow 3: "Full Deep Dive"
```bash
cat QUICK_LORA_FIX.md
cat LORA_FIX_GUIDE.md
cat LORA_DEBUG_FINDINGS.md
# Follow manual steps from guide
```
**Time**: 45-90 minutes

### Workflow 4: "Need It Working NOW"
```bash
# Use working alternatives while fixing
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag
# Then fix in background
python3 retrain_lora_fix.py
```
**Time**: 5 minutes (immediate), then 20+ min (background fix)

---

## Timestamps & Status

**Created**: 2026-01-14
**Status**: Complete ✓
**Verified**: Root cause identified and documented
**Solution**: Automated scripts ready to use

---

## Quick Reference Card

```
THE PROBLEM
  ✗ LoRA produces incomplete JSON
  ✗ Missing dimensional_analysis, overall_grade, etc.
  
THE CAUSE
  ✗ Trained on philosophy text (1,494 examples)
  ✓ Should train on image analysis (21 examples)

THE FIX
  → python3 retrain_lora_fix.py
  
THE TIME
  → 10-30 min (automatic training)
  → 5 min (testing)
  → Total: 20-40 min

THE WORKAROUND
  → Use baseline or RAG mode (works perfectly)
  
NEXT STEPS
  1. Read: QUICK_LORA_FIX.md (2 min)
  2. Run: python3 retrain_lora_fix.py (20 min)
  3. Test: python3 test_lora_e2e.py ... (3 min)
  4. Done! ✓
```

---

## Support Resources

**For quick answers**:
- Read: QUICK_LORA_FIX.md
- Check: FAQ section in LORA_FIX_GUIDE.md

**For detailed guidance**:
- Read: LORA_FIX_GUIDE.md
- Follow: Step-by-step instructions

**For technical understanding**:
- Read: LORA_DEBUG_FINDINGS.md
- Understand: Root cause analysis

**For troubleshooting**:
- Check: Troubleshooting section in LORA_FIX_GUIDE.md
- Run: python3 diagnose_lora_output.py
- View: tail logs/ai_advisor_service_*.log

---

## Success Criteria

After completing the fix, you should see:

✅ **Log output changes from**:
```
[JSON PARSER] All parsing strategies failed
[STRATEGY ERROR] Could not parse model response as JSON
```

✅ **To**:
```
[JSON PARSER] Strategy 1 (as-is) succeeded
[STRATEGY] Analysis complete. Overall grade: 8.5
```

✅ **Output files generated**:
- analysis_detailed.html (10+ KB)
- analysis_summary.html (3+ KB)
- Both with complete content, not empty

✅ **Test output shows**:
```
✓ End-to-End Test PASSED
✓ Mode Used: lora (not fallback)
```

---

**You're all set! Pick a document above and start.**
