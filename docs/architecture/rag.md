# Mondrian RAG Architecture & Data Flow

## Overview

Mondrian supports Retrieval-Augmented Generation (RAG) for advisor-specific, image-specific feedback. The system uses a **distribution-based dimensional RAG approach** that compares user images against an advisor's portfolio using statistical analysis and dimensional profiles.

The RAG system uses a **2-pass analysis workflow**:
1. **Pass 1**: Extract dimensional profile from user image
2. **Pass 2**: Compare to advisor's portfolio distribution and generate comparative feedback

---

## Data Flow Summary

### 1. Preprocessing Pipeline (Reference Data)

- **Reference Images:**
  - Stored in: `source/advisor/{category}/{advisor_id}/` (e.g., `source/advisor/photographer/ansel/`)
  - Each advisor has a curated set of reference images
  - Images can include metadata files (YAML) with title, date, location, significance

- **Dimensional Profiles:**
  - Scripts analyze each advisor image using the AI Advisor Service
  - Extracts 8 dimensional scores (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact)
  - Stores scores, comments, and metadata in `dimensional_profiles` table
  - Metadata fields: `image_title`, `date_taken`, `location`, `image_significance`, `image_description`

### 2. Inference Query (User Upload)

- **User uploads an image** and selects an advisor with `enable_rag=true`
- **RAG-enabled workflow:**
  1. **Pass 1**: User image is analyzed to extract dimensional profile (8 scores + comments)
  2. User's dimensional profile is saved to database
  3. System calculates advisor's portfolio statistics (mean, std) for each dimension
  4. System identifies dimensions where user score falls below advisor's distribution (user_score < advisor_mean - threshold)
  5. System finds representative images (best examples) for each dimension needing improvement
  6. **Pass 2**: Advisor prompt is augmented with statistical comparisons and representative examples
  7. MLX model generates feedback using augmented prompt with comparative context
- **If RAG is disabled (`enable_rag=false`):**
  - Single-pass analysis using only the advisor's base prompt (no retrieval/comparison)

---

## Data Flow Diagrams

### Preprocessing Pipeline

```
Advisor Reference Images (+ metadata.yaml)
      ↓
[tools/rag/index_ansel_dimensional_profiles.py]
  OR
[tools/rag/index_with_metadata.py] (recommended - includes metadata)
      ↓
AI Advisor Service /analyze endpoint
      ↓
Extract Dimensional Profile:
  - 8 dimensional scores (0-10)
  - 8 dimensional comments
  - image_description
  - Metadata (if using index_with_metadata.py):
    - image_title
    - date_taken
    - location
    - image_significance
      ↓
[Database: dimensional_profiles table]
```

### Inference Query (RAG Enabled)

```
User Uploads Image (enable_rag=true)
      ↓
┌──────────────────────────────────────┐
│ PASS 1: Extract Dimensional Profile  │
│                                      │
│ - Analyze image with MLX model       │
│ - Extract 8 dimensional scores       │
│ - Extract dimensional comments       │
│ - Save profile to database           │
└──────────────────────────────────────┘
      ↓
┌──────────────────────────────────────┐
│ Distribution Analysis                │
│                                      │
│ - Calculate advisor portfolio stats  │
│   (mean, std) for each dimension     │
│ - Compare user scores to distribution│
│ - Identify dimensions needing        │
│   improvement (below threshold)      │
│ - Find representative images for     │
│   each dimension                     │
└──────────────────────────────────────┘
      ↓
┌──────────────────────────────────────┐
│ Prompt Augmentation                  │
│                                      │
│ - Add statistical comparisons        │
│ - Add representative examples        │
│ - Add dimension-specific context     │
└──────────────────────────────────────┘
      ↓
┌──────────────────────────────────────┐
│ PASS 2: Generate Comparative Feedback│
│                                      │
│ - MLX model with augmented prompt    │
│ - Provides comparative analysis      │
│ - References representative examples │
└──────────────────────────────────────┘
      ↓
User Receives Advisor-Specific, Comparative Analysis
```

---

## Key Components

### Database Schema: dimensional_profiles

