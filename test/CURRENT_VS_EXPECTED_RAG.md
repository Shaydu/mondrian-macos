# Current RAG Workflow vs Expected Behavior

## ✅ What We DO Now (Correct)

1. **Extract Techniques**: Pass 1 extracts dimensional scores AND techniques from user photo ✓
2. **Find Similar Images**: Finds closest matches from advisor's pre-analyzed photos ✓
   - Primary: Technique-based matching (same techniques)
   - Fallback: Dimensional similarity (if no technique matches)
3. **Full Comparison in Detail View**: Shows reference images, dimensional comparisons, and full feedback ✓

## ❌ What We DON'T Do (Issue)

### Summary: Top 3 Recommendations

**CURRENT BEHAVIOR**:
- Sorts by **lowest dimension scores** (user's worst-performing dimensions)
- Example: If user has composition=4.0, lighting=6.0, focus=7.0
  - Shows: Composition (4.0), Lighting (6.0), Focus (7.0)
  - But if reference images show composition=5.0 and lighting=9.0, we should prioritize lighting!

**EXPECTED BEHAVIOR**:
- Calculate **deltas** for each dimension: `reference_score - user_score`
- Sort by **largest positive deltas** (biggest improvement opportunities)
- Example:
  - User composition: 4.0, Reference: 5.0 → Delta: +1.0
  - User lighting: 6.0, Reference: 9.0 → Delta: +3.0 ⭐ (BIGGEST)
  - User focus: 7.0, Reference: 7.5 → Delta: +0.5
  - **Should show**: Lighting (+3.0), Composition (+1.0), Focus (+0.5)

## Code Location

- **Summary extraction**: `mondrian/job_service_v2.3.py` → `extract_critical_recommendations()` (line 2523)
- **Current sorting**: Line 2711: `recommendations.sort(key=lambda x: x['dimension_score'])` (sorts by lowest score)
- **Needs**: Access to reference image scores to calculate deltas

## The Fix Needed

1. Store deltas when finding similar images (already calculated in `technique_rag.py`)
2. Pass deltas to `extract_critical_recommendations()` 
3. Sort by largest delta instead of lowest score
