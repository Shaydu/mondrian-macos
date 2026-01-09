# RAG System Architecture Diagram

## Current State: Two Parallel RAG Systems

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MONDRIAN RAG SYSTEMS                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────┐  ┌───────────────────────────────────┐
│   SYSTEM 1: Caption-Based RAG     │  │   SYSTEM 2: Dimensional RAG       │
│   (Semantic Similarity)           │  │   (Technical Quality)             │
│   Status: ❌ Broken (Missing Link)│  │   Status: ✅ Working              │
└───────────────────────────────────┘  └───────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYSTEM 1: Caption-Based RAG                           │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: Generate Embeddings
┌──────────────────────────────────────┐
│ compute_image_embeddings.py          │
│                                      │
│ Input: Advisor images                │
│ Process: CLIP ViT-B/32               │
│ Output: .npy files (512-dim)         │
└──────────────────────────────────────┘
              ↓
         .npy files saved to disk
              ↓
    ❌ MISSING LINK ❌
    (No ingestion into database)
              ↓
┌──────────────────────────────────────┐
│ image_captions table                 │
│                                      │
│ - id                                 │
│ - job_id                             │
│ - image_path                         │
│ - caption                            │
│ - embedding (BLOB)                   │
│ - metadata                           │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ rag_service.py                       │
│                                      │
│ Endpoints:                           │
│ - /index (caption → embed → store)   │
│ - /search (text query)               │
│ - /search_by_image (image query)     │
└──────────────────────────────────────┘
              ↓
      Cosine Similarity Search
              ↓
    Returns similar images by content


┌─────────────────────────────────────────────────────────────────────────────┐
│                      SYSTEM 2: Dimensional RAG (Active)                      │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: User Uploads Image
┌──────────────────────────────────────┐
│ Job Service (port 5005)              │
│ /upload endpoint                     │
│                                      │
│ Parameters:                          │
│ - image file                         │
│ - advisor=ansel                      │
│ - enable_rag=true                    │
└──────────────────────────────────────┘
              ↓
Step 2: PASS 1 - Initial Analysis
┌──────────────────────────────────────┐
│ AI Advisor Service (port 5100)       │
│                                      │
│ 1. Analyze image (MLX/Ollama)        │
│ 2. Parse JSON response               │
│ 3. Extract dimensional profile:      │
│    - composition_score: 7.0          │
│    - lighting_score: 8.0             │
│    - focus_sharpness_score: 9.0      │
│    - color_harmony_score: 7.5        │
│    - subject_isolation_score: 8.0    │
│    - depth_perspective_score: 7.0    │
│    - visual_balance_score: 8.5       │
│    - emotional_impact_score: 7.5     │
└──────────────────────────────────────┘
              ↓
Step 3: Save Dimensional Profile
┌──────────────────────────────────────┐
│ dimensional_profiles table           │
│                                      │
│ - id                                 │
│ - job_id                             │
│ - advisor_id                         │
│ - image_path                         │
│ - composition_score (REAL)           │
│ - lighting_score (REAL)              │
│ - focus_sharpness_score (REAL)       │
│ - color_harmony_score (REAL)         │
│ - subject_isolation_score (REAL)     │
│ - depth_perspective_score (REAL)     │
│ - visual_balance_score (REAL)        │
│ - emotional_impact_score (REAL)      │
│ - composition_comment (TEXT)         │
│ - lighting_comment (TEXT)            │
│ - ... (comments for each dimension)  │
│ - overall_grade (REAL)               │
│ - image_description (TEXT)           │
└──────────────────────────────────────┘
              ↓
Step 4: Query for Similar Images
┌──────────────────────────────────────┐
│ find_similar_by_dimensions()         │
│                                      │
│ Method: Euclidean distance across    │
│         8-dimensional space          │
│                                      │
│ Distance = √(Σ(score_i - target_i)²)│
│                                      │
│ Returns: Top-k similar images        │
│          sorted by distance          │
└──────────────────────────────────────┘
              ↓
Step 5: Build Comparison Context
┌──────────────────────────────────────┐
│ augment_prompt_with_rag_context()    │
│                                      │
│ For each similar image:              │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ Quantitative Comparison        │   │
│ │                                │   │
│ │ | Dimension    | User | Ref |  │   │
│ │ |--------------|------|-----|  │   │
│ │ | Composition  | 7.0  | 9.0 |  │   │
│ │ | Lighting     | 8.0  | 9.5 |  │   │
│ │ | Focus        | 9.0  | 8.5 |  │   │
│ └────────────────────────────────┘   │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ Qualitative Insights           │   │
│ │                                │   │
│ │ What Worked in Reference:      │   │
│ │ - Composition: Sweeping curves │   │
│ │ - Lighting: Dramatic shadows   │   │
│ └────────────────────────────────┘   │
└──────────────────────────────────────┘
              ↓
