# RAG Data Flow: From Advisor Images to User Evaluation

This document describes the complete pipeline for analyzing advisor images and populating the database with the dimensions and techniques used to evaluate user images.

---

## Overview

The RAG (Retrieval-Augmented Generation) system works in two phases:

1. **Preprocessing Phase**: Analyze advisor reference images and populate database
2. **Inference Phase**: Evaluate user images using advisor reference data

---

## Phase 1: Preprocessing - Building the Reference Database

### Step 1: Download Advisor Images with Metadata

**Script**: `scripts/download_with_metadata.py`

```bash
python3 scripts/download_with_metadata.py --advisor ansel
```

**What happens:**

```
┌─────────────────────────────────────────────────────────┐
│ Wikimedia Commons API                                    │
│                                                          │
│ For each artwork (e.g., "Adams The Tetons and...")     │
│   1. Fetch high-resolution image (2000px+)              │
│   2. Extract metadata:                                   │
│      - Title: "The Tetons and the Snake River"         │
│      - Date: "1942"                                      │
│      - Description: "One of Adams' most iconic..."      │
│      - Artist: "Ansel Adams"                            │
│      - License: "Public Domain"                         │
│      - Location: "Grand Teton National Park, Wyoming"  │
│   3. Download image                                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Local Filesystem                                         │
│                                                          │
│ mondrian/source/advisor/photographer/ansel/             │
│   ├── Adams_The_Tetons_and_the_Snake_River.jpg         │
│   ├── Clearing_Winter_Storm_Yosemite.jpg                │
│   ├── Half_Dome_Merced_River_Winter.jpg                 │
│   ├── ... (11 total images)                             │
│   └── metadata.yaml                                      │
└─────────────────────────────────────────────────────────┘
```

**Output**: `metadata.yaml`

```yaml
images:
  - filename: Adams_The_Tetons_and_the_Snake_River.jpg
    title: "The Tetons and the Snake River"
    date_taken: "1942"
    description: "Iconic landscape selected for Voyager Golden Record..."
    location: "Grand Teton National Park, Wyoming"
    significance: ""  # To be filled in Step 2
    techniques: []     # To be filled in Step 3
    source:
      commons_url: "https://commons.wikimedia.org/wiki/File:Adams..."
      artist: "Ansel Adams"
      license: "Public Domain"
```

---

### Step 2: Dimensional Analysis of Advisor Images

**Script**: `tools/rag/index_with_metadata.py`

```bash
# Start AI service (loads MLX vision model)
python3 mondrian/ai_advisor_service.py --port 5100

# Index images with dimensional analysis
python3 tools/rag/index_with_metadata.py \
  --advisor ansel \
  --metadata-file mondrian/source/advisor/photographer/ansel/metadata.yaml
```

**What happens:**

```
For each advisor image:

┌─────────────────────────────────────────────────────────┐
│ AI Advisor Service (MLX Vision Model)                   │
│                                                          │
│ Input: advisor image + metadata                         │
│                                                          │
│ Prompt: "Analyze this Ansel Adams photograph across     │
│          8 rubric dimensions..."                        │
│                                                          │
│ Model analyzes and returns JSON:                        │
│ {                                                        │
│   "composition": {                                       │
│     "score": 9.5,                                       │
│     "comment": "Masterful rule of thirds with Snake    │
│                 River creating leading line..."         │
│   },                                                     │
│   "lighting": {                                          │
│     "score": 9.0,                                       │
│     "comment": "Golden hour sidelight emphasizes        │
│                 mountain texture..."                    │
│   },                                                     │
│   "depth_and_perspective": {                            │
│     "score": 10.0,                                      │
│     "comment": "f/64 technique - front-to-back         │
│                 sharpness from river to peaks..."       │
│   },                                                     │
│   ... (8 dimensions total)                              │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ json_to_html_converter.py                               │
│                                                          │
│ extract_dimensional_profile_from_json(analysis)         │
│   → Extracts scores and comments                        │
│                                                          │
│ save_dimensional_profile(                               │
│   db_path="mondrian.db",                                │
│   profile_id="ansel_tetons_001",                        │
│   advisor_id="ansel",                                    │
│   image_path="/path/to/Adams_The_Tetons...",           │
│   dimensional_data={                                     │
│     'composition_score': 9.5,                           │
│     'composition_comment': "Masterful...",              │
│     'lighting_score': 9.0,                              │
│     'lighting_comment': "Golden hour...",               │
│     ... (all 8 dimensions)                              │
│   },                                                     │
│   image_title="The Tetons and the Snake River",        │
│   date_taken="1942",                                     │
│   location="Grand Teton National Park, Wyoming",       │
│   image_significance="One of Adams' most iconic..."    │
│ )                                                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Database: mondrian.db                                    │
│ Table: dimensional_profiles                             │
│                                                          │
│ INSERT INTO dimensional_profiles (                      │
│   profile_id,                                           │
│   job_id,                                               │
│   advisor_id,                                            │
│   image_path,                                           │
│   composition_score,      ← 9.5                         │
│   composition_comment,    ← "Masterful rule of thirds" │
│   lighting_score,         ← 9.0                         │
│   lighting_comment,       ← "Golden hour sidelight"    │
│   focus_sharpness_score,  ← ...                         │
│   focus_sharpness_comment,← ...                         │
│   color_harmony_score,    ← ...                         │
│   ... (8 dimensions × 2 fields each)                   │
│   image_title,            ← "The Tetons and..."        │
│   date_taken,             ← "1942"                      │
│   location,               ← "Grand Teton NP, WY"       │
│   image_significance,     ← "Selected for Voyager..."  │
│   techniques_json,        ← NULL (filled in Step 3)    │
│   overall_grade,          ← "A+"                        │
│   image_description,      ← "Iconic landscape..."      │
│   analysis_json,          ← {full JSON response}        │
│   created_at              ← timestamp                   │
│ )                                                        │
└─────────────────────────────────────────────────────────┘
```

