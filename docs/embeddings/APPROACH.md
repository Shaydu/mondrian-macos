# Embedding-Based Pedagogical Feedback Architecture

## Overview

We've implemented a multi-layered retrieval system that uses CLIP embeddings to enhance the Ansel Adams photography advisor with pedagogically-sound feedback. Rather than just showing students images that are *similar* to their work, we show them *contrasting* approaches to help them understand diverse techniques.

## The Problem We Solved

Traditional RAG systems find similar examples. For photography education, this is limiting:
- If a student shoots dark, moody landscapes, showing similar dark landscapes reinforces their existing approach
- What they *need* is to see how the advisor handles different scenarios
- Best learning happens by understanding *contrasts* — "here's what I did, here's what the master did differently"

## The Solution: Contrasting Approaches

### Core Architecture

Three complementary retrieval functions work together:

```
User Image (with scores in 8 dimensions)
    ↓
[1] Dimensional Analysis (Pass 1)
    Scores: composition=3, lighting=2, focus=5, color=4, etc.
    ↓
[2] Identify Weak Dimensions
    Weak (<5): lighting, color harmony, isolation
    ↓
[3] Find Contrasting Approaches
    ├─ For lighting weakness:
    │  ├─ Find advisor images that EXCEL in lighting (≥7 score)
    │  ├─ Compare those elite images by visual embedding
    │  └─ Show visually DIFFERENT elite approaches
    │
    ├─ For color weakness:
    │  ├─ Find advisor images that EXCEL in color (≥7 score)
    │  ├─ Compare those elite images by visual embedding
    │  └─ Show visually DIFFERENT elite approaches
    │
    └─ [Repeat for each weak dimension]
    ↓
[4] Generate Pedagogical Context
    "Your lighting scores 2/10. Study these two Adams images:
     - 'High Key Landscape' (8/10 score) — soft, diffused approach
     - 'Dramatic Shadows' (8/10 score) — strong contrast approach
     Both excel but use DIFFERENT visual techniques."
    ↓
[5] LLM Uses This Context
    Generates nuanced feedback contrasting both approaches
```

## Implementation Details

### Three Core Functions

#### 1. `find_similar_by_embedding()`
**Purpose:** Find advisor images visually most similar to user's image  
**Use Case:** Show reference images that match user's visual style  
**Returns:** Top-k images sorted by cosine similarity (highest = most similar)  
**Metric:** Embedding cosine similarity (-1 to 1, higher is more similar)

```python
from mondrian.json_to_html_converter import find_similar_by_embedding

similar_images = find_similar_by_embedding(
    db_path=DATABASE_PATH,
    advisor_id="ansel",
    user_embedding=user_embedding,
    top_k=3,
    exclude_image_path=image_path
)
# Returns: [
#   {'image_path': ..., 'embedding_similarity': 0.87, ...},
#   {'image_path': ..., 'embedding_similarity': 0.84, ...},
#   ...
# ]
```

#### 2. `find_different_by_embedding()`
**Purpose:** Find advisor images visually MOST DIFFERENT from user's image  
**Use Case:** Show contrasting visual approaches; break student out of their comfort zone  
**Returns:** Top-k images sorted by embedding distance (highest = most different)  
**Metric:** Embedding distance (0 to 2, higher is more different)

```python
from mondrian.json_to_html_converter import find_different_by_embedding

different_images = find_different_by_embedding(
    db_path=DATABASE_PATH,
    advisor_id="ansel",
    user_embedding=user_embedding,
    top_k=3,
    exclude_image_path=image_path
)
# Returns: [
#   {'image_path': ..., 'embedding_distance': 1.45, ...},
#   {'image_path': ..., 'embedding_distance': 1.38, ...},
#   ...
# ]
```

#### 3. `find_contrasting_approaches_for_weak_dimensions()`
**Purpose:** For each dimension where student scored low, find pairs of advisor images that BOTH excel but use DIFFERENT visual approaches  
**Use Case:** Teach students that mastery isn't monolithic — multiple paths exist  
**Returns:** Dict mapping dimension → list of (image pair, visual distance, teaching note, qualitative_comment)  
**Metric:** Combination of dimensional score (advisor excellence) + embedding distance (visual diversity)

