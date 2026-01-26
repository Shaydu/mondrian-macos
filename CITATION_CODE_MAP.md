# Citation System Code Map

Quick reference guide to where citations are handled in the codebase.

---

## Citation Flow Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER SUBMITS IMAGE                        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│         1. RETRIEVE REFERENCE DATA                           │
│  Files: rag_retrieval.py, embedding_retrieval.py            │
│  ├─ get_top_reference_images() → [IMG_1, IMG_2, ...]       │
│  └─ get_top_book_passages() → [QUOTE_1, QUOTE_2, ...]      │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│    2. SEND TO LLM WITH CITATION CONTEXT                     │
│  File: ai_advisor_service_linux.py                          │
│        _build_rag_prompt()                                  │
│  "You can cite IMG_1, IMG_2, ... and QUOTE_1, QUOTE_2, ..." │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  3. LLM RESPONSE WITH CITATIONS                             │
│  JSON: dimensions[].case_study_id = "IMG_1"                 │
│        dimensions[].quote_id = "QUOTE_2"                    │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│   4. VALIDATE CITATIONS                                     │
│  File: ai_advisor_service_linux.py                          │
│        Lines 1427-1500 (VALIDATE AND RESOLVE CITATIONS)     │
│  ├─ Is IMG_1 in lookup? → Attach dim['_cited_image']       │
│  └─ Is QUOTE_2 in lookup? → Attach dim['_cited_quote']     │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│    5. RENDER HTML WITH CITATIONS                            │
│  Files: citation_service.py, html_generator.py              │
│  ├─ render_cited_image_html() → HTML with image             │
│  └─ render_cited_quote_html() → HTML with quote text        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│               HTML OUTPUT WITH CITATIONS                     │
│  <div class="reference-citation">...</div>                  │
│  <div class="advisor-quote-box">...</div>                   │
└─────────────────────────────────────────────────────────────┘
```

---

## File-by-File Citation Code Location

### 1. Citation Data Retrieval

#### File: `mondrian/rag_retrieval.py`

**Function:** `get_top_reference_images()`
```python
def get_top_reference_images(db_path, advisor_id, max_total=10):
    """
    Retrieve top reference images for the given advisor.
    Returns list of dicts with: image_path, image_title, dimensional scores, etc.
    """
    # Uses CLIP embeddings to find visually similar images
    # Returns empty list if no embeddings exist
```

**Status:** ✅ Working - unchanged since ffd754e

**Location:** [mondrian/rag_retrieval.py](mondrian/rag_retrieval.py)

---

#### File: `mondrian/embedding_retrieval.py`

**Function:** `get_top_book_passages()`
```python
def get_top_book_passages(advisor_id, max_passages=6):
    """
    Retrieve top book passages for the given advisor.
    Returns list of dicts with: book_title, passage_text, dimensions, etc.
    """
    # Uses semantic embeddings to find relevant quotes
    # Returns empty list if no embeddings exist
```

**Status:** ✅ Working - unchanged since ffd754e

**Location:** [mondrian/embedding_retrieval.py](mondrian/embedding_retrieval.py)

---

### 2. Citation Validation and Attachment

#### File: `mondrian/ai_advisor_service_linux.py`

**Function:** Main analysis method (handles citation validation)

**Key Section:** Lines 1427-1500
```python
# VALIDATE AND RESOLVE CITATIONS
dimensions = analysis_data.get('dimensions', [])
if dimensions:
    # Build lookup maps
    img_lookup = {}
    for idx, img in enumerate(reference_images, 1):
        img_id = f"IMG_{idx}"
        img_lookup[img_id] = img
    
    quote_lookup = {}
    for idx, passage in enumerate(book_passages, 1):
        quote_id = f"QUOTE_{idx}"
        quote_lookup[quote_id] = passage
    
    # Validate each citation
    for dim in dimensions:
        if 'case_study_id' in dim:
            img_id = dim['case_study_id']
            if img_id in img_lookup:
                dim['_cited_image'] = img_lookup[img_id]  # ← CRITICAL
        
        if 'quote_id' in dim:
            quote_id = dim['quote_id']
            if quote_id in quote_lookup:
                dim['_cited_quote'] = quote_lookup[quote_id]  # ← CRITICAL