**Result**: 11 dimensional profiles stored in database, one per advisor image.

---

### Step 3: Technique Detection in Advisor Images

**Script**: `tools/rag/analyze_advisor_techniques.py`

```bash
python3 tools/rag/analyze_advisor_techniques.py --advisor ansel
```

**What happens:**

```
For each advisor image:

┌─────────────────────────────────────────────────────────┐
│ AI Advisor Service (MLX Vision Model)                   │
│                                                          │
│ Input: advisor image                                     │
│                                                          │
│ Prompt: "Analyze this Ansel Adams photograph for       │
│          specific technical approaches:                 │
│          1. Zone System Tonal Range: none/moderate/    │
│             strong                                      │
│          2. Depth of Field: shallow_dof/moderate/      │
│             deep_dof_f64                                │
│          3. Foreground Anchoring: none/present/strong  │
│          4. Composition: rule_of_thirds/s_curve/       │
│             triangular/leading_lines/centered           │
│          5. Lighting: dramatic_sidelight/golden_hour/  │
│             high_contrast/overcast_diffused/backlight   │
│          6. Subject: grand_landscape/intimate_scene/   │
│             architectural/natural_detail/portrait       │
│          7. Technical Precision: low/medium/high"      │
│                                                          │
│ Model analyzes VISUAL content and returns JSON:        │
│ {                                                        │
│   "zone_system": "strong",                              │
│   "depth_of_field": "deep_dof_f64",                    │
│   "foreground_anchor": "strong",                        │
│   "composition": "rule_of_thirds",                      │
│   "lighting": "golden_hour",                            │
│   "subject": "grand_landscape",                         │
│   "technical_precision": "high",                        │
│   "explanation": "Classic Adams technique: f/64 deep   │
│                   DOF with river rocks as foreground   │
│                   anchor, full Zone System tonal range" │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ analyze_advisor_techniques.py                           │
│                                                          │
│ save_techniques_to_db(                                  │
│   db_path="mondrian.db",                                │
│   image_path="/path/to/Adams_The_Tetons...",           │
│   techniques={                                           │
│     "zone_system": "strong",                            │
│     "depth_of_field": "deep_dof_f64",                  │
│     "foreground_anchor": "strong",                      │
│     "composition": "rule_of_thirds",                    │
│     "lighting": "golden_hour",                          │
│     "subject": "grand_landscape",                       │
│     "technical_precision": "high"                       │
│   },                                                     │
│   advisor_id="ansel"                                     │
│ )                                                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Database: mondrian.db                                    │
│ Table: dimensional_profiles                             │
│                                                          │
│ UPDATE dimensional_profiles                             │
│ SET techniques_json = '{"zone_system": "strong", ...}' │
│ WHERE image_path = '/path/to/Adams_The_Tetons...'      │
│   AND advisor_id = 'ansel'                              │
└─────────────────────────────────────────────────────────┘
```