```python
from mondrian.json_to_html_converter import find_contrasting_approaches_for_weak_dimensions

teaching_examples = find_contrasting_approaches_for_weak_dimensions(
    db_path=DATABASE_PATH,
    advisor_id="ansel",
    user_scores={'lighting': 2.5, 'composition': 6, 'color_harmony': 3},
    user_embedding=user_embedding,
    weakness_threshold=5,      # Scores <5 are weak
    top_k=2                    # Show 2 contrasting approaches per dimension
)
# Returns: {
#   'lighting': [
#     {
#       'image': 'high_key_landscape.jpg',
#       'advisor_score': 8.5,
#       'qualitative_comment': 'Soft diffused light from overcast sky, careful exposure preserves highlight detail in snow',
#       'contrasting_image': 'dramatic_portrait.jpg',
#       'contrasting_score': 8.2,
#       'contrasting_comment': 'Strong side-lighting creates deep shadows, emphasizing texture and form',
#       'visual_distance': 0.62,
#       'teaching_note': 'Both excel in lighting but use different approaches'
#     }
#   ],
#   'color_harmony': [...]
# }
```

#### Qualitative Comment Extraction

The `qualitative_comment` field explains **WHY** the advisor image excels in a given dimension, providing actionable context beyond just the score.

**Source:** Parse existing HTML analysis outputs from `analysis/` or `advisor_output_review/` folders.

**Extraction Logic:**
```python
# Extract from HTML feedback cards
from bs4 import BeautifulSoup

def extract_qualitative_comments(html_path):
    """Extract per-dimension comments from analysis HTML."""
    soup = BeautifulSoup(open(html_path), 'html.parser')
    comments = {}
    for card in soup.select('.feedback-card'):
        dimension = card.select_one('h3').text.split('(')[0].strip().lower()
        comment = card.select_one('.feedback-comment')
        if comment:
            comments[dimension] = comment.text.strip()
    return comments
```

**Storage:** JSON blob in `dimensional_profiles.qualitative_comments`

---

### Text-Based Retrieval (Advisor's Written Teachings)

Beyond visual examples, we retrieve relevant passages from the advisor's own writings to strengthen the pedagogical voice and provide authoritative context.

#### 4. `find_relevant_text_passages()`
**Purpose:** Find advisor text passages relevant to the user's weak dimensions  
**Use Case:** Quote the master's own words when explaining technique  
**Returns:** List of text chunks with source attribution and relevance score  
**Data Source:** `training/ansel_ocr/*/ocr_output/*.txt` (per-page OCR text files)

```python
from mondrian.text_retrieval import find_relevant_text_passages

text_passages = find_relevant_text_passages(
    db_path=DATABASE_PATH,
    advisor_id="ansel",
    weak_dimensions=['lighting', 'composition'],
    user_context="dark moody landscape with low contrast",
    top_k=2
)
# Returns: [
#   {
#     'chunk_text': 'To visualize an image is to see it clearly in the mind prior to exposure...',
#     'source_book': 'the_camera',
#     'page_number': 10,
#     'chapter': 'Visualization',
#     'relevance_score': 0.84,
#     'matched_dimension': 'composition'
#   },
#   {
#     'chunk_text': 'The sensitive photographer feels his images in a plastic sense...',
#     'source_book': 'the_camera',
#     'page_number': 44,
#     'chapter': 'Lenses',
#     'relevance_score': 0.79,
#     'matched_dimension': 'emotional_impact'
#   }
# ]
```

#### Text Chunking Strategy

The OCR training data is processed into searchable chunks optimized for embedding retrieval:

**Source Files:**
- `training/ansel_ocr/the_camera_vol1/ocr_output/*.txt` (~219 pages)
- `training/ansel_ocr/the_print_vol3/ocr_output/*.txt` (~224 pages)

**Chunking Approach:**
1. Use per-page `.txt` files (already page-segmented by OCR)
2. Split into paragraphs (double newline delimiter)
3. Merge short paragraphs (<100 tokens) with adjacent ones
4. Split overly long paragraphs (>500 tokens) at sentence boundaries
5. Target chunk size: **300-500 tokens** for optimal embedding quality

**Stored Fields per Chunk:**
- `source_book`: "the_camera" or "the_print"
- `page_number`: Original page number (from filename)
- `chapter`: Inferred from TOC mapping or keyword detection
- `chunk_text`: The actual text content
- `embedding`: 512-dim CLIP text embedding

**Content Curation (Selective Inclusion):**

Not all OCR content is pedagogically valuable. We prioritize:

