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

## RAG Preprocessing Scripts Location

All scripts for RAG preprocessing, embedding generation, and database population are now located in:

    tools/rag/

This includes:
- compute_image_embeddings.py
- compute_image_embeddings_to_db.py
- ingest_npy_embeddings.py
- index_ansel_dimensional_profiles.py

Use this directory for all future RAG-related tooling and batch processing.

---

## Detailed Preprocessing Data Flow

### End-to-End Pipeline

1. **Input: Advisor Reference Images**
   - Source: Curated directories (e.g., advisor_artworks/{advisor_id}, source/advisor/{category}/{advisor_id})
   - Format: JPEG/PNG images, optionally with metadata (EXIF, sidecar files, or a manifest)

2. **Preprocessing Scripts (tools/rag/)**
   - Scripts Used:
     - compute_image_embeddings.py / compute_image_embeddings_to_db.py
     - ingest_npy_embeddings.py
     - index_ansel_dimensional_profiles.py
   - Purpose:
     - Analyze each advisor image to extract:
       - Embeddings (vector representations, e.g., CLIP or custom model)
       - Dimensional scores (composition, lighting, etc.)
       - Qualitative comments (if LLM is used for analysis)
       - Metadata (title, date_taken, description, etc.)

3. **Processing Steps**
   - Image Loading: Each script loads images from the advisor directories.
   - Embedding Generation:
     - Uses a vision model (e.g., CLIP, MLX, or custom) to generate embeddings for each image.
     - Output: .npy files (if using numpy) or direct DB insertion.
   - Dimensional Analysis:
     - May use an LLM (e.g., MLX model or OpenAI GPT) to analyze the image and produce scores/comments for each rubric dimension.
     - Output: Structured data (scores, comments).
   - Metadata Extraction:
     - Reads metadata from EXIF, sidecar files, or a manifest (CSV/JSON/YAML).
     - Output: title, date_taken, description, etc.

4. **Output: Database Population**
   - Destination:
     - dimensional_profiles table in mondrian.db
   - Fields Populated:
     - advisor_id, image_path, embedding, dimensional scores, comments, metadata (title, date_taken, description, etc.)
   - Alternative Output:
     - .npy embedding files (if not writing directly to DB)

5. **Usage in Inference**
   - When a user uploads an image, the system:
     - Processes the user image to generate an embedding/dimensional profile.
     - Searches the database for similar advisor images using the precomputed embeddings/profiles.
     - Retrieves metadata for the matched images to use in prompt augmentation and user-facing output.

### LLMs/Models Used
- Vision Model: For embeddings (e.g., CLIP, MLX, or other vision transformer)
- LLM (optional): For generating dimensional comments or extracting qualitative feedback (could be MLX, OpenAI, or another LLM, depending on your script)

### Summary Table

| Step                | Input                | Processing (Script/Model)         | Output/Storage                |
|---------------------|----------------------|-----------------------------------|-------------------------------|
| Image Ingestion     | Advisor images       | Python scripts (tools/rag/)       | Loaded image objects          |
| Embedding           | Image                | Vision model (CLIP/MLX)           | .npy file or DB field         |
| Dimensional Scoring | Image                | LLM (MLX/OpenAI, etc.)            | Scores/comments in DB         |
| Metadata Extraction | Image/manifest/EXIF  | Python script                     | Metadata fields in DB         |
| DB Population       | All above            | Python script                     | dimensional_profiles table    |

---

## See Also
- [dimensional-rag-implementation.md](dimensional-rag-implementation.md)
- [rag-system-analysis.md](rag-system-analysis.md)
- [rag-diagrams.md](rag-diagrams.md)
- [requirements/rag.md](../requirements/rag.md)
- [guides/rag-comparison.md](../guides/rag-comparison.md)

All RAG documentation is now consolidated here. Please update this file for future RAG architecture changes.