Step 6: PASS 2 - Comparative Analysis
┌──────────────────────────────────────┐
│ AI Advisor Service                   │
│                                      │
│ Prompt = Base prompt +               │
│          Dimensional context         │
│                                      │
│ LLM generates feedback with:         │
│ - Comparative language               │
│ - Specific dimensional references    │
│ - Actionable improvements            │
│                                      │
│ Example:                             │
│ "Your composition (7.0/10) follows   │
│  rule of thirds, but unlike          │
│  Reference #1 (9.0/10, +2.0 delta)   │
│  which uses sweeping S-curves..."    │
└──────────────────────────────────────┘
              ↓
         HTML Output


┌─────────────────────────────────────────────────────────────────────────────┐
│                          THE MISSING LINK (Fixed)                            │
└─────────────────────────────────────────────────────────────────────────────┘

BEFORE (Broken):
┌──────────────────────────────────────┐
│ compute_image_embeddings.py          │
│ Generates .npy files                 │
└──────────────────────────────────────┘
              ↓
         .npy files on disk
              ↓
         ❌ NOWHERE ❌
         (Not in database)
              ↓
┌──────────────────────────────────────┐
│ rag_service.py                       │
│ Queries database → finds nothing     │
└──────────────────────────────────────┘


AFTER (Fixed - Option 1):
┌──────────────────────────────────────┐
│ compute_image_embeddings_to_db.py    │
│                                      │
│ 1. Generate CLIP embeddings          │
│ 2. Insert into database              │
│    (one atomic operation)            │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ image_captions table                 │
│ ✅ Embeddings stored                 │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ rag_service.py                       │
│ ✅ Can query embeddings              │
└──────────────────────────────────────┘


AFTER (Fixed - Option 2):
┌──────────────────────────────────────┐
│ compute_image_embeddings.py          │
│ Generates .npy files                 │
└──────────────────────────────────────┘
              ↓
         .npy files on disk
              ↓
┌──────────────────────────────────────┐
│ ingest_npy_embeddings.py             │
│ ✅ NEW SCRIPT                        │
│                                      │
│ 1. Find all .npy files               │
│ 2. Load embeddings                   │
│ 3. Insert into database              │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ image_captions table                 │
│ ✅ Embeddings stored                 │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ rag_service.py                       │
│ ✅ Can query embeddings              │
└──────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    FUTURE: Hybrid RAG System (Recommended)                   │
└─────────────────────────────────────────────────────────────────────────────┘

User uploads image
      ↓
┌──────────────────────────────────────┐
│ AI Advisor Service                   │
│                                      │
│ enable_rag=true                      │
│ use_semantic_rag=true                │
└──────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Parallel RAG Queries                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────┐   ┌─────────────────────────┐     │
│  │ Dimensional RAG         │   │ Semantic RAG            │     │
│  │                         │   │                         │     │
│  │ Query:                  │   │ Query:                  │     │
│  │ Find images with        │   │ Find images with        │     │
│  │ similar scores          │   │ similar content         │     │
│  │                         │   │                         │     │
│  │ Results:                │   │ Results:                │     │
│  │ 1. dunes_oceano.jpg     │   │ 1. desert_shrub.jpg     │     │
│  │    (distance: 2.1)      │   │    (similarity: 0.92)   │     │
│  │    Similar composition  │   │    Similar subject      │     │
│  │                         │   │                         │     │
│  │ 2. death_valley.jpg     │   │ 2. joshua_tree.jpg      │     │
│  │    (distance: 2.8)      │   │    (similarity: 0.87)   │     │
│  │    Similar lighting     │   │    Similar landscape    │     │
│  └─────────────────────────┘   └─────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
      ↓
┌──────────────────────────────────────┐
│ Merge Results                        │
│                                      │
│ Combine dimensional + semantic       │
│ Deduplicate and rank                 │
│                                      │
│ Final Context:                       │
│ - Technical comparison (scores)      │
│ - Content comparison (subject)       │
│ - Best of both worlds                │
└──────────────────────────────────────┘
      ↓
   Enhanced Analysis


┌─────────────────────────────────────────────────────────────────────────────┐
│                         Database Schema Overview                             │
└─────────────────────────────────────────────────────────────────────────────┘