```

**Status:** ✅ Identical to ffd754e (with added type checking)

**Location:** [mondrian/ai_advisor_service_linux.py#L1427](mondrian/ai_advisor_service_linux.py#L1427)

---

### 3. Citation HTML Rendering

#### File: `mondrian/citation_service.py`

**Function:** `render_cited_image_html()`
```python
def render_cited_image_html(cited_image: dict, dimension_name: str) -> str:
    """
    Render HTML for a cited reference image.
    Delegates to html_generator.generate_reference_image_html()
    """
    from mondrian.html_generator import generate_reference_image_html
    return generate_reference_image_html(
        ref_image=cited_image,
        dimension_name=dimension_name
    )
```

**Status:** ✅ Working - NEW in current version (moved from inline in ai_advisor_service_linux.py)

**Location:** [mondrian/citation_service.py#L11](mondrian/citation_service.py#L11)

---

**Function:** `render_cited_quote_html()`
```python
def render_cited_quote_html(cited_quote: dict, dimension_name: str) -> str:
    """
    Render HTML for a cited advisor quote.
    Generates: <div class="advisor-quote-box">
    """
    book_title = cited_quote.get('book_title', 'Unknown Book')
    passage_text = cited_quote.get('passage_text', cited_quote.get('text', ''))
    
    # Truncate to 75 words
    words = passage_text.split()
    truncated_text = ' '.join(words[:75])
    if len(words) > 75:
        truncated_text += "..."
    
    html = '<div class="advisor-quote-box">'
    html += '<div class="advisor-quote-title">Advisor Insight</div>'
    html += f'<div class="advisor-quote-text">"{truncated_text}"</div>'
    html += f'<div class="advisor-quote-source"><strong>From:</strong> {book_title}</div>'
    html += '</div>'
    
    return html
```

**Status:** ✅ Identical output to ffd754e (moved from inline)

**Location:** [mondrian/citation_service.py#L30](mondrian/citation_service.py#L30)

---

#### File: `mondrian/html_generator.py`

**Function:** `generate_reference_image_html()`
```python
def generate_reference_image_html(
    ref_image: Dict[str, Any],
    dimension_name: str,
    ref_score: Optional[float] = None,
    user_gap: Optional[float] = None
) -> str:
    """
    Generate HTML for a case study citation box.
    Includes:
    - Image (embedded as base64)
    - Title and metadata
    - How it compares to user's image
    """
    # Path resolution
    resolved_path = resolve_image_path(ref_path)
    
    # Load and encode image
    if resolved_path:
        with open(resolved_path, 'rb') as img_file:
            b64_image = base64.b64encode(image_data).decode('utf-8')
            ref_image_url = f"data:image/jpeg;base64,{b64_image}"
    
    # Build HTML
    html = '<div class="reference-citation"><div class="case-study-box">'
    html += f'<img class="case-study-image" src="{ref_image_url}" />'
    html += f'<div class="case-study-title">{ref_title}</div>'
    # ... more HTML ...
    html += '</div></div>'
    
    return html
```

**Status:** ✅ Unchanged since ffd754e

**Location:** [mondrian/html_generator.py#L104](mondrian/html_generator.py#L104)

---

**Function:** `resolve_image_path()`
```python
def resolve_image_path(image_path: str) -> Optional[str]:
    """
    Resolve image path across different environments:
    - Development: /home/doo/dev/mondrian-macos/mondrian/source/...
    - Docker: ./mondrian/source/...
    - RunPod: ./mondrian/source/...
    
    Returns resolved path or None if not found.
    """
    # Multiple strategies to find image
    # 1. Absolute path as-is
    # 2. Extract mondrian-relative part
    # 3. Try common prefixes
    # 4. Search advisor directories
