# User Image-Specific Recommendations Fix

## Problem
The system was giving generic recommendations about mountains, rocks, and landscape elements even for non-landscape images (portraits, street photography, etc.). Users were receiving recommendations like "Include a foreground rock" or "Position the mountain mass on the left third" regardless of their actual image content.

## Root Cause
The system prompt (`system_prompt.txt`) contained a **hardcoded mountain landscape example** that showed what recommendations should look like. This example used specific elements like:
- "Include the distinctive foreground rock 3-4 feet from lens"
- "Switch to 24mm focal length to create separation between foreground, midground mountain, and background sky"
- "Reposition to move the darker mountain mass from center to the left third"

The LLM learned from this example and applied these patterns universally, even though it could see the user's actual image.

## Solution Implemented

### 1. Updated System Prompt (`system_prompt.txt`)
**Changes:**
- Added critical enforcement at the top: "**YOU ARE ANALYZING THE USER'S UPLOADED PHOTOGRAPH.** All scores, comments, and recommendations MUST describe and improve THEIR specific image"
- Replaced concrete mountain/rock example with abstract placeholders
- Changed example text from specific elements (e.g., "Move the mountain mass") to generic guidance (e.g., "Move [specific element they photographed]")
- Added explicit rule: "**Recommendations must work with elements PRESENT in the user's image**"
- Added warning: "**DO NOT recommend adding elements that aren't in their image**"

**Example of change:**
- **Before:** `"recommendation": "Include a strong foreground element 3-5 feet from the lens (distinctive boulder, interesting vegetation...)"`
- **After:** `"recommendation": "Provide 2-3 specific actions to enhance depth using elements PRESENT in their scene (e.g., 'Lower camera angle to emphasize [foreground element in their image]')"`

### 2. Updated RAG Prompt Builder (`mondrian/ai_advisor_service_linux.py`)
**Changes:**
- Added clear visual separators (80-character lines) around reference materials
- Added **CRITICAL INSTRUCTION** section explaining:
  - Reference materials are LEARNING EXAMPLES only
  - **YOU ARE ANALYZING THE USER'S UPLOADED PHOTOGRAPH - NOT THESE REFERENCES**
  - Do NOT describe elements from reference images
  - Do NOT recommend adding elements that only exist in references
- Added explicit boundary: "NOW ANALYZE THE USER'S UPLOADED PHOTOGRAPH BELOW"

**Example of change:**
```python
rag_context = "\n\n" + "="*80 + "\n"
rag_context += "## REFERENCE MATERIALS FOR LEARNING (NOT FOR ANALYSIS)\n"
rag_context += "="*80 + "\n\n"
rag_context += "**CRITICAL INSTRUCTION:**\n"
rag_context += "- **YOU ARE ANALYZING THE USER'S UPLOADED PHOTOGRAPH - NOT THESE REFERENCES**\n"
rag_context += "- Do NOT recommend adding elements that only exist in references but not in the user's image\n"
```

## Testing

### Automated Test
Run the test script with different image types:

```bash
# Test with a portrait
python test_user_specific_recommendations.py path/to/portrait.jpg portrait

# Test with street photography
python test_user_specific_recommendations.py path/to/street_photo.jpg street

# Test with a landscape (should still work normally)
python test_user_specific_recommendations.py path/to/landscape.jpg landscape
```

### Manual Test via Web Interface
1. Upload a **non-landscape image** (portrait, street photo, macro, etc.)
2. Analyze with Ansel advisor
3. Check that recommendations:
   - ✅ Describe elements actually in the user's image
   - ✅ Suggest improvements based on what exists
   - ❌ Do NOT mention mountains, rocks, horizons, or landscape-specific elements
   - ❌ Do NOT recommend adding elements that don't exist in the image

### What to Look For

**Good recommendations (user-specific):**
- "Reposition the subject to the right third of the frame"
- "Increase aperture to f/2.8 to blur the background behind the subject"
- "Wait for better directional light from the window"
- "Lower camera angle to emphasize the subject's expression"

**Bad recommendations (generic/irrelevant):**
- "Include a foreground rock 3-4 feet from the lens" (for a portrait)
- "Position the mountain mass on the left third" (for street photography)
- "Place the horizon line on the upper third gridline" (for an image with no horizon)
- "Add a substantial boulder in the bottom right corner" (for any non-landscape)

## Deployment
Changes have been applied and the Docker container has been rebuilt:

```bash
docker-compose build
docker-compose down
docker-compose up -d
```

All services are running and healthy. The fix is now live.

## Verification
To verify the fix is working:
1. Check the system prompt was updated: `docker exec mondrian-services cat /app/system_prompt.txt | head -20`
2. Upload a test image via the web interface
3. Review recommendations for relevance to the actual image content

## Notes
- The LLM (Qwen2-VL/Qwen3-VL) has full vision access to the user's uploaded image
- The problem was NOT that the model couldn't see the image
- The problem was that the prompt's hardcoded example was too strong and overrode what the model saw
- The solution focuses on explicit instruction and clear boundaries between reference materials and user image analysis
