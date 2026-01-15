# Why LoRA Mode is Less Verbose Than RAG Mode

## The Issue

When using `mode=lora`, the output is much shorter and less detailed than `mode=rag`. The LoRA results lack:
- Dimensional comparison analysis
- Similar image references
- Comparative language and context
- Portfolio statistics
- Actionable recommendations based on portfolio average

## Root Cause

**LoRA and RAG strategies both use the same underlying analysis** - they're both single-pass analyses that just run the model with a prompt.

The **difference** is in what happens AFTER the analysis:

### RAG Mode (Verbose)

In legacy `_analyze_image_rag()` function:
1. Runs initial analysis to get dimensional scores
2. **Finds similar images from portfolio** using `find_similar_by_dimensions()`
3. **Augments prompt** with comparative context: `augment_prompt_with_rag_context()`
4. **Re-analyzes** with enriched prompt (comparative analysis)
5. Results include:
   - Comparisons to reference images
   - Portfolio percentile rankings
   - Deltas from advisor's average
   - Actionable recommendations

### LoRA Mode (Not Verbose)

In new `LoRAStrategy.analyze()` function:
1. Loads LoRA model with fine-tuned adapter
2. Runs analysis with basic prompt (no portfolio context)
3. Returns raw model output
4. **Skips all RAG enrichment steps**

## Why This Happens

The strategy-based architecture was designed for:
- Single-pass efficiency (especially for LoRA)
- Clean separation of concerns
- Fallback chain support

But it **doesn't reuse the RAG context augmentation logic** that makes RAG output more helpful.

## What's Missing in LoRA

The LoRA strategy should (but doesn't) include:

```python
# In LoRAStrategy.analyze() after getting first response:

# 1. Extract dimensional scores from response
dimensional_scores = json_data.get("dimensional_analysis", {})

# 2. Find similar images from portfolio
similar_images = find_similar_by_dimensions(
    db_path, advisor_id, dimensional_scores, top_k=3
)

# 3. Augment prompt with comparative context
enriched_prompt = augment_prompt_with_rag_context(
    adv_prompt, similar_images
)

# 4. Re-analyze with enriched prompt
response2 = stream_generate(model, processor, enriched_prompt, image, max_tokens=8192)
json_data2 = parse_json_response(response2)

# 5. Return enriched results
return AnalysisResult(
    dimensional_analysis=json_data2["dimensional_analysis"],
    # ... with comparative analysis included
)
```

## The Prompt Difference

### LoRA Prompt (Current)
```
[System prompt about advisor]
[Advisor's style/technique prompt]

Analyze the provided image.
```
→ No portfolio context, no comparisons

### RAG Prompt (What LoRA Should Do)
```
[System prompt about advisor]
[Advisor's style/technique prompt]

The user's image has been compared to similar professional photographs from the master's portfolio:
- Reference #1: [Image description] - Dimensional profile [scores]
  - Gap: +0.5 points (user at 75th percentile)
- Reference #2: [Image description] - Dimensional profile [scores]
  - Gap: -1.2 points (user at 45th percentile)

Provide comparative analysis highlighting:
1. How the user's approach compares to references
2. Specific strengths matching portfolio patterns
3. Gaps vs. advisor's typical scores
4. Actionable recommendations to match advisor's standards
```
→ Rich context, comparative analysis, specific improvements

## Fix Strategy

To make LoRA as verbose as RAG, LoRA strategy should:

1. ✅ **First pass**: Get dimensional analysis (already doing)
2. ❌ **Find similar images**: Add portfolio lookup
3. ❌ **Augment prompt**: Add comparative context
4. ❌ **Second pass**: Re-analyze with enriched prompt
5. ❌ **Merge results**: Combine both analyses

This would make LoRA results more helpful and actionable.

## Trade-offs

**Current approach (less verbose but fast):**
- Single GPU pass
- Faster response
- Less helpful analysis
- No portfolio context

**Proposed approach (more verbose but richer):**
- Two GPU passes
- Slower response (but LoRA is already fast)
- Much more helpful analysis
- Portfolio-aware recommendations

## Recommendations

1. **Option A (Quick)**: Add portfolio context to LoRA prompts (no second pass)
   - Reuse `augment_prompt_with_rag_context()` logic
   - Add comparative instruction to initial prompt
   - Moderate improvement in verbosity

2. **Option B (Best)**: Implement full two-pass for LoRA
   - First pass: Get dimensional scores
   - Query portfolio for similar images
   - Second pass: Re-analyze with context
   - Highest quality output
   - 2x slower (still acceptable)

3. **Option C (Simplest)**: Make LoRA fall back to RAG+LoRA
   - Users requesting pure LoRA get RAG+LoRA
   - Get full verbosity benefits
   - Lose "pure LoRA" distinction

## Current Mode Behaviors

| Mode | First Pass | Portfolio Lookup | Second Pass | Verbosity |
|------|-----------|------------------|------------|-----------|
| `baseline` | ✅ | ❌ | ❌ | Low |
| `rag` | ✅ | ✅ | ✅ | High |
| `lora` | ✅ (fine-tuned) | ❌ | ❌ | Low |
| `rag+lora` | ✅ (fine-tuned) | ❌ | ❌ | Low (should be high!) |

**Issue**: `rag+lora` also needs the portfolio context to be truly RAG+LoRA!

## Suggested Fix

Update both LoRA and RAGLoRA strategies to include the portfolio augmentation step. This would:
- Make output more helpful and actionable
- Provide comparative context that users expect
- Still leverage the fine-tuned model advantages
- Keep performance acceptable (modern GPUs can handle 2 passes)
