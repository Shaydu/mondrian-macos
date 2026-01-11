# Mondrian RAG Architecture & Data Flow

## Overview

Mondrian supports Retrieval-Augmented Generation (RAG) for advisor-specific, image-specific feedback. The system uses preprocessed advisor images and embeddings, and augments user queries with context from similar reference images.

---

## Data Flow Summary

### 1. Preprocessing Pipeline (Reference Data)

- **Reference Images:**
  - Stored in: `advisor_artworks/{advisor_id}` or `source/advisor/{category}/{advisor_id}`
  - Each advisor has a curated set of images.
- **Embeddings/Dimensional Profiles:**
  - Scripts (e.g., `compute_image_embeddings.py`, `ingest_npy_embeddings.py`) generate embeddings or dimensional scores for each advisor image.
  - Embeddings are stored in the database (e.g., `dimensional_profiles` table) or as `.npy` files.
  - Dimensional profiles include 8 rubric scores (composition, lighting, etc.) and qualitative comments.

### 2. Inference Query (User Upload)

- **User uploads an image** and selects an advisor (and optionally enables RAG).
- **If RAG is enabled:**
  1. The user image is processed by the MLX model to extract techniques or embeddings.
  2. The system searches for the most similar advisor images using precomputed embeddings/dimensional profiles.
  3. The advisor's prompt is augmented with comparative context from these similar images (quantitative and qualitative).
  4. The MLX model generates feedback using the augmented prompt and the user image.
- **If RAG is disabled:**
  - The MLX model analyzes the user image using only the advisor's base prompt (no retrieval).

---

## Data Flow Diagrams

### Preprocessing Pipeline

```
Advisor Images (curated)
      ↓
[compute_image_embeddings.py / ingest_npy_embeddings.py]
      ↓
Embeddings & Dimensional Profiles
      ↓
[Database: dimensional_profiles table]
```

### Inference Query (RAG Enabled)

```
User Uploads Image
      ↓
[MLX Model: extract techniques/embedding]
      ↓
[Similarity Search: compare to advisor embeddings]
      ↓
Top-N Similar Advisor Images
      ↓
[Prompt Augmentation: add comparative context]
      ↓
[MLX Model: generate feedback]
      ↓
User Receives Advisor-Specific, Comparative Analysis
```

---

## Key Tables & Files

- **Advisor Images:** `advisor_artworks/{advisor_id}/`, `source/advisor/{category}/{advisor_id}/`
- **Embeddings:** `.npy` files, `dimensional_profiles` table
- **Preprocessing Scripts:** `compute_image_embeddings.py`, `ingest_npy_embeddings.py`, `compute_image_embeddings_to_db.py`
- **RAG Query Logic:** `ai_advisor_service.py`, `technique_rag.py`, `rag_service.py`

---

## Consolidated Notes

- All advisor reference images are preprocessed (embeddings/dimensional scores) before inference.
- User images are always processed at query time.
- RAG-enabled queries retrieve and use similar advisor images to augment the prompt.
- No advisor images are reprocessed at query time; only user images are processed live.

---

## See Also
- [dimensional-rag-implementation.md](dimensional-rag-implementation.md)
- [rag-system-analysis.md](rag-system-analysis.md)
- [rag-diagrams.md](rag-diagrams.md)
- [requirements/rag.md](../requirements/rag.md)
- [guides/rag-comparison.md](../guides/rag-comparison.md)

All RAG documentation is now consolidated here. Please update this file for future RAG architecture changes.
