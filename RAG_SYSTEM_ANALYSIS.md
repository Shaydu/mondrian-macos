# RAG System Analysis: Missing Ingestion Link

## Executive Summary

Your Mondrian system has **TWO separate RAG implementations**:

1. **Caption-Based RAG** (Original) - Has missing ingestion link ❌
2. **Dimensional RAG** (Current) - Fully functional ✅

The issue you identified is correct: `compute_image_embeddings.py` generates `.npy` files but they're never ingested into the RAG system.

---

## System 1: Caption-Based RAG (The Problem)

### Architecture

```
compute_image_embeddings.py
    ↓
Generates .npy files (CLIP embeddings)
    ↓
❌ MISSING LINK ❌
    ↓
Should ingest into image_captions table
    ↓
rag_service.py /search_by_image endpoint
```

### Current Files

1. **`compute_image_embeddings.py`**
   - Purpose: Generate CLIP embeddings for advisor images
   - Output: `.npy` files saved next to images
   - Problem: **Only saves to disk, doesn't update database**

2. **`compute_image_embeddings_to_db.py`**
   - Purpose: Generate embeddings AND save to database
   - Output: Inserts into `image_captions` table with embedding BLOB
   - Status: **This is the correct script but may not be used**

3. **`rag_service.py`**
   - Purpose: Semantic search service
   - Endpoints:
     - `/index` - Generate caption → embed → store
     - `/search` - Text-based semantic search
     - `/search_by_image` - Image-based similarity search
   - Problem: **Expects embeddings in database, not .npy files**

### The Missing Link

**Current Workflow (Broken):**
```bash
# Step 1: Generate embeddings (saves .npy files)
python compute_image_embeddings.py --advisor_dir mondrian/source/advisor/photographer/ansel/

# Step 2: ❌ MISSING - No script ingests .npy files into database

# Step 3: RAG service queries database (finds nothing)
curl -X POST http://localhost:5400/search_by_image -F "image=@test.jpg"
# Returns: No results (database is empty)
```

**Correct Workflow (Should Be):**
```bash
# Option A: Use compute_image_embeddings_to_db.py instead
python compute_image_embeddings_to_db.py \
  --advisor_dir mondrian/source/advisor/photographer/ansel/ \
  --advisor_id ansel

# Option B: Create ingestion script to load .npy files into database
python ingest_npy_embeddings.py --advisor_dir mondrian/source/advisor/photographer/ansel/
```

### Database State

```sql
-- image_captions table exists and has 20 records
SELECT COUNT(*) FROM image_captions;
-- Result: 20

-- But these were likely created via /index endpoint, not from .npy files
SELECT job_id, image_path, LENGTH(embedding) FROM image_captions LIMIT 5;
-- Shows embeddings exist (1536 bytes = 384 floats * 4 bytes)
```

---

## System 2: Dimensional RAG (Working)

### Architecture

```
User uploads image
    ↓
AI Advisor Service (enable_rag=true)
    ↓
PASS 1: Analyze image → Extract dimensional profile
    ↓
Save to dimensional_profiles table
    ↓
Query for similar images (Euclidean distance on 8 dimensions)
    ↓
PASS 2: Re-analyze with dimensional comparison context
    ↓
Return augmented analysis
```

### Key Functions

**`get_similar_images_from_rag()` (ai_advisor_service.py:143-238)**
- Queries `dimensional_profiles` table (NOT `image_captions`)
- Finds images with similar dimensional scores
- Returns dimensional comparisons (deltas for each dimension)

**`augment_prompt_with_rag_context()` (ai_advisor_service.py:240-333)**
- Injects dimensional comparison tables into prompt
- Provides quantitative (score deltas) and qualitative (comments) context
- Enables comparative feedback

### Database State

```sql
-- dimensional_profiles table has 16 Ansel profiles
SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id = 'ansel';
-- Result: 16

-- These are automatically generated during analysis
SELECT image_path, composition_score, lighting_score, overall_grade 
FROM dimensional_profiles LIMIT 3;
```

---

## The Confusion: Which RAG System is Active?

### When `enable_rag=true` is set:

**Current Behavior:**
- ✅ Uses **Dimensional RAG** (System 2)
- ❌ Does NOT use Caption-Based RAG (System 1)
- ❌ Does NOT use `.npy` files
- ❌ Does NOT call `rag_service.py`

**Evidence:**
```python
# ai_advisor_service.py:748
similar_images = get_similar_images_from_rag(abs_image_path, top_k=3, advisor_id=advisor)

# This function queries dimensional_profiles table, NOT image_captions
# It never calls rag_service.py
```

