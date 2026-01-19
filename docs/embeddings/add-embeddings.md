# Adding Advisor Quotes and Reference Images

This guide explains how to expand the advisor's knowledge base by adding more reference images and book quotes.

## Overview

The advisor system uses two types of content for RAG (Retrieval-Augmented Generation):

1. **Reference Images** - Example photos with dimensional scores used for visual comparison
2. **Book Quotes** - Text passages from the advisor's writings used for contextual citations

Both are retrieved using CLIP embeddings for semantic similarity to the user's photo.

---

## 1. Adding More Reference Images

Reference images provide visual examples that the LLM can cite when giving feedback. More images = better visual diversity and relevance.

### Steps

#### 1.1. Add Images to Advisor Directory

```bash
# Place new photos in the advisor's folder
cp /path/to/new/ansel/photos/*.jpg mondrian/source/advisor/photographer/ansel/

# Supported formats: .jpg, .jpeg, .png
# Recommended: High-quality images showcasing strong dimensional qualities
```

**Directory structure:**
```
mondrian/source/advisor/
├── photographer/
│   └── ansel/          # Place Ansel Adams reference images here
├── painter/
│   └── okeefe/         # Georgia O'Keeffe paintings
└── architect/
    └── gehry/          # Gehry buildings
```

#### 1.2. Analyze Images (Compute Dimensional Scores)

The system needs to analyze each reference image to compute dimensional scores (composition, lighting, etc.).

```bash
# Start AI Advisor Service (if not already running)
python mondrian/ai_advisor_service_linux.py

# In another terminal, run batch analysis
python batch_analyze_advisor_images.py --advisor ansel

# This will:
# - Analyze each image without RAG (to avoid circular references)
# - Extract dimensional scores (composition_score, lighting_score, etc.)
# - Save scores to dimensional_profiles table
```

**What happens:**
- Each image is analyzed by the VLM
- Dimensional scores (1-10) are extracted and stored in `dimensional_profiles` table
- Images with high scores (≥8.0) become candidates for RAG retrieval

#### 1.3. Compute CLIP Embeddings

Generate visual and text embeddings for semantic similarity search:

```bash
# Compute both CLIP (visual) and text embeddings
python scripts/compute_embeddings.py --advisor ansel

# Verify embeddings were created successfully
python scripts/compute_embeddings.py --advisor ansel --verify-only
```

**What this does:**
- **CLIP embedding** (visual): Enables finding visually similar images to user's photo
- **Text embedding** (semantic): Enables searching by image title/description/significance
- Embeddings stored as BLOBs in `dimensional_profiles.embedding` and `dimensional_profiles.text_embedding`

#### 1.4. Update Image Manifest (Optional)

Add metadata to the canonical image manifest:

```yaml
# Edit: advisor_image_manifest.yaml

advisors:
  - category: photographer
    advisor: ansel
    images:
      - filename: new_monolith_photo.jpg
        title: "Monolith, Face of Half Dome"
        date_taken: "1927"
        description: "Iconic close-up of Half Dome's sheer granite face"
```

This metadata is used for display and context but isn't required for RAG retrieval.

### Verification

Check that your new images are indexed:

```bash
# Open Python shell
python3

>>> import sqlite3
>>> conn = sqlite3.connect('mondrian.db')
>>> cursor = conn.cursor()

# Check for dimensional scores
>>> cursor.execute("""
    SELECT image_path, composition_score, lighting_score, 
           CASE WHEN embedding IS NOT NULL THEN 'Yes' ELSE 'No' END as has_embedding
    FROM dimensional_profiles
    WHERE advisor_id = 'ansel'
    ORDER BY composition_score DESC
    LIMIT 5
""")
>>> for row in cursor.fetchall():
...     print(row)
```

---

## 2. Adding Book Quotes (Text Passages)

Book quotes provide authoritative text that the LLM can cite when explaining feedback. These come from the advisor's published writings.

### Steps

#### 2.1. Create the book_passages Table

First-time setup only:

```bash
# Create the table structure
python3 scripts/add_book_passages_table.py
```

This creates:
- `book_passages` table with columns: `id`, `advisor_id`, `book_title`, `passage_text`, `dimension_tags`, `embedding`
- Indices for fast retrieval by advisor and book

