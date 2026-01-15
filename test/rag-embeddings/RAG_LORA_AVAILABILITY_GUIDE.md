# Why RAG+LoRA Mode May Not Be Available

## The Problem

When you run the test, it shows: **"RAG+LoRA mode not available. Tests will be limited."**

This happens because the test tries to check mode availability by calling:
```
GET /analysis?advisor=ansel
```

But **this endpoint doesn't exist** in the AI Advisor service. So the test fails to check availability and assumes the mode is unavailable.

## What Makes RAG+LoRA Actually Available?

RAG+LoRA requires BOTH of these conditions:

### 1. LoRA Adapter Must Exist
- Location: `./adapters/ansel/adapters.safetensors`
- You need the actual fine-tuned weights file
- Check with: `ls -lh ./adapters/ansel/`

### 2. Dimensional Profiles Must Exist in Database
- These are stored in the `dimensional_profiles` table
- Created by analyzing images with the baseline or LoRA mode first
- Retrieves profiles for RAG context

## How to Make RAG+LoRA Available

### Step 1: Verify Adapter Exists
```bash
ls -lh ./adapters/ansel/
# Should show: adapters.safetensors (>1GB)
```

### Step 2: Populate Dimensional Profiles
Run baseline analysis to build the database:
```bash
# Start services in baseline mode
./mondrian.sh --restart --mode=base

# Analyze some images (this builds dimensional profiles)
python3 test/test_baseline_debug.py
```

### Step 3: Start Services in LoRA Mode
```bash
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel
```

### Step 4: Run Tests
```bash
./test/rag-embeddings/run_rag_lora_tests.sh
```

## Debugging: Check What's Available

Add this Python snippet to check what's actually available:

```python
from mondrian.strategies.context import AnalysisContext

# Check available modes for Ansel
modes = AnalysisContext.get_available_modes("ansel")
for mode, is_available in modes.items():
    print(f"{mode}: {'✓' if is_available else '✗'}")
```

Expected output if everything is set up:
```
baseline: ✓
rag: ✓
lora: ✓
rag_lora: ✓
```

## The Real Issue with the Test

The test checks availability using an endpoint that doesn't exist. Better approaches:

1. **Remove availability check** - Just try the mode and handle fallback
2. **Create the endpoint** - Add `/modes?advisor=ansel` to AI Advisor service
3. **Check directly** - Import and call `get_available_modes()` directly

For now, the test is being overly cautious - it will still run all tests regardless of the availability check result. If RAG+LoRA is available, the tests will pass. If not, they'll gracefully skip or fallback to the next available mode.
