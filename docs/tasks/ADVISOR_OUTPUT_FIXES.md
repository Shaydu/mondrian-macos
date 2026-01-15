# Advisor Output View Fixes

## Summary
Fixed 4 bugs in the detailed advisor output view to improve clarity and production compatibility.

## Changes Made

### 1. Reference Titles - Show Title + Year Only
**Location:** `mondrian/json_to_html_converter.py` lines 364-377, 501-515

**Before:**
- `Reference #1: ansel-old-faithful-geyser-1944.png (Composition)`
- Showed filename and dimension name in parentheses

**After:**
- `Reference #1: Old Faithful Geyser 1944`
- Shows clean title and year only

**Implementation:**
- Removed dimension name from inline reference text
- Removed extra parentheses and commas
- Kept format simple: `Reference #{i}: {title} {year}`

### 2. Reference Images - Production-Compatible URLs
**Location:** 
- `mondrian/json_to_html_converter.py` lines 515-565
- `mondrian/job_service_v2.3.py` new endpoint at line 270

**Before:**
- Hardcoded `http://localhost:5100/advisor_artwork/...` URLs
- Broke when deployed or when services run on different ports
- Images failed to load with flickering placeholders

**After:**
- Uses relative API path: `/api/reference-image/{filename}`
- Works in development and production (Vercel)
- New endpoint searches `source/advisor/` subdirectories automatically

**New Endpoint:**
```python
@app.route("/api/reference-image/<path:filename>")
def serve_reference_image(filename):
    """Serve reference images from source/advisor directory"""
```

### 3. Dimensional Scores - Simplified Display
**Location:** `mondrian/json_to_html_converter.py` lines 555-580

**Before:**
```
• Composition: Your 8.0 / Ref 10.0 ↑+2.0
• Lighting: Your 7.0 / Ref 10.0 ↑+3.0
```

**After:**
```
• Composition: 8.0 / 10.0
• Lighting: 7.0 / 10.0
```

**Changes:**
- Removed "Your" and "Ref" labels
- Removed arrow symbols (↑↓)
- Removed delta values (+2.0, +3.0)
- Clean format: `{user_score} / {ref_score}`

### 4. Section Headers - Removed Duplication
**Location:** `mondrian/json_to_html_converter.py` lines 246-260, 412-422

**Before:**
- Had two section headers:
  1. "Dimensional Comparison with {Advisor}'s Portfolio"  
  2. "Detailed Dimensional Analysis & Improvement Guide"

**After:**
- Single section: **"Advisor Analysis"**
- Kept the descriptive subtext: "Each dimension is analyzed with specific feedback..."
- Removed redundant "Dimensional Comparison" section

## Debug Instrumentation

Added comprehensive debug logging to track:
- **Hypothesis A**: Reference title generation (inline and gallery)
- **Hypothesis B**: Image URL conversion (absolute → relative)
- **Hypothesis C**: Dimensional score formatting
- **Hypothesis D**: Section header rendering

Logs write to: `/Users/shaydu/dev/mondrian-macos/.cursor/debug.log`

## Testing

Run test script:
```bash
python3 test_advisor_fixes.py
```

Manual verification:
1. Submit new analysis job with RAG enabled
2. Check HTML output at `/api/jobs/{job_id}/status`
3. Verify:
   - ✓ Reference titles show clean "Title Year" format
   - ✓ Reference images load without flickering
   - ✓ Dimensional scores show simple "X / Y" format
   - ✓ Only one "Advisor Analysis" section exists

## Files Modified

1. `mondrian/json_to_html_converter.py` - Core HTML generation fixes
2. `mondrian/job_service_v2.3.py` - New `/api/reference-image` endpoint
3. `test_advisor_fixes.py` - Test script (new)

## Production Deployment

The new `/api/reference-image/<filename>` endpoint:
- Works with relative URLs (no hardcoded hosts)
- Compatible with Vercel serverless functions
- Automatically searches advisor subdirectories
- Includes proper CORS headers for cross-origin requests
- Implements 24-hour caching for performance

## Next Steps

1. Test with a real analysis job
2. Verify reference images load in browser
3. Check formatting in both dark and light themes
4. If successful, remove debug instrumentation
