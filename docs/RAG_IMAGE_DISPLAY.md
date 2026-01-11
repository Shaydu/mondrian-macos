# RAG Reference Images in HTML Output

## Overview

The RAG (Retrieval-Augmented Generation) system now displays **actual reference images** from the advisor's portfolio in the HTML analysis output, not just filenames.

When a user uploads an image with `enable_rag=true`, the system:
1. Finds dimensionally similar images from the advisor's portfolio
2. Displays these reference images with rich metadata
3. Shows visual comparisons alongside the textual feedback

## What's Displayed

For each reference image, the HTML output includes:

### 1. **The Actual Image**
- Full-resolution reference photograph
- Responsive sizing (max-width: 100%)
- Rounded corners and shadow for visual appeal
- Alt text with the artwork title

### 2. **Rich Metadata**
- **Title**: Formal artwork name (e.g., "The Tetons and the Snake River")
- **Date**: When the photograph was taken (e.g., "1942")
- **Location**: Where it was photographed (e.g., "Grand Teton National Park, Wyoming")
- **Historical Significance**: Why the work is important (e.g., "Selected for the Voyager Golden Record")

### 3. **Similarity Score**
- Percentage showing how similar the reference is to the user's image
- Calculated from Euclidean distance in 8-dimensional space

### 4. **Key Dimensional Scores**
- Top 4 dimensions displayed (Composition, Lighting, Focus, Emotional Impact)
- Scores out of 10 for each dimension
- Provides concrete comparison points

## Example Output

```html
<h2>Reference Images from Master's Portfolio</h2>
<p class="rag-intro">Your image was compared to these similar works:</p>

<div class="reference-image-card">
  <h3>Reference #1: The Tetons and the Snake River</h3>
  <p><strong>Date:</strong> 1942 | <strong>Location:</strong> Grand Teton National Park, Wyoming</p>
  <p><strong>Similarity:</strong> 45.5%</p>
  
  <div class="reference-image-container">
    <img src="http://localhost:5100/advisor_image/ansel/1.jpg" 
         alt="The Tetons and the Snake River">
  </div>
  
  <div class="reference-significance">
    <strong>Historical Significance:</strong><br>
    One of Ansel Adams' most famous photographs, selected for the Voyager Golden Record.
  </div>
  
  <div class="reference-dimensions">
    <strong>Key Dimensions:</strong>
    <ul>
      <li>Composition: 9.5/10</li>
      <li>Lighting: 9.0/10</li>
      <li>Focus & Sharpness: 9.5/10</li>
      <li>Emotional Impact: 9.0/10</li>
    </ul>
  </div>
</div>
```

## Implementation Details

### Modified Files

#### 1. `mondrian/json_to_html_converter.py`

**Updated `json_to_html()` function:**
```python
def json_to_html(json_data, similar_images=None, base_url=None):
    """Convert JSON response to HTML feedback cards.
    
    Args:
        json_data: Parsed JSON analysis data
        similar_images: Optional list of similar reference images from RAG
        base_url: Optional base URL for serving images (e.g., 'http://localhost:5100')
    """
```

**Key changes:**
- Added `similar_images` and `base_url` parameters
- Generates RAG reference section before detailed feedback
- Extracts metadata from dimensional profiles
- Constructs image URLs from absolute file paths
- Displays images with `<img>` tags

#### 2. `mondrian/ai_advisor_service.py`

**Added endpoint to serve advisor images:**
```python
@app.route("/advisor_image/<advisor_id>/<filename>", methods=["GET"])
def serve_advisor_image(advisor_id, filename):
    """Serve advisor reference images for RAG display."""
```

**Updated analyze endpoint:**
- Tracks `similar_images_for_html` variable
- Passes similar images to `json_to_html()`
- Constructs base URL for image serving

#### 3. `mondrian/technique_rag.py`

**Updated `get_similar_images_by_techniques()`:**
- Returns formatted results with `dimensional_profile` key
- Ensures compatibility with HTML display expectations

### Image URL Generation

The system converts absolute file paths to web-accessible URLs:

```python
# Input: /Users/.../mondrian/source/advisor/photographer/ansel/1.jpg
# Output: http://localhost:5100/advisor_image/ansel/1.jpg
```

**Path parsing logic:**
1. Split path on `/advisor/`
2. Extract advisor category and ID (e.g., `photographer/ansel`)
3. Get filename (e.g., `1.jpg`)
4. Construct URL: `{base_url}/advisor_image/{advisor_id}/{filename}`

### Image Serving

The `/advisor_image/<advisor_id>/<filename>` endpoint:
- Tries multiple possible image locations
- Returns JPEG with proper MIME type
- Handles errors gracefully with 404 responses

