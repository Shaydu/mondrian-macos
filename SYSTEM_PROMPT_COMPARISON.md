# System Prompt Comparison Guide

This document describes the two available system prompts for photographic analysis.

## Available Prompts

### 1. `system_prompt` (6 Dimensions) - Full Analysis
**Database key:** `system_prompt`
**Dimensions:** 6
**Target tokens:** 4000-4500
**Recommended profile:** `optimized` or `beam_search`

**Evaluates:**
1. Composition
2. Lighting
3. Focus & Sharpness
4. Depth & Perspective
5. Visual Balance
6. Emotional Impact

**Best for:**
- Complete photographic critique
- Training data generation
- Detailed advisor feedback
- Portfolio reviews

**Example command:**
```bash
./mondrian.sh --restart --mode=lora+rag \
  --gen-profile=optimized \
  --lora-path=./training/training/lora_adapters/ansel_qwen3_4b_instruct/epoch_15 \
  --model=Qwen/Qwen3-VL-4B-Instruct
```

Then update `model_config.json` defaults:
```json
"defaults": {
  "system_prompt_key": "system_prompt"
}
```

---

### 2. `system_prompt_3` (3 Dimensions) - Fast Analysis
**Database key:** `system_prompt_3`
**Dimensions:** 3
**Target tokens:** 2000-2500
**Recommended profile:** `ultra_fast` or `fast_greedy`

**Evaluates:**
1. Composition
2. Lighting
3. Emotional Impact

**Best for:**
- Quick iterations during development
- A/B testing prompt changes
- Faster GPU throughput comparisons
- Initial image screening

**Example command:**
```bash
./mondrian.sh --restart --mode=lora+rag \
  --gen-profile=ultra_fast \
  --lora-path=./training/training/lora_adapters/ansel_qwen3_4b_instruct/epoch_15 \
  --model=Qwen/Qwen3-VL-4B-Instruct
```

Then update `model_config.json` defaults:
```json
"defaults": {
  "system_prompt_key": "system_prompt_3"
}
```

---

## Switching Between Prompts

### Method 1: Update model_config.json (Recommended)
Edit `model_config.json` and change the `system_prompt_key`:

```json
"defaults": {
  "model_preset": "qwen3-4b-instruct",
  "mode": "lora",
  "generation_profile": "optimized",
  "enable_rag": true,
  "system_prompt_key": "system_prompt_3"  // ← Change this
}
```

Then restart services:
```bash
./mondrian.sh --restart --mode=lora+rag --gen-profile=ultra_fast
```

### Method 2: Directly in Database
```bash
# View current prompts
sqlite3 mondrian.db "SELECT key, length(value) FROM config WHERE key LIKE 'system_prompt%'"

# The service will use the key specified in model_config.json defaults
```

---

## Performance Comparison

| Prompt | Dimensions | Target Tokens | Recommended Profile | Typical Duration | GPU Utilization |
|--------|-----------|---------------|---------------------|------------------|-----------------|
| `system_prompt` | 6 | 4000-4500 | `optimized` (2-beam) | 15-25s | High (80-95%) |
| `system_prompt` | 6 | 4000-4500 | `beam_search` (4-beam) | 25-40s | Very High (90-100%) |
| `system_prompt_3` | 3 | 2000-2500 | `ultra_fast` (greedy) | 5-10s | Medium (60-75%) |
| `system_prompt_3` | 3 | 2000-2500 | `fast_greedy` | 8-12s | Medium (70-80%) |

---

## Testing Workflow

### Compare 3-dim vs 6-dim on Same Image

1. **Test with 3 dimensions:**
```bash
# Update model_config.json to use system_prompt_3
./mondrian.sh --restart --mode=lora+rag --gen-profile=ultra_fast
python3 test/rag-embeddings/test_mode_lora_rag.py --verbose
```

2. **Test with 6 dimensions:**
```bash
# Update model_config.json to use system_prompt
./mondrian.sh --restart --mode=lora+rag --gen-profile=optimized
python3 test/rag-embeddings/test_mode_lora_rag.py --verbose
```

3. **Compare results:**
- Check token counts
- Verify dimension counts (3 vs 6)
- Compare GPU memory usage
- Measure inference time
- Assess quality of recommendations

---

## Current Configuration

The default configuration in `model_config.json` is currently set to:
```json
"system_prompt_key": "system_prompt_3"
```

This means the **3-dimension fast analysis** is active by default.

---

## Notes

- Both prompts use the same citation system (IMG_X, QUOTE_X)
- Both prompts enforce the same quality standards
- The 3-dimension version focuses on the most critical aspects: composition, lighting, and emotional impact
- The 6-dimension version adds technical dimensions: focus/sharpness, depth/perspective, and visual balance
- Citation rules scale proportionally (3-dim allows fewer citations than 6-dim)
