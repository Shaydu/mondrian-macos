# Citation Fix Implementation - Complete

## Summary

Fixed the missing reference images and advisor quotes in both streaming and non-streaming endpoints of the AI Advisor service. The system now properly retrieves, validates, and displays citations with **strict error handling** and **no silent fallbacks**.

## What Was Fixed

### 1. **Configuration**
- Added `ENABLE_CITATIONS = True` constant at the top of [ai_advisor_service_linux.py](mondrian/ai_advisor_service_linux.py#L68)
- Can be set to `False` to disable citation retrieval system-wide

### 2. **Citation Retrieval - Strict Error Handling**
Both endpoints now have identical citation retrieval with **no silent fallbacks**:

**Non-streaming endpoint** ([lines 899-924](mondrian/ai_advisor_service_linux.py#L899-L924)):
- Retrieves 10 reference images via `get_top_reference_images()`
- Retrieves 6 book passages via `get_top_book_passages()`
- Raises `RuntimeError` if retrieval fails or returns None
- Raises `RuntimeError` if ENABLE_CITATIONS is True but retrieval fails

**Streaming endpoint** ([lines 1796-1824](mondrian/ai_advisor_service_linux.py#L1796-L1824)):
- Identical retrieval logic to non-streaming
- Same strict error handling - **no silent fallbacks**
- All failures raise exceptions immediately

### 3. **HTML Generation in Streaming Endpoint**
Added complete HTML generation to streaming endpoint ([lines 2007-2034](mondrian/ai_advisor_service_linux.py#L2007-L2034)):

```python
# Generate HTML outputs with strict error handling
analysis_html = advisor._generate_ios_detailed_html(...)
if not analysis_html:
    raise RuntimeError("_generate_ios_detailed_html returned empty string")

summary_html = generate_summary_html(...)
if not summary_html:
    raise RuntimeError("generate_summary_html returned empty string")

advisor_bio_html = generate_advisor_bio_html(...)
if not advisor_bio_html:
    raise RuntimeError("generate_advisor_bio_html returned empty string")
```

### 4. **Case Studies Computation in Streaming**
Added case studies computation to streaming endpoint ([lines 1975-2006](mondrian/ai_advisor_service_linux.py#L1975-L2006)):
- Computes 3 case studies based on weak dimensions
- Uses visual relevance filtering when user image is available
- Falls back to gap-only selection when no user image
- Raises `RuntimeError` if computation fails or returns None

### 5. **Enhanced Result Structure**
Streaming endpoint now returns complete result matching non-streaming ([lines 2043-2055](mondrian/ai_advisor_service_linux.py#L2043-L2055)):
```python
result.update({
    'analysis_html': analysis_html,      # HTML with citations
    'summary_html': summary_html,         # Top 3 recommendations
    'advisor_bio_html': advisor_bio_html, # Advisor bio
    'summary': summary,                   # Text summary
    'advisor_bio': advisor_bio,           # Text bio
    'overall_score': overall_score,       # Numeric score
    'advisor': advisor_name,
    'mode': mode_str,
    'timestamp': datetime.now().isoformat()
})
```

## Citation Flow (End-to-End)

### Stage 1: Retrieval
```python
# Both endpoints - with strict error handling
if ENABLE_CITATIONS:
    reference_images = get_top_reference_images(DB_PATH, advisor, max_total=10)
    if reference_images is None:
        raise RuntimeError("get_top_reference_images returned None")
    
    book_passages = get_top_book_passages(advisor_id=advisor, max_passages=6)
    if book_passages is None:
        raise RuntimeError("get_top_book_passages returned None")
```

### Stage 2: Prompt Building
```python
# Build RAG prompt with citation IDs
prompt = advisor._build_rag_prompt(prompt, reference_images, book_passages)
# Adds: IMG_1, IMG_2, ..., IMG_10 (reference images)
#       QUOTE_1, QUOTE_2, ..., QUOTE_6 (book passages)
```

### Stage 3: LLM Generation
LLM analyzes image and returns JSON with optional citations:
```json
{
  "dimensions": [
    {
      "name": "Composition",
      "score": 7,
      "comment": "...",
      "recommendation": "...",
      "case_study_id": "IMG_1"  ← LLM cites reference image
    },
    {
      "name": "Lighting",
      "score": 5,
      "comment": "...",
      "recommendation": "...",
      "quote_id": "QUOTE_2"  ← LLM cites book passage
    }
  ]
}
```

### Stage 4: Citation Validation
```python
# _parse_response validates citations ([lines 1407-1463](mondrian/ai_advisor_service_linux.py#L1407-L1463))
for dim in dimensions:
    if 'case_study_id' in dim:
        img_id = dim['case_study_id']
        # Validate: not duplicate, exists in candidates, under limit
        if valid:
            dim['_cited_image'] = img_lookup[img_id]  # Attach full data
    
    if 'quote_id' in dim:
        quote_id = dim['quote_id']
        # Validate: not duplicate, exists in candidates, under limit
        if valid:
            dim['_cited_quote'] = quote_lookup[quote_id]  # Attach full data
```

### Stage 5: HTML Rendering
```python
# _generate_ios_detailed_html renders citations ([lines 1281-1313](mondrian/ai_advisor_service_linux.py#L1281-L1313))
for dim in dimensions:
    cited_image = dim.get('_cited_image')
    if cited_image:
        image_citation_html = generate_reference_image_html(
            ref_image=cited_image,
            dimension_name=name
        )
        # Renders case study box with base64 image, instructive text, metadata
    
    cited_quote = dim.get('_cited_quote')
    if cited_quote:
        quote_citation_html = generate_advisor_quote_box(...)
        # Renders quote box with truncated text, book title
```

## Error Handling Philosophy

**NO SILENT FALLBACKS** - All failures raise exceptions:

1. **Citation Retrieval**
   - `RuntimeError` if `get_top_reference_images()` returns None
   - `RuntimeError` if `get_top_book_passages()` returns None
   - `RuntimeError` if retrieval raises exception

2. **Case Studies Computation**
   - `RuntimeError` if `compute_case_studies()` returns None
   - `RuntimeError` if computation raises exception

3. **HTML Generation**
   - `RuntimeError` if any HTML generation returns empty string
   - `RuntimeError` if HTML generation raises exception

4. **Streaming Error Propagation**
   - All errors are caught and sent as SSE error events
   - Client receives detailed error messages
   - No partial results - either complete success or clear failure

## Configuration

To disable citations system-wide:
```python
# In mondrian/ai_advisor_service_linux.py line 68
ENABLE_CITATIONS = False  # Disables retrieval and display
```

When disabled:
- Reference images and book passages are not retrieved
- LLM prompt does not include citations
- HTML generation works but without citations
- No performance impact from embedding lookups

## Verification

Run the verification script:
```bash
python3 verify_citations_simple.py
```

Expected output:
```
✓ ENABLE_CITATIONS constant found and set to True
✓ Reference image retrieval
✓ Book passage retrieval
✓ None check for images
✓ None check for passages
✓ RuntimeError for images
✓ RuntimeError for passages
✓ Image citation validation
✓ Quote citation validation
✓ ALL CHECKS PASSED
```

## Database Requirements

Ensure these tables have data:
1. **dimensional_profiles** - Reference images with embeddings and instructive text
2. **book_passages** - Advisor quotes with embeddings and dimension tags

Check data:
```sql
SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel';
SELECT COUNT(*) FROM book_passages WHERE advisor_id='ansel';
```

## Testing

### Manual Test
1. Start services:
   ```bash
   python mondrian/job_service_v2.3.py  # Terminal 1
   python mondrian/ai_advisor_service.py  # Terminal 2
   ```

2. Submit an image for analysis via iOS app or API

3. Check logs for:
   ```
   [Stream] Retrieved 10 reference image candidates
   [Stream] Retrieved 6 quote candidates
   ✓ Valid image citation: IMG_1 in Composition
   ✓ Valid quote citation: QUOTE_2 in Lighting
   [Stream] ✓ Complete result with HTML generated: 8 dimensions, score=6.5
   ```

4. Verify HTML output includes:
   - Case study boxes with embedded images
   - Advisor quote boxes with passages
   - Instructive text explaining why image is relevant

### Expected Output Format

**Case Study Box:**
```html
<div class="reference-citation">
  <div class="case-study-box">
    <div class="case-study-title">Case Study: Moonrise, Hernandez (1941)</div>
    <img src="data:image/jpeg;base64,..." class="case-study-image" />
    <div class="case-study-metadata">
      <strong>Focus On:</strong> Three-plane depth with foreground anchor<br/>
      <strong>Location:</strong> New Mexico<br/>
      <strong>Reference Score:</strong> 9.5/10 in Composition
    </div>
  </div>
</div>
```

**Advisor Quote Box:**
```html
<div class="advisor-quote-box">
  <div class="advisor-quote-title">Advisor Insight</div>
  <div class="advisor-quote-text">"Visualize the result before exposing..."</div>
  <div class="advisor-quote-source"><strong>From:</strong> The Negative</div>
</div>
```

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `mondrian/ai_advisor_service_linux.py` | 68 | Added ENABLE_CITATIONS constant |
| `mondrian/ai_advisor_service_linux.py` | 899-924 | Strict error handling for non-streaming citations |
| `mondrian/ai_advisor_service_linux.py` | 1796-1824 | Strict error handling for streaming citations |
| `mondrian/ai_advisor_service_linux.py` | 1975-2006 | Added case studies computation to streaming |
| `mondrian/ai_advisor_service_linux.py` | 2007-2034 | Added HTML generation to streaming |
| `mondrian/ai_advisor_service_linux.py` | 2043-2055 | Enhanced streaming result structure |

## Status

✅ **IMPLEMENTATION COMPLETE**

Both streaming and non-streaming endpoints now:
1. ✅ Retrieve reference images and book passages (with ENABLE_CITATIONS check)
2. ✅ Pass citations to LLM in augmented prompt
3. ✅ Validate LLM-generated citations
4. ✅ Compute case studies for weak dimensions
5. ✅ Generate HTML with case study boxes and quote boxes
6. ✅ Return complete result structure to client
7. ✅ Raise exceptions on all failures - NO SILENT FALLBACKS
8. ✅ Support enable/disable via ENABLE_CITATIONS constant

Reference images and advisor quotes are now fully functional with strict error handling!