```

**Status:** ✅ Enhanced (added Docker support) - functionally backward compatible

**Location:** [mondrian/html_generator.py#L32](mondrian/html_generator.py#L32)

---

### 4. Citation Usage in HTML Generation

#### File: `mondrian/ai_advisor_service_linux.py`

**Section:** HTML generation (Lines 1300-1330)

```python
for dim in dimensions:
    name = dim.get('name', 'Unknown')
    score = dim.get('score', 0)
    comment = dim.get('comment', '')
    recommendation = dim.get('recommendation', '')
    
    # ← KEY: Citation data attached here
    cited_image = dim.get('_cited_image')
    image_citation_html = ""
    if cited_image:
        image_citation_html = render_cited_image_html(cited_image, name)
    
    cited_quote = dim.get('_cited_quote')
    quote_citation_html = ""
    if cited_quote:
        quote_citation_html = render_cited_quote_html(cited_quote, name)
    
    # Add to final HTML
    html += f'''
    <div class="feedback-card">
      <h3>{name}</h3>
      <div class="feedback-comment"><p>{comment}</p></div>
      <div class="feedback-recommendation"><p>{recommendation}</p></div>
      {image_citation_html}
      {quote_citation_html}
    </div>
    '''
```

**Status:** ✅ Identical logic to ffd754e

**Location:** [mondrian/ai_advisor_service_linux.py#L1309](mondrian/ai_advisor_service_linux.py#L1309)

---

## Citation Status Checklist

- [x] Reference image retrieval: ✅ Working
- [x] Book passage retrieval: ✅ Working
- [x] Citation validation: ✅ Working
- [x] Citation attachment: ✅ Working
- [x] Image HTML rendering: ✅ Working
- [x] Quote HTML rendering: ✅ Working
- [x] Path resolution: ✅ Working (enhanced)
- [x] Error handling: ✅ Working (improved)

---

## How to Trace Citations in Code

### Step 1: Check if References Are Retrieved
Look in logs for:
```
[Stream] Retrieved 5 reference image candidates
[Stream] Retrieved 6 quote candidates
```

### Step 2: Check if Citations Are Validated
Look in logs for:
```
✓ Valid image citation: IMG_1 in Composition
✓ Valid quote citation: QUOTE_2 in Lighting
```

### Step 3: Check if HTML Is Generated
Look in logs for:
```
[HTML Gen] ✅ Successfully embedded reference image: ...
[Citation Service] Rendered quote for Composition from '...'
```

### Step 4: Check Final HTML Output
Look for in generated HTML:
```html
<div class="reference-citation">...</div>
<div class="advisor-quote-box">...</div>
```

---

## Common Citation Issues and Where to Check

| Issue | Location to Check | Likely Cause |
|-------|-------------------|--------------|
| Citations in LLM response but not in HTML | `dim.get('_cited_image')` validation | Lookup building failed |
| Citations showing but images missing | `resolve_image_path()` | Path resolution failed |
| No citations in LLM response | `_build_rag_prompt()` | LLM wasn't told about citations |
| Empty reference/quote lists | `get_top_reference_images()` | No embeddings in database |
| Type errors in validation | `isinstance()` checks | Malformed LLM response |

---

## Summary

All citation code is **present, functional, and identical to ffd754e** with only refactoring and enhancements. If citations don't appear, check:

1. **Database has data:** `sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles;"`
2. **Embeddings exist:** Check for `embedding IS NOT NULL`
3. **Retrieval works:** Run diagnostic script: `python3 diagnose_citation_system.py`
4. **Image paths exist:** Check `mondrian/source/advisor/` directory
5. **Logs show "Valid citation":** Enable debug logging and look for success messages

