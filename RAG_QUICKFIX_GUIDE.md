# RAG System Quick Fix Guide

## Problem Summary

You identified that `compute_image_embeddings.py` generates `.npy` files but they're never ingested into the database, so the RAG system can't use them.

**You were correct!** ✅

## Current State

Your system has **TWO RAG implementations**:

| System | Status | Database Table | Used By |
|--------|--------|----------------|---------|
| **Dimensional RAG** | ✅ Working | `dimensional_profiles` | `ai_advisor_service.py` when `enable_rag=true` |
| **Caption-Based RAG** | ❌ Broken | `image_captions` | Not currently used |

## Quick Fix Options

### Option 1: Use compute_image_embeddings_to_db.py (Recommended)

**This script already does everything correctly - generates embeddings AND saves to database:**

```bash
# Install dependencies if needed
pip install torch clip opencv-python

# Run the script
python mondrian/source/advisor/compute_image_embeddings_to_db.py \
  --advisor_dir mondrian/source/advisor/photographer/ansel/ \
  --advisor_id ansel

# Verify
sqlite3 mondrian.db "SELECT COUNT(*) FROM image_captions WHERE job_id LIKE 'ansel-%'"
```

**Pros:**
- One-step solution (generate + ingest)
- Includes creative attributes (exposure, contrast, etc.)
- Already exists in your codebase

**Cons:**
- Requires CLIP model installation
- Slower than loading pre-computed .npy files

---

### Option 2: Use the New Ingestion Script

**If you already have .npy files and want to ingest them:**

```bash
# Step 1: Generate .npy files (if not already done)
python mondrian/source/advisor/compute_image_embeddings.py \
  --advisor_dir mondrian/source/advisor/photographer/ansel/

# Step 2: Ingest .npy files into database
python ingest_npy_embeddings.py \
  --advisor_dir mondrian/source/advisor/photographer/ansel/ \
  --advisor_id ansel \
  --verify

# Verify
sqlite3 mondrian.db "SELECT COUNT(*) FROM image_captions WHERE caption_type='clip_embedding'"
```

**Pros:**
- Fast (just loads pre-computed embeddings)
- No need to re-run CLIP model
- Good for batch processing

**Cons:**
- Two-step process
- Requires new script (now created)

---

### Option 3: Deprecate .npy Workflow

**Remove `compute_image_embeddings.py` and standardize on `compute_image_embeddings_to_db.py`:**

```bash
# Update documentation to use only compute_image_embeddings_to_db.py
# Remove or archive compute_image_embeddings.py
# Update any scripts that reference the old workflow
```

**Pros:**
- Simplifies architecture
- One canonical way to generate embeddings
- No confusion about which script to use

**Cons:**
- Breaking change if other code depends on .npy files
- Need to update documentation

---

## Testing the Fix

### Test Caption-Based RAG Service

```bash
# Step 1: Start RAG service
python mondrian/rag_service.py --port 5400

# Step 2: Test search by image
curl -X POST http://localhost:5400/search_by_image \
  -F "image=@source/mike-shrub.jpg" \
  -F "top_k=3"

# Expected output:
# {
#   "query_caption": "A desert shrub...",
#   "results": [
#     {"image_path": "...", "caption": "...", "score": 0.92},
#     {"image_path": "...", "caption": "...", "score": 0.87},
#     {"image_path": "...", "caption": "...", "score": 0.85}
#   ],
#   "total": 20
# }
```

### Test Dimensional RAG (Already Working)

```bash
# This already works - uses dimensional_profiles table
curl -X POST http://localhost:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "auto_analyze=true" \
  -F "enable_rag=true"

# Check logs for:
# [RAG] Retrieved X dimensionally similar images
```

---

## Integration: Use Both RAG Systems

**To enable caption-based RAG in addition to dimensional RAG:**

### Step 1: Modify ai_advisor_service.py

Add caption-based RAG query:

```python
def get_similar_images_from_rag(image_path, top_k=3, advisor_id="ansel", 
                                 use_dimensional=True, use_semantic=False):
    """
    Query for similar images using dimensional and/or semantic RAG.
    """
    results = []
    
    # Dimensional RAG (current implementation)
    if use_dimensional:
        dimensional_results = query_dimensional_rag(image_path, top_k, advisor_id)
        results.extend(dimensional_results)
    
    # Semantic RAG (new)
    if use_semantic:
        try:
            with open(image_path, 'rb') as f:
                response = requests.post(
                    f"{RAG_SERVICE_URL}/search_by_image",
                    files={"image": f},
                    data={"top_k": top_k}
                )
            
            if response.status_code == 200:
                semantic_results = response.json()["results"]
                results.extend(format_semantic_results(semantic_results))
        except Exception as e:
            print(f"[RAG] Semantic RAG error: {e}")
    
    return results
```

### Step 2: Update Job Service

Add `use_semantic_rag` parameter:

```python
# mondrian/job_service_v2.3.py
enable_rag = request.form.get("enable_rag", "false").lower() == "true"
use_semantic_rag = request.form.get("use_semantic_rag", "false").lower() == "true"

# Pass to AI Advisor Service
response = requests.post(
    f"{AI_ADVISOR_URL}/analyze",
    json={
        "advisor": advisor,
        "image_path": image_path,
        "job_id": job_id,
        "enable_rag": enable_rag,
        "use_semantic_rag": use_semantic_rag
    }
)
```

### Step 3: Test Combined RAG

```bash
curl -X POST http://localhost:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "auto_analyze=true" \
  -F "enable_rag=true" \
  -F "use_semantic_rag=true"

# Should use BOTH:
# - Dimensional RAG: Find images with similar composition/lighting scores
# - Semantic RAG: Find images with similar subject matter/content
```

---

## Recommended Approach

**For immediate fix:**

1. ✅ Use `compute_image_embeddings_to_db.py` (Option 1)
2. ✅ Verify embeddings are in database
3. ✅ Test `rag_service.py` endpoints
4. ✅ Integrate caption-based RAG into `ai_advisor_service.py` (optional)

**For long-term architecture:**

1. ✅ Keep both RAG systems (dimensional + semantic)
2. ✅ Make them complementary:
   - **Dimensional**: "Find images with similar technical quality"
   - **Semantic**: "Find images with similar subject matter"
3. ✅ Let user choose which to enable:
   - `enable_rag=true` → Dimensional RAG only (current)
   - `use_semantic_rag=true` → Add semantic RAG
   - Both → Hybrid RAG with best of both worlds

---

## Database Verification

```bash
# Check dimensional profiles (currently used)
sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles"
# Expected: 16 (Ansel profiles)

# Check image captions (caption-based RAG)
sqlite3 mondrian.db "SELECT COUNT(*) FROM image_captions WHERE embedding IS NOT NULL"
# Expected: 20+ after running fix

# Check embedding dimensions
sqlite3 mondrian.db "SELECT LENGTH(embedding) FROM image_captions LIMIT 1"
# Expected: 1536 (384 floats * 4 bytes) or 2048 (512 floats * 4 bytes for CLIP)
```

---

## Summary

**Your diagnosis was spot-on:** The `.npy` files are orphaned and never make it into the RAG system.

**The fix:** Use `compute_image_embeddings_to_db.py` or the new `ingest_npy_embeddings.py` script.

**The surprise:** Your system is already using a different RAG system (Dimensional RAG) that doesn't need caption embeddings at all!

**The opportunity:** You can use BOTH RAG systems together for more powerful analysis:
- Dimensional RAG → Technical quality comparison
- Semantic RAG → Subject matter similarity
- Combined → Best of both worlds

See `RAG_SYSTEM_ANALYSIS.md` for complete details.

