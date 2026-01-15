# LoRA Mode Fix - JSON Response Format Conversion

## Problem
LORA mode (and RAG, RAG+LORA modes) were completing but not producing summary/detailed output because the response parsing was failing to extract dimensional analysis and overall grades.

## Root Cause
The strategies were looking for `dimensional_analysis` dict and `overall_grade` fields directly, but the model's system prompt instructs it to output:
- A `dimensions` array (list) instead of `dimensional_analysis` dict
- An `overall_score` (numeric) instead of `overall_grade` (letter)

The **baseline strategy** had conversion logic to handle this (lines 105-118), but the **LoRA, RAG, and RAG+LORA strategies** were missing this critical conversion.

### What was happening:
1. Model generates response with `dimensions` array and `overall_score` numeric
2. Strategies try to get `dimensional_analysis` and `overall_grade` → get defaults (empty dict, "N/A")
3. HTML is generated with no content
4. `extract_critical_recommendations()` can't find any recommendations 
5. Summary endpoint returns empty/thinking-only response

## Solution
Added proper JSON response format conversion to all three strategies:

### For LoRA Strategy (`mondrian/strategies/lora.py`)
- Convert `dimensions` array → `dimensional_analysis` dict (keyed by dimension name)
- Convert `overall_score` (numeric) → `overall_grade` (letter grade)
- Added debug logging to help diagnose future issues

### For RAG Strategy (`mondrian/strategies/rag.py`)
- Same conversions as LoRA strategy
- Added debug logging

### For RAG+LORA Strategy (`mondrian/strategies/rag_lora.py`)
- Same conversions in Pass 2 analysis
- Added debug logging

## Conversion Details

### Dimensions Array to Dict
```python
# Input: {"dimensions": [{"name": "Composition", "score": 8, ...}, ...]}
# Output: {"dimensional_analysis": {"composition": {"score": 8, ...}, ...}}
```

Dimension names are converted to lowercase with underscores:
- "Composition" → "composition"
- "Focus & Sharpness" → "focus_and_sharpness"
- "Color Harmony" → "color_harmony"

### Overall Score to Grade
Numeric scores (0.0-10.0) are converted to letter grades:
- 9.5+ → A+
- 9.0+ → A
- 8.5+ → A-
- 8.0+ → B+
- 7.5+ → B
- 7.0+ → B-
- 6.5+ → C+
- 6.0+ → C
- 5.5+ → C-
- 5.0+ → D
- Below 5.0 → F

## Testing
After this fix, LORA mode should:
1. Successfully parse the model's JSON response
2. Extract dimensional analysis and overall grades
3. Generate complete HTML output with feedback cards
4. Extract critical recommendations for the summary
5. Display both detailed analysis and summary views

## Files Modified
- `mondrian/strategies/lora.py`
- `mondrian/strategies/rag.py`
- `mondrian/strategies/rag_lora.py`

## Related Files
- `mondrian/strategies/baseline.py` - Contains the original conversion logic (used as reference)
- `mondrian/json_to_html_converter.py` - Uses the converted dimensional_analysis format
