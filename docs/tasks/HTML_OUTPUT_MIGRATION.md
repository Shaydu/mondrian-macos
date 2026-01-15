# HTML Output Migration - Complete

## Summary

Successfully migrated the Mondrian photography analysis system from JSON output to HTML output. This change eliminates complex JSON parsing/validation and provides more reliable results for iOS rendering.

## What Changed

### 1. System Prompt (`mondrian/prompts/system.md`)
**Before:** Asked LLM to output JSON with strict structure
**After:** Asks LLM to output clean HTML with table structure

**Key Changes:**
- ✅ Direct HTML output instead of JSON
- ✅ Simplified structure with fewer parsing requirements
- ✅ Table-based feedback display (8 dimensions)
- ✅ Overall grade calculation as average
- ✅ Clear formatting rules to prevent LLM confusion

### 2. AI Advisor Service (`mondrian/ai_advisor_service_v1.13.py`)
**Before:** 200+ lines of JSON extraction, validation, and repair logic
**After:** Simple HTML validation and passthrough

**Removed Functions:**
- `extract_json_from_llm_output()` - No longer needed
- `validate_and_repair_feedback()` - No longer needed
- `convert_json_to_html()` - Moved to job service, then removed

**Simplified Logic:**
```python
# Old: Complex JSON extraction → validation → repair → conversion
# New: Simple HTML validation → passthrough
html_output = md.strip()
if not ("<" in html_output and ">" in html_output):
    return error_response
return Response(complete_html, mimetype="text/html")
```

### 3. Job Service (`mondrian/job_service_v2.3.py`)
**Before:** Received JSON, converted to HTML for display
**After:** Receives HTML directly, wraps in advisor sections

**Removed Functions:**
- `convert_json_to_html()` - No longer needed

**Updated Logic:**
```python
# Old: llm_output (JSON) → convert_json_to_html() → display
# New: llm_output (HTML) → wrap in div → display
html_output = llm_output.strip()
advisor_html = f'<div class="advisor-section">{html_output}</div>'
```

### 4. CSS Styling (`mondrian/analysis/styles.css`)
**New file** - Professional styling for iOS display

**Features:**
- iOS-native fonts and design
- Responsive mobile layout
- Dark mode support
- Beautiful table styling
- Proper spacing and colors

## Expected Output Format

### HTML Structure
```html
<div class="advisor-header">
  <h1>Ansel Adams</h1>
  <p class="years">1902-1984</p>
  <p class="bio">Famous for black-and-white landscape photography.</p>
</div>

<div class="analysis">
  <h2>Image Analysis</h2>
  <p>[Description of the photograph]</p>
  
  <h2>Detailed Feedback</h2>
  <table>
    <thead>
      <tr><th>Dimension</th><th>Grade</th><th>Comment</th><th>Suggestion</th></tr>
    </thead>
    <tbody>
      <tr><td>Composition</td><td>9/10</td><td>...</td><td>...</td></tr>
      <tr><td>Lighting</td><td>8/10</td><td>...</td><td>...</td></tr>
      <!-- 6 more dimensions -->
    </tbody>
  </table>
  
  <h2>Overall Grade</h2>
  <p class="overall-grade"><strong>8.1/10</strong></p>
  <p class="grade-note">(Average of all dimension scores)</p>
</div>
```

## Benefits

### ✅ Reliability
- **No more JSON parsing errors** - LLMs generate HTML more consistently
- **Simpler error handling** - Just check for HTML tags
- **Fewer failure points** - Removed 200+ lines of error-prone code

### ✅ Maintainability
- **Less code to maintain** - Removed complex extraction logic
- **Easier debugging** - HTML output is human-readable
- **Clearer flow** - LLM → HTML → Display

### ✅ iOS Compatibility
- **Native display** - WKWebView handles HTML perfectly
- **Better formatting** - CSS provides professional styling
- **Dark mode support** - Automatic dark mode handling
- **Responsive design** - Mobile-optimized layout

## Testing

### Manual Test
```bash
# 1. Start services (in mondrian directory)
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 start_services.py

# 2. Upload an image via iOS app or API
curl -X POST http://localhost:5005/upload \
  -F "image=@/path/to/test-image.jpg" \
  -F "advisor=ansel" \
  -F "auto_analyze=true"

# 3. Check the job status
curl http://localhost:5005/status/{job_id}

# 4. Get the analysis HTML
curl http://localhost:5005/analysis/{job_id}
```

### Verify Output
- ✅ HTML contains advisor name, bio, years
- ✅ Table has all 8 feedback dimensions
- ✅ Each dimension has grade, comment, suggestion
- ✅ Overall grade is calculated correctly
- ✅ No JSON artifacts in output
- ✅ iOS app displays HTML correctly

## Migration Checklist

- [x] Update system prompt to HTML format
- [x] Migrate prompt to database (via `migrate_system_prompt.py`)
- [x] Remove JSON extraction functions from AI advisor service
- [x] Simplify AI advisor service response handling
- [x] Remove JSON conversion from job service
- [x] Update job service to handle HTML directly
- [x] Add CSS styling for iOS display
- [x] Document changes
- [x] **FIX: Run migration on mondrian.db (was not run initially!)**
- [x] **FIX: Consolidate to single mondrian.db database**
- [x] **FIX: Update all service defaults from jobs.db to mondrian.db**
- [x] **FIX: Remove old jobs.db to prevent confusion**

## Rollback Plan

If issues arise, revert these files to their previous versions:

1. `mondrian/prompts/system.md` - Revert to JSON instructions
2. `mondrian/ai_advisor_service_v1.13.py` - Restore JSON parsing functions
3. `mondrian/job_service_v2.3.py` - Restore `convert_json_to_html()` function
4. Run `python3 migrate_system_prompt.py` to update database

## iOS App Integration

The iOS app should work **without changes** because:
- Same endpoint: `GET /analysis/{job_id}`
- Same response type: `text/html`
- WKWebView displays HTML natively

**Optional Enhancement:**
Add CSS link in iOS app:
```swift
let htmlWithCSS = """
<link rel="stylesheet" href="http://localhost:5005/styles.css">
\(htmlContent)
"""
webView.loadHTMLString(htmlWithCSS, baseURL: nil)
```

## Next Steps

1. **Test thoroughly** - Run several analyses with different images
2. **Monitor errors** - Check logs for any HTML validation issues
3. **Gather feedback** - Ensure iOS app displays correctly
4. **Iterate on CSS** - Adjust styling based on iOS rendering
5. **Update documentation** - Document any edge cases found

## Support

If LLM output is malformed:
- Check `mondrian/analysis_md/` for raw outputs
- Enable debug mode: `--debug` flag on services
- Review prompt in database: `SELECT * FROM config WHERE key='system_prompt'`

## Performance

Expected improvements:
- **Faster processing** - Less string manipulation
- **Lower error rate** - Simpler validation
- **Smaller codebase** - ~200 lines removed
- **Better UX** - Cleaner HTML output

---

**Migration completed:** December 18, 2025
**Version:** v1.14 (HTML Output)
**Status:** ✅ Ready for testing
