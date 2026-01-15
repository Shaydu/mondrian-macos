# Fix: ENABLE_RAG 2-Pass Implementation

## Date
January 11, 2026

## Problem Fixed
The `enable_rag` flag was broken - both `enable_rag=true` and `enable_rag=false` were behaving identically (baseline mode). The RAG system was trying to retrieve the user's dimensional profile from the database **before** it had been saved, causing it to always fail silently.

## Solution Implemented
Implemented a **2-pass analysis workflow** when RAG is enabled:

### Pass 1: Dimensional Extraction
- Quick analysis using a minimal prompt focused only on extracting 8 dimensional scores
- Parses JSON response and extracts dimensional profile
- Saves profile to `dimensional_profiles` table in database
- **Does not** return results to user

### Pass 2: Comparative Analysis
- Queries database for similar advisor images using saved dimensional profile
- Augments prompt with RAG context (real image names, metadata, comparative scores)
- Runs full analysis with comparative feedback
- Returns HTML with reference images to user

### Baseline Mode (enable_rag=false)
- Single-pass analysis without RAG context
- No dimensional comparison with advisor images
- Generic feedback based only on the uploaded image

## Changes Made

### File: `mondrian/ai_advisor_service.py`

**1. Added `get_dimensional_extraction_prompt()` function** (line ~561)
```python
def get_dimensional_extraction_prompt():
    """Minimal prompt for Pass 1: Extract dimensional scores only"""
```
- Returns a focused prompt that asks only for 8 dimensional scores
- JSON-only output format for reliable parsing
- Minimal, fast analysis (~10-15 seconds)

**2. Rewrote RAG workflow in `_analyze_image()` function** (line ~680-760)
```python
# 2-PASS RAG WORKFLOW
if enable_rag:
    # PASS 1: Extract dimensional profile
    pass1_result = run_model_mlx(pass1_prompt, image_path=abs_image_path)
    dimensional_data = extract_dimensional_profile_from_json(pass1_json)
    profile_id = save_dimensional_profile(...)  # Save to DB
    
    # QUERY: Find similar advisor images
    augmented_prompt, similar_images = get_technique_based_rag_context(...)
    
    # PASS 2: Full analysis with RAG context
    # (continues to existing full analysis code)
```

**Key improvements:**
- Clear logging with `[RAG PASS 1]`, `[RAG QUERY]`, `[RAG PASS 2]`, `[BASELINE]` prefixes
- Graceful fallback to baseline if any step fails
- Detailed error messages explaining why RAG failed
- Helpful hints (e.g., "Run: python3 tools/rag/index_ansel_dimensional_profiles.py")

## Testing

### Prerequisites
```bash
# 1. Make sure dimensional_profiles table exists
python3 migrate_dimensional_profiles.py

# 2. Index advisor images (one-time setup)
# Start AI service first
cd mondrian && python3 ai_advisor_service.py --port 5100

# In another terminal:
python3 tools/rag/index_ansel_dimensional_profiles.py

# Expected output:
# [✓] AI Advisor Service is running
# Found 9 images to index
# [1/9] Processing: Adams_The_Tetons_and_the_Snake_River.jpg
#   [✓] Analysis complete
# ...
# [✓] 9 dimensional profiles saved to database
```

### Test Baseline Mode (enable_rag=false)
```bash
# Start services
cd mondrian && python3 job_service_v2.3.py --port 5005 &
cd mondrian && python3 ai_advisor_service.py --port 5100 &

# Upload test image
curl -X POST http://localhost:5005/upload \
  -F "image=@test_landscape.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=false"

# Expected logs:
# [BASELINE] ===== SINGLE-PASS BASELINE ANALYSIS (NO RAG) =====
```

**Expected result:**
- Generic feedback without reference images
- No comparative language ("Unlike...", "Similar to...")
- Single model inference (~30-40 seconds total)

### Test RAG Mode (enable_rag=true)
```bash
curl -X POST http://localhost:5005/upload \
  -F "image=@test_landscape.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"

# Expected logs:
# [RAG] ======================================
# [RAG] 2-PASS RAG WORKFLOW ACTIVATED
# [RAG PASS 1] Extracting dimensional profile...
# [RAG PASS 1] ✓ Profile saved to database
# [RAG QUERY] Searching for similar Ansel Adams images...
# [RAG QUERY] ✓ Found 3 similar images
# [RAG QUERY]   1. Adams_The_Tetons_and_the_Snake_River.jpg (similarity: 0.85)
# [RAG QUERY]   2. Ansel_Adams_-_National_Archives_79-AA-G01.jpg (similarity: 0.82)
# [RAG QUERY]   3. Ansel_Adams_-_National_Archives_79-AA-G06.jpg (similarity: 0.79)
# [RAG PASS 2] ===== FULL ANALYSIS WITH RAG CONTEXT =====
```

**Expected result:**
- Comparative feedback referencing specific advisor images
- Real image names in feedback (e.g., "The Tetons and the Snake River")
- Reference images displayed in HTML output
- Dimensional comparison tables
- Two model inferences (~60-80 seconds total)

### Verify Database State
```bash
# Check that advisor profiles exist
sqlite3 mondrian/mondrian.db "SELECT advisor_id, COUNT(*) FROM dimensional_profiles GROUP BY advisor_id"
# Expected: ansel|9

# Check user profiles are being saved
sqlite3 mondrian/mondrian.db "SELECT image_path, created_at FROM dimensional_profiles ORDER BY created_at DESC LIMIT 5"
# Should show recently uploaded images
```

## Behavior Differences

| Feature | enable_rag=false (Baseline) | enable_rag=true (RAG) |
|---------|----------------------------|----------------------|
| Analysis passes | 1 (single pass) | 2 (extract + compare) |
| Dimensional profile saved | Yes | Yes |
| Queries advisor images | No | Yes |
| Reference images in output | No | Yes (3 similar images) |
| Feedback style | Generic | Comparative |
| Processing time | ~30-40s | ~60-80s |
| Example feedback | "Your composition is strong with good use of rule of thirds" | "Like 'The Tetons and the Snake River', you've used rule of thirds effectively. However, unlike Adams who uses f/64 for front-to-back sharpness in all 3 reference images, your shallow DOF limits depth..." |

## Fallback Behavior

The system gracefully falls back to baseline mode if:
1. Pass 1 fails to parse JSON
2. Dimensional profile can't be extracted from JSON
3. Profile fails to save to database
4. No similar advisor images found (advisor images not indexed yet)
5. Any exception occurs during RAG workflow

In all cases:
- Clear error messages are logged
- Reason for fallback is explained
- System continues with baseline analysis
- User still gets useful feedback (just not comparative)

## Next Steps

1. **Test both modes** with real images
2. **Index advisor images** for all advisors you want to support with RAG
3. **Monitor logs** to ensure correct code path is being used
4. **Verify HTML output** includes reference images when RAG is enabled

## Files Modified
- `mondrian/ai_advisor_service.py` - Added 2-pass workflow

## Files Unchanged (Already Correct)
- `mondrian/technique_rag.py` - Correctly reads from database
- `mondrian/json_to_html_converter.py` - Already supports displaying reference images
- `mondrian/config.py` - RAG_ENABLED flag already exists
- `tools/rag/index_ansel_dimensional_profiles.py` - Pre-analysis script already correct




