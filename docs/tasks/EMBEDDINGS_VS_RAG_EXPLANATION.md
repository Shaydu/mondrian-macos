# Embeddings vs RAG: Are They the Same?

## Short Answer

**No, they are different but related:**

- **RAG (Retrieval-Augmented Generation)**: Finds similar images using **dimensional scores** (composition, lighting, color harmony, etc.)
- **Embeddings**: Finds similar images using **visual similarity** (CLIP embeddings - machine learning model that understands visual content)

They can work **together or separately**.

---

## What is RAG?

### Current RAG Implementation

RAG uses **dimensional analysis** to find similar images:

1. **First pass**: Analyze user's image → Get dimensional scores
   ```
   composition: 7.2/10
   lighting: 6.8/10
   color_harmony: 5.9/10  ← Low
   depth_perspective: 6.5/10
   ```

2. **Query**: Find portfolio images with strong scores in user's weak areas
   ```
   WHERE composition >= 8.5
   AND color_harmony >= 8.8
   ORDER BY similarity DESC
   ```

3. **Result**: Reference images for comparison
   ```
   "Reference #1: Perfect color harmony (9.2/10)"
   "Reference #2: Excellent depth (9.5/10)"
   ```

**Code location:** `find_similar_by_dimensions()` in `json_to_html_converter.py`

---

## What are Embeddings?

### Embedding-Based Visual Similarity

Embeddings use **CLIP model** (visual understanding neural network):

1. **CLIP embedding**: Convert image to 512-dimensional vector
   ```
   User's image → [0.12, -0.45, 0.89, ..., 0.34]
                    (512 dimensions)
   ```

2. **Database lookup**: Find images with similar embeddings
   ```
   Portfolio images also have embeddings stored
   Calculate cosine similarity between user and each portfolio image
   Top matches = most visually similar
   ```

3. **Result**: Images that "look similar" visually
   ```
   "Reference #1: Visually similar - 94% match"
   "Reference #2: Visually similar - 89% match"
   ```

**Code location:** `find_similar_by_embedding()` in `json_to_html_converter.py`

---

## Key Differences

| Aspect | RAG (Dimensional) | Embeddings (CLIP) |
|--------|-------------------|------------------|
| **How it works** | Analyzes 8 dimensions (composition, lighting, etc.) | Uses CLIP neural network to understand visual content |
| **Finds** | Images with good scores in weak dimensions | Images that look visually similar |
| **Use case** | "Show me images that excel where I'm weak" | "Show me images that look like mine" |
| **Speed** | Fast (SQL query on numeric scores) | Moderate (embeddings already computed) |
| **Dependency** | Dimensional profile database | CLIP embedding service (port 5300) |
| **Status** | ✅ Fully implemented | ⚠️ Partially implemented |

---

## Current Status

### ✅ What We Have

1. **RAG (Dimensional)** - FULLY IMPLEMENTED
   - `find_similar_by_dimensions()` function exists and works
   - Used by RAG, RAG+LoRA modes
   - Provides comparative context for analysis

2. **Embeddings (CLIP)** - PARTIALLY IMPLEMENTED
   - `find_similar_by_embedding()` function exists
   - Embedding service infrastructure (port 5300)
   - Can be enabled via `enable_embeddings=true` parameter
   - **Status:** Marked as "TODO" / "experimental" in code

### ❌ What's Missing

Looking at line 1862 in ai_advisor_service.py:
```python
if enable_embeddings:
    print(f"[RAG] [INFO] TODO: Call find_similar_by_embedding() when implemented")
```

The embedding lookup is **not being called** even when enabled!

---

## How They Work in Current Modes

### baseline
- Single-pass analysis
- No reference images
- ❌ No dimensional similarity
- ❌ No visual similarity

### rag
- Single-pass analysis (currently)
- ✅ Finds similar images by **dimensional scores**
- ❌ Doesn't use embeddings

### lora
- Single-pass fine-tuned analysis
- ❌ No reference images
- ❌ No dimensional similarity
- ❌ No visual similarity

### rag+lora
- Two-pass fine-tuned analysis
- ✅ Finds similar images by **dimensional scores** (Pass 1 extracts dimensions, Query finds references)
- ❌ Doesn't use embeddings

---

## Could They Work Together?

**YES!** A combined approach could:

1. **First**: Use embeddings to find visually similar images (fast visual grouping)
2. **Then**: Use dimensional analysis to find portfolio images with strong scores

Or vice versa:
1. **First**: Use dimensional analysis to find strong performers in user's weak areas
2. **Then**: Filter by visual similarity (embeddings)

Example: "Show me images that (visually look like mine) AND (have excellent lighting)"

---

## Enabling Embeddings

Currently disabled by default:

```python
EMBEDDINGS_ENABLED = os.environ.get("EMBEDDINGS_ENABLED", "false").lower() == "true"
```

To enable:
```bash
export EMBEDDINGS_ENABLED=true
./mondrian.sh
```

But it won't do anything yet because the function call is marked as TODO.

---

## Summary Table

| Feature | Current | Needed |
|---------|---------|--------|
| Embedding service | ✅ Exists | ✅ Works |
| Embedding storage | ✅ In database | ✅ Present |
| Embedding lookup | ✅ Function exists | ❌ Not called |
| Dimensional RAG | ✅ Fully working | ✅ Good |
| Combined RAG+Embeddings | ❌ Not implemented | ⚠️ Possible |

---

## Why Embeddings Matter

**Dimensional RAG** is great because:
- Shows images with strong scores in weak dimensions
- Very helpful for improvement guidance

**Embeddings** would add:
- Visual style matching
- "Find images like mine" functionality
- Better for aesthetic comparisons
- Independent of dimensional scoring

**Together** they could provide:
- The best of both visual and technical analysis
- More diverse reference images
- Multi-faceted comparison options

---

## Next Steps

To fully implement embeddings:
1. Uncomment/implement the `find_similar_by_embedding()` call
2. Decide when to use embeddings vs dimensional RAG vs both
3. Test with enable_embeddings parameter
4. Consider hybrid approach (embeddings + dimensional)

For now, **RAG mode uses dimensional similarity** (which works great), and embeddings remain an experimental feature not yet integrated into the analysis flow.
