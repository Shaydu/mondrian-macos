# LLM Thinking/Repetition Issue - Fixed

## Issue Summary
The Qwen3-VL-4B model in LoRA mode was experiencing a token repetition issue where it would get stuck repeating the word "peace" (appearing as `**peace**` hundreds of times) during the Emotional Impact analysis dimension.

### Root Cause
The model's generation parameters were not optimized for controlled output. Without a repetition penalty and proper sampling strategy, the model could enter a loop of repeating tokens, especially when generating longer sequences.

**Original Output Issue:**
```
"The image evokes a sense of peace**peace**peace**peace**peace**peace**peace**peace**..." 
(repeated 1000+ times)
```

## Solution Implemented

### Code Change
**File:** `mondrian/ai_advisor_service_linux.py` (lines 300-310)

**Before:**
```python
with torch.no_grad():
    output_ids = self.model.generate(
        **inputs, 
        max_new_tokens=2000,
        eos_token_id=self.processor.tokenizer.eos_token_id
    )
```

**After:**
```python
with torch.no_grad():
    output_ids = self.model.generate(
        **inputs, 
        max_new_tokens=1500,
        repetition_penalty=1.2,
        do_sample=True,
        temperature=0.5,
        top_p=0.95,
        eos_token_id=self.processor.tokenizer.eos_token_id
    )
```

### Parameter Explanation

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `max_new_tokens` | 1500 | Reduced from 2000 to keep output focused and prevent lengthy repetition loops |
| `repetition_penalty` | 1.2 | **Critical**: Penalizes repeated tokens, preventing word loops |
| `do_sample` | True | Enable sampling instead of greedy decoding for more natural output |
| `temperature` | 0.5 | Controls randomness (lower = more deterministic, better for JSON) |
| `top_p` | 0.95 | Nucleus sampling - only consider top 95% probability tokens |

## Results

✅ **Test Status:** PASSED

- No repetition issues detected in LoRA mode
- All 7 dimensions generated properly with unique, meaningful content
- JSON output properly formatted and parseable
- Generation completes in reasonable time

### Example Output (Post-Fix)
```json
{
  "image_description": "A dramatic sunset with fiery orange and yellow clouds...",
  "dimensions": [
    {
      "name": "Emotional Impact",
      "score": 7,
      "comment": "The image evokes a sense of peace and contemplation...",
      "recommendation": "Consider enhancing the emotional narrative..."
    }
  ]
}
```

## Testing

To verify the fix works:

```bash
# Option 1: Test via API
python3 test_lora_fix.py

# Option 2: Manual test
curl -X POST -F "image=@source/mike-shrub-01004b68.jpg" \
  -F "advisor=ansel" -F "enable_rag=false" \
  http://localhost:5100/analyze | jq '.dimensions'
```

## Additional Notes

- ✅ The fix maintains output quality while preventing repetition
- ✅ Sampling parameters still generate consistent JSON structures
- ✅ Works with both LoRA adapter mode and baseline mode
- ✅ No significant performance degradation
- ✅ Prevents the model from getting stuck in token loops

## Regarding "LLM Thinking" Feature

While we addressed the repetition issue, **direct access to LLM thinking tokens is not readily available** with the current Qwen3-VL-4B model:

1. **Model doesn't expose internal reasoning:** Qwen3-VL doesn't have built-in thinking/reasoning tokens like Claude or o1
2. **Chain-of-thought prompting:** We can encourage the model to show thinking by prompt engineering
3. **Alternative approaches:**
   - Extract reasoning from the model's comments/recommendations
   - Use structured prompts that ask for step-by-step analysis
   - Monitor intermediate outputs during inference

If you want to capture thinking-like output, consider:
```json
{
  "thinking_process": "Step 1: Analyze composition... Step 2: Check lighting...",
  "final_analysis": "..."
}
```
