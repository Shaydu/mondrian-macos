# Visual Guide: CLIP + LoRA + Dimensional RAG

## The Complete Picture

```
┌────────────────────────────────────────────────────────────────────┐
│                    USER UPLOADS PHOTO                              │
└────────────────────────┬───────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  Which mode should we use?         │
        └────────────────────┬───────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
    ┌─────────┐          ┌──────────┐      ┌────────────┐
    │  CLIP   │          │  LoRA    │      │ Dimensional│
    │ Finder  │          │ Analyzer │      │    RAG     │
    └────┬────┘          └────┬─────┘      └─────┬──────┘
         │                    │                   │
         │ Pre-computed       │ Fine-tuned        │ Calculated
         │ embeddings         │ model             │ scores
         │ in database        │ (50-500MB)        │ (8 dimensions)
         │                    │                   │
         ▼                    ▼                   ▼
    ┌─────────────────┐  ┌─────────────┐   ┌──────────────┐
    │ "Your image     │  │ "Your       │   │ "Your        │
    │ is similar to   │  │ leading     │   │ Composition: │
    │ these masters"  │  │ lines are   │   │ 7/10         │
    │                 │  │ strong      │   │ vs Ref:9/10" │
    │ Reference       │  │ (Ansel      │   │              │
    │ Image 1: 92%    │  │ would       │   │ Score        │
    │ Reference       │  │ approve)"   │   │ Breakdown:   │
    │ Image 2: 78%    │  │             │   │ • Lighting   │
    │ Reference       │  │             │   │ • Exposure   │
    │ Image 3: 65%    │  │             │   │ • Depth      │
    └────────┬────────┘  └──────┬──────┘   │ • Balance    │
             │                  │          │ • Etc.       │
             │                  │          └──────┬───────┘
             └──────────────────┼─────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  COMBINE ALL OUTPUTS  │
                    │  FOR BEST FEEDBACK    │
                    └───────────┬───────────┘
                                │
                                ▼
        ┌───────────────────────────────────────────────────────┐
        │ "Your image echoes [Master A's] composition (92%      │
        │ similar). Your technique is strong (7/10), similar    │
        │ to Reference B which scored 9/10. Ansel would approve │
        │ of your leading line usage."                          │
        └───────────────────────────────────────────────────────┘
```

---

## What Each System Needs

### CLIP (Visual Similarity Finder)

```
INPUTS:
├─ Pre-computed embeddings (in database) ✅ YOU HAVE A SCRIPT
├─ GPU for computation (2-3 sec, or use pre-computed)
└─ Target image

OUTPUTS:
├─ Similar image 1 (92% match)
├─ Similar image 2 (78% match)
└─ Similar image 3 (65% match)

TIME: 5 seconds (without pre-computation) → 1 second (with pre-computation)
```

### LoRA (Specialized Analyzer)

```
INPUTS:
├─ Base vision model (Qwen3-VL-4B) ✅ ALREADY HAVE
├─ LoRA adapter weights (50-500MB) ✅ ALREADY HAVE
├─ Target image
└─ GPU for fast inference

OUTPUTS:
├─ "Leading lines are strong"
├─ "Lighting follows zone system"
├─ "Overall: Ansel-like composition"
└─ Score card

TIME: 3-5 seconds
```

### Dimensional RAG (Technical Scorer)

```
INPUTS:
├─ Target image
├─ Base vision model
├─ Advisor reference profiles ✅ ALREADY HAVE
└─ Comparison database ✅ ALREADY HAVE

OUTPUTS:
├─ Composition: 7/10 (vs ref: 9/10)
├─ Lighting: 6/10 (vs ref: 8/10)
├─ Focus: 8/10 (vs ref: 8/10)
├─ Color: 7/10 (vs ref: 7/10)
├─ Isolation: 8/10 (vs ref: 9/10)
├─ Depth: 7/10 (vs ref: 8/10)
├─ Balance: 7/10 (vs ref: 8/10)
└─ Impact: 6/10 (vs ref: 8/10)

TIME: 5-10 seconds (complex scoring)
```

---

## Current State vs. Desired State

### Current (What You Have Today)

```
┌─────────────────────────────────────────────────────┐
│ User Analysis Request                              │
├─────────────────────────────────────────────────────┤
│ enable_rag=true                                     │
│   → Uses: Dimensional RAG ✅                         │
│   → Uses: LoRA ✅                                    │
│                                                     │
│ enable_rag=false                                    │
│   → Uses: LoRA ✅                                    │
│   → Uses: Baseline (generic) ⚠️                      │
│                                                     │
│ enable_embeddings=true                              │
│   → Works in RAG mode only ⚠️                       │
│   → Requires 5 seconds per embedding computation    │
│                                                     │
│ enable_lora=true                                    │
│   → Uses: LoRA ✅                                    │
│   → Can't add embeddings ❌                         │
└─────────────────────────────────────────────────────┘
```

