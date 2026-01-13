# Mondrian Data Flow

Brief overview of how system prompts, advisor prompts, and image analysis flow through the system for both baseline and RAG modes.

---

## Configuration & Analysis Modes

Mondrian supports three analysis modes that can be enabled/disabled independently:

### 1. **RAG Mode** (Distribution-Based Retrieval)
- **What it does**: 2-pass analysis comparing user image to advisor's reference portfolio using dimensional statistics
- **Enable globally**: Set `RAG_ENABLED = True` in `mondrian/config.py`
- **Enable per-request**: Pass `enable_rag=true` in upload/analyze API request
- **Requires**: Indexed reference images in `dimensional_profiles` table (see RAG Preprocessing below)

### 2. **Embeddings Mode** (Visual Similarity)
- **What it does**: Uses CLIP embeddings for visual similarity matching (separate from dimensional RAG)
- **Enable globally**: Set environment variable `EMBEDDINGS_ENABLED=true` or edit `config.py`
- **Enable per-request**: Pass `enable_embeddings=true` in analyze API request
- **Requires**: Pre-computed embeddings in database

### 3. **Baseline Mode** (No Retrieval)
- **What it does**: Single-pass analysis using only advisor prompt, no reference comparisons
- **Enable**: Set both `enable_rag=false` and `enable_embeddings=false`
- **Default**: When RAG/embeddings are disabled in config and not specified in request
- **Requires**: Nothing (standalone analysis)

**Note**: RAG and Embeddings can be used together or independently. When both are enabled, the system uses hybrid retrieval combining dimensional and visual similarity.

---

## System Prompt Storage