| Include (High Value) | Exclude (Low Value) |
|---------------------|--------------------|
| Visualization chapter | Equipment specifications |
| Philosophy of craft | Film chemistry details |
| Seeing & previsualization | Darkroom-specific processes |
| Emotional expression | Camera mechanics (bellows, shutters) |
| Composition principles | Brand/model comparisons |

**Rationale:** Adams' writing excels at *philosophy* and *attitude* toward photography, not technical rules. The text complements image-based retrieval by adding *why* and *mindset*, while images demonstrate *what* and *technique*.

#### Dimension-to-Keyword Mapping

Hybrid search combines embedding similarity with keyword boosting to improve retrieval relevance:

```python
DIMENSION_KEYWORDS = {
    'composition': [
        'frame', 'framing', 'placement', 'rule of thirds', 'balance',
        'arrangement', 'seeing', 'viewfinder', 'crop', 'format'
    ],
    'lighting': [
        'exposure', 'light', 'shadow', 'contrast', 'brightness',
        'meter', 'zone system', 'luminance', 'highlight', 'dark'
    ],
    'focus_sharpness': [
        'focus', 'sharp', 'sharpness', 'depth of field', 'aperture',
        'lens', 'plane of focus', 'hyperfocal', 'diffraction'
    ],
    'color_harmony': [
        'color', 'tone', 'tonal', 'value', 'gray', 'black and white',
        'monochrome', 'contrast', 'harmony'
    ],
    'subject_isolation': [
        'subject', 'isolation', 'background', 'foreground', 'separation',
        'bokeh', 'selective focus', 'attention', 'dominant'
    ],
    'depth_perspective': [
        'depth', 'perspective', 'dimension', 'space', 'distance',
        'foreground', 'layering', 'scale', 'receding'
    ],
    'visual_balance': [
        'balance', 'weight', 'symmetry', 'asymmetry', 'tension',
        'harmony', 'equilibrium', 'distribution'
    ],
    'emotional_impact': [
        'emotion', 'feeling', 'mood', 'expression', 'impact',
        'visualization', 'creative', 'artistic', 'resonance', 'soul'
    ]
}
```

**Hybrid Scoring:**
```python
def hybrid_relevance_score(chunk, query_embedding, target_dimension):
    # Base: embedding cosine similarity (0-1)
    embedding_score = cosine_similarity(chunk.embedding, query_embedding)
    
    # Boost: keyword presence (0-0.2 bonus)
    keywords = DIMENSION_KEYWORDS.get(target_dimension, [])
    keyword_hits = sum(1 for kw in keywords if kw.lower() in chunk.text.lower())
    keyword_boost = min(0.2, keyword_hits * 0.05)
    
    return embedding_score + keyword_boost
```

### Data Flow in RAG Mode

```
┌─────────────────────────────────────────────────────────────┐
│ Pass 1: Extract Dimensional Profile                         │
├─────────────────────────────────────────────────────────────┤
│ Input: User image                                           │
│ Output: {composition: 4, lighting: 2, focus: 5, ...}       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Compute User Embedding (CLIP ViT-B/32)                     │
├─────────────────────────────────────────────────────────────┤
│ Input: User image                                           │
│ Output: [0.123, -0.456, ..., 0.789] (512-dim vector)      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Parallel Retrieval (all enabled when enable_embeddings=true)│
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ IMAGE RETRIEVAL:                                            │
│ 1. find_similar_by_embedding()                              │
│    → Similar visual approaches                              │
│                                                              │
│ 2. find_representative_images_by_distribution()             │
│    → Images with similar dimensional profiles               │
│                                                              │
│ 3. find_contrasting_approaches_for_weak_dimensions()       │
│    → Diverse approaches to improve weak areas               │
│    → Now includes qualitative_comment per image             │
│                                                              │
│ 4. find_images_by_technique_match()                         │
│    → Same photographic techniques                           │
│                                                              │
│ TEXT RETRIEVAL:                                             │
│ 5. find_relevant_text_passages()  ← NEW!                   │
│    → Advisor's written teachings for weak dimensions        │
│    → Philosophy, visualization, artistic intent             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Context Consolidation  ← NEW!                              │
├─────────────────────────────────────────────────────────────┤
│ consolidate_pedagogical_context(                            │
│   image_results,                                            │
│   text_results,                                             │
│   user_scores,                                              │
│   max_total_references=4                                    │
│ )                                                           │
│                                                              │
│ Actions:                                                    │
│ - Deduplicate images across retrieval methods               │
│ - Rank by priority weighting (weakness severity first)      │
│ - Limit to 2-3 images + 1-2 text passages                  │
│ - Ensure coverage of weakest dimensions                     │
│                                                              │
│ Output: Curated set of 4-5 high-impact references          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Augment Prompt with Hybrid Context                         │
├─────────────────────────────────────────────────────────────┤
│ augment_prompt_with_hybrid_context(                         │
│   advisor_prompt,                                           │
│   visual_matches,                                           │
│   technique_matches,                                        │
│   dimensional_matches,                                      │
│   contrasting_approaches,                                   │
│   text_passages  ← NEW!                                    │
│ )                                                           │
│                                                              │
│ Output: Enhanced prompt with images + advisor's own words   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Pass 2: Generate Analysis with LLM                         │
├─────────────────────────────────────────────────────────────┤
│ Input: Pass 1 profile + augmented prompt + reference images│
│ Output: Comprehensive feedback using all perspectives       │
│         + quotes from advisor's writings                    │
└─────────────────────────────────────────────────────────────┘
```

