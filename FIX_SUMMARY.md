# Mondrian LLM Output Issue - Summary

## Problem Identified

The qwen3-vl:4b model is **NOT following the system prompt** and is generating its own output format instead.

### Root Cause

1. **System Prompt**: Asks for JSON format with specific structure
2. **Model Behavior**: Ignores prompt and generates HTML tables with ratings/scores
3. **Result**: AI Advisor Service gets HTML instead of expected JSON, leading to 500 errors

### Evidence

- **Test 1 (File: analysis-ansel-dbeaedcf...)**: LLM returned JSON wrapped in markdown code blocks with thinking tags
- **Test 2 (File: analysis-ansel-diagnostic-test.md)**: LLM completely ignored JSON prompt and returned HTML table with scores

## Solution Implemented

### Changes Made

1. **Created JSON-to-HTML Converter** in [ai_advisor_service_v1.13.py](mondrian/ai_advisor_service_v1.13.py)
   - Lines 562-647: Functions to extract JSON and convert to HTML
   - Handles both JSON array and object formats
   - Strips markdown code blocks and thinking tags
   - Fallback to pass-through if HTML detected

2. **Result**: Service now returns HTTP 200 instead of 500 ✅

### Current Status

✅ **FIXED**: HTTP 500 errors eliminated
⚠️ **ISSUE**: Model still not following prompts reliably
✅ **WORKING**: JSON-to-HTML conversion works when model returns JSON
❌ **PROBLEM**: Model sometimes returns HTML tables instead of JSON

## Test Results

### Diagnostic Test Output

```
Response Status: 200 ✅
Response Content-Type: text/html; charset=utf-8 ✅
```

The service successfully returns HTML to the client, eliminating the 500 error.

## Recommendations

### Option 1: Accept Current Solution (Recommended for Now)
- ✅ No more 500 errors
- ✅ Works with both JSON and HTML-table outputs
- ⚠️ Output format inconsistent

### Option 2: Switch Models
Try a better instruction-following model:
- llama3.2-vision
- llava:13b
- bakllava

### Option 3: Improve Prompt Engineering
- Add more explicit instructions
- Include example outputs
- Use few-shot prompting

### Option 4: Add Output Format Validation
- Parse HTML tables and convert to our format
- Normalize all outputs to consistent structure

## Files Changed

1. **mondrian/ai_advisor_service_v1.13.py** - Added JSON extraction and HTML conversion
2. **mondrian/prompts/system_html.md** - Created (but model ignores it)
3. **mondrian/prompts/system_json_backup.md** - Backup of original prompt
4. **update_system_prompt.py** - Tool for updating system prompt in database

## Next Steps

1. **Test end-to-end** through iOS app to verify full workflow works
2. **Monitor** which format the model prefers (JSON vs HTML tables)
3. **Consider** switching to a more reliable vision model
4. **Document** expected output formats for debugging

## Code Review vs Usage Guide

### ✅ Compliance with Usage Guide

| Feature | Usage Guide | Implementation | Status |
|---------|-------------|----------------|--------|
| POST /upload | ✅ Documented | ✅ Working | ✅ |
| SSE /stream | ✅ Documented | ✅ Working | ✅ |
| GET /analysis | Returns HTML | Returns HTML | ✅ |
| GET /llm-outputs | Returns JSON | Would work if model followed prompt | ⚠️ |
| Progress tracking | 0-100% | Implemented | ✅ |
| Status phases | Defined | Implemented | ✅ |

### Summary

The code **follows the usage guide correctly**. The issue is **LLM instruction-following**, not code architecture. The system is now resilient to model output variations.
