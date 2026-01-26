# Citation Investigation - Complete Analysis

**Investigation Date:** January 26, 2026  
**Status:** ✅ COMPLETE  
**Finding:** Citations are **NOT broken** in current code

---

## Quick Answer

**Q: Why are citations not showing in current code?**

**A:** Citations ARE working in the code. The issue is either:
1. **Empty citation database** (no reference images or quotes indexed)
2. **Missing embeddings** (data exists but embeddings are NULL)
3. **Image path issues** (images can't be found on filesystem)

**NOT** a code bug or removed functionality.

---

## Investigation Documents

This directory now contains comprehensive analysis:

### 📋 Summary Documents

1. **[CITATION_INVESTIGATION_SUMMARY.md](CITATION_INVESTIGATION_SUMMARY.md)** - Start here!
   - Quick overview of findings
   - What changed between commits
   - Why citations appear missing
   - How to fix

2. **[CITATION_INVESTIGATION_REPORT.md](CITATION_INVESTIGATION_REPORT.md)** - Deep dive
   - How citations worked in ffd754e
   - How they work in current code
   - Root cause analysis
   - Step-by-step code flow

### 🔍 Technical Comparison

3. **[CITATION_CODE_COMPARISON.md](CITATION_CODE_COMPARISON.md)** - Side-by-side code
   - Line-by-line comparison of key functions
   - Highlights what changed and what didn't
   - Impact analysis for each change

4. **[CITATION_CODE_MAP.md](CITATION_CODE_MAP.md)** - Reference guide
   - Where citation code lives
   - Function signatures
   - Data flow diagram
   - Common issues and locations

### 🛠️ Tools and Guides

5. **[diagnose_citation_system.py](diagnose_citation_system.py)** - Run this first!
   ```bash
   python3 diagnose_citation_system.py
   ```
   - Checks if citation system is properly configured
   - Identifies specific issues
   - Provides remediation steps

6. **[CITATION_DEBUGGING_GUIDE.md](CITATION_DEBUGGING_GUIDE.md)** - Fix issues
   - Step-by-step debugging procedures
   - Quick diagnosis (2 minutes)
   - Full diagnosis (5 minutes)
   - Advanced diagnosis (10+ minutes)
   - Recovery procedures

---

## Key Findings

### ✅ What's Still Working

| Component | Status | Evidence |
|-----------|--------|----------|
| Citation data retrieval | ✅ Working | Code identical to ffd754e |
| Citation validation | ✅ Working | Lookup and attach logic unchanged |
| Image citation HTML rendering | ✅ Working | Refactored but functionally identical |
| Quote citation HTML rendering | ✅ Working | Moved to citation_service.py, logic unchanged |
| Path resolution | ✅ Enhanced | Better Docker support, backward compatible |
| Error handling | ✅ Improved | Type checking added, better error messages |

### 🔄 What Changed

| Change | Type | Impact |
|--------|------|--------|
| Quote rendering moved to citation_service.py | Refactoring | Code cleaner, output identical |
| Image citation uses render_cited_image_html() | Refactoring | Code cleaner, output identical |
| Type validation added | Enhancement | More robust, no breaking changes |
| Docker path support | Enhancement | Backward compatible improvement |
| Deprecated function removed | Cleanup | Function was already broken, no impact |
| Logging improved | Enhancement | Better debugging, no functional change |

### ⚠️ Not a Code Issue

If citations aren't showing, the code is **not the problem**. Check:

- [ ] Database has reference images: `SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel';`
- [ ] Database has book passages: `SELECT COUNT(*) FROM book_passages WHERE advisor_id='ansel';`
- [ ] Embeddings exist: `embedding IS NOT NULL` in both tables
- [ ] Image files are on disk: `ls mondrian/source/advisor/photographer/ansel/`

---

## Step-by-Step Fix

### 1. Diagnose (2 minutes)
```bash
python3 diagnose_citation_system.py
```

### 2. Fix Based on Output

**If: "No reference images"**
```bash
python3 batch_analyze_advisor_images.py --advisor ansel
python3 tools/rag/compute_embeddings.py --advisor ansel
```

**If: "No book passages"**
```bash
python3 tools/rag/import_book_passages.py --advisor ansel
python3 tools/rag/compute_embeddings.py --type passages --advisor ansel
```

**If: "No embeddings"**
```bash
python3 tools/rag/compute_embeddings.py --advisor ansel --force
```

### 3. Verify
```bash
python3 diagnose_citation_system.py
python3 test_enhanced_single_pass_citations.py
```

---

## Code Proof

### Citation Validation (Lines 1427-1500 of ai_advisor_service_linux.py)

This code is **IDENTICAL** between ffd754e and current:

```python
# Build lookup
img_lookup = {}
for idx, img in enumerate(reference_images, 1):
    img_lookup[f"IMG_{idx}"] = img

# Validate and attach
for dim in dimensions:
    if 'case_study_id' in dim:
        img_id = dim['case_study_id']
        if img_id in img_lookup:
            dim['_cited_image'] = img_lookup[img_id]  # ← THIS WORKS
```

When `dim['_cited_image']` is set, citations are attached and will render.

### HTML Rendering (Lines 1309-1323 of ai_advisor_service_linux.py)

This code is **IDENTICAL** in logic between ffd754e and current:

```python
cited_image = dim.get('_cited_image')
if cited_image:
    image_citation_html = render_cited_image_html(cited_image, name)
    # Returns: <div class="reference-citation">...</div>

cited_quote = dim.get('_cited_quote')
if cited_quote:
    quote_citation_html = render_cited_quote_html(cited_quote, name)
    # Returns: <div class="advisor-quote-box">...</div>
```

Both functions exist and return the same HTML as before.

---

## File Reference

### Current Code Files

- [mondrian/ai_advisor_service_linux.py](mondrian/ai_advisor_service_linux.py) - Main service
  - Citation retrieval: Lines ~1910-1937
  - Citation validation: Lines ~1427-1500
  - HTML rendering: Lines ~1309-1323

- [mondrian/citation_service.py](mondrian/citation_service.py) - NEW in current version
  - `render_cited_image_html()` - Delegates to html_generator
  - `render_cited_quote_html()` - Generates quote HTML

- [mondrian/html_generator.py](mondrian/html_generator.py) - HTML generation
  - `resolve_image_path()` - Smart path resolution
  - `generate_reference_image_html()` - Case study HTML

- [mondrian/rag_retrieval.py](mondrian/rag_retrieval.py) - RAG functions
  - `get_top_reference_images()` - Retrieves reference images

- [mondrian/embedding_retrieval.py](mondrian/embedding_retrieval.py) - Embedding queries
  - `get_top_book_passages()` - Retrieves book quotes

### Reference Commits

- **ffd754e** (Jan 25, 2026) - "fixed images, references, citations and quotes"
  - Citation rendering inline in ai_advisor_service_linux.py
  - All citation logic present

- **HEAD** (Jan 26, 2026) - "Fix import error: remove deleted generate_ios_detailed_html function"
  - Citation rendering moved to citation_service.py
  - All citation logic present + improvements
  - No functionality removed

---

## Next Steps

### For Users

1. Run diagnostic: `python3 diagnose_citation_system.py`
2. Follow the recommendations
3. Run test: `python3 test_enhanced_single_pass_citations.py`
4. Check for success messages in logs

### For Developers

1. Review [CITATION_CODE_MAP.md](CITATION_CODE_MAP.md) for architecture
2. Review [CITATION_CODE_COMPARISON.md](CITATION_CODE_COMPARISON.md) for changes
3. Use [CITATION_DEBUGGING_GUIDE.md](CITATION_DEBUGGING_GUIDE.md) for troubleshooting
4. Enable debug logging: `--log-level DEBUG`

### For CI/CD

Add verification test to pipeline:
```bash
python3 diagnose_citation_system.py || exit 1
python3 test_enhanced_single_pass_citations.py || exit 1
```

---

## Conclusion

**The citation system is fully functional in the current code.** All changes between ffd754e and HEAD are either:

- ✅ Pure refactoring (moving code, no logic change)
- ✅ Enhancement (better error checking, Docker support)
- ✅ Cleanup (removing deprecated code)

**If citations aren't appearing, the issue is data-related, not code-related.**

Use the diagnostic script and debugging guide to identify and fix the specific issue.

---

## Questions?

Check the appropriate document:
- **Quick answer?** → [CITATION_INVESTIGATION_SUMMARY.md](CITATION_INVESTIGATION_SUMMARY.md)
- **Deep dive?** → [CITATION_INVESTIGATION_REPORT.md](CITATION_INVESTIGATION_REPORT.md)
- **Code comparison?** → [CITATION_CODE_COMPARISON.md](CITATION_CODE_COMPARISON.md)
- **Where is the code?** → [CITATION_CODE_MAP.md](CITATION_CODE_MAP.md)
- **How do I fix it?** → [CITATION_DEBUGGING_GUIDE.md](CITATION_DEBUGGING_GUIDE.md)
- **Let me diagnose it** → `python3 diagnose_citation_system.py`