### Why Caption-Based RAG is Not Used

Looking at the code flow:

1. `ai_advisor_service.py` has `RAG_SERVICE_URL` defined (line 67)
2. But it's **never actually used** in the code
3. No `requests.post(RAG_SERVICE_URL + "/search_by_image")` calls exist
4. The dimensional RAG system was implemented instead

---

## Solutions

### Option 1: Complete Caption-Based RAG Implementation (Recommended)

**Create ingestion script to load .npy files into database:**

```python
#!/usr/bin/env python3
"""
Ingest .npy embedding files into image_captions table.
Usage:
    python ingest_npy_embeddings.py --advisor_dir /path/to/advisor/images --advisor_id ansel
"""
import os
import argparse
from pathlib import Path
import numpy as np
import sqlite3
import uuid

DB_PATH = "mondrian.db"

def ingest_npy_embeddings(advisor_dir, advisor_id):
    """Load .npy embeddings and insert into database"""
    advisor_dir = Path(advisor_dir)
    npy_files = list(advisor_dir.rglob("*.npy"))
    
    print(f"Found {len(npy_files)} .npy files")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for npy_path in npy_files:
        # Get corresponding image path
        image_path = npy_path.with_suffix('')  # Remove .npy extension
        if not image_path.exists():
            print(f"Warning: Image not found for {npy_path}")
            continue
        
        # Load embedding
        embedding = np.load(npy_path)
        
        # Insert into database
        cursor.execute("""
            INSERT OR REPLACE INTO image_captions
            (id, job_id, image_path, caption, caption_type, embedding, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            f"{advisor_id}-{image_path.stem}",
            str(image_path),
            '',  # No caption for CLIP embeddings
            'clip_embedding',
            embedding.tobytes(),
            '{}'
        ))
    
    conn.commit()
    conn.close()
    print(f"Ingested {len(npy_files)} embeddings into database")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--advisor_dir", type=str, required=True)
    parser.add_argument("--advisor_id", type=str, required=True)
    args = parser.parse_args()
    
    ingest_npy_embeddings(args.advisor_dir, args.advisor_id)
```

**Then integrate caption-based RAG into ai_advisor_service.py:**

```python
# In ai_advisor_service.py, add to get_similar_images_from_rag():

def get_similar_images_from_rag(image_path, top_k=3, advisor_id="ansel", use_caption_rag=False):
    """
    Query for similar images using either dimensional or caption-based RAG.
    
    Args:
        use_caption_rag: If True, use caption-based RAG via rag_service.py
                        If False, use dimensional RAG (default)
    """
    if use_caption_rag:
        # Call rag_service.py /search_by_image endpoint
        try:
            with open(image_path, 'rb') as f:
                response = requests.post(
                    f"{RAG_SERVICE_URL}/search_by_image",
                    files={"image": f},
                    data={"top_k": top_k}
                )
            
            if response.status_code == 200:
                results = response.json()["results"]
                return format_caption_rag_results(results)
            else:
                print(f"[RAG] Caption-based RAG failed: {response.text}")
                return []
        except Exception as e:
            print(f"[RAG] Error calling caption-based RAG: {e}")
            return []
    else:
        # Use existing dimensional RAG (current implementation)
        # ... existing code ...
```

### Option 2: Use compute_image_embeddings_to_db.py Directly

**This script already does everything correctly:**

```bash
# Generate embeddings AND insert into database in one step
python mondrian/source/advisor/compute_image_embeddings_to_db.py \
  --advisor_dir mondrian/source/advisor/photographer/ansel/ \
  --advisor_id ansel
```

**Advantages:**
- No need for separate ingestion script
- Generates embeddings + saves to database atomically
- Includes creative attributes (exposure, contrast, sharpness, colorfulness)

**Disadvantage:**
- Requires CLIP model to be installed (`pip install torch clip`)
- Slower than just loading pre-computed .npy files

### Option 3: Deprecate compute_image_embeddings.py

**Recommendation:**
- Remove or deprecate `compute_image_embeddings.py`
- Use `compute_image_embeddings_to_db.py` as the canonical script
- Update documentation to reflect this

---

## Current RAG System Status

### What's Working ✅

1. **Dimensional RAG** (System 2)
   - 16 Ansel profiles in database
   - Automatically extracts profiles during analysis
   - Finds similar images by dimensional scores
   - Augments prompts with dimensional comparisons
   - Fully integrated into `ai_advisor_service.py`