#### 2.2. Prepare Quote JSON Files

Create JSON files with dimension-tagged quotes in `training/book_passages/`:

**Format:** `training/book_passages/camera_approved.json`

```json
{
  "advisor": "ansel",
  "book": "The Camera",
  "passages": [
    {
      "id": "camera_001",
      "text": "The Zone System is not an invention; it is a codification of the principles of sensitometry, worked out by Fred Archer and myself at the Art Center School in Los Angeles, around 1939-40.",
      "dimensions": ["technical_precision", "lighting", "exposure"],
      "relevance_score": 8,
      "notes": "Explains Zone System foundation"
    },
    {
      "id": "camera_042",
      "text": "Visualization is a conscious process of projecting the final photographic image in the mind before taking the first steps in actually photographing the subject.",
      "dimensions": ["composition", "planning", "vision"],
      "relevance_score": 9,
      "notes": "Core concept of pre-visualization"
    }
  ]
}
```

**Field guide:**
- `id`: Unique identifier (e.g., `camera_001`, `print_125`)
- `text`: The actual quote (keep under 200 words for best results)
- `dimensions`: Array of relevant dimensions (composition, lighting, focus_sharpness, color_harmony, subject_isolation, depth_perspective, visual_balance, emotional_impact)
- `relevance_score`: Your quality rating (1-10) - import only scores ≥5
- `notes`: Internal notes (not shown to users)

**Dimension tags:**
- `composition` - Rule of thirds, framing, visual arrangement
- `lighting` - Light quality, direction, dynamic range
- `focus_sharpness` - Focus technique, depth of field, sharpness
- `color_harmony` - Color relationships, palette, saturation
- `subject_isolation` - Subject clarity, background separation
- `depth_perspective` - Spatial depth, layering, perspective
- `visual_balance` - Weight distribution, symmetry, equilibrium
- `emotional_impact` - Mood, feeling, narrative power
- `technical_precision` - Exposure, Zone System, print quality

#### 2.3. Import Quotes with Embeddings

```bash
# Preview what will be imported (dry run)
python3 scripts/import_book_passages.py --dry-run

# Import for real
python3 scripts/import_book_passages.py
```

**What happens:**
1. Loads JSON files from `training/book_passages/*_approved.json`
2. Computes sentence-transformer embeddings for semantic search
3. Inserts into `book_passages` table with embeddings
4. Skips duplicates (based on `id` field)

### Verification

Check that quotes were imported:

```bash
python3

>>> import sqlite3
>>> conn = sqlite3.connect('mondrian.db')
>>> cursor = conn.cursor()

# Count total quotes
>>> cursor.execute("SELECT COUNT(*) FROM book_passages WHERE advisor_id='ansel'")
>>> print(f"Total quotes: {cursor.fetchone()[0]}")

# Show sample quotes with dimensions
>>> cursor.execute("""
    SELECT book_title, dimension_tags, substr(passage_text, 1, 80) || '...' as preview
    FROM book_passages
    WHERE advisor_id = 'ansel'
    LIMIT 3
""")
>>> for row in cursor.fetchall():
...     print(row)
...     print()
```

---

## 3. How RAG Retrieval Works

Once images and quotes are indexed with embeddings, the system uses them automatically during analysis.

### Reference Image Retrieval

**Single-Pass Analysis:**
1. User submits photo for analysis
2. System computes CLIP embedding of user's photo
3. Retrieves top 3-4 visually similar reference images from advisor's portfolio
4. LLM sees reference images and can cite them using `case_study_id: IMG_1`

**Two-Pass Analysis (after weak dimensions identified):**
1. First pass identifies weakest dimensions (e.g., composition, lighting)
2. Second pass retrieves images that score ≥8.0 in those specific weak dimensions
3. LLM sees targeted examples and cites relevant ones

### Quote Retrieval

**Single-Pass:**
1. System retrieves top 6 book passages using semantic similarity
2. Passages are filtered by dimension tags
3. LLM can cite up to 3 quotes using `quote_id: QUOTE_1`

**Two-Pass:**
1. Retrieves quotes specifically tagged with the user's weak dimensions
2. Provides focused, relevant quotations