---

### Context Consolidation Layer

With 5 retrieval methods potentially returning 10+ references, we need to consolidate to prevent prompt bloat and maintain focus.

#### `consolidate_pedagogical_context()`

**Purpose:** Rank, deduplicate, and limit references to the most pedagogically impactful subset.

**Constraints:**
- **Max total references:** 4-5 (configurable via `max_total_references`)
- **Composition:** 2-3 images + 1-2 text passages
- **Coverage:** Ensure weakest dimension is always represented

```python
def consolidate_pedagogical_context(
    image_results: List[Dict],
    text_results: List[Dict],
    user_scores: Dict[str, float],
    max_total_references: int = 4,
    weakness_threshold: float = 5.0
) -> Dict:
    """
    Consolidate all retrieval results into a focused set.
    
    Returns: {
        'images': [top 2-3 images with deduplication],
        'text_passages': [top 1-2 relevant passages],
        'coverage': ['lighting', 'composition']  # dimensions covered
    }
    """
    # 1. Identify weak dimensions sorted by severity
    weak_dims = [
        (dim, (weakness_threshold - score) / weakness_threshold)
        for dim, score in user_scores.items()
        if score < weakness_threshold
    ]
    weak_dims.sort(key=lambda x: x[1], reverse=True)  # Most severe first
    
    # 2. Deduplicate images (same image may appear in multiple methods)
    seen_images = set()
    unique_images = []
    for img in image_results:
        if img['image_path'] not in seen_images:
            seen_images.add(img['image_path'])
            unique_images.append(img)
    
    # 3. Score and rank all references
    scored_refs = []
    for img in unique_images:
        score = compute_priority_score(img, weak_dims, 'image')
        scored_refs.append(('image', img, score))
    for txt in text_results:
        score = compute_priority_score(txt, weak_dims, 'text')
        scored_refs.append(('text', txt, score))
    
    scored_refs.sort(key=lambda x: x[2], reverse=True)
    
    # 4. Select top references ensuring balance
    selected_images = []
    selected_text = []
    for ref_type, ref, score in scored_refs:
        if ref_type == 'image' and len(selected_images) < 3:
            selected_images.append(ref)
        elif ref_type == 'text' and len(selected_text) < 2:
            selected_text.append(ref)
        if len(selected_images) + len(selected_text) >= max_total_references:
            break
    
    return {
        'images': selected_images,
        'text_passages': selected_text,
        'coverage': list(set(r.get('matched_dimension') for r in selected_images + selected_text))
    }
```

#### Priority Weighting Formula

References are ranked using a weighted scoring formula:

```
score = 0.4 × weakness_severity + 0.3 × text_relevance + 0.2 × visual_contrast + 0.1 × similarity
```

**Component Definitions:**

| Component | Calculation | Rationale |
|-----------|-------------|----------|
| `weakness_severity` | `(threshold - user_score) / threshold` | Prioritize weakest areas (lighting=2 → severity=0.6) |
| `text_relevance` | Hybrid score (embedding + keyword) | How well text matches dimension |
| `visual_contrast` | Embedding distance (0-1 normalized) | Diverse approaches teach more |
| `similarity` | Embedding similarity | Some grounding in user's style |