The `dimensional_profiles` table stores dimensional analysis data for both reference images and user images:

```sql
CREATE TABLE dimensional_profiles (
    -- Identity
    id TEXT PRIMARY KEY,
    job_id TEXT,
    advisor_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    
    -- 8 Dimensional Scores (0-10)
    composition_score REAL,
    lighting_score REAL,
    focus_sharpness_score REAL,
    color_harmony_score REAL,
    subject_isolation_score REAL,
    depth_perspective_score REAL,
    visual_balance_score REAL,
    emotional_impact_score REAL,
    
    -- 8 Dimensional Comments
    composition_comment TEXT,
    lighting_comment TEXT,
    focus_sharpness_comment TEXT,
    color_harmony_comment TEXT,
    subject_isolation_comment TEXT,
    depth_perspective_comment TEXT,
    visual_balance_comment TEXT,
    emotional_impact_comment TEXT,
    
    -- Summary
    overall_grade TEXT,
    image_description TEXT,
    analysis_html TEXT,
    
    -- Rich Metadata (for reference images)
    image_title TEXT,
    date_taken TEXT,
    location TEXT,
    image_significance TEXT,
    
    -- Technique Data (JSON)
    techniques TEXT,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(advisor_id, image_path)
)
```

### Key Functions

**Distribution-Based RAG Functions** (in `json_to_html_converter.py`):
- `find_representative_images_by_distribution()`: Finds best example images for dimensions needing improvement
- `calculate_advisor_dimension_statistics()`: Calculates mean/std for each dimension in advisor's portfolio
- `compare_user_to_distribution()`: Compares user scores to advisor distribution
- `augment_prompt_with_distribution_context()`: Adds statistical comparisons to prompt

**Analysis Functions** (in `ai_advisor_service.py`):
- `_analyze_image_rag()`: 2-pass RAG workflow
- `extract_dimensional_profile_from_json()`: Extracts scores/comments from LLM JSON
- `save_dimensional_profile()`: Saves profile to database

---

## RAG Preprocessing Scripts

All scripts for RAG preprocessing are located in:

    tools/rag/

### Recommended Scripts

1. **`index_with_metadata.py`** (Recommended)
   - Analyzes images and includes metadata from YAML files
   - Populates: image_title, date_taken, location, image_significance
   - Usage:
     ```bash
     python3 tools/rag/index_with_metadata.py \
       --advisor ansel \
       --metadata-file mondrian/source/advisor/photographer/ansel/metadata.yaml
     ```

2. **`index_ansel_dimensional_profiles.py`**
   - Analyzes images but does NOT include metadata
   - Only populates dimensional scores/comments
   - Usage:
     ```bash
     python3 tools/rag/index_ansel_dimensional_profiles.py
     ```

### Other Scripts (Legacy/Alternative)

- `compute_image_embeddings.py` - Generates CLIP embeddings (not currently used in dimensional RAG)
- `compute_image_embeddings_to_db.py` - Alternative embedding generation
- `ingest_npy_embeddings.py` - Ingests pre-generated embeddings

---

## Detailed Workflow

### Preprocessing (Indexing Reference Images)

1. **Input**: Advisor reference images + optional metadata.yaml
   - Images: JPEG/PNG files in `source/advisor/{category}/{advisor_id}/`
   - Metadata: YAML file with title, date_taken, location, significance, description

2. **Processing**:
   - Script calls AI Advisor Service `/analyze` endpoint for each image
   - Service analyzes image and extracts dimensional profile
   - Profile is saved to `dimensional_profiles` table
   - If using `index_with_metadata.py`, metadata from YAML is merged into profile

3. **Output**: 
   - `dimensional_profiles` table populated with:
     - Dimensional scores (8 dimensions, 0-10 scale)
     - Dimensional comments (qualitative feedback)
     - Metadata (title, date, location, significance)
     - Analysis HTML

### Inference (User Image Analysis with RAG)

**Pass 1: Dimensional Profile Extraction**
1. User uploads image with `enable_rag=true`
2. AI Advisor Service analyzes image using minimal dimensional extraction prompt
3. System extracts 8 dimensional scores and comments from JSON response
4. Profile is saved to `dimensional_profiles` table (temporary, for comparison)

