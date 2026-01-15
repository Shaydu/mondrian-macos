# LoRA Mode Badge Implementation

## Changes Made

Added a visual mode badge to the job viewer that displays which analysis mode was used (Baseline, RAG, LoRA, or A/B Test).

### Files Modified (in mondrian/ submodule)

1. **mondrian/ai_advisor_service.py**
   - Updated `_analyze_image_with_strategy()` to pass `mode=result.mode_used` to `_result_to_html()`
   - Updated `_result_to_html()` function signature to accept `mode` parameter
   - Added `mode_used` to the json_data dictionary passed to `json_to_html()`
   - Pass mode parameter to `json_to_html()` function call

2. **mondrian/json_to_html_converter.py**
   - Updated `json_to_html()` function signature to accept `mode` parameter
   - Added mode badge rendering logic with color-coding:
     - **BASELINE**: Blue (#3d5a80)
     - **RAG**: Brown/warm (#5a4a3d)
     - **LORA**: Green (#3d5a3d)
     - **AB_TEST**: Purple (#5a3d5a)
   - Badge displays at the top of the analysis HTML, just below the main analysis container

## Badge Styling

The mode badge is rendered as:
- **Style**: Inline flex container with gap spacing
- **Colors**: Mode-specific color scheme
- **Position**: Top of analysis report, before image description
- **Format**: Uppercase text (BASELINE, RAG, LORA, AB_TEST)
- **Styling**: Rounded corners, semi-transparent background with border

## Code Changes

### In ai_advisor_service.py

```python
# Line 1389: Pass mode to _result_to_html
html = _result_to_html(result, abs_image_path, mondrian_api_base_url, mode=result.mode_used)

# Lines 1447-1454: Updated function signature
def _result_to_html(result, image_path, mondrian_api_base_url=None, mode=None):
    """
    Convert AnalysisResult to HTML using existing json_to_html converter.

    Args:
        result: AnalysisResult from strategy
        image_path: Path to analyzed image
        mondrian_api_base_url: Base URL for iOS app
        mode: Analysis mode (baseline, rag, lora, etc.)

    Returns:
        HTML string
    """

# Lines 1502-1516: Add mode to json_data and pass to json_to_html
json_data = {
    "dimensions": dimensions,
    "dimensional_analysis": result.dimensional_analysis,
    "overall_grade": result.overall_grade,
    "overall_score": _grade_to_score(result.overall_grade),
    "advisor_notes": dim_analysis.get("advisor_notes", ""),
    "mode_used": mode  # Add mode for badge display
}

html = json_to_html(
    json_data=json_data,
    similar_images=None,
    base_url=mondrian_api_base_url,
    advisor_name=result.advisor_id,
    mode=mode  # Pass mode to json_to_html
)
```

### In json_to_html_converter.py

```python
# Lines 157-165: Updated function signature
def json_to_html(json_data, similar_images=None, base_url=None, advisor_name=None, mode=None):
    """Convert JSON response to HTML feedback cards.
    
    Args:
        json_data: Parsed JSON analysis data
        similar_images: Optional list of similar reference images from RAG
        base_url: Optional base URL for serving images (e.g., 'http://localhost:5100')
        advisor_name: Optional advisor name for reference section header (e.g., "Ansel Adams")
        mode: Optional analysis mode for badge display (e.g., 'baseline', 'rag', 'lora')
    """

# Lines 172-188: Mode badge rendering
display_mode = mode or json_data.get('mode_used')

# Display mode badge if available
if display_mode:
    mode_colors = {
        'baseline': '#3d5a80',  # Blue
        'rag': '#5a4a3d',       # Brown/warm
        'lora': '#3d5a3d',      # Green
        'ab_test': '#5a3d5a'    # Purple
    }
    mode_color = mode_colors.get(display_mode.lower(), '#3d5a80')
    mode_label = display_mode.upper()
    
    html += '  <div style="display: flex; gap: 10px; margin-bottom: 15px; align-items: center;">\n'
    html += f'    <div style="background: {mode_color}; padding: 6px 12px; border-radius: 4px; font-size: 0.85em; color: #b3d9ff; border: 1px solid #4a7ba7; font-weight: bold;">\n'
    html += f'      {html_escape(mode_label)}\n'
    html += f'    </div>\n'
    html += '  </div>\n'
```

## How It Works

1. When analysis completes via strategy pattern, `result.mode_used` contains the mode that was actually used
2. This is passed to `_result_to_html()` function
3. The mode is added to the JSON data structure
4. In `json_to_html()`, the mode is extracted and displayed as a colored badge
5. The badge appears at the top of the analysis report with a mode-specific color scheme

## Visual Effect

The badge will appear like:
```
┌─────────────────────────────────────────────────────────┐
│ ┌───────┐                                               │
│ │ LORA  │ (with green background and bold text)        │
│ └───────┘                                               │
│                                                         │
│ Image Analysis                                          │
│ [rest of analysis...]                                   │
└─────────────────────────────────────────────────────────┘
```

## Testing

To verify the badge displays correctly:

1. Run the mode verification test:
   ```bash
   python3 test_mode_verification.py
   ```

2. For each mode (baseline, rag, lora), check the analysis output:
   - The colored badge should appear at the top
   - Each mode should have its designated color
   - The text should be uppercase

3. Check iOS app when connected:
   - The badge should display in the analysis view
   - Different colors indicate different modes

## Color Scheme Reference

| Mode | Color | Hex Value | Meaning |
|------|-------|-----------|---------|
| BASELINE | Blue | #3d5a80 | Standard analysis |
| RAG | Brown | #5a4a3d | RAG comparison mode |
| LORA | Green | #3d5a3d | Fine-tuned model |
| AB_TEST | Purple | #5a3d5a | A/B testing |

## Backward Compatibility

- The `mode` parameter is optional (defaults to None)
- If no mode is provided, no badge will display
- All existing calls to `json_to_html()` remain compatible
- The badge is purely additive - doesn't affect existing analysis content

## Next Steps

1. Restart services: `./mondrian.sh --restart`
2. Test with the mode verification script: `python3 test_mode_verification.py`
3. Check iOS app for badge display in analysis results
4. Verify each mode shows the correct color badge