**Example Calculation:**
```python
# User scores: lighting=2, composition=6
# Reference: Ansel text passage about visualization

weakness_severity = (5 - 2) / 5  # = 0.6 (lighting is weak)
text_relevance = 0.84            # from hybrid search
visual_contrast = 0.0            # N/A for text
similarity = 0.0                 # N/A for text

priority_score = 0.4 * 0.6 + 0.3 * 0.84 + 0.2 * 0.0 + 0.1 * 0.0
             # = 0.24 + 0.252 + 0 + 0
             # = 0.492
```

## Why This Architecture?

### 1. Multiple Retrieval Perspectives

Students learn best when exposed to multiple viewpoints:

- **Dimensional perspective**: "Your composition score is 4/10, but this Adams image scores 9/10 using a different approach"
- **Technique perspective**: "You both used rule-of-thirds framing, but Adams executed it differently"
- **Visual perspective**: "Your image is dark and moody; Adams has both dark AND bright landscapes in his portfolio"
- **Contrasting perspective**: "To improve your weak lighting, study BOTH these approaches: soft diffusion AND dramatic shadows"

### 2. Pedagogically Sound

Research in photography education shows:
- **Comparative analysis** improves learning over example-only instruction
- **Diverse approaches** prevent formulaic thinking
- **Weak-area focus** with multiple solutions builds adaptability
- **Visual similarity + contrast** creates cognitive anchors

### 3. Computationally Efficient

- **Pre-computed embeddings**: ~120 KB per advisor = no per-request CLIP computation
- **Parallel retrieval**: All four methods run simultaneously
- **Database queries**: Index-friendly lookups (dimensional scores, image_path)
- **Scaling**: 100 requests → 0 seconds CLIP overhead (vs 5+ minutes without pre-computation)

## Configuration & Usage

### Enable Embeddings in RAG Analysis

```python
# In job request:
{
    "advisor_id": "ansel",
    "enable_embeddings": true,  # Enable all embedding-based retrieval
    "mode": "rag"               # Use RAG (two-pass) analysis
}
```

### Control Retrieval Parameters

```python
# In augment_prompt_with_hybrid_context():

# Number of similar images to show
top_k_similar = 2

# Number of contrasting approaches per weak dimension
top_k_contrasting = 2

# Threshold for "weak" dimensions (score below this)
weakness_threshold = 5

# Threshold for "excellent" dimensions in advisor portfolio (>=this)
advisor_excellence_threshold = 7

# --- NEW: Text Retrieval & Consolidation Parameters ---

# Maximum total references after consolidation (images + text)
max_total_references = 4

# Enable text passage retrieval from advisor's writings
include_text_passages = True

# Number of text passages to retrieve before consolidation
text_chunk_top_k = 2

# Priority weights for consolidation scoring
consolidation_weights = {
    'weakness_severity': 0.4,   # Prioritize weakest dimensions
    'text_relevance': 0.3,      # How well text matches dimension
    'visual_contrast': 0.2,     # Diverse approaches teach more
    'similarity': 0.1           # Some grounding in user's style
}

# Dimension-to-keyword mapping for hybrid text search
# (See full mapping in Text-Based Retrieval section)
from mondrian.dimension_keywords import DIMENSION_KEYWORDS
```

### Precompute Embeddings (One-Time Setup)

```bash
# For Ansel advisor - IMAGE embeddings
python3 tools/rag/compute_image_embeddings_to_db.py \
  --advisor_dir mondrian/source/advisor/photographer/ansel/ \
  --advisor_id ansel

# For Ansel advisor - TEXT embeddings (NEW)
python3 tools/rag/compute_text_embeddings_to_db.py \
  --ocr_dir training/ansel_ocr/ \
  --advisor_id ansel \
  --curate  # Optional: only include high-value passages

# Extract qualitative comments from existing HTML analyses (NEW)
python3 tools/rag/extract_qualitative_comments.py \
  --analysis_dir analysis/ \
  --advisor_id ansel

# For any new advisor
python3 tools/rag/compute_image_embeddings_to_db.py \
  --advisor_dir <path/to/advisor/images> \
  --advisor_id <advisor_name>
```

