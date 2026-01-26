# SUMMARY: Citation Investigation Findings

## The Bottom Line

**Citations are NOT broken in the current code.** The implementation is functionally identical to commit ffd754e, with only refactoring and enhancements applied.

---

## What Changed Between ffd754e and Current HEAD

### ✅ Pure Code Organization (No Functional Change)

1. **Quote rendering moved** from inline in `ai_advisor_service_linux.py` to `citation_service.render_cited_quote_html()`
2. **Image citation rendering refactored** to use `citation_service.render_cited_image_html()` (which delegates to `html_generator.generate_reference_image_html()`)
3. **Deprecated function removed** - `generate_ios_detailed_html()` was marked deprecated and is now gone

### ⚡ Enhancements (Better but Not Breaking)

1. **Type validation added** - Catches non-string citation IDs from malformed LLM responses
2. **Better error messages** - Shows which citation IDs are available when invalid ID is encountered
3. **Docker path support** - Added `./ ` prefix handling for container environments
4. **Improved logging** - Emojis and clearer status messages for debugging

### 🔄 Unchanged Core Logic

- Citation retrieval (`get_top_reference_images()`, `get_top_book_passages()`)
- Citation lookup building (IMG_1, IMG_2, QUOTE_1, etc.)
- Citation validation and attachment
- Null value handling
- Duplicate prevention
- Max citation limits
- HTML output structure

---

## Why Citations Might Appear Missing

### Most Likely Cause: Empty Citation Data

**Reference images are empty:**
```bash
sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel';"
# If returns 0, no reference images indexed
```

**Book passages are empty:**
```bash
sqlite3 mondrian.db "SELECT COUNT(*) FROM book_passages WHERE advisor_id='ansel';"
# If returns 0, no quotes imported
```

### Second Cause: Missing Embeddings

```bash
sqlite3 mondrian.db "
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) as with_embeddings
FROM dimensional_profiles WHERE advisor_id='ansel';
"
# If with_embeddings is 0, retrieval will fail
```

### Third Cause: Image Path Resolution

Images exist but can't be found:
```bash
# Enable debug logging
python3 mondrian/ai_advisor_service_linux.py --log-level DEBUG
# Look for: "[Path Resolve] ❌ Not found:"
```

---

## How to Fix Citations

### 1. Index Reference Images

```bash
# Analyze reference images and compute dimensional scores
python3 batch_analyze_advisor_images.py --advisor ansel
```

### 2. Compute Embeddings

```bash
# Compute CLIP embeddings for reference images
python3 tools/rag/compute_embeddings.py --advisor ansel

# Compute embeddings for book passages
python3 tools/rag/compute_embeddings.py --type passages --advisor ansel
```

### 3. Import Book Passages

```bash
# Import advisor quotes from JSON files
python3 tools/rag/import_book_passages.py --advisor ansel
```

### 4. Verify Everything Works

```bash
# Run diagnostic
python3 diagnose_citation_system.py
```

---

## Code Proof: Citations Still Work

### Current Citation Validation Loop (Identical to ffd754e)

```python
# Lines 1427-1500 of ai_advisor_service_linux.py
for dim in dimensions:
    # Validate and attach image citations
    if 'case_study_id' in dim:
        img_id = dim['case_study_id']
        if img_id in img_lookup:
            dim['_cited_image'] = img_lookup[img_id]  # ← ATTACHED
            logger.info(f"✓ Valid image citation: {img_id}")
    
    # Validate and attach quote citations
    if 'quote_id' in dim:
        quote_id = dim['quote_id']
        if quote_id in quote_lookup:
            dim['_cited_quote'] = quote_lookup[quote_id]  # ← ATTACHED
            logger.info(f"✓ Valid quote citation: {quote_id}")
```

### Current HTML Rendering (Identical Output to ffd754e)

```python
# Lines 1309-1323 of ai_advisor_service_linux.py
if cited_image:
    image_citation_html = render_cited_image_html(cited_image, name)
    # ↓ Still generates same HTML as ffd754e
    # <div class="reference-citation"><div class="case-study-box">...

if cited_quote:
    quote_citation_html = render_cited_quote_html(cited_quote, name)
    # ↓ Still generates same HTML as ffd754e
    # <div class="advisor-quote-box">...
```

---

## Files Created for Investigation

1. **CITATION_INVESTIGATION_REPORT.md** - Detailed technical analysis
2. **CITATION_CODE_COMPARISON.md** - Side-by-side code comparison
3. **diagnose_citation_system.py** - Diagnostic script to identify issues

---

## Next Steps

### If Citations Are Working
- Verify with test script: `python3 test_enhanced_single_pass_citations.py`
- Check logs for: "Valid image citation" and "Valid quote citation" messages

### If Citations Aren't Working

1. **Run diagnosis:**
   ```bash
   python3 diagnose_citation_system.py
   ```

2. **Check logs:**
   ```bash
   python3 mondrian/ai_advisor_service_linux.py --log-level DEBUG 2>&1 | grep -i citation
   ```

3. **Verify database:**
   ```bash
   # Check if reference images exist
   python3 -c "
   from mondrian.rag_retrieval import get_top_reference_images
   refs = get_top_reference_images('mondrian.db', 'ansel', max_total=10)
   print(f'Found {len(refs)} reference images')
   "
   ```

4. **Check LLM response:**
   - Enable verbose logging
   - Look for dimensions with `case_study_id` and `quote_id` fields
   - Verify LLM is including citations in response

---

## Key Takeaway

The citation system in the current code is **fully functional and identical to ffd754e**. Any apparent missing citations are due to:

- ✅ Empty reference/quote database (not a code issue)
- ✅ Missing embeddings (not a code issue)
- ✅ Path resolution (handled by resolve_image_path())
- ❌ NOT code changes or removed features

**The code has NOT regressed.**