2. **image_captions table** (System 1)
   - Table exists with 20 records
   - Embeddings are stored (1536 bytes each)
   - `rag_service.py` can query this table
   - `/search_by_image` endpoint works

### What's Broken ❌

1. **compute_image_embeddings.py**
   - Generates .npy files but they're orphaned
   - No ingestion into database
   - Not used by any service

2. **Caption-Based RAG Integration**
   - `RAG_SERVICE_URL` defined but never called
   - `rag_service.py` is running but not used by `ai_advisor_service.py`
   - The dimensional RAG system replaced it

### What's Confusing 🤔

1. **Two RAG systems exist but only one is active**
   - Dimensional RAG is the active system
   - Caption-based RAG infrastructure exists but is dormant

2. **Documentation mismatch**
   - `RAG_COMPARISON_GUIDE.md` describes caption-based RAG
   - `DIMENSIONAL_RAG_IMPLEMENTATION.md` describes dimensional RAG
   - Both claim to be "the" RAG system

---

## Recommendations

### Immediate Actions

1. **Clarify which RAG system to use:**
   - **Dimensional RAG**: Better for photographic analysis (composition, lighting, etc.)
   - **Caption-Based RAG**: Better for semantic similarity (subject matter, scene type)
   - **Both**: Could be complementary (dimensional + semantic)

2. **Fix the ingestion issue:**
   - Create `ingest_npy_embeddings.py` script (see Option 1 above)
   - OR use `compute_image_embeddings_to_db.py` directly (Option 2)
   - OR deprecate `.npy` workflow entirely (Option 3)

3. **Update documentation:**
   - Create `RAG_ARCHITECTURE.md` explaining both systems
   - Clarify when each system is used
   - Document the complete workflow

### Long-Term Architecture

**Hybrid RAG System:**

```python
def get_similar_images_from_rag(image_path, top_k=3, advisor_id="ansel", 
                                 use_dimensional=True, use_semantic=True):
    """
    Query for similar images using both dimensional and semantic RAG.
    
    Returns images that are similar in BOTH:
    - Dimensional profile (composition, lighting, etc.)
    - Semantic content (subject matter, scene type)
    """
    results = []
    
    if use_dimensional:
        # Query dimensional_profiles table
        dimensional_results = query_dimensional_rag(image_path, top_k, advisor_id)
        results.extend(dimensional_results)
    
    if use_semantic:
        # Query image_captions table via rag_service.py
        semantic_results = query_semantic_rag(image_path, top_k)
        results.extend(semantic_results)
    
    # Merge and deduplicate results
    # Rank by combined similarity score
    return merge_rag_results(results, top_k)
```

**Benefits:**
- **Dimensional RAG**: "Find images with similar composition quality"
- **Semantic RAG**: "Find images with similar subject matter"
- **Combined**: "Find desert landscapes with similar composition quality"

---

## Testing the Fix

### Test Caption-Based RAG

```bash
# Step 1: Ensure embeddings are in database
python compute_image_embeddings_to_db.py \
  --advisor_dir mondrian/source/advisor/photographer/ansel/ \
  --advisor_id ansel

# Step 2: Verify database
sqlite3 mondrian.db "SELECT COUNT(*) FROM image_captions WHERE job_id LIKE 'ansel-%'"

# Step 3: Test rag_service.py directly
curl -X POST http://localhost:5400/search_by_image \
  -F "image=@source/mike-shrub.jpg" \
  -F "top_k=3"

# Should return similar images with similarity scores
```

### Test Dimensional RAG

```bash
# Already working - test with enable_rag=true
curl -X POST http://localhost:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "auto_analyze=true" \
  -F "enable_rag=true"

# Check logs for "[RAG] Retrieved X dimensionally similar images"
```

---

## Conclusion

**You were absolutely correct** about the missing ingestion link for caption-based RAG. The `.npy` files generated by `compute_image_embeddings.py` are never loaded into the database, so the RAG service can't use them.

**However**, your system is currently using a **different RAG system** (Dimensional RAG) that doesn't rely on caption embeddings at all. It extracts dimensional scores from analysis and finds similar images by comparing those scores.

**The fix depends on your goal:**

1. **If you want caption-based RAG to work**: Use `compute_image_embeddings_to_db.py` or create an ingestion script
2. **If dimensional RAG is sufficient**: Deprecate the caption-based system and clean up unused code
3. **If you want both**: Implement a hybrid RAG system that uses both dimensional and semantic similarity

Let me know which direction you'd like to pursue and I can help implement the solution!

