# Technique-Based RAG Architecture

## Overview

Rearchitect the RAG system from score-based matching to technique-based matching, enabling comparative feedback that references specific photographic techniques used by master photographers like Ansel Adams.

## Current vs. Proposed Architecture

### Current (Score-Based)
```
User Image → Extract 8 Dimensional Scores → Find Similar Scores → Generic Feedback
Example: "Composition: 8/10, Reference image scored 9.5/10 (+1.5 stronger)"
```

### Proposed (Technique-Based)
```
User Image → Extract Techniques Used → Match Techniques → Specific Comparative Feedback
Example: "You used foreground anchoring like Adams did in 'Moonrise over Hernandez'. 
         His foreground element (village) creates stronger depth - try positioning 
         your element lower in the frame for similar effect."
```

## Database Schema Changes

### 1. New Table: `photographer_techniques`

Stores the catalog of known photographic techniques:

```sql
CREATE TABLE photographer_techniques (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,                    -- "Foreground Anchoring"
    category TEXT NOT NULL,                -- "Composition", "Lighting", "Technical"
    description TEXT NOT NULL,             -- What this technique is
    detection_criteria TEXT,               -- How to identify it in images
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Example Techniques for Ansel Adams:**
- **Composition:**
  - Foreground Anchoring with Natural Elements
  - Deep Depth of Field for Landscape Sharpness
  - Rule of Thirds with Horizon Placement
  - Leading Lines through Natural Formations
  - Triangular Composition
  
- **Lighting:**
  - Zone System for Dramatic Tonal Range
  - High Contrast Lighting (Zones II-IX)
  - Sidelight for Texture Enhancement
  - Golden Hour Warmth
  - Overcast Diffusion for Even Tones
  
- **Technical:**
  - Large Format Camera Precision
  - f/64 Group Sharpness
  - Pre-visualization and Exposure Planning
  - Dodging and Burning in Post

### 2. New Table: `advisor_image_techniques`

Links advisor images to the techniques they demonstrate:

```sql
CREATE TABLE advisor_image_techniques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisor_id TEXT NOT NULL,              -- "ansel"
    image_path TEXT NOT NULL,              -- Path to the reference image
    technique_id TEXT NOT NULL,            -- FK to photographer_techniques
    strength TEXT NOT NULL,                -- "strong", "moderate", "subtle"
    evidence TEXT,                         -- Specific description of how technique appears
    example_region TEXT,                   -- Optional: bounding box or region description
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advisor_id) REFERENCES advisors(id),
    FOREIGN KEY (technique_id) REFERENCES photographer_techniques(id)
);
```

**Example Entry:**
```json
{
  "advisor_id": "ansel",
  "image_path": "/advisor_artworks/ansel/moonrise-hernandez.jpg",
  "technique_id": "foreground_anchoring",
  "strength": "strong",
  "evidence": "Village buildings in lower third create strong foreground anchor, 
               establishing scale and depth against moonrise and mountains",
  "example_region": "bottom 30% of frame"
}
```

### 3. New Table: `user_image_techniques`

Stores detected techniques in user-submitted images:

```sql
CREATE TABLE user_image_techniques (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,                  -- FK to jobs table
    image_path TEXT NOT NULL,
    technique_id TEXT NOT NULL,            -- FK to photographer_techniques
    confidence REAL NOT NULL,              -- 0.0-1.0 confidence score
    evidence TEXT,                         -- What the AI detected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    FOREIGN KEY (technique_id) REFERENCES photographer_techniques(id)
);
```

### 4. Modified Table: `dimensional_profiles`

Keep existing table but add technique summary:

```sql
ALTER TABLE dimensional_profiles ADD COLUMN techniques_json TEXT;
-- JSON array of technique IDs detected in this image
```

## Workflow Changes

### Phase 1: Technique Indexing (One-Time Setup)

**Goal:** Analyze all Ansel Adams reference images and tag them with techniques.

```python
# Script: index_advisor_techniques.py

1. Load all advisor images from /advisor_artworks/ansel/
2. For each image:
   a. Use MLX vision model with technique detection prompt
   b. Extract techniques present (from predefined list)
   c. Store in advisor_image_techniques table
3. Build technique index for fast lookup
```

**Technique Detection Prompt:**
```
Analyze this photograph by Ansel Adams and identify which of these techniques are present:

