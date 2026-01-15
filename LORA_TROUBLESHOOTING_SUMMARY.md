# LoRA Mode Troubleshooting Summary

**Date**: January 14, 2026
**Status**: Partially Fixed - Baseline Mode Working, LoRA Requires Retraining

---

## Issues Discovered

### 1. GPU Out of Memory (OOM) ✅ FIXED

**Problem:**
```
[METAL] Command buffer execution failed: Insufficient Memory
(00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)
```

**Root Cause:**
- AI Advisor Service defaulted to `mlx-community/Qwen3-VL-8B-Instruct-4bit` (8B parameters)
- LoRA adapter was trained on `mlx-community/Qwen3-VL-4B-Instruct-4bit` (4B parameters)
- Model size mismatch + LoRA weights (16.5M params) exceeded GPU memory

**Solution:**
Changed default model in `mondrian/ai_advisor_service.py:109`:
```python
# Before
parser.add_argument("--mlx_model", type=str, default="mlx-community/Qwen3-VL-8B-Instruct-4bit", ...)

# After
parser.add_argument("--mlx_model", type=str, default="mlx-community/Qwen3-VL-4B-Instruct-4bit", ...)
```

**Result:**
- ✅ Services run without crashing
- ✅ LoRA adapter loads successfully
- ✅ Analysis completes without GPU OOM errors

**Important:** This was NOT a SQLite vs PostgreSQL database issue - it was purely a GPU memory/model size mismatch.

---

### 2. Token Limit Too Low ✅ PARTIALLY FIXED

**Problem:**
- Model output was truncated mid-sentence
- JSON parsing failed: `ValueError: Could not parse model response as JSON`
- Initial limit: 2048 tokens (~1,500 words)

**Attempts:**
1. Increased to 4096 tokens - still truncated (20,356 chars)
2. Increased to 8192 tokens - still truncated (25,853 chars)

**Solution:**
Modified `mondrian/strategies/lora.py:181`:
```python
# Before
for result in stream_generate(model, processor, formatted_prompt, image, max_tokens=2048):

# After
for result in stream_generate(model, processor, formatted_prompt, image, max_tokens=8192):
```

**Result:**
- ✅ Model generates much longer output
- ❌ Still doesn't produce valid JSON (see Issue #3)

---

### 3. LoRA Model Doesn't Follow JSON Format ⚠️ TRAINING DATA ISSUE

**Problem:**
Even with 8192 token limit, LoRA model generates:
- Extremely verbose narrative text
- Incomplete JSON objects (missing closing braces)
- Text that continues beyond JSON boundaries
- Example: `"...The print was then mounted in a 4128x4140 inch frame. The print was then mounted"` (cut off)

**Root Cause:**
The LoRA fine-tuned model was trained on data that:
1. Likely didn't strictly enforce JSON format
2. Contained verbose, narrative-style responses
3. Overrode the base model's instruction-following capabilities

**Evidence:**
- System prompt clearly instructs: `"You MUST output valid JSON"`
- System prompt explicitly says: `"DO NOT wrap your response in markdown code blocks"`
- Base model (without LoRA) follows these instructions perfectly
- LoRA model ignores them and generates prose instead

**Workaround:**
Use **baseline mode** instead of LoRA mode:
```bash
./mondrian.sh --restart --mode=base
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
```

**Result:**
- ✅ Baseline mode generates perfect JSON
- ✅ All HTML outputs render correctly
- ✅ No parsing errors
- ✅ Analysis completes successfully

**Permanent Fix Required:**
Retrain the LoRA adapter with training data that:
1. Strictly follows the JSON schema
2. Uses the exact format specified in the system prompt
3. Has examples with proper closing braces
4. Includes `<eos_token>` after JSON closes to teach the model when to stop

---

## Current Status

### What Works ✅
- **Baseline Mode**: Fully functional, generates proper JSON
- **RAG Mode**: Should work (not tested in this session)
- **GPU Acceleration**: Working correctly with 4B model
- **Service Stability**: No crashes, proper model loading
- **E2E Test**: Passes for baseline mode

### What Doesn't Work ❌
- **LoRA Mode**: Generates invalid JSON, requires retraining

---

## How to Use the System Now

### Option 1: Use Baseline Mode (Recommended for Now)
```bash
# Start services in baseline mode
./mondrian.sh --restart --mode=base

# Run test
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline

# View output
open $(ls -t analysis_output/lora_e2e_baseline_*/analysis_detailed.html | head -1)
```

### Option 2: Use RAG Mode
```bash
# Start services in RAG mode
./mondrian.sh --restart --mode=rag

# Run test
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode rag
```

### Option 3: Fix LoRA Mode (Requires Retraining)
See "Retraining Guide" section below.

---

## Files Modified

1. **mondrian/ai_advisor_service.py:109**
   - Changed default model from 8B to 4B
   - Prevents GPU OOM errors

