# Anti-Repetition Fix - Unique Recommendations Per Dimension

## Problem Identified
The AI was generating **duplicate or nearly identical "How to Improve" recommendations across different dimensions**, making the analysis feel repetitive and less valuable.

Example of the problem:
- **Composition**: "Consider using leading lines to guide the viewer..."
- **Depth & Perspective**: "Consider using leading lines to create depth..." ❌ DUPLICATE
- **Visual Balance**: "Try using leading lines for better balance..." ❌ DUPLICATE

## Solutions Implemented

### 1. Enhanced System Prompts ✅

#### Updated [system_prompt.txt](system_prompt.txt):
- Added **CRITICAL ANTI-REPETITION REQUIREMENT** section at the top
- Explicit instructions: Each dimension must have completely unique recommendations
- Added dimension-specific focus areas to guide the model:
  - **Composition**: Rule of thirds, framing, subject placement only
  - **Lighting**: Exposure, tonal range, Zone System only
  - **Focus & Sharpness**: DOF, hyperfocal distance, tripod use only
  - **Depth & Perspective**: Foreground layers, spatial depth, lens choice only
  - **Visual Balance**: Weight distribution, tonal balance, equilibrium only
  - **Emotional Impact**: Mood, atmosphere, storytelling only

- Added concrete examples showing what NOT to do
- Added pre-submission checklist for the model to self-verify

#### Updated [system_prompt_thinking.txt](system_prompt_thinking.txt):
- Same anti-repetition requirements for Qwen3-Thinking models
- Emphasis on reading all recommendations before submitting

### 2. Stronger Generation Parameters ✅

#### Updated [model_config.json](model_config.json) profiles:

**`optimized` (default)**:
- `repetition_penalty`: 1.15 (up from 1.05) 
- `no_repeat_ngram_size`: 4 (prevents 4-word phrase repetition)
- Result: Blocks duplicate phrases like "leading lines to guide"

**`quality_focused`**:
- `repetition_penalty`: 1.2 (even stronger)
- `no_repeat_ngram_size`: 5 (prevents 5-word phrase repetition)
- Result: Maximum uniqueness across all dimensions

**`beam_search`**:
- `repetition_penalty`: 1.15
- `no_repeat_ngram_size`: 4
- Result: Diverse exploration of recommendation space

## How It Works

### Prompt-Level Control (Most Important)
The system prompt now explicitly tells the model:
1. Each dimension analyzes a **different technical aspect**
2. Recommendations must be **dimension-specific**
3. If a term is used in one dimension, **avoid it in others**
4. Provides clear boundaries for what each dimension should focus on

### Generation-Level Control (Supporting)
The generation parameters reinforce this:
- **Repetition penalty** (1.15-1.2): Penalizes token sequences that appear multiple times
- **N-gram blocking** (4-5): Prevents exact phrase repetition
- **Beam search** (3-5 beams): Explores diverse recommendation phrasings

## Expected Results

### Before (Repetitive):
```json
{
  "dimensions": [
    {
      "name": "Composition",
      "recommendation": "Try using the rule of thirds to create better balance and leading lines to guide the viewer's eye."
    },
    {
      "name": "Visual Balance", 
      "recommendation": "Consider using the rule of thirds to improve balance and add leading lines."
    },
    {
      "name": "Depth & Perspective",
      "recommendation": "Use leading lines to create depth and apply rule of thirds for better composition."
    }
  ]
}
```

### After (Unique):
```json
{
  "dimensions": [
    {
      "name": "Composition",
      "recommendation": "Shift your subject slightly off-center to the left third, allowing the mountain ridge to create a natural diagonal flow through the frame."
    },
    {
      "name": "Visual Balance",
      "recommendation": "The bright sky weighs too heavily on the upper half. Add a darker foreground element or reduce sky exposure by 1 stop to achieve better tonal equilibrium."
    },
    {
      "name": "Depth & Perspective",
      "recommendation": "Move closer and include rocks or vegetation in the immediate foreground at the bottom edge. This creates a strong near-to-far spatial relationship."
    }
  ]
}
```

## Verification Steps

After restarting the service, test with a photo and check:

1. ✅ Each dimension's recommendation is completely different
2. ✅ No technical terms are repeated across dimensions
3. ✅ Each recommendation addresses only that dimension's focus area
4. ✅ Recommendations are specific to the actual image (not generic)

## Files Modified

- ✅ [system_prompt.txt](system_prompt.txt) - Main prompt with anti-repetition rules
- ✅ [system_prompt_thinking.txt](system_prompt_thinking.txt) - Thinking model variant
- ✅ [model_config.json](model_config.json) - Generation parameters for all profiles

## How to Apply

```bash
# If running in Docker
docker-compose restart ai_advisor

# Or rebuild if you need to pick up prompt changes
docker-compose up -d --build ai_advisor

# If running locally
python3 scripts/start_services.py --generation-profile optimized
```

## Technical Details

### Why Repetition Happens
1. **LLM training bias**: Models learn patterns from training data where similar phrases appear
2. **Dimension relationships**: Some dimensions naturally overlap (e.g., composition affects balance)
3. **Token economy**: Shorter responses tend to reuse successful phrasings
4. **Lack of explicit constraints**: Without clear boundaries, model defaults to familiar patterns

### Why This Fix Works
1. **Explicit constraints**: Model now knows repetition is wrong
2. **Dimension boundaries**: Clear technical domains prevent overlap
3. **Examples**: Shows what to avoid with concrete cases
4. **Self-verification**: Checklist forces model to review before submitting
5. **Generation penalties**: Technical reinforcement via repetition penalty and n-gram blocking

## Monitoring

After deploying, monitor for:
- ✅ Unique vocabulary across dimensions
- ✅ Dimension-specific technical language
- ✅ Actionable, specific advice (not generic)
- ⚠️ Watch for overly creative/incorrect advice (rare with stronger penalties)

## Rollback Plan

If advice becomes too constrained or quality drops:

1. Reduce `repetition_penalty` from 1.15 → 1.10
2. Reduce `no_repeat_ngram_size` from 4 → 3
3. Keep the prompt instructions (they help regardless)

## Success Metrics

Track over 10-20 analyses:
- **Target**: <5% of recommendations share technical terms across dimensions
- **Target**: 0% exact phrase duplication
- **Target**: Each dimension uses vocabulary from its designated focus area