COMPOSITION TECHNIQUES:
- Foreground anchoring with natural elements (strong/moderate/subtle/absent)
- Deep depth of field for landscape sharpness (strong/moderate/subtle/absent)
- Rule of thirds horizon placement (strong/moderate/subtle/absent)
- Leading lines through natural formations (strong/moderate/subtle/absent)
- Triangular composition (strong/moderate/subtle/absent)

LIGHTING TECHNIQUES:
- Zone System dramatic tonal range (strong/moderate/subtle/absent)
- High contrast lighting (Zones II-IX) (strong/moderate/subtle/absent)
- Sidelight for texture enhancement (strong/moderate/subtle/absent)
- Golden hour warmth (strong/moderate/subtle/absent)

TECHNICAL APPROACHES:
- f/64 group sharpness throughout frame (strong/moderate/subtle/absent)

For each technique present, provide:
1. Strength (strong/moderate/subtle)
2. Evidence (1-2 sentences describing how it appears in this specific image)
3. Region (where in the frame it's most evident)

Output as JSON.
```

### Phase 2: User Image Analysis (Real-Time)

**Modified Analysis Flow:**

```python
# In ai_advisor_service.py - analyze_image()

1. Analyze user image with standard dimensional analysis (existing)
2. NEW: Analyze user image for techniques present:
   - Use technique detection prompt
   - Store results in user_image_techniques table
3. NEW: Find matching advisor images by technique overlap:
   - Query advisor_image_techniques for images with similar techniques
   - Rank by technique overlap score
4. Augment prompt with technique-based context (not score deltas)
5. Generate feedback with comparative technique examples
```

### Phase 3: Technique-Based RAG Matching

**New Function:** `get_similar_images_by_techniques()`

```python
def get_similar_images_by_techniques(
    user_techniques: List[str],
    advisor_id: str = "ansel",
    top_k: int = 3
) -> List[Dict]:
    """
    Find advisor images that demonstrate similar techniques.
    
    Args:
        user_techniques: List of technique IDs detected in user image
        advisor_id: Advisor to search within
        top_k: Number of results to return
        
    Returns:
        List of advisor images with technique overlap details
    """
    
    # Query for advisor images that share techniques
    query = """
        SELECT 
            ait.image_path,
            ait.technique_id,
            pt.name as technique_name,
            pt.description,
            ait.strength,
            ait.evidence,
            COUNT(*) OVER (PARTITION BY ait.image_path) as technique_count
        FROM advisor_image_techniques ait
        JOIN photographer_techniques pt ON ait.technique_id = pt.id
        WHERE ait.advisor_id = ?
          AND ait.technique_id IN ({})
        ORDER BY technique_count DESC, ait.strength DESC
        LIMIT ?
    """.format(','.join(['?'] * len(user_techniques)))
    
    # Group results by image_path
    # Return images with most technique overlap
```

**Technique Overlap Scoring:**
```python
def calculate_technique_overlap(user_techniques, advisor_techniques):
    """
    Score = (shared_techniques / total_unique_techniques) * strength_multiplier
    
    Strength multiplier:
    - strong: 1.0
    - moderate: 0.7
    - subtle: 0.4
    """
    shared = set(user_techniques) & set(advisor_techniques)
    total = set(user_techniques) | set(advisor_techniques)
    
    base_score = len(shared) / len(total) if total else 0
    
    # Apply strength multipliers
    strength_bonus = sum(
        get_strength_multiplier(t) 
        for t in shared
    ) / len(shared) if shared else 0
    
    return base_score * strength_bonus
```

### Phase 4: Technique-Based Prompt Augmentation

**New Function:** `augment_prompt_with_technique_context()`

```python
def augment_prompt_with_technique_context(
    advisor_prompt: str,
    user_techniques: List[Dict],
    similar_images: List[Dict]
) -> str:
    """
    Build context showing:
    1. Techniques detected in user image
    2. How Adams used same techniques in reference images
    3. Specific comparative guidance
    """
    
    context = "\n\n## TECHNIQUE-BASED REFERENCE CONTEXT\n\n"
    context += "### Techniques Detected in User's Image:\n\n"
    
    for tech in user_techniques:
        context += f"- **{tech['name']}** ({tech['confidence']:.0%} confidence)\n"
        context += f"  Evidence: {tech['evidence']}\n\n"
    
    context += "\n### How Ansel Adams Used These Techniques:\n\n"
    
    for i, img in enumerate(similar_images, 1):
        img_name = os.path.basename(img['image_path'])
        context += f"#### Reference Image #{i}: {img_name}\n\n"
        
        # List shared techniques
        for tech in img['shared_techniques']:
            context += f"**{tech['name']}** ({tech['strength']})\n"
            context += f"- Adams' approach: {tech['evidence']}\n"
            context += f"- Region: {tech['example_region']}\n\n"
    
    context += "\n### Instructions for Comparative Feedback:\n\n"
    context += """
When providing recommendations, reference these specific examples:
1. Identify which techniques the user attempted
2. Compare their execution to Adams' reference images
3. Provide specific guidance: "Like Adams did in [image], try [specific action]"
4. Explain WHY the technique works in the reference image
5. Suggest concrete improvements based on the comparison

Example format:
"You've used foreground anchoring similar to Adams' 'Moonrise over Hernandez'. 
In that image, Adams positioned the village buildings in the lower third, creating 
a strong base that leads the eye upward to the moon. Your foreground element could 
be strengthened by lowering it in the frame and ensuring it has clear separation 
from the background through lighting or depth of field."
"""
    
    return advisor_prompt + context
```

## Implementation Plan

### Step 1: Database Migration
```bash
python3 scripts/migrate_technique_schema.py
```
- Create new tables
- Populate photographer_techniques with Ansel Adams techniques
- Add indexes for performance

### Step 2: Technique Indexing
```bash
python3 scripts/index_advisor_techniques.py --advisor ansel
```
- Analyze all Ansel Adams images
- Extract and store techniques
- Validate coverage (all images should have 3-5 techniques)

### Step 3: Update AI Advisor Service
- Modify `analyze_image()` to detect techniques
- Implement `get_similar_images_by_techniques()`
- Update `augment_prompt_with_technique_context()`
- Keep dimensional analysis as secondary signal

### Step 4: Update Prompts
- Create technique detection prompt
- Modify advisor prompts to use technique context
- Add examples of technique-based feedback

### Step 5: Testing
```bash
python3 test_technique_rag.py
```
- Test technique detection accuracy
- Verify matching finds relevant images
- Validate feedback quality

## Benefits

### For Users:
- **Specific, actionable feedback** instead of abstract scores
- **Learn from concrete examples** of master techniques
- **Understand the "why"** behind recommendations
- **See technique progression** across multiple reference images

### For System:
- **More meaningful similarity** than numerical scores
- **Explainable recommendations** (technique-based)
- **Scalable** to other photographers (each has unique techniques)
- **Flexible** - can add new techniques without schema changes

## Example Output Comparison

### Before (Score-Based):
```
Composition: 8/10

Your composition shows good balance. Reference image scored 9.5/10 
(+1.5 stronger). Consider improving foreground elements.
```

### After (Technique-Based):
```
Composition: 8/10

You've used foreground anchoring similar to Adams' "Moonrise over Hernandez, 
New Mexico" (1941). In that image, Adams positioned the village buildings in 
the lower 30% of the frame, creating a strong base that establishes scale and 
leads the eye upward to the moon and mountains.

Your foreground element (the rocks) attempts this but could be strengthened:
1. Lower the rocks to occupy the bottom third (currently at 40%)
2. Ensure sharper focus (Adams used f/64 for front-to-back sharpness)
3. Add more separation through lighting - Adams used the last light on the 
   village to make it "pop" against darker mountains

This technique works because it gives the viewer a visual "entry point" and 
establishes depth through scale relationships.
```

## Migration Strategy

### Phase 1: Parallel Systems (Week 1-2)
- Keep existing score-based RAG running
- Build technique system alongside
- A/B test outputs

### Phase 2: Hybrid Approach (Week 3-4)
- Use techniques for matching
- Keep scores for fallback
- Gather user feedback

### Phase 3: Full Migration (Week 5+)
- Switch to technique-based by default
- Deprecate score-based matching
- Keep scores only for analytics

## Open Questions

1. **Technique Taxonomy:** Should we use a hierarchical taxonomy (Composition > Foreground > Anchoring) or flat list?
2. **Confidence Thresholds:** What confidence level should trigger technique detection (0.6? 0.7?)?
3. **Multiple Advisors:** How to handle techniques unique to different photographers?
4. **User Feedback Loop:** How to improve technique detection based on user corrections?

## Next Steps

1. Review and approve this architecture
2. Create database migration script
3. Build technique detection prompt
4. Index first 10 Ansel Adams images as pilot
5. Test end-to-end with sample user image
6. Iterate based on results


