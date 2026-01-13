# RAG Workflow: Current vs Expected

## What the Code Does NOW

### Pass 1: Extract Profile from User Photo ✓
- Extracts dimensional scores (8 dimensions: composition, lighting, etc.)
- Extracts techniques (zone_system, depth_of_field, composition, lighting, foreground_anchoring)
- Saves profile to database

### Query: Find Similar Advisor Images ✓
- **Primary**: Technique-based matching (finds advisor images with same techniques)
- **Fallback**: Dimensional similarity (if no technique matches)
- Returns top 3 similar reference images

### Pass 2: Full Analysis with Comparison ✓
- Augments prompt with reference image context
- Includes dimensional comparisons (deltas) in the prompt
- Generates full analysis with comparative feedback

### Summary: Top 3 Recommendations ❌
- **CURRENT**: Sorts by lowest dimension scores (user's worst dimensions)
- **PROBLEM**: Doesn't prioritize by biggest improvement potential (deltas)
- Example: If user has composition=5 and reference has composition=6 (small delta), but lighting=6 and reference has lighting=9 (big delta), it might show composition first

### Detail View: Full Comparison ✓
- Shows reference images with similarities
- Shows dimensional comparisons
- Shows full feedback for all dimensions

## What We SHOULD Do

### Summary: Top 3 Biggest Improvement Areas
- Calculate deltas for each dimension: `reference_score - user_score`
- Sort by largest positive deltas (biggest improvement opportunities)
- Show top 3 dimensions where user can improve most by learning from references

### Example:
- User composition: 5.0, Reference: 6.0 → Delta: +1.0
- User lighting: 6.0, Reference: 9.0 → Delta: +3.0 ⭐ (BIGGEST)
- User focus: 7.0, Reference: 7.5 → Delta: +0.5
- User color: 8.0, Reference: 8.5 → Delta: +0.5

**Top 3 should be**: Lighting (+3.0), Composition (+1.0), Focus (+0.5)

## Code Changes Needed

1. **In `extract_critical_recommendations`**: Need access to reference image dimensional scores to calculate deltas
2. **Store deltas**: Save dimensional deltas in the job or profile data
3. **Sort by deltas**: Instead of sorting by lowest user score, sort by largest delta
