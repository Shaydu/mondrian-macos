# LoRA Badge - Visual Summary

## What Was Added

A **mode badge** now displays at the top of every job analysis result showing which analysis flow was used.

## Visual Examples

### Baseline Mode Badge
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ [BASELINE]  ← Blue badge shows baseline mode            │   │
│  │                                                          │   │
│  │ Image Analysis                                           │   │
│  │ This image demonstrates strong technical precision...   │   │
│  │                                                          │   │
│  │ Composition: 8.5/10                                      │   │
│  │ Lighting: 7.5/10                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### RAG Mode Badge
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ [RAG]  ← Brown/warm badge shows RAG 2-pass mode        │   │
│  │                                                          │   │
│  │ Image Analysis                                           │   │
│  │ Analyzed against Ansel Adams portfolio...               │   │
│  │                                                          │   │
│  │ Similar Compositions: 3 images found                     │   │
│  │ Composition: 8.2/10                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### LoRA Mode Badge
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ [LORA]  ← Green badge shows fine-tuned LoRA mode        │   │
│  │                                                          │   │
│  │ Image Analysis                                           │   │
│  │ Using fine-tuned Ansel Adams model...                    │   │
│  │                                                          │   │
│  │ Composition: 8.7/10 (optimized with LoRA)              │   │
│  │ Lighting: 8.1/10                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Badge Details

### Appearance
- **Position**: Top-left of analysis container
- **Style**: Inline badge with padding and border
- **Font**: Bold, uppercase
- **Size**: Small/medium (0.85em)
- **Transparency**: Partially transparent with border

### Colors by Mode

| Mode | Color | RGB | Appearance |
|------|-------|-----|------------|
| BASELINE | Blue | #3d5a80 | Standard analysis (cold/neutral) |
| RAG | Brown | #5a4a3d | Portfolio comparison (warm/earthy) |
| LORA | Green | #3d5a3d | Fine-tuned model (growth/enhanced) |
| AB_TEST | Purple | #5a3d5a | Experimental (exploratory) |

## Implementation Details

### How Mode is Tracked Through the Analysis

```
User Upload
    ↓
Job Service Receives Mode Parameter
    ↓
Process Job with Mode=baseline|rag|lora
    ↓
AI Advisor Service Receives Mode
    ↓
Strategy Pattern Executes Appropriate Analysis
    ↓
Result.mode_used = actual mode used
    ↓
_result_to_html() passes mode to json_to_html()
    ↓
Badge Rendered in HTML Output
    ↓
iOS App Displays Analysis with Mode Badge
```

### Code Flow

```python
# 1. Mode comes from analysis result
result.mode_used = "lora"

# 2. Pass to _result_to_html()
html = _result_to_html(result, image_path, base_url, mode=result.mode_used)

# 3. Add to json_data
json_data["mode_used"] = mode

# 4. Pass to json_to_html()
html = json_to_html(json_data, ..., mode=mode)

# 5. Render badge in HTML
if display_mode:
    html += '<div style="background: color; ...">BADGE_TEXT</div>'
```

## Badge HTML Structure

```html
<div style="display: flex; gap: 10px; margin-bottom: 15px; align-items: center;">
  <div style="background: #3d5a3d; padding: 6px 12px; border-radius: 4px; 
              font-size: 0.85em; color: #b3d9ff; border: 1px solid #4a7ba7; 
              font-weight: bold;">
    LORA
  </div>
</div>
```

## Real-World Example

When you upload an image and run analysis:

### Terminal Output (./mondrian.sh --restart)
```
[UPLOAD] Mode: lora
[JOB] Mode: lora
[STRATEGY] Mode: lora
[STRATEGY] ✓ Analysis complete
```

### iOS App Analysis View
```
┌─────────────────────────────┐
│  [LORA]                     │  ← Green badge shows this used LoRA
│                             │
│  Photography Analysis       │
│  by Ansel Adams             │
│                             │
│  Composition: 8.7/10        │
│  Lighting: 8.1/10           │
│  ...                        │
└─────────────────────────────┘
```

## Testing the Badge

### 1. Verify in Terminal
```bash
# Run test that creates jobs in all modes
python3 test_mode_verification.py

# In separate terminal, watch for mode markers
tail -f logs/*.log | grep "\[LORA\]\|\[RAG\]\|\[BASELINE\]"
```

### 2. Check Analysis HTML
- Open the analysis results in a browser
- Look for the colored badge at the top
- Each mode should show its designated color

### 3. Test on iOS
- Upload an image in LORA mode
- The analysis view should show the green LORA badge
- Switch to RAG mode and verify brown badge appears
- Switch to BASELINE and verify blue badge appears

## Badge Meaning

**What does each badge tell you?**

- **BASELINE** (Blue): Standard analysis without special optimizations
  - Single pass through the model
  - No portfolio comparison
  - Fast analysis

- **RAG** (Brown): Two-pass analysis with reference images
  - Compares against advisor portfolio
  - Shows similar compositions
  - More comprehensive analysis

- **LORA** (Green): Analysis using fine-tuned model
  - Uses specialized weights for this advisor
  - May be more accurate for advisor style
  - Enhanced recommendations

- **AB_TEST** (Purple): Experimental comparison mode
  - Compares multiple analysis approaches
  - Research/testing mode
  - Not for production use

## Benefits

✓ **Visual Clarity**: Immediately see which analysis mode was used
✓ **User Understanding**: Clear indication of analysis depth/approach
✓ **Debug Help**: Confirms the right flow was executed
✓ **iOS Integration**: Works seamlessly with mobile app
✓ **Color Coding**: Easy to distinguish modes at a glance

## Future Enhancements

Potential improvements for the badge:
- Add tooltip on hover explaining mode
- Add icon alongside text (↻ for RAG, ⚡ for LoRA)
- Show secondary info (confidence, processing time)
- Make badge clickable to show analysis details
- Add animation indicating analysis method used

---

The LoRA badge is now live! When you analyze images, you'll immediately see which flow was used. 🎨