image_captions (Caption-Based RAG)
├── id (TEXT PRIMARY KEY)
├── job_id (TEXT)
├── image_path (TEXT)
├── caption (TEXT) ← Generated by caption_service.py
├── caption_type (TEXT) ← 'detailed' or 'clip_embedding'
├── embedding (BLOB) ← 384-dim or 512-dim vector
├── metadata (JSON)
└── created_at (TIMESTAMP)

Current Records: 20
Embedding Dimension: 384 (sentence-transformers) or 512 (CLIP)
Search Method: Cosine similarity on embeddings


dimensional_profiles (Dimensional RAG)
├── id (TEXT PRIMARY KEY)
├── job_id (TEXT)
├── advisor_id (TEXT)
├── image_path (TEXT)
├── Quantitative Scores (8 dimensions)
│   ├── composition_score (REAL 0-10)
│   ├── lighting_score (REAL 0-10)
│   ├── focus_sharpness_score (REAL 0-10)
│   ├── color_harmony_score (REAL 0-10)
│   ├── subject_isolation_score (REAL 0-10)
│   ├── depth_perspective_score (REAL 0-10)
│   ├── visual_balance_score (REAL 0-10)
│   └── emotional_impact_score (REAL 0-10)
├── Qualitative Comments (8 dimensions)
│   ├── composition_comment (TEXT)
│   ├── lighting_comment (TEXT)
│   └── ... (one for each dimension)
├── overall_grade (REAL)
├── image_description (TEXT)
├── analysis_html (TEXT)
└── created_at (TIMESTAMP)

Current Records: 16 (Ansel only)
Search Method: Euclidean distance in 8-dimensional space
Distance Formula: √(Σ(score_i - target_i)²)


┌─────────────────────────────────────────────────────────────────────────────┐
│                         Service Architecture                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              Services Stack                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ Job Service (port 5005)                                             │    │
│  │ - Receives image uploads                                            │    │
│  │ - Manages job queue                                                 │    │
│  │ - Calls AI Advisor Service                                          │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                   ↓                                          │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ AI Advisor Service (port 5100)                                      │    │
│  │ - Orchestrates analysis                                             │    │
│  │ - Calls RAG services (dimensional + semantic)                       │    │
│  │ - Runs vision model (MLX/Ollama)                                    │    │
│  │ - Extracts dimensional profiles                                     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│            ↓                                    ↓                            │
│  ┌─────────────────────────┐      ┌─────────────────────────────────┐      │
│  │ Dimensional RAG         │      │ Caption-Based RAG               │      │
│  │ (Built-in)              │      │ (External Service)              │      │
│  │                         │      │                                 │      │
│  │ - Query DB directly     │      │  ┌───────────────────────────┐ │      │
│  │ - Euclidean distance    │      │  │ RAG Service (port 5400)   │ │      │
│  │ - dimensional_profiles  │      │  │ - /index                  │ │      │
│  │   table                 │      │  │ - /search                 │ │      │
│  │                         │      │  │ - /search_by_image        │ │      │
│  └─────────────────────────┘      │  └───────────────────────────┘ │      │
│                                    │            ↓                    │      │
│                                    │  ┌───────────────────────────┐ │      │
│                                    │  │ Caption Service (5200)    │ │      │
│                                    │  │ - Generate captions       │ │      │
│                                    │  └───────────────────────────┘ │      │
│                                    │            ↓                    │      │
│                                    │  ┌───────────────────────────┐ │      │
│                                    │  │ Embedding Service (5300)  │ │      │
│                                    │  │ - sentence-transformers   │ │      │
│                                    │  │ - 384-dim embeddings      │ │      │
│                                    │  └───────────────────────────┘ │      │
│                                    └─────────────────────────────────┘      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         Key Takeaways                                        │
└─────────────────────────────────────────────────────────────────────────────┘

1. ✅ You correctly identified the missing ingestion link
   - compute_image_embeddings.py generates .npy files
   - But they're never loaded into the database
   - So rag_service.py can't find them

2. ✅ Your system is already using a different RAG system
   - Dimensional RAG is active and working
   - It doesn't need caption embeddings
   - It uses dimensional scores instead

3. ✅ Both RAG systems have value
   - Dimensional RAG: Technical quality comparison
   - Semantic RAG: Subject matter similarity
   - They're complementary, not competing

4. ✅ The fix is straightforward
   - Use compute_image_embeddings_to_db.py (one-step)
   - OR use ingest_npy_embeddings.py (two-step)
   - Then integrate semantic RAG into ai_advisor_service.py

5. ✅ Future architecture: Hybrid RAG
   - Use both systems together
   - Dimensional + Semantic = Powerful analysis
   - Let user choose which to enable