### Pre-computation Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `compute_image_embeddings_to_db.py` | CLIP embeddings for advisor images | `mondrian/source/advisor/*/` | `dimensional_profiles.embedding` |
| `compute_text_embeddings_to_db.py` | CLIP embeddings for OCR text | `training/ansel_ocr/*/ocr_output/*.txt` | `advisor_text_chunks` table |
| `extract_qualitative_comments.py` | Parse feedback comments from HTML | `analysis/*.html` | `dimensional_profiles.qualitative_comments` |

## Technical Specifications

### CLIP Embedding Model

- **Model**: OpenAI CLIP ViT-B/32
- **Input**: RGB image (any resolution, auto-scaled)
- **Output**: 512-dimensional vector
- **Properties**:
  - No training required (pre-trained)
  - Pre-computed storage: 2 KB per image (binary BLOB in SQLite)
  - Computation: ~2-3 sec per image on GPU, ~20 sec on CPU
  - Compute cost: $0 (offline pre-computation)

### Distance Metrics

**Cosine Similarity** (used for all comparisons):
```
similarity = (vec_a · vec_b) / (||vec_a|| × ||vec_b||)
distance = 1 - similarity

Range: 
- Similarity: -1 (opposite) to +1 (identical)
- Distance: 0 (identical) to 2 (opposite)
```

**Why cosine similarity?**
- Invariant to vector magnitude (only direction matters)
- Standard for high-dimensional embeddings
- Computationally efficient for large-scale retrieval

### Database Schema

```sql
-- Pre-computed image embeddings stored in dimensional_profiles
CREATE TABLE dimensional_profiles (
    id TEXT PRIMARY KEY,
    advisor_id TEXT,
    image_path TEXT,
    
    -- 8 dimensional scores
    composition_score REAL,
    lighting_score REAL,
    focus_sharpness_score REAL,
    color_harmony_score REAL,
    subject_isolation_score REAL,
    depth_perspective_score REAL,
    visual_balance_score REAL,
    emotional_impact_score REAL,
    
    -- CLIP embedding (512-dimensional vector)
    embedding BLOB,  -- Binary: 512 × 4 bytes = 2 KB per image
    
    -- Qualitative comments explaining WHY image excels (NEW)
    qualitative_comments TEXT,  -- JSON: {"lighting": "Soft diffused light...", ...}
    
    -- Metadata
    metadata TEXT,   -- JSON with creative attributes
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pre-computed text embeddings for advisor's written teachings (NEW)
CREATE TABLE advisor_text_chunks (
    id TEXT PRIMARY KEY,
    advisor_id TEXT NOT NULL,
    
    -- Source attribution
    source_book TEXT NOT NULL,    -- 'the_camera' or 'the_print'
    page_number INTEGER,          -- Original page number
    chapter TEXT,                 -- Inferred chapter name
    
    -- Content
    chunk_text TEXT NOT NULL,     -- The actual text (300-500 tokens)
    
    -- CLIP text embedding (512-dimensional vector)
    embedding BLOB,               -- Binary: 512 × 4 bytes = 2 KB per chunk
    
    -- Metadata
    is_curated BOOLEAN DEFAULT 0, -- Manually marked as high-value
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indices for efficient retrieval
CREATE INDEX idx_text_chunks_advisor ON advisor_text_chunks(advisor_id);
CREATE INDEX idx_text_chunks_book ON advisor_text_chunks(source_book);
```

## Performance Characteristics

### Without Pre-Computation (On-Demand CLIP)

```
Request latency:
  Pass 1 (dimensional analysis):     ~3 sec (LLM + database)
  Pass 2 user embedding computation: ~2-3 sec (CLIP forward pass)
  Pass 2 retrieval:                  ~1 sec (database queries)
  Pass 2 LLM analysis:               ~5-10 sec (LLM + formatting)
  ────────────────────────────────────────────────
  TOTAL:                             ~11-17 sec per request

Scaling (100 concurrent requests):
  CLIP compute overhead:             ~350 seconds (5+ min!)
  GPU memory:                        Very high (batch processing challenges)
```

### With Pre-Computed Embeddings

```
Request latency:
  Pass 1 (dimensional analysis):     ~3 sec
  Pass 2 embedding lookup:           ~0.1 sec (pre-computed, just query)
  Pass 2 retrieval:                  ~0.5 sec (database queries)
  Pass 2 LLM analysis:               ~5-10 sec
  ────────────────────────────────────────────────
  TOTAL:                             ~8.6-13.6 sec per request

Scaling (100 concurrent requests):
  CLIP compute overhead:             0 (pre-computed)
  GPU memory:                        Minimal
  Speedup:                           ~5-10x on embedding latency
  
Database size:
  Ansel advisor (40 images):         ~120 KB embeddings + metadata
  Cost to scale to 1000 images:      ~3 MB (negligible)
```