### Desired (After Phase 1 + Pre-computation)

```
┌─────────────────────────────────────────────────────┐
│ User Analysis Request                              │
├─────────────────────────────────────────────────────┤
│ enable_embeddings=true                              │
│   → Works in ANY mode ✅                            │
│   → Uses pre-computed database lookups (1 sec) ✅  │
│                                                     │
│ combinations:                                       │
│   enable_rag=true + enable_embeddings=true ✅      │
│   enable_lora=true + enable_embeddings=true ✅     │
│   baseline + enable_embeddings=true ✅             │
│   (all combinations possible)                       │
│                                                     │
│ Speed: All under 5 seconds ✅                      │
│ GPU throughput: 10-20 requests/sec ✅              │
└─────────────────────────────────────────────────────┘
```

---

## Performance Comparison

### Time Per Request

```
Current Setup:
┌────────────────────────────────────────────────────┐
│ Baseline alone:              3 seconds              │
│ Baseline + RAG:              8-10 seconds           │
│ LoRA alone:                  3-5 seconds            │
│ LoRA + RAG:                  10-12 seconds          │
│ RAG + CLIP (on-demand):      5-7 seconds            │
│                                                     │
│ Problem: CLIP embedding is expensive (2-3 sec)     │
└────────────────────────────────────────────────────┘

After Pre-computation (Phase 1):
┌────────────────────────────────────────────────────┐
│ Baseline alone:              3 seconds              │
│ Baseline + Embeddings:       4 seconds ⚡          │
│ LoRA alone:                  3-5 seconds            │
│ LoRA + Embeddings:           5 seconds ⚡          │
│ RAG + Embeddings:            6 seconds ⚡          │
│ All three:                   7 seconds ⚡          │
│                                                     │
│ Benefit: 3-5x faster embeddings, new modes!       │
└────────────────────────────────────────────────────┘
```

### GPU Throughput

```
Without Pre-computation:
┌──────────────────────────┐
│ Per-request GPU time:    │
│ • Model load: 2 sec      │
│ • Embedding: 2-3 sec     │
│ • Inference: 3 sec       │
│ Total: 7-8 sec per req   │
│                          │
│ Concurrent requests:     │
│ ~1-2 GPU-bound requests  │
│ before bottleneck        │
└──────────────────────────┘

With Pre-computation:
┌──────────────────────────┐
│ Per-request GPU time:    │
│ • Model load: 1 sec      │
│ • Inference: 3 sec       │
│ • DB lookup: 0.5 sec     │
│ Total: 4-5 sec per req   │
│                          │
│ Concurrent requests:     │
│ ~10-20 requests before   │
│ bottleneck (5x better!)  │
└──────────────────────────┘
```

---

## Decision Tree: Which System for Which Use Case?

```
User wants quick feedback?
├─ YES → Use Embeddings + LoRA (5 sec, visual + technique)
└─ NO
     │
     └─ User wants detailed scoring?
        ├─ YES → Use Dimensional RAG (10 sec, quantitative feedback)
        └─ NO
             │
             └─ User wants everything?
                └─ YES → Use All Three (7 sec, comprehensive)

Best for beginners?
└─ Embeddings + LoRA (most intuitive: similar images + feedback)

Best for power users?
└─ All three (most information)

Best for performance?
└─ Embeddings alone (1 sec lookup, fastest)

Most valuable?
└─ All three combined (visual + feedback + scores)
```

---

## Implementation Roadmap

### Week 1: Setup (40 minutes)

```
[X] Understand concepts (QUICK_REFERENCE.md + PRIMER.md)
[X] Run pre-computation script (15 min)
[ ] Verify database has embeddings
[ ] Test embedding lookups work

Result: 5x faster CLIP queries
```

### Week 2: Integration (2-3 hours)

```
[ ] Add embeddings to BaselineStrategy
[ ] Add embeddings to LoRAStrategy  
[ ] Test all combinations:
    [ ] baseline+embeddings
    [ ] lora+embeddings
    [ ] rag+embeddings
[ ] Benchmark improvements

Result: All 8 mode combinations work
```

### Week 3+: Optimization (Optional)

```
[ ] Create batch setup script
[ ] Add to advisor onboarding
[ ] Documentation for users
[ ] Consider semantic RAG integration

Result: System fully optimized
```

---

## Summary in One Picture

```
Your System = CLIP + LoRA + Dimensional RAG

CLIP alone = "Similar images"
LoRA alone = "You did this well"
Dimensional = "Technical score 7/10"

All three = "Your image matches Master A (visual),
            your technique is strong (LoRA),
            and your score is 7/10 vs reference 9/10
            (dimensional)"

Currently: Missing independent embeddings
Fix: Run pre-computation + enable in all modes
Result: 5x faster + 8 analysis modes
Time: 2-3 hours total work
Value: Highest impact improvement you can make
```