**Result**: Each advisor image now has BOTH:
- **Dimensional scores** (8 dimensions × score + comment)
- **Technique data** (7 technique categories)

---

### Step 3 Summary: Complete Database State

After preprocessing, `dimensional_profiles` table contains:

```
┌────────────────┬──────────────┬──────────────────┬────────────────────┐
│ profile_id     │ advisor_id   │ image_path       │ Dimensional Data   │
├────────────────┼──────────────┼──────────────────┼────────────────────┤
│ ansel_001      │ ansel        │ ...Tetons.jpg    │ comp: 9.5          │
│                │              │                  │ light: 9.0         │
│                │              │                  │ depth: 10.0        │
│                │              │                  │ ... (8 dims)       │
├────────────────┼──────────────┼──────────────────┼────────────────────┤
│ ansel_002      │ ansel        │ ...Clearing.jpg  │ comp: 9.0          │
│                │              │                  │ light: 10.0        │
│                │              │                  │ ... (8 dims)       │
├────────────────┼──────────────┼──────────────────┼────────────────────┤
│ ... (11 total) │              │                  │                    │
└────────────────┴──────────────┴──────────────────┴────────────────────┘

┌────────────────┬──────────────────────┬──────────────────────────────┐
│ profile_id     │ Metadata             │ Technique Data               │
├────────────────┼──────────────────────┼──────────────────────────────┤
│ ansel_001      │ title: "The Tetons"  │ zone_system: strong          │
│                │ date: "1942"         │ dof: deep_dof_f64            │
│                │ location: "GT NP"    │ foreground: strong           │
│                │ significance: "..."  │ composition: rule_of_thirds  │
│                │                      │ lighting: golden_hour        │
│                │                      │ subject: grand_landscape     │
│                │                      │ precision: high              │
├────────────────┼──────────────────────┼──────────────────────────────┤
│ ansel_002      │ title: "Clearing..." │ zone_system: strong          │
│                │ date: "1944"         │ dof: deep_dof_f64            │
│                │ ...                  │ foreground: strong           │
│                │                      │ composition: triangular      │
│                │                      │ lighting: high_contrast      │
│                │                      │ ...                          │
├────────────────┼──────────────────────┼──────────────────────────────┤
│ ... (11 total) │                      │                              │
└────────────────┴──────────────────────┴──────────────────────────────┘
```

**This database now contains everything needed to evaluate user images!**

---

## Phase 2: Inference - Evaluating User Images

### User Upload Flow (with RAG enabled)

