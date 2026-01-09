# Root Cause Analysis: "Analysis Completing Too Quickly"

## Problem
The analysis completes very quickly (5% → 90% → 100% in seconds) but returns an error: "Failed to parse model response. Please try again."

## Root Cause

The analysis is **failing** due to a `KeyError: 'model_type'` in the MLX model call. Here's what's happening:

1. **Model Call**: `run_model_mlx()` calls the MLX vision model
2. **apply_chat_template Error**: When calling `apply_chat_template()`, it's passed an empty dict `{}` instead of a config with `model_type`
3. **KeyError**: `apply_chat_template()` tries to access `config['model_type']` but the key doesn't exist in the empty dict
4. **Error Returned**: The function catches the exception and returns `"# ERROR: MLX inference failed: 'model_type'"`
5. **Parsing Failure**: `parse_json_response()` tries to parse this error message as JSON and fails
6. **Error HTML Returned**: The service returns error HTML with HTTP 200 status
7. **Job Marked Complete**: The job service treats the 200 response as success and completes the job immediately

### Actual Error
```
# ERROR: MLX inference failed: 'model_type'
```

This is a 43-character error message, not actual JSON model output.

## Why It's "Too Fast"

The job completes quickly because:
- The model call either fails immediately OR
- The model returns a very short/invalid response that fails JSON parsing
- The error is returned immediately (no actual analysis happens)
- The job service sees HTTP 200 and marks it complete

## Evidence

- HTML output shows: `<div class="analysis"><h2>Error</h2><p>Failed to parse model response. Please try again.</p></div>`
- Job completes in seconds instead of minutes
- No actual analysis content is generated

## Fixes Applied

### 1. Fixed apply_chat_template Config Issue
- **Root cause fix**: Now extracts config from `model.config` or `processor.config` instead of passing empty dict `{}`
- Infers `model_type` from model name if not present (e.g., `qwen2_vl`, `qwen3_vl`)
- Added fallback to empty dict if config inference fails (for backward compatibility)
- Enhanced logging to show config type, keys, and whether `model_type` is present

### 2. Enhanced Error Logging
- Logs the full raw model response when JSON parsing fails
- Saves raw response to debug file: `analysis_md/error-response-{advisor}-{job_id}.txt`
- Shows first 1000 and last 500 chars of response in logs

### 3. Better Model Response Inspection
- Logs response type and length
- Checks if response starts with JSON structure
- Warns if response doesn't look like JSON

### 4. Improved Error Detection
- Detects error responses from model (starts with "ERROR:" or contains "error")
- Saves error responses to separate debug files
- More detailed error messages in HTML output
- Wraps `apply_chat_template` in try-except with fallback

## Next Steps to Diagnose

1. **Check Debug Files**: After running a test, check:
   - `mondrian/analysis_md/error-response-ansel-{job_id}.txt` - Raw model response
   - `mondrian/analysis_md/error-ansel-{job_id}.txt` - Error responses

2. **Check Logs**: Look for:
   - `[ERROR] Could not parse JSON response from model`
   - `[ERROR] Raw response (first 1000 chars):`
   - `[WARN] Response does NOT start with JSON structure`

3. **Possible Issues**:
   - Model is hitting token limit and cutting off
   - Model is returning error messages instead of JSON
   - Model is not following the JSON format instructions in the system prompt
   - Model call is failing and returning exception text

## How to Test

Run the test again:
```bash
python test_ios_e2e_rag_comparison.py
```

Then check:
1. The console output for detailed error logs
2. `mondrian/analysis_md/error-response-*.txt` files
3. The actual model response to see why JSON parsing is failing

## Expected Behavior After Fix

- More detailed error messages in logs
- Debug files saved for inspection
- Better visibility into what the model is actually returning
- Ability to identify if the issue is:
  - Model not following JSON format
  - Model hitting token limits
  - Model returning errors
  - Model call failing