**Possible image locations checked:**
```python
[
    "mondrian/source/advisor/photographer/{advisor_id}/{filename}",
    "source/advisor/photographer/{advisor_id}/{filename}",
    "mondrian/advisor_artworks/{advisor_id}/{filename}",
    "advisor_artworks/{advisor_id}/{filename}"
]
```

## Usage

### For End Users

When uploading an image with RAG enabled:

```bash
curl -X POST http://localhost:5005/upload \
  -F "image=@my_landscape.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

The returned HTML will include:
- Your image analysis
- 2-3 reference images from Ansel Adams' portfolio
- Visual comparison with metadata
- Detailed feedback referencing the shown images

### For Developers

**Test the HTML generation:**
```bash
python3 test_rag_html_display.py
```

**View sample output:**
```bash
open test_rag_output.html
```

**Start the AI service:**
```bash
python3 mondrian/ai_advisor_service.py --port 5100
```

## Benefits

### 1. **Visual Learning**
Users can **see** the reference images, not just read about them.

### 2. **Contextual Feedback**
Feedback like "Unlike Reference #1..." now shows what Reference #1 actually looks like.

### 3. **Educational Value**
Users learn about famous photographs while improving their own work.

### 4. **Credibility**
Showing actual master works adds authority to the recommendations.

### 5. **Comparison**
Users can visually compare their image to the references side-by-side.

## Before vs. After

### Before (Filename Only)
```
Reference Image #1: 2.jpg
Dimensional similarity: 0.89
Composition: 8.5/10
```

**Problem:** User has no idea what "2.jpg" looks like.

### After (With Image)
```
Reference #1: The Tetons and the Snake River
Date: 1942 | Location: Grand Teton National Park, Wyoming
Similarity: 45.5%

[ACTUAL IMAGE DISPLAYED]

Historical Significance: One of Ansel Adams' most famous photographs...

Key Dimensions:
- Composition: 9.5/10
- Lighting: 9.0/10
```

**Benefit:** User sees the actual photograph and understands the context.

## Styling

The HTML includes inline styles for immediate visual appeal:

```css
.reference-image-card {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.reference-image-container img {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.reference-significance {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  margin: 10px 0;
}
```

## Testing

The test suite (`test_rag_html_display.py`) verifies:

- ✅ HTML generation without RAG (baseline)
- ✅ HTML generation with RAG references
- ✅ Image URLs are generated correctly
- ✅ Metadata is displayed (titles, dates, locations)
- ✅ Historical significance is shown
- ✅ Similarity scores are calculated
- ✅ Dimensional scores are displayed
- ✅ `<img>` tags have proper src and alt attributes
- ✅ Edge cases (empty/None similar_images)

## Future Enhancements

### Potential Improvements

1. **Thumbnails**: Generate smaller thumbnails for faster loading
2. **Lazy Loading**: Load images on scroll for performance
3. **Lightbox**: Click to view full-resolution images
4. **Side-by-Side**: Display user image next to reference for direct comparison
5. **Annotations**: Highlight specific areas (composition lines, lighting zones)
6. **Download**: Allow users to download reference images for study
7. **Caching**: Cache served images for faster repeated access

### iOS App Integration

The iOS app can parse the HTML and:
- Extract image URLs
- Display in native image views
- Implement native zoom/pan
- Cache images locally
- Provide native comparison UI

## Troubleshooting

### Images Not Loading

**Symptom:** Broken image icons in HTML output

**Causes:**
1. AI service not running on expected port
2. Image files not in expected locations
3. Incorrect URL generation

**Solutions:**
```bash
# Check AI service is running
curl http://localhost:5100/health

# Verify image exists
ls -la mondrian/source/advisor/photographer/ansel/1.jpg

# Test image endpoint directly
curl http://localhost:5100/advisor_image/ansel/1.jpg
```

### No RAG Section

**Symptom:** HTML output doesn't include reference images

**Causes:**
1. `enable_rag=false` or not set
2. No similar images found in database
3. Advisor images not indexed

**Solutions:**
```bash
# Ensure RAG is enabled
curl -X POST ... -F "enable_rag=true"

# Check database has profiles
sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel';"

# Index advisor images if needed
python3 tools/rag/index_with_metadata.py --advisor ansel
```

### Wrong Images Displayed

**Symptom:** Reference images don't match the advisor

**Cause:** Incorrect advisor_id in image path parsing

**Solution:** Check image path format in database:
```sql
SELECT image_path FROM dimensional_profiles WHERE advisor_id='ansel' LIMIT 1;
```

Should be: `/path/to/mondrian/source/advisor/photographer/ansel/image.jpg`

## Summary

This enhancement transforms the RAG system from text-only references to a **visual learning experience**. Users now see the actual master works their images are compared to, making the feedback more concrete, educational, and actionable.

**Key Achievement:** Bridging the gap between abstract feedback and visual understanding.