```bash
curl -X POST http://localhost:5005/upload \
  -F "image=@user_landscape.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

---

### Step 1: Initial User Image Analysis (Pass 1)

```
┌─────────────────────────────────────────────────────────┐
│ Job Service (port 5005)                                  │
│                                                          │
│ 1. Receive user image upload                            │
│ 2. Create job record in database                        │
│ 3. Forward to AI Advisor Service                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ AI Advisor Service (port 5100)                          │
│ File: ai_advisor_service.py                             │
│                                                          │
│ _analyze_image(job_id, image_path, advisor_id,         │
│                enable_rag=True)                         │
│                                                          │
│ Step 1: Analyze user image (no RAG context yet)        │
│   → Call MLX model with advisor prompt                  │
│   → Get dimensional analysis                            │
│   → Extract dimensional profile                         │
│                                                          │
│ Result: {                                               │
│   "composition": {                                       │
│     "score": 6.5,                                       │
│     "comment": "Subject centered, follows rule of      │
│                 thirds but lacks foreground element"    │
│   },                                                     │
│   "depth_and_perspective": {                            │
│     "score": 5.0,                                       │
│     "comment": "Shallow depth of field - background    │
│                 is blurred. Limited sense of depth"     │
│   },                                                     │
│   ... (8 dimensions)                                    │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ json_to_html_converter.py                               │
│                                                          │
│ Extract user's dimensional profile:                     │
│   composition_score: 6.5                                │
│   depth_and_perspective_score: 5.0                     │
│   ... (8 dimensions)                                    │
└─────────────────────────────────────────────────────────┘
```

---

### Step 2: RAG Retrieval - Find Similar Advisor Images

```
┌─────────────────────────────────────────────────────────┐
│ technique_rag.py                                         │
│                                                          │
│ get_technique_based_rag_context(...)                    │
│                                                          │
│ Step 1: Get similar advisor images by dimensions       │
│   get_similar_images_by_techniques(                     │
│     db_path="mondrian.db",                              │
│     advisor_id="ansel",                                  │
│     user_dimensional_profile={                          │
│       'composition': 6.5,                               │
│       'depth_and_perspective': 5.0,                    │
│       ... (user scores)                                 │
│     },                                                   │
│     top_k=3                                             │
│   )                                                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ json_to_html_converter.py                               │
│                                                          │
│ find_similar_by_dimensions(...)                         │
│                                                          │
│ SELECT * FROM dimensional_profiles                      │
│ WHERE advisor_id = 'ansel'                              │
│   AND image_path != user_image_path                     │
│                                                          │
│ For each advisor image:                                 │
│   1. Calculate Euclidean distance:                      │
│      distance = sqrt(                                   │
│        (user_comp - ref_comp)² +                        │
│        (user_depth - ref_depth)² +                      │
│        ... (8 dimensions)                               │
│      )                                                   │
│                                                          │
│   2. Sort by distance (ascending)                       │
│   3. Return top 3 closest matches                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Query Result: Top 3 Similar Images                      │
│                                                          │
│ 1. "The Tetons and the Snake River" (distance: 2.8)    │
│    - composition: 9.5 (vs user 6.5) [+3.0 gap]         │
│    - depth: 10.0 (vs user 5.0) [+5.0 gap]             │
│    - lighting: 9.0                                      │
│    - metadata: title, date, location, significance     │
│    - techniques: {zone_system: strong,                  │
│                   dof: deep_dof_f64,                   │
│                   foreground: strong, ...}              │
│                                                          │
│ 2. "Clearing Winter Storm" (distance: 3.1)             │
│    - composition: 9.0 (vs user 6.5) [+2.5 gap]         │
│    - depth: 9.5 (vs user 5.0) [+4.5 gap]              │
│    - techniques: {zone_system: strong,                  │
│                   dof: deep_dof_f64, ...}              │
│                                                          │
│ 3. "Half Dome, Merced River, Winter" (distance: 3.4)   │
│    - composition: 8.5 (vs user 6.5) [+2.0 gap]         │
│    - depth: 10.0 (vs user 5.0) [+5.0 gap]             │
│    - techniques: {zone_system: strong,                  │
│                   dof: deep_dof_f64, ...}              │
└─────────────────────────────────────────────────────────┘
```

---

### Step 3: Technique Comparison & Prompt Augmentation

```
┌─────────────────────────────────────────────────────────┐
│ technique_rag.py                                         │
│                                                          │
│ augment_prompt_with_technique_context(...)              │
│                                                          │
│ Build enhanced prompt with:                             │
│                                                          │
│ 1. Dimensional Comparison Table:                        │
│    ┌──────────────┬──────┬──────────────┬──────┐      │
│    │ Dimension    │ User │ Reference #1 │ Gap  │      │
│    ├──────────────┼──────┼──────────────┼──────┤      │
│    │ Composition  │ 6.5  │ 9.5          │ +3.0 │      │
│    │ Depth        │ 5.0  │ 10.0         │ +5.0 │ ← BIG│
│    │ Lighting     │ 7.0  │ 9.0          │ +2.0 │      │
│    └──────────────┴──────┴──────────────┴──────┘      │
│                                                          │
│ 2. Reference Image Details:                             │
│    **Reference #1: "The Tetons and the Snake River"**  │
│    - Date: 1942                                         │
│    - Location: Grand Teton National Park, Wyoming      │
│    - Significance: Selected for Voyager Golden Record  │
│    - Top Dimension: Depth & Perspective (10.0/10)      │
│      "f/64 technique - front-to-back sharpness..."     │
│                                                          │
│ 3. Technical Approach:                                  │
│    - Zone System: strong                                │
│    - Depth of Field: Deep (f/64 style - everything    │
│      sharp)                                             │
│    - Composition: Rule of Thirds                        │
│    - Lighting: Golden Hour                              │
│                                                          │
│ 4. Instructions for Technique-Based Analysis:          │
│    "THE CRUX: Compare the user's photographic          │
│     techniques to the advisor's signature approaches.   │
│     Grade based on how well they match the master's    │
│     style..."                                           │
│                                                          │
│    Examples:                                            │
│    - "You used shallow DOF, but Ansel Adams' f/64     │
│       approach uses deep DOF... Recommendation: Use    │
│       f/11 or smaller"                                  │
│                                                          │
│    - "Like Reference #1, you've used rule of thirds.   │
│       Excellent! Strengthen it by adding foreground    │
│       anchor..."                                        │
└─────────────────────────────────────────────────────────┘
```

---

### Step 4: LLM Generation with RAG Context (Pass 2)

```
┌─────────────────────────────────────────────────────────┐
│ AI Advisor Service - MLX Model (Pass 2)                 │
│                                                          │
│ Input:                                                   │
│   - User image                                          │
│   - Original advisor prompt                             │
│   - RAG context (3 reference images with techniques)   │
│   - Dimensional comparison tables                       │
│   - Technique comparison instructions                   │
│                                                          │
│ Model generates technique-based feedback:               │
│                                                          │
│ "Your landscape photograph shows promise, but reveals   │
│  key technique gaps when compared to Adams' approach:   │
│                                                          │
│  **Composition (6.5/10)**                               │
│  You've correctly applied rule of thirds placement,     │
│  which aligns with Adams' approach seen in 'The Tetons  │
│  and the Snake River'. However, you're missing a        │
│  critical Adams technique: foreground anchoring.        │
│                                                          │
│  Reference #1 uses strong foreground rocks to establish │
│  scale and guide the eye into the frame. **Your grade   │
│  could improve to 8.5/10** by including a foreground   │
│  element in the lower third.                            │
│                                                          │
│  **Depth & Perspective (5.0/10)** ← MAJOR GAP          │
│  This is where your technique diverges most from        │
│  Adams' signature style. You've used shallow depth of   │
│  field (likely f/2.8-4), creating background blur.     │
│                                                          │
│  Adams' f/64 Group philosophy—evident in all three      │
│  references—prioritizes front-to-back sharpness. In    │
│  'The Tetons', everything from foreground river rocks   │
│  to distant peaks is tack-sharp (10.0/10).             │
│                                                          │
│  **Recommendation**: Use f/11 or smaller aperture.     │
│  This will bring your foreground and distant elements   │
│  into sharp focus, matching Adams' deep DOF mastery.   │
│  **Potential improvement**: 5.0 → 9.0                  │
│                                                          │
│  **Zone System Application**                            │
│  Your tonal range is moderate, but references #1-3     │
│  all show strong Zone System usage with deep blacks    │
│  and bright whites. Expose for the highlights, develop  │
│  for the shadows..."                                    │
└─────────────────────────────────────────────────────────┘
```

---

### Step 5: Save User Profile & Return Response

```
┌─────────────────────────────────────────────────────────┐
│ json_to_html_converter.py                               │
│                                                          │
│ save_dimensional_profile(                               │
│   profile_id=f"user_{job_id}",                         │
│   job_id=job_id,                                        │
│   advisor_id="ansel",                                    │
│   image_path=user_image_path,                           │
│   dimensional_data={user scores from Pass 1},          │
│   analysis_json={full Pass 2 response with RAG}        │
│ )                                                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Database: dimensional_profiles                          │
│                                                          │
│ Now contains:                                           │
│   - 11 advisor profiles (references)                    │
│   - 1 user profile (this upload)                        │
│                                                          │
│ User can upload more images → more comparisons!         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Response to Client                                       │
│                                                          │
│ {                                                        │
│   "job_id": "...",                                      │
│   "status": "completed",                                 │
│   "html_output": "<technique-based feedback>",         │
│   "rag_enabled": true,                                   │
│   "references_used": [                                   │
│     "The Tetons and the Snake River",                   │
│     "Clearing Winter Storm",                            │
│     "Half Dome, Merced River, Winter"                   │
│   ],                                                     │
│   "technique_gaps": [                                    │
│     {"dimension": "depth", "gap": 5.0, "technique":    │
│      "Use f/64 deep DOF instead of shallow DOF"}       │
│   ]                                                      │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
```

---

## Summary: What Gets Evaluated

### 8 Dimensional Scores (extracted from image analysis)

1. **Composition** (0-10)
   - Rule of thirds, golden ratio, balance
   - Comments explain specific strengths/weaknesses

2. **Lighting** (0-10)
   - Quality, direction, mood
   - Golden hour, sidelight, high contrast, etc.

3. **Focus & Sharpness** (0-10)
   - Sharpness, bokeh quality, focus point selection
   - Critical focus, depth of field

4. **Color Harmony** (0-10)
   - Color relationships, palette, saturation
   - Complementary, analogous, monochromatic

5. **Subject Isolation** (0-10)
   - Subject separation from background
   - Visual hierarchy, emphasis

6. **Depth & Perspective** (0-10)
   - Sense of three-dimensionality
   - Foreground/midground/background layers

7. **Visual Balance** (0-10)
   - Weight distribution, symmetry/asymmetry
   - Tonal balance, compositional stability

8. **Emotional Impact** (0-10)
   - Mood, storytelling, viewer engagement
   - How effectively the image communicates

### 7 Technique Categories (detected from visual analysis)

1. **Zone System Usage**: none / moderate / strong
2. **Depth of Field**: shallow_dof / moderate / deep_dof_f64
3. **Foreground Anchoring**: none / present / strong
4. **Composition Type**: rule_of_thirds / s_curve / triangular / leading_lines / centered
5. **Lighting Style**: dramatic_sidelight / golden_hour / high_contrast / overcast_diffused / backlight
6. **Subject Matter**: grand_landscape / intimate_scene / architectural / natural_detail / portrait
7. **Technical Precision**: low / medium / high

### Rich Metadata (for context and teaching)

- **Image Title**: "The Tetons and the Snake River"
- **Date Taken**: "1942"
- **Location**: "Grand Teton National Park, Wyoming"
- **Significance**: Why this image matters historically/artistically
- **Source**: Wikimedia Commons URL, artist, license

---

## The Crux: How It All Comes Together

```
User Image Analysis (Pass 1)
    ↓
Dimensional Profile Extracted
    ↓
[Query Database]
    ↓
Find 3 Most Similar Advisor Images by Dimensions
    ↓
For Each Reference:
    ├─ Retrieve dimensional scores & comments
    ├─ Retrieve detected techniques
    ├─ Retrieve rich metadata (title, date, significance)
    └─ Calculate dimensional gaps
    ↓
Build Comparative RAG Context:
    ├─ "Your depth: 5.0 vs Reference #1: 10.0 = +5.0 gap"
    ├─ "You used shallow DOF"
    ├─ "Adams uses deep_dof_f64 in all 3 references"
    └─ "Recommendation: Use f/11+ to match this technique"
    ↓
Re-analyze with RAG Context (Pass 2)
    ↓
LLM generates technique-based, comparative feedback
    ↓
User learns specific techniques, not just scores!
```

**This transforms generic feedback into masterclass-quality teaching.**

---

## Database Schema Reference

### dimensional_profiles Table

Stores all analyzed images (both advisor references and user uploads):

```sql
CREATE TABLE dimensional_profiles (
    -- Identity
    profile_id TEXT PRIMARY KEY,
    job_id TEXT,
    advisor_id TEXT,
    image_path TEXT,
    
    -- 8 Dimensional Scores & Comments
    composition_score REAL,
    composition_comment TEXT,
    lighting_score REAL,
    lighting_comment TEXT,
    focus_sharpness_score REAL,
    focus_sharpness_comment TEXT,
    color_harmony_score REAL,
    color_harmony_comment TEXT,
    subject_isolation_score REAL,
    subject_isolation_comment TEXT,
    depth_perspective_score REAL,
    depth_perspective_comment TEXT,
    visual_balance_score REAL,
    visual_balance_comment TEXT,
    emotional_impact_score REAL,
    emotional_impact_comment TEXT,
    
    -- Summary
    overall_grade TEXT,
    image_description TEXT,
    
    -- Rich Metadata (for references)
    image_title TEXT,
    date_taken TEXT,
    location TEXT,
    image_significance TEXT,
    
    -- Technique Data (JSON)
    techniques_json TEXT,  -- {"zone_system": "strong", "dof": "deep_dof_f64", ...}
    
    -- Full Analysis
    analysis_json TEXT,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Next Steps

1. **Add More Advisors**: Repeat this process for other photographers/artists
2. **Expand Technique Detection**: Add advisor-specific technique categories
3. **User Technique Detection**: Analyze user images for techniques (not just dimensions)
4. **Automatic Grading**: Adjust scores based on technique alignment with advisor

---

**The key insight**: By storing BOTH dimensional data AND technique data for advisor images, we can provide technique-specific, comparative feedback that teaches users HOW to shoot like the masters, not just WHAT score they received.




