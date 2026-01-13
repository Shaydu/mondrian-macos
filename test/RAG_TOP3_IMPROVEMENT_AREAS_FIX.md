# RAG Analysis: Top 3 Biggest Improvement Areas Fix

## Problem Fixed

Previously, the RAG-enabled summary was showing the **top 3 lowest-scoring dimensions** (user's worst dimensions), rather than the **top 3 biggest improvement areas** based on deltas with reference images.

### Example of the Issue:

- User composition: 4.0, Reference: 5.0 → Delta: +1.0
- User lighting: 6.0, Reference: 9.0 → Delta: +3.0 ⭐ (BIGGEST opportunity)
- User focus: 7.0, Reference: 7.5 → Delta: +0.5

**Before**: Would show Composition (4.0), Lighting (6.0), Focus (7.0) - sorted by lowest scores  
**After**: Will show Lighting (+3.0), Composition (+1.0), Focus (+0.5) - sorted by biggest improvement deltas

## Changes Made

### 1. Modified `extract_critical_recommendations()` Function

**Location**: `mondrian/job_service_v2.3.py` (line ~2523)

**Changes**:
- Added `enable_rag` and `job_id` parameters
- When RAG is enabled:
  1. Gets user's dimensional profile from database
  2. Finds similar advisor images (same as RAG workflow)
  3. Calculates deltas for each dimension: `reference_score - user_score`
  4. Averages deltas across all reference images
  5. Sorts recommendations by **largest positive delta** (biggest improvement opportunities)
- When RAG is disabled (baseline):
  - Uses original logic (sorts by lowest scores)

### 2. Updated Function Call

**Location**: `mondrian/job_service_v2.3.py` (line ~654)

**Change**:
```python
# Before:
critical_recs = extract_critical_recommendations(llm_outputs)

# After:
critical_recs = extract_critical_recommendations(llm_outputs, enable_rag=enable_rag, job_id=job_id)
```

## How It Works

### RAG Mode (enable_rag=True):

1. **Gets User Profile**: Retrieves user's dimensional scores from database
2. **Finds Reference Images**: Uses same RAG logic to find similar advisor images
3. **Calculates Deltas**: For each dimension:
   - `delta = reference_score - user_score`
   - Only considers positive deltas (improvement opportunities)
   - Averages across all reference images
4. **Sorts by Deltas**: Recommendations sorted by largest positive delta
5. **Top 3**: Shows the 3 dimensions with biggest improvement potential

### Baseline Mode (enable_rag=False):

- Uses original logic: sorts by lowest dimension scores
- No reference images available, so can't calculate deltas

## Benefits

1. **More Actionable**: Shows where user can improve most, not just where they're worst
2. **RAG-Specific**: Only applies delta-based sorting when RAG is enabled
3. **Backward Compatible**: Baseline mode unchanged
4. **Robust Matching**: Handles dimension name variations (e.g., "Focus & Sharpness" vs "focus_sharpness")

## Testing

After restarting services, run:
```bash
python3 test/test_ios_e2e_rag_comparison.py --rag
```

The summary should now show the top 3 dimensions where the user has the biggest opportunity to improve by learning from the reference images.
