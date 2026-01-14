# Nuanced Image Training with Independent Dimension Scoring

## What's Different Now?

Your original question was perfect: **"Can we add nuance so a photo can have good composition but soft focus?"**

**Yes!** Each dimension is now scored independently (0-10).

## Why This Matters

### Before (Simple Templates):
```
Label: negative → All dimensions get low scores (2-4)
Label: positive → All dimensions get high scores (8-10)
```

This is unrealistic. Real photos are complex:
- Beautiful light + poor composition
- Perfect focus + no emotional impact
- Great composition + terrible exposure

### After (Nuanced Scoring):
```
composition: 8       ← Excellent!
lighting: 7          ← Good
focus_sharpness: 2   ← PROBLEM!
color_harmony: 6     ← OK
subject_isolation: 7 ← Good
depth_perspective: 5 ← Weak
visual_balance: 8    ← Excellent!
emotional_impact: 4  ← Weak

Overall: 5.9 (mixed/negative)
```

## Two New Scripts

### 1. [review_images_interactive.py](review_images_interactive.py) - For All Images

Score each dimension independently with 3 modes:

**Mode 1: Quick**
- Set one overall grade (e.g., 6/10)
- Auto-applies to all dimensions with ±1 variation
- Fastest option

**Mode 2: Dimension by Dimension**
- Score all 8 dimensions individually
- Most control, most realistic
- Takes ~2 minutes per image

**Mode 3: Mixed** ⭐ **RECOMMENDED**
- Pick 2-3 standout dimensions (good or bad)
- Score those carefully
- Auto-fill the rest with base score
- **Best balance of speed and nuance**

### 2. [add_negative_nuanced.py](add_negative_nuanced.py) - For Negative Examples

Auto-generates realistic negative examples with 8 problem patterns:

1. **good_comp_bad_focus** - Great composition ruined by soft focus
2. **good_light_bad_comp** - Beautiful light wasted on poor framing
3. **sharp_but_boring** - Technically perfect but emotionally void
4. **one_bad_dimension** - Generally solid with one critical failure
5. **mixed_amateur** - Inconsistent work, some good instincts
6. **flat_lighting_only** - Everything OK except lighting destroys it
7. **cluttered_but_sharp** - Perfect focus on compositional chaos
8. **good_vision_poor_execution** - Strong concept, weak technique

## Real-World Examples

### Example 1: Good Composition, Bad Focus
```json
{
  "composition": 8,
  "lighting": 6,
  "focus_sharpness": 2,    ← Critical failure
  "color_harmony": 6,
  "subject_isolation": 7,
  "depth_perspective": 5,
  "visual_balance": 8,
  "emotional_impact": 4
}

Advisor: "Compositional merit is utterly destroyed by technical failure.
Photography demands both vision AND technical precision."
```

### Example 2: Sharp But Boring
```json
{
  "composition": 7,
  "lighting": 6,
  "focus_sharpness": 9,    ← Perfect!
  "color_harmony": 7,
  "subject_isolation": 7,
  "depth_perspective": 6,
  "visual_balance": 7,
  "emotional_impact": 2    ← Critical failure
}

Advisor: "Technical perfection in service of nothing. Master the craft, yes,
but remember: photography is art, not merely technical exercise."
```

### Example 3: Beautiful Light, Poor Composition
```json
{
  "composition": 3,        ← Critical failure
  "lighting": 9,           ← Perfect!
  "focus_sharpness": 7,
  "color_harmony": 8,
  "subject_isolation": 4,
  "depth_perspective": 6,
  "visual_balance": 3,
  "emotional_impact": 5
}

Advisor: "Magnificent light utterly wasted on a poorly conceived composition.
The photographer saw the light but failed to organize the visual elements."
```

## How to Use

### For Your 17 Ansel Photos

```bash
cd /Users/shaydu/dev/mondrian-macos/training/datasets

python review_images_interactive.py \
    --images-dir ../ansel_ocr/extracted_photos \
    --output ansel_nuanced.jsonl
```

**Recommended approach:**
- Mode 3 (Mixed)
- Most Ansel photos: Base score 8-9
- Highlight 2-3 exceptional dimensions (composition, lighting) → 9-10
- Mark any teaching examples lower in specific dimensions

### For User Photos (Good)

```bash
python review_images_interactive.py \
    --images-dir ../user_images/good \
    --output positive_user_nuanced.jsonl
```

**Recommended:**
- Mode 3 (Mixed)
- Find 2-3 standout strengths, score those 8-10
- Set base score 6-7 for rest
- Be honest about weaknesses

### For Bad Photos (Auto-Generate)

