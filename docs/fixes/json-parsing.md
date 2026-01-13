# JSON Parsing Fix for RAG Workflow

**Date:** 2026-01-13  
**Status:** Implemented  
**Priority:** Critical  

## Problem

The RAG workflow was producing empty "Top 3 Recommendations" summaries and error HTML instead of proper analysis feedback cards. Root cause: MLX model output with malformed JSON containing extra closing braces.

## Root Cause Analysis

### Model Output Pattern

The MLX model wraps JSON responses in markdown code blocks AND adds extra closing braces:

```
```json
{
  "image_description": "...",
  "dimensions": [...],
  "overall_score": 7.4,
  "technical_notes": "..."
  }     ← First closing brace (correct)
}       ← Extra closing brace (malformed!)
```
```

### Parsing Failure Chain

1. **Pass 2 Analysis**: Model returns JSON with markdown and extra brace
2. **parse_json_response()**: Strategies 1-3 fail on this pattern
3. **JSON parsing returns None**: Error HTML generated instead
4. **No feedback-card elements**: HTML has no dimensions/recommendations
5. **extract_critical_recommendations()**: Finds nothing to extract
6. **Summary is empty**: "Top 3 Recommendations" section has no items

### Evidence

From test run `ios_e2e_rag-enabled_20260113_063632`:
- `analysis_detailed.html` shows error: "Failed to parse model response. The model returned 2928 characters that could not be parsed as JSON."
- `analysis_summary.html` is empty (no recommendation items)
- Debug file shows JSON with `}\n}` pattern at end

## Solution

Enhanced `parse_json_response()` function in `mondrian/json_to_html_converter.py` with two additional recovery strategies:

### Strategy 2.5: Strip Trailing Extra Braces

After markdown stripping, remove extra closing braces at end of JSON:

```python
# Strategy 2.5: Strip trailing extra braces
cleaned_extra = re.sub(r'\}\s*\}+\s*$', '}', cleaned)
if cleaned_extra != cleaned:
    try:
        result = json.loads(cleaned_extra)
        print(f"[JSON PARSER] Strategy 2.5 (strip extra braces) succeeded")
        return result
    except json.JSONDecodeError:
        pass
```

**Why it works:** The regex `r'\}\s*\}+\s*$'` matches one or more closing braces at the end with optional whitespace, replacing them with a single closing brace.

### Strategy 4: Regex Extraction of Outermost JSON

If all strategies fail, extract valid JSON using regex:

```python
# Strategy 4: Regex extraction of outermost JSON object
match = re.search(r'\{[\s\S]*\}', cleaned)
if match:
    try:
        result = json.loads(match.group(0))
        print(f"[JSON PARSER] Strategy 4 (regex extraction) succeeded")
        return result
    except json.JSONDecodeError:
        pass
```

**Why it works:** Finds the first `{` and last `}` in the response, extracting what should be valid JSON between them.

## Implementation Details

### Files Modified

| File | Changes |
|------|---------|
| `mondrian/json_to_html_converter.py` | Added Strategy 2.5 and Strategy 4 to `parse_json_response()` function (lines 32-65) |

### Strategy Execution Order

1. **Strategy 1**: Parse as-is (for well-formed responses)
2. **Strategy 2**: Strip markdown code blocks
3. **Strategy 2.5**: Strip trailing extra braces ✨ **NEW**
4. **Strategy 3**: Extract valid JSON prefix using `raw_decode()`
5. **Strategy 4**: Regex extraction of outermost JSON ✨ **NEW**

### Logging Improvements

Each strategy prints success/failure to logs:
- `[JSON PARSER] Strategy 2.5 (strip extra braces) succeeded`
- `[JSON PARSER] Strategy 4 (regex extraction) succeeded`
- Tracks which strategy recovers malformed responses

## Testing

### Before Fix
```
analysis_summary.html: Empty (no recommendations)
analysis_detailed.html: Error HTML (no feedback cards)
```

### After Fix
```
analysis_summary.html: Contains 3 recommendation items
analysis_detailed.html: Contains feedback-card elements with dimensions
Logs: Show which parsing strategy succeeded
```

### Test Command
```bash
python3 test/test_ios_e2e_rag_comparison.py --rag
```

### Expected Results
- Top 3 recommendations visible in summary
- Detailed analysis with feedback cards for each dimension
- Logs showing `[JSON PARSER] Strategy 2.5 (strip extra braces) succeeded` or similar

## Impact

- **RAG Workflow**: Now produces proper comparative analysis instead of errors
- **Summary Endpoints**: Returns meaningful recommendations
- **HTML Output**: Contains all dimension feedback and improvements
- **Robustness**: Multiple fallback strategies handle various JSON malformations

## Future Improvements

1. Consider adding JSON schema validation to catch issues earlier
2. Monitor which strategies succeed most frequently to optimize order
3. Consider requesting model output format compliance from LLM providers
4. Add metrics to track JSON parsing failures vs successes

## Related Files

- `mondrian/json_to_html_converter.py` - Contains `parse_json_response()` function
- `mondrian/ai_advisor_service.py` - Uses `parse_json_response()` in RAG Pass 1 & 2
- `test/test_ios_e2e_rag_comparison.py` - E2E test for RAG workflow
- `docs/architecture/data-flow.md` - Overall system architecture