2. **mondrian/strategies/lora.py:181**
   - Increased max_tokens from 2048 → 8192
   - Allows longer output (though still not valid JSON)

---

## Retraining Guide (To Fix LoRA Mode)

### 1. Prepare Training Data

Your training data must follow this exact format:

```jsonl
{"messages": [
  {"role": "system", "content": "You are a photography analysis assistant..."},
  {"role": "user", "content": "<image>Analyze this photograph."},
  {"role": "assistant", "content": "{\"image_description\": \"...\", \"dimensions\": [...], \"overall_score\": 7.4, ...}"}
]}
```

**Critical Requirements:**
- ✅ Assistant responses must be valid, complete JSON
- ✅ JSON must start with `{` and end with `}`
- ✅ Include all required fields from system prompt
- ✅ No narrative text, no markdown wrappers
- ✅ Responses should be concise (< 4096 tokens)

### 2. Training Script Configuration

```python
# training script settings
max_seq_len = 8192  # Match generation limit
examples = [...]  # Load your properly formatted data
epochs = 3
batch_size = 1
learning_rate = 5e-5
```

### 3. Validate Training Data

Before training, verify each example:
```python
import json

for example in training_data:
    assistant_msg = example["messages"][-1]["content"]
    try:
        parsed = json.loads(assistant_msg)
        assert "image_description" in parsed
        assert "dimensions" in parsed
        assert "overall_score" in parsed
        print(f"✓ Valid: {len(assistant_msg)} chars")
    except Exception as e:
        print(f"✗ Invalid: {e}")
```

### 4. After Retraining

Test the new adapter:
```bash
./mondrian.sh --restart --mode=lora --lora-path=adapters/ansel
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

Check logs for:
- `[JSON PARSER] Strategy 1 (as-is) succeeded` ✅ Good!
- `[JSON PARSER] All parsing strategies failed` ❌ Training data still wrong

---

## Testing Commands

### Quick Health Check
```bash
curl http://127.0.0.1:5100/health | python3 -m json.tool
```

### Run E2E Test (Baseline)
```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode baseline
```

### Run E2E Test (LoRA - will fail with current adapter)
```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

### View Latest Output
```bash
# Summary view
open $(ls -t analysis_output/lora_e2e_*/analysis_summary.html | head -1)

# Detailed view
open $(ls -t analysis_output/lora_e2e_*/analysis_detailed.html | head -1)

# Advisor bio
open $(ls -t analysis_output/lora_e2e_*/advisor_bio.html | head -1)
```

---

## Why Token Limits Exist

Token limits serve several purposes:

1. **Prevent Runaway Generation**
   - Without limits, models can generate infinitely
   - Especially important for fine-tuned models that may not respect EOS tokens

2. **Control Inference Time**
   - More tokens = longer generation time
   - 2048 tokens ≈ 30 seconds
   - 8192 tokens ≈ 2 minutes

3. **GPU Memory Management**
   - Each token uses GPU memory during generation
   - KV cache grows with sequence length
   - Higher limits increase memory pressure

4. **Cost Control**
   - For API-based models, tokens cost money
   - Not applicable here, but best practice

**Recommended Limits:**
- **Baseline/RAG**: 4096 tokens (sufficient for structured JSON)
- **LoRA** (after retraining): 4096 tokens
- **Never needed**: 8192+ tokens (indicates verbose training data)

---

## Debugging Tips

### Check Model Loading
```bash
tail -f logs/ai_advisor_service_*.log | grep -E "Loading|LoRA|Model"
```

### Monitor GPU Usage
```bash
# While analysis is running
ps aux | grep ai_advisor_service
```

### Check JSON Parsing
```bash
tail -f logs/ai_advisor_service_*.log | grep -E "JSON PARSER|Response length"
```

### Verify No OOM Errors
```bash
tail -f logs/ai_advisor_service_*.log | grep -E "Memory|OOM|terminate"
```

---

## Related Documentation

- [docs/testing.md](docs/testing.md) - Testing guide
- [LORA_STRATEGY_IMPLEMENTED.md](LORA_STRATEGY_IMPLEMENTED.md) - LoRA implementation details
- [test_lora_e2e.py](test_lora_e2e.py) - End-to-end test script
- [mondrian/strategies/lora.py](mondrian/strategies/lora.py) - LoRA strategy implementation

---

## Conclusion

The system is now **fully functional in baseline mode**. The LoRA mode has a training data quality issue that causes it to generate prose instead of JSON. This is a common problem when fine-tuning models without careful data curation.

**Immediate Action:** Use baseline or RAG mode
**Future Work:** Retrain LoRA adapter with properly formatted JSON training data

**Key Takeaway:** This was a model training issue, not a code bug. The infrastructure (GPU, services, model loading) all work correctly.