```bash
# Random mix of problems (recommended)
python add_negative_nuanced.py \
    --dir ../user_images/bad \
    --output negative_nuanced.jsonl

# Or specific problem type
python add_negative_nuanced.py \
    --dir ../user_images/bad \
    --problem good_comp_bad_focus \
    --output negative_nuanced.jsonl
```

## Training Data Quality

### Good Nuanced Training Data Has:

✅ **Variety in score patterns**
- Some photos: all dimensions 8-10 (masterworks)
- Some photos: 2-3 dimensions excel, rest mediocre (common)
- Some photos: mostly good, one critical failure (teaching moments)
- Some photos: mixed scores across all dimensions (amateur work)

✅ **Realistic problems**
- Good composition + bad focus (common technical failure)
- Good technique + no emotion (technically competent but uninspired)
- Good vision + poor execution (beginner with potential)

✅ **Honest Ansel-style critique**
- Specific about what works and what doesn't
- Constructive guidance
- References Zone System, previsualization, technique

### Bad Training Data Has:

❌ All positive examples scoring 10/10 across all dimensions
❌ All negative examples scoring 2/10 across all dimensions
❌ No variation in score patterns
❌ Generic comments that don't match scores

## Workflow Example

### Step 1: Review Ansel's Photos (30 min)
```bash
python review_images_interactive.py

# For each image:
# - View it
# - Press 'p' (most are positive)
# - Mode 3 (Mixed)
# - Pick 2-3 exceptional dimensions (e.g., "2,3,8" for lighting, focus, emotional_impact)
# - Score those 9-10
# - Base score 8 for rest
# - Press Enter for auto advisor notes
```

Result: ~17 positive examples with nuanced scoring

### Step 2: Download Bad Photos (15 min)
- Go to Unsplash.com
- Search "amateur photography" or "beginner photographer"
- Download 50 photos to `training/user_images/bad/`

### Step 3: Auto-Label Bad Photos (5 min)
```bash
python add_negative_nuanced.py \
    --dir ../user_images/bad \
    --output negative_nuanced.jsonl
```

Result: 50 negative examples with varied, realistic problems

### Step 4: Check Status
```bash
python check_training_status.py
```

### Step 5: Combine Everything
```bash
cat ansel_print_filtered_train.jsonl \
    ansel_nuanced.jsonl \
    negative_nuanced.jsonl \
    > ansel_complete_nuanced.jsonl
```

## Score Distribution Guidelines

### Positive Examples (50-100 photos)
- **Master works** (10-20%): 9-10 across all dimensions
- **Excellent** (40-50%): 8-9 most dimensions, maybe one 6-7
- **Very good** (30-40%): 7-8 most dimensions, 2-3 exceptional areas

### Negative Examples (50-100 photos)
- **Fundamentally flawed** (30%): 2-4 across most dimensions
- **One critical failure** (30%): 6-8 most dimensions, one 2-3
- **Mixed amateur** (40%): Scores ranging 3-7, inconsistent

## Why This Training Data Is Better

### For the LoRA Model:

1. **More realistic patterns** - Learns that photos have mixed qualities
2. **Better critique ability** - Can identify specific strengths/weaknesses
3. **Nuanced evaluation** - Not just "good" or "bad" but "good composition, poor focus"
4. **Matches real use** - User photos will have varied qualities

### For Your Use Case:

When a user submits a photo, the model can say:
```
"Excellent composition (8/10) and strong visual balance (8/10),
but the soft focus (3/10) undermines the technical credibility.
Return with a tripod and master your depth of field calculations."
```

Instead of just:
```
"This photo is bad. Score: 4/10"
```

## Files You'll Create

```
ansel_nuanced.jsonl                  # 17 Ansel photos, nuanced scoring
positive_user_nuanced.jsonl          # Your good photos, nuanced scoring
negative_nuanced.jsonl               # Bad photos, varied realistic problems
ansel_complete_nuanced.jsonl         # Everything combined
```

## Quick Reference

### Review Images (Interactive)
```bash
python review_images_interactive.py --images-dir <path> --output <file>
```

### Auto-Label Negative (Batch)
```bash
python add_negative_nuanced.py --dir <path> --output <file>
```

### Check Status
```bash
python check_training_status.py
```

### Combine
```bash
cat file1.jsonl file2.jsonl file3.jsonl > combined.jsonl
```

## Tips for Best Results

1. **Use Mode 3 (Mixed)** for reviewing - best speed/quality balance
2. **Be honest** - Not every photo needs 9-10 scores
3. **Vary your negative examples** - Mix different problem types
4. **Focus on teaching moments** - Photos where one dimension fails
5. **Use auto-comments** - They're based on Ansel's actual writing
6. **Review in batches** - 5-10 images per session to avoid fatigue

Your model will learn to evaluate photos the way Ansel would: nuanced, specific, constructive, and honest.
