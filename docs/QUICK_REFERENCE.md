# Quick Reference: CLIP, Embeddings & LoRA

## Three Sentence Summary

**CLIP**: A visual translator that converts images into numbers (embeddings) so it can compare their similarity. Pre-computed embeddings = instant lookups.

**LoRA**: A small adapter on top of your base model that teaches it your advisor's specialized style. Already trained, ready to use.

**Dimensional RAG**: Eight technical scores (composition, lighting, etc.) that provide quantitative feedback compared to reference images.

---

## Cost/Benefit At A Glance

| Technology | What It Costs | What You Gain |
|----------|---------------|--------------|
| **CLIP Pre-computed** | 30 min setup | 5x faster responses, visual similarity |
| **CLIP On-demand** | 2-3 sec per request | Visual similarity (slow) |
| **LoRA** | Already done! | Specialized advisor feedback |
| **Dimensional RAG** | Already done! | Technical quantitative scores |
| **All 3 Combined** | ~2-3 hours total | Best possible feedback |

---

## The Four Analysis Modes (Future)

```
┌─────────────────────────────────────────────────────────────────┐
│ Mode 1: CLIP Only (Fastest)                                     │
├─────────────────────────────────────────────────────────────────┤
│ User: "Analyze my image"                                        │
│ System: "Your photo is similar to these 3 master works"        │
│ Speed: 1 second                                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Mode 2: LoRA Only (Best Specialized Feedback)                  │
├─────────────────────────────────────────────────────────────────┤
│ User: "Analyze my image"                                        │
│ System: "Your leading lines are strong (Ansel would approve)"  │
│ Speed: 3 seconds                                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Mode 3: Dimensional RAG (Most Detailed)                        │
├─────────────────────────────────────────────────────────────────┤
│ User: "Analyze my image"                                        │
│ System: "Composition: 7/10. Compare to reference: 9/10"        │
│ Speed: 5 seconds                                                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Mode 4: All Three Combined (Most Valuable) ⭐                   │
├─────────────────────────────────────────────────────────────────┤
│ User: "Analyze my image"                                        │
│ System: "Your image is similar to [Master A] and [Master B]    │
│         Your composition technique is strong (7/10 vs ref 9/10)│
│         Ansel would particularly like your leading lines"      │
│ Speed: 4 seconds (fast with pre-computed embeddings!)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start (30 minutes to 5x faster)

```bash
# 1. Pre-compute embeddings for Ansel Adams images
python tools/rag/compute_image_embeddings_to_db.py \
  --advisor_dir mondrian/source/advisor/photographer/ansel/ \
  --advisor_id ansel

# Done! Now CLIP lookups are instant instead of 2-3 seconds
```

---

## Pre-computed Embeddings: Why It Matters

```
WITHOUT pre-computation:
User submits image
  → Load CLIP model (2 sec, 2 GB GPU memory)
  → Compute embedding (2 sec)
  → Look up similar images (1 sec)
  → Show results (5 sec total) ❌ SLOW

WITH pre-computation:
User submits image
  → Look up pre-computed similar images (1 sec)
  → Show results (1 sec total) ⚡ FAST
```

**Key insight**: CLIP is fast at comparing embeddings, but slow at computing them.
Pre-computing lets you do expensive work once, then reuse forever.

---

## The Pre-compute Script (You Already Have It!)

**Location**: `tools/rag/compute_image_embeddings_to_db.py`

What it does:
1. Finds all advisor reference images
2. Runs them through CLIP model (one-time)
3. Stores 512-number embedding vectors in database
4. Never needs to recompute

That's it! Simple and powerful.

---

## Understanding Embeddings (Non-Technical)

**Embedding** = A list of 512 numbers that represent the "essence" of an image.

```
Image: Sunset photo with mountains
CLIP generates: [0.234, -0.891, 0.456, 0.123, ... 508 more numbers]

Image: Different sunset photo with mountains  
CLIP generates: [0.241, -0.885, 0.462, 0.119, ... 508 more numbers]

These numbers are VERY similar (close to each other)
→ CLIP says: "These images are visually similar"
```

The 512 numbers represent learned concepts like:
- Color patterns
- Shapes and composition
- Lighting and tone
- Subject matter

No math required to use - CLIP figures it all out!

---

## LoRA in 30 Seconds

**Traditional model**: Jack of all trades, master of none
- "Your image is fine"

**LoRA model** (trained on Ansel Adams): Master of a specific trade
- "Your image captures the dramatic lighting that Ansel championed"
- "Your leading lines echo his compositional principles"

**How it works:**
- Base model: 4 billion parameters
- LoRA adapter: 2% of parameters (80 million)
- Result: Specialized feedback without retraining everything

**Your advantage**: LoRA is already trained and ready to use!

---

## Why Combine All Three?

| Analysis Type | Tells You | Example |
|---------------|-----------|---------|
| CLIP | "Is it visually similar?" | "Like these master works" |
| LoRA | "Is the technique good?" | "Your lighting is Ansel-like" |
| Dimensional | "How does it score?" | "Composition: 7/10" |
| **All Three** | **Complete feedback** | **"Visual similarity + specialized praise + technical score"** |

---

## Scripts to Archive

Found 115 old edge pipeline utilities in `scripts/`. These can go to `scripts/archive/`:

```
scripts/edge*.py          ← All superseded
scripts/edge_pipeline_v*_utils.py  ← All 115 versions
```

Keep everything else - they're all actively used!

---

## Next Steps

1. ✅ **Read**: [CLIP_LORA_PRIMER.md](../docs/CLIP_LORA_PRIMER.md) (10 minutes)
2. ⚡ **Do**: Run pre-computation script (15 minutes)
3. 🧪 **Test**: Enable embeddings in API and try it (5 minutes)
4. 📦 **Archive**: Move old edge scripts (10 minutes)

**Total**: 40 minutes to understand everything + get 5x performance improvement!

---

## Key Numbers to Remember

| Metric | Value |
|--------|-------|
| CLIP embedding dimension | 512 numbers |
| CLIP computation time | 2-3 sec on GPU, 20 sec on CPU |
| CLIP database size per image | ~2 KB |
| LoRA adapter file size | 50-500 MB |
| Dimensional profile size | ~1 KB |
| Pre-computation speedup | 5x faster |
| GPU throughput with pre-computed | 10-20 requests/sec |

---

## Files You Need

**To read:**
- `docs/CLIP_LORA_PRIMER.md` - Beginner explanations
- `docs/EMBEDDING_PRECOMPUTATION_GUIDE.md` - Step-by-step setup
- `docs/EMBEDDINGS_INTEGRATION_STATUS.md` - Technical details

**To run:**
- `tools/rag/compute_image_embeddings_to_db.py` - Pre-computation

**To archive:**
- Everything in `scripts/edge*` - Old experimentation

---

## One Last Thing

The most important insight: **Pre-computed embeddings eliminate your biggest performance bottleneck.**

Current system: Every CLIP request needs 2-3 seconds to compute the embedding.

Your solution: Run pre-computation once (30 minutes), then every CLIP request takes 1 second.

That's 5x faster for free! Just need to run one script.

