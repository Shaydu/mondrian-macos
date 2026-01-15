# 500 Error Fix Summary

## Problem Identified
The `/analyze` endpoint at `169.254.136.128:5100` was returning HTTP 500 errors.

### Root Cause
The system prompt stored in the database contained **markdown code blocks** (```) around the HTML example, which created a contradiction:

1. The prompt showed HTML **wrapped in markdown blocks**
2. But then instructed: "❌ NO markdown code blocks like ```html or ```"

This confused the LLM (qwen3-vl:4b), causing it to either:
- Wrap its HTML output in markdown blocks
- Return invalid/unparseable HTML
- Result in 500 errors when the AI service tried to process the response

### The Fix Applied

**File Modified:** `mondrian/prompts/system.md`

**Change:** Removed the markdown code block wrappers (```) around the HTML example, presenting it as plain HTML in the prompt.

**Before:**
```
Required HTML Structure (COPY THIS EXACT FORMAT):
```
<div class="analysis">
  ...
</div>
```
```

**After:**
```
Required HTML Structure (COPY THIS EXACT FORMAT):

<div class="analysis">
  ...
</div>
```

### Implementation Steps

1. ✅ Updated `mondrian/prompts/system.md` to remove markdown wrappers
2. ✅ Re-migrated prompt to database using `python3 mondrian/migrate_system_prompt.py`
3. ✅ Restarted AI Advisor Service to load the new prompt
4. ✅ Restarted Job Service
5. ⏳ Testing the `/analyze` endpoint to verify the fix

### Services Running

- **AI Advisor Service**: http://169.254.136.128:5100 (PID: 62588)
- **Job Service**: http://169.254.136.128:5005 (PID: 63063)
- **Model**: qwen3-vl:4b via Ollama

### Expected Result

The LLM should now return pure HTML output without markdown wrappers, allowing the AI service to parse and return it successfully with HTTP 200 status.

## Date
December 18, 2025, 4:37 PM MDT