---

## 4. Best Practices

### For Reference Images

✅ **Do:**
- Use high-quality images (at least 1920px on longest side)
- Include diverse subjects, lighting conditions, and compositions
- Choose images that strongly demonstrate specific dimensions (score ≥8.0)
- Aim for 20-50+ reference images per advisor for good coverage

❌ **Don't:**
- Add low-resolution or poor-quality images
- Include images without clear dimensional strengths
- Use copyrighted images without permission
- Mix different advisors' work in the same folder

### For Book Quotes

✅ **Do:**
- Keep passages under 200 words (75 words preferred for citations)
- Tag with specific, relevant dimensions
- Include only high-quality, insightful quotes (relevance_score ≥7)
- Verify quotes are accurate and properly attributed
- Group by book/source for organization

❌ **Don't:**
- Include entire pages of text (too long for context window)
- Use generic or vague passages
- Mix quotes from different advisors in the same file
- Forget to compute embeddings after importing

---

## 5. Troubleshooting

### Images not appearing in RAG results

```bash
# Check if dimensional scores exist
python diagnose_reference_images.py

# Verify embeddings
python scripts/compute_embeddings.py --advisor ansel --verify-only

# Re-analyze if needed
python batch_analyze_advisor_images.py --advisor ansel
```

### Quotes not being cited

```bash
# Check if quotes were imported
python3 -c "
import sqlite3
conn = sqlite3.connect('mondrian.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM book_passages WHERE advisor_id=\"ansel\"')
print(f'Total quotes: {cursor.fetchone()[0]}')
"

# Check if embeddings exist
python3 -c "
import sqlite3
conn = sqlite3.connect('mondrian.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM book_passages WHERE advisor_id=\"ansel\" AND embedding IS NOT NULL')
print(f'Quotes with embeddings: {cursor.fetchone()[0]}')
"
```

### Embeddings failing to compute

```bash
# Install required dependencies
pip install sentence-transformers torch transformers

# For CUDA support (Linux)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Verify CLIP model can load
python3 -c "from transformers import CLIPModel, CLIPProcessor; print('CLIP OK')"
```

---

## 6. Quick Reference

| Task | Command |
|------|---------|
| Add reference images | `cp *.jpg mondrian/source/advisor/photographer/ansel/` |
| Analyze images | `python batch_analyze_advisor_images.py --advisor ansel` |
| Compute embeddings | `python scripts/compute_embeddings.py --advisor ansel` |
| Verify embeddings | `python scripts/compute_embeddings.py --advisor ansel --verify-only` |
| Create quotes table | `python3 scripts/add_book_passages_table.py` |
| Import quotes | `python3 scripts/import_book_passages.py` |
| Diagnose RAG | `python diagnose_reference_images.py` |

---

## 7. Database Schema Reference

### dimensional_profiles table (reference images)
```sql
CREATE TABLE dimensional_profiles (
    id INTEGER PRIMARY KEY,
    advisor_id TEXT,
    image_path TEXT,
    image_title TEXT,
    composition_score REAL,
    lighting_score REAL,
    focus_sharpness_score REAL,
    color_harmony_score REAL,
    subject_isolation_score REAL,
    depth_perspective_score REAL,
    visual_balance_score REAL,
    emotional_impact_score REAL,
    embedding BLOB,           -- CLIP visual embedding
    text_embedding BLOB       -- Sentence-transformer text embedding
);
```

### book_passages table (quotes)
```sql
CREATE TABLE book_passages (
    id TEXT PRIMARY KEY,
    advisor_id TEXT,
    book_title TEXT,
    passage_text TEXT,
    dimension_tags TEXT,      -- JSON array of dimensions
    embedding BLOB,           -- Sentence-transformer embedding
    relevance_score REAL,
    source TEXT,
    notes TEXT
);
```

---

## Need Help?

- **Reference Images Issues:** See `diagnose_reference_images.py` for diagnostics
- **Embeddings Issues:** Check `docs/embeddings/SETUP.md`
- **RAG Architecture:** See `ARCHITECTURE_ASSESSMENT.md`
- **Database Schema:** See `init_database.py`