**Storage Location:** Database (`config` table)
- Key: `system_prompt`
- Loaded at service startup: [ai_advisor_service.py:130](../../mondrian/ai_advisor_service.py#L130)
- Retrieval: `get_config(DB_PATH, "system_prompt")` via [sqlite_helper.py:161](../../mondrian/sqlite_helper.py#L161)

**Advisor Prompt Storage:** Database (`advisors` table)
- Columns: `id`, `name`, `bio`, `years`, `prompt`, `focus_areas`, `category`, etc.
- Retrieval: `get_advisor_from_db(db_path, advisor_id)` via [sqlite_helper.py:193](../../mondrian/sqlite_helper.py#L193)

---

## Baseline Analysis Flow (Single-Pass, No RAG)

```
┌─────────────────────────────────────┐
│ User Request                        │
│ - Image upload                      │
│ - Advisor selection                 │
│ - enable_rag=false                  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ AI Advisor Service                  │
│ /analyze endpoint                   │
│ _analyze_image_baseline()           │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Load Prompts from Database          │
│                                     │
│ 1. SYSTEM_PROMPT (from config)      │
│    - Contains JSON formatting rules │
│    - 8 dimensional analysis schema  │
│                                     │
│ 2. Advisor Prompt (from advisors)   │
│    - Advisor-specific guidance      │
│    - Style preferences              │
│    - Focus areas                    │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Build Full Prompt                   │
│                                     │
│ full_prompt = (                     │
│   SYSTEM_PROMPT                     │
│     .replace("<AdvisorName>", id)   │
│   + "\n\n"                          │
│   + advisor_prompt                  │
│   + "\n\nAnalyze the image."        │
│ )                                   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ MLX Model Inference                 │
│ run_model_mlx()                     │
│                                     │
│ - Model: Qwen2-VL-2B-Instruct       │
│ - Input: full_prompt + image        │
│ - Output: JSON response             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Parse & Convert Response            │
│                                     │
│ 1. parse_json_response()            │
│ 2. json_to_html()                   │
│                                     │
│ Output: HTML analysis               │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Return to User                      │
│ - HTML formatted analysis           │
│ - Dimensional scores & comments     │
│ - Overall grade & recommendations   │
└─────────────────────────────────────┘
```

---

## RAG Analysis Flow (2-Pass, Distribution-Based)

```
┌─────────────────────────────────────┐
│ User Request                        │
│ - Image upload                      │
│ - Advisor selection                 │
│ - enable_rag=true                   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ AI Advisor Service                  │
│ /analyze endpoint                   │
│ _analyze_image_rag()                │
└──────────────┬──────────────────────┘
               ↓
╔═════════════════════════════════════╗
║ PASS 1: Extract Dimensional Profile ║
╚══════════════┬══════════════════════╝
               ↓
┌─────────────────────────────────────┐
│ Load Minimal Extraction Prompt      │
│ get_dimensional_extraction_prompt() │
│                                     │
│ - Simplified prompt for quick       │
│   dimensional analysis only         │
│ - No advisor-specific guidance      │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ MLX Model Inference (Pass 1)        │
│                                     │
│ - Model: Qwen2-VL-2B-Instruct       │
│ - Input: extraction_prompt + image  │
│ - Output: JSON with 8 scores +      │
│           8 comments                │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Extract & Save Profile              │
│                                     │
│ 1. parse_json_response()            │
│ 2. extract_dimensional_profile()    │
│ 3. save_dimensional_profile()       │
│                                     │
│ Saves to: dimensional_profiles table│
│ - 8 dimensional scores              │
│ - 8 dimensional comments            │
│ - job_id, advisor_id, image_path    │
└──────────────┬──────────────────────┘
               ↓
╔═════════════════════════════════════╗
║ DISTRIBUTION ANALYSIS & RETRIEVAL   ║
╚══════════════┬══════════════════════╝
               ↓
┌─────────────────────────────────────┐
│ Calculate Advisor Statistics        │
│ calculate_advisor_dimension_stats() │
│                                     │
│ For each dimension:                 │
│ - Query all advisor reference images│
│ - Calculate mean & std deviation    │
│                                     │
│ Database: dimensional_profiles      │
│   WHERE advisor_id = selected       │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Compare User to Distribution        │
│ compare_user_to_distribution()      │
│                                     │
│ Identify dimensions where:          │
│   user_score < (mean - threshold*std)│
│                                     │
│ Result: List of dimensions needing  │
│         improvement                 │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Find Representative Images          │
│ find_representative_images_by_      │
│   distribution()                    │
│                                     │
│ For each weak dimension:            │
│ - Find advisor image with highest   │
│   score in that dimension           │
│ - Include metadata (title, date,    │
│   location, significance)           │
│                                     │
│ Result: Dict mapping dimension      │
│         to best example image       │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Augment Prompt with Context         │
│ augment_prompt_with_distribution_   │
│   context()                         │
│                                     │
│ Adds to advisor_prompt:             │
│ - Statistical comparisons           │
│   (user score vs mean ± std)        │
│ - Representative image examples     │
│ - Dimension-specific comments       │
│ - Metadata (title, significance)    │
│                                     │
│ Result: augmented_prompt            │
└──────────────┬──────────────────────┘
               ↓
╔═════════════════════════════════════╗
║ PASS 2: Comparative Analysis        ║
╚══════════════┬══════════════════════╝
               ↓
┌─────────────────────────────────────┐
│ Load Prompts from Database          │
│                                     │
│ 1. SYSTEM_PROMPT (from config)      │
│ 2. Advisor Prompt (from advisors)   │
│    + RAG augmentation               │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Build Full Augmented Prompt         │
│                                     │
│ full_prompt = (                     │
│   SYSTEM_PROMPT                     │
│     .replace("<AdvisorName>", id)   │
│   + "\n\n"                          │
│   + augmented_advisor_prompt        │
│   + "\n\nAnalyze the image."        │
│ )                                   │
│                                     │
│ augmented_advisor_prompt contains:  │
│ - Original advisor guidance         │
│ - Statistical context               │
│ - Representative examples           │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ MLX Model Inference (Pass 2)        │
│                                     │
│ - Model: Qwen2-VL-2B-Instruct       │
│ - Input: augmented_prompt + image   │
│ - Output: JSON with comparative     │
│           analysis                  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Parse & Convert Response            │
│                                     │
│ 1. parse_json_response()            │
│ 2. json_to_html()                   │
│    - Includes similar_images_data   │
│    - Shows representative examples  │
│                                     │
│ Output: HTML analysis with context  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Return to User                      │
│ - HTML formatted comparative        │
│   analysis                          │
│ - Statistical comparisons           │
│ - References to representative      │
│   examples                          │
│ - Dimensional scores & comments     │
│ - Overall grade & recommendations   │
└─────────────────────────────────────┘
```

---

## RAG Preprocessing (Reference Image Indexing)

This happens **before** any user uploads - it builds the reference database for RAG comparisons.

```
┌─────────────────────────────────────┐
│ Advisor Reference Images            │
│                                     │
│ Location: source/advisor/           │
│           {category}/{advisor_id}/  │
│                                     │
│ Optional: metadata.yaml             │
│ - image_title                       │
│ - date_taken                        │
│ - location                          │
│ - image_significance                │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Indexing Script                     │
│                                     │
│ tools/rag/index_with_metadata.py    │
│   (Recommended - includes metadata) │
│                                     │
│ OR                                  │
│                                     │
│ tools/rag/index_ansel_dimensional_  │
│   profiles.py                       │
│   (Legacy - no metadata)            │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ For Each Reference Image:           │
│                                     │
│ 1. Call AI Advisor Service          │
│    /analyze endpoint                │
│                                     │
│ 2. Extract dimensional profile:     │
│    - 8 scores (0-10 scale)          │
│    - 8 comments                     │
│    - image_description              │
│                                     │
│ 3. Merge with metadata (if using    │
│    index_with_metadata.py)          │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│ Save to Database                    │
│                                     │
│ Table: dimensional_profiles         │
│                                     │
│ Columns:                            │
│ - id, job_id, advisor_id            │
│ - image_path                        │
│ - 8 dimensional scores              │
│ - 8 dimensional comments            │
│ - overall_grade                     │
│ - image_description                 │
│ - image_title (metadata)            │
│ - date_taken (metadata)             │
│ - location (metadata)               │
│ - image_significance (metadata)     │
│ - techniques (JSON)                 │
│ - analysis_html                     │
│ - created_at                        │
└─────────────────────────────────────┘
```

---

## Key Database Tables

### `config` Table
- Stores system-level configuration
- Key column: `key` (e.g., "system_prompt")
- Value column: `value` (TEXT)

### `advisors` Table
- Stores advisor metadata and prompts
- Key columns: `id`, `name`, `prompt`
- Metadata: `bio`, `years`, `focus_areas`, `category`, URLs

### `dimensional_profiles` Table
- Stores dimensional analysis for both reference and user images
- Used by RAG for distribution-based comparison
- Key columns:
  - Identity: `id`, `job_id`, `advisor_id`, `image_path`
  - Scores: 8 dimensional scores (0-10 scale)
  - Comments: 8 dimensional comments
  - Metadata: `image_title`, `date_taken`, `location`, `image_significance`
  - Summary: `overall_grade`, `image_description`, `analysis_html`
  - Techniques: `techniques` (JSON)

---

## Key Differences: Baseline vs RAG vs Embeddings

| Aspect | Baseline | RAG (Dimensional) | Embeddings (Visual) |
|--------|----------|-------------------|---------------------|
| **Passes** | Single-pass | 2-pass | 1-pass with retrieval |
| **Prompt** | System + Advisor | System + Advisor + RAG context | System + Advisor + visual examples |
| **Context** | No reference images | Statistical comparison + representative examples | Visually similar reference images |
| **Retrieval Method** | None | Dimensional distribution analysis | CLIP embedding similarity |
| **Database Queries** | None during analysis | Query dimensional_profiles for statistics | Query embeddings table |
| **Analysis Time** | ~5-15 seconds | ~15-30 seconds (2 model calls + DB queries) | ~10-20 seconds (1 call + embedding search) |
| **Output** | Standalone analysis | Comparative analysis with references | Analysis with visually similar examples |
| **Prerequisites** | None | Requires indexed dimensional profiles | Requires pre-computed CLIP embeddings |
| **Best For** | Quick feedback | Dimensional improvement guidance | Style/composition matching |

**Hybrid Mode**: Both RAG and Embeddings can be enabled together for comprehensive retrieval combining dimensional and visual similarity.

---

## Related Documentation

- [rag.md](rag.md) - Detailed RAG architecture
- [architecture.md](architecture.md) - Overall system architecture
- [../requirements/rag.md](../requirements/rag.md) - RAG requirements

**Last Updated:** 2026-01-13