**Distribution Analysis & Representative Image Selection**
1. System queries `dimensional_profiles` table for all advisor reference images
2. Calculates statistical distribution (mean, std) for each dimension
3. Compares user scores to advisor distribution
4. Identifies dimensions where: `user_score < advisor_mean - threshold_std * advisor_std`
5. For each dimension needing improvement, finds representative image (best example)
6. Representative images are selected based on highest score in that dimension

**Pass 2: Comparative Analysis**
1. System augments advisor prompt with:
   - Statistical comparisons (user score vs advisor mean/std)
   - Representative examples for each dimension needing improvement
   - Dimension-specific comments from representative images
2. MLX model analyzes user image with augmented prompt
3. Generates comparative feedback referencing representative examples
4. Returns HTML analysis with comparative context

---

## Metadata Fields

The `dimensional_profiles` table includes metadata fields for reference images:

- **`image_title`**: Title of the artwork (e.g., "The Tetons and the Snake River")
- **`date_taken`**: Year or date when image was created (e.g., "1942")
- **`location`**: Geographic location where image was taken
- **`image_significance`**: Historical or artistic significance of the image
- **`image_description`**: Descriptive text about the image

**To populate these fields:**
- Use `tools/rag/index_with_metadata.py` script
- Provide `metadata.yaml` file with image metadata
- Script merges metadata from YAML into dimensional profiles

**Example metadata.yaml structure:**
```yaml
images:
- filename: Adams_The_Tetons_and_the_Snake_River.jpg
  title: Adams The Tetons and the Snake River
  date_taken: '1942'
  description: Ansel Adams The Tetons and the Snake River...
  location: '43.800000'
  significance: ''
```

---

## Summary Table

| Step | Input | Processing | Output/Storage |
|------|-------|------------|----------------|
| Image Ingestion | Advisor images | Python scripts (tools/rag/) | Loaded image objects |
| Dimensional Analysis | Image | AI Advisor Service (MLX model) | Scores/comments in DB |
| Metadata Extraction | metadata.yaml | index_with_metadata.py | Metadata fields in DB |
| DB Population | All above | Python script | dimensional_profiles table |
| User Analysis (Pass 1) | User image | AI Advisor Service | User profile in DB |
| Distribution Comparison | User profile + Advisor profiles | Statistical analysis | Representative images |
| Prompt Augmentation | Representative images | augment_prompt_with_distribution_context() | Augmented prompt |
| Comparative Analysis (Pass 2) | User image + Augmented prompt | MLX model | Comparative feedback |

---

## Key Features

### Distribution-Based Comparison

Unlike simple similarity search, the system uses statistical distribution analysis:
- Compares user scores to advisor's portfolio distribution (mean, std)
- Identifies dimensions that need improvement (below threshold)
- Finds best examples (representative images) for each dimension
- Provides percentile estimates (where user ranks in advisor's portfolio)

### Targeted Recommendations

- Focuses on dimensions where user needs improvement
- Provides specific representative examples for each dimension
- Uses comparative language referencing advisor's portfolio statistics
- Actionable recommendations based on statistical gaps

### Metadata Integration

- Reference images can include rich metadata (title, date, location, significance)
- Metadata enhances context in comparative analysis
- Improves user-facing output with meaningful image titles instead of filenames

---

## See Also

- [dimensional-rag-implementation.md](dimensional-rag-implementation.md) (DEPRECATED - see this file)
- [rag-diagrams.md](rag-diagrams.md) (DEPRECATED - see this file)
- [requirements/rag.md](../requirements/rag.md)
- [guides/rag-comparison.md](../guides/rag-comparison.md)

**Note:** The deprecated files above contain historical information but may not reflect the current implementation. This file (`rag.md`) is the authoritative source for current RAG architecture.

---

## Maintenance

All RAG documentation is consolidated here. Please update this file for future RAG architecture changes.

**Last Updated:** 2025-01-XX (Distribution-based RAG implementation)