## Use Cases

### 1. Photography Student Self-Assessment

**Flow:**
1. Student uploads their work
2. System analyzes dimensions (Pass 1)
3. Identifies weak areas (lighting=2, color=3)
4. Retrieves contrasting Ansel approaches for each weak dimension
5. Student reads LLM feedback: "You need better lighting. Ansel uses two approaches—try both."
6. Student studies reference images and tries next shot

**Outcome:** Structured improvement path, understanding of technique diversity

### 2. Instructor-Guided Critique

**Flow:**
1. Instructor uploads student work to Mondrian
2. Requests analysis with embeddings enabled
3. Gets structured critique showing dimensional weaknesses
4. Uses contrasting approaches to teach: "See these two Ansel shots? Both master lighting. Try his techniques."
5. Provides feedback using system-suggested references

**Outcome:** Faster critiques, consistent pedagogical approach, reference images always available

### 3. Portfolio Development

**Flow:**
1. Student uploads 10 images over semester
2. System tracks dimension scores across portfolio
3. Each feedback includes contrasting approaches in weak areas
4. Student iteratively improves

**Outcome:** Portfolio shows progression, understanding of technical mastery

## Future Enhancements

### Phase 2: Batch Indexing
- Compute embeddings for multiple advisors efficiently
- Build search indices for faster retrieval
- Support 10k+ advisor images

### Phase 3: Semantic RAG Enhancement
- Combine dimensional distance + embedding distance for hybrid ranking
- Weight contrastiveness vs. similarity based on learning objective
- Fine-tune thresholds per advisor style

### Phase 4: Student Adaptation
- Track which contrasting approaches each student learns best from
- Personalize retrieval based on learning history
- A/B test pedagogical strategies

### Phase 5: Add "The Negative" (Vol 2)
- OCR and embed content from Adams' "The Negative" book
- Focus on exposure/development concepts applicable to digital
- Map to lighting, contrast, and tonal dimensions
- Filter out film-chemistry-specific content

### Phase 6: Digital User Contextualization
- Auto-detect and flag film-specific passages
- Provide digital equivalents for analog concepts (e.g., "Zone V" → "18% gray / middle exposure")
- Optionally show historical context: "Adams wrote about film, but the principle applies: ..."
- Build mapping table: analog_concept → digital_equivalent

## Integration Checklist

- [x] Compute `find_contrasting_approaches_for_weak_dimensions()` function
- [x] Export from all strategy modules (RAG, RAG+LoRA, Baseline)
- [x] Enhance `augment_prompt_with_hybrid_context()` to include contrasting approaches
- [x] Pre-compute embeddings for Ansel advisor
- [ ] Integration test: Verify all four retrieval methods work together
- [ ] End-to-end test: Full request with embeddings enabled
- [ ] Performance benchmark: Compare with/without embeddings
- [ ] Documentation complete ✓

## Troubleshooting

### Embedding Table Missing
```
Error: "no such table: image_captions"
Fix: Run precomputation script first:
  python3 tools/rag/compute_image_embeddings_to_db.py --advisor_dir ... --advisor_id ...
```

### No Weak Dimensions Found
```
Output: "No weak dimensions found (all scores >= 5)"
Reason: User's image is well-balanced (good!)
Action: No contrasting context generated (normal)
```

### Slow Retrieval
```
Symptom: Retrieval taking >1 second
Reason: Database indices may not be built
Fix: Run `sqlite3 mondrian.db "CREATE INDEX idx_advisor_id ON dimensional_profiles(advisor_id);"`
```

### Embeddings Not Being Used
```
Check: Is enable_embeddings=true in request?
Check: Does advisor have pre-computed embeddings? (sqlite3 query to verify)
Check: Are CLIP dependencies installed? (pip list | grep torch)
```

## References

- CLIP Paper: https://arxiv.org/abs/2103.14030
- Cosine Similarity: https://en.wikipedia.org/wiki/Cosine_similarity
- RAG Concept: https://arxiv.org/abs/2005.11401
- Photography Pedagogy: Research on comparative feedback in visual arts education
