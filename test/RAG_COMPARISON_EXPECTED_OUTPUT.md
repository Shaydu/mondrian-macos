# RAG-Enabled Analysis Expected Output

## Issue
The RAG-enabled analysis is currently failing with a 500 error, so the detailed view only shows the error message (with advisor bio) instead of the RAG comparisons.

## What Should Appear in RAG-Enabled Analysis

When RAG analysis succeeds, the detailed HTML should include:

### 1. Reference Images Section
- **Header**: "Reference Images from Master's Portfolio"
- **Introduction**: "Your image was compared to these similar works:"
- **For each reference image**:
  - Image title
  - Date and location (if available)
  - Similarity percentage (e.g., "Similarity: 85.2%")
  - The actual reference image (displayed)
  - Historical significance (if available)
  - Key dimensional scores (Composition, Lighting, Focus & Sharpness, Emotional Impact)

### 2. Detailed Feedback Section
- Each dimension should include:
  - **Comparative comments** referencing the reference images
  - Language like: "Unlike Reference #1 which...", "Similar to the master work...", "To match the dramatic effect seen in Reference #2..."
  - Specific recommendations based on what worked in the reference images

### 3. Dimensional Comparisons
- Score deltas showing how the user's image compares to references
- Specific feedback on what the reference images did better
- Actionable recommendations to reach the level shown in reference images

## Current Status

The RAG analysis is failing at the AI advisor service level (500 error), so:
- ✅ The code to display RAG comparisons exists in `json_to_html_converter.py`
- ❌ The analysis never completes, so the RAG HTML is never generated
- ❌ Only the error message (with bio header) is shown

## How to Verify RAG is Working

Once the 500 error is fixed, you should see:

1. **In the detailed HTML**:
   - A "Reference Images from Master's Portfolio" section
   - Actual images displayed
   - Similarity scores
   - Dimensional comparisons

2. **In the analysis text**:
   - References to specific reference images
   - Comparative language ("Unlike Reference #1...", "Similar to...")
   - Specific recommendations based on reference images

3. **Difference from baseline**:
   - Baseline: Generic feedback without image references
   - RAG: Specific comparisons to master works with images

## Next Steps

1. **Fix the 500 error** using the diagnostic script:
   ```bash
   python3 test/diagnose_ai_service_error.py
   ```

2. **Re-run the test** once the error is fixed:
   ```bash
   python3 test/test_ios_e2e_rag_comparison.py --rag
   ```

3. **Check the detailed HTML** - it should now show:
   - Reference images section
   - Dimensional comparisons
   - Comparative feedback

## Code Location

The RAG comparison display code is in:
- `mondrian/json_to_html_converter.py` - `json_to_html()` function (lines 42-131)
- `mondrian/ai_advisor_service.py` - `_analyze_image_rag()` function (passes `similar_images_for_html` to `json_to_html()`)
