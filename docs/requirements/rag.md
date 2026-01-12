# [DEPRECATED] See docs/architecture/rag.md for the latest RAG architecture and data flow documentation.

## Overview

The Mondrian RAG (Retrieval-Augmented Generation) system enables advisor-specific and image-specific recommendations by comparing user-uploaded images to advisor reference images based on dimensional scores.

---

## Goal Statement

> Analyze and compute dimensional scores from our rubric (lighting, composition, depth of field, etc.) for each advisor's reference images, then use those scores as embeddings to compare against the user's uploaded image, enabling advisor-specific and image-specific recommendations.

---

## Functional Requirements

### FR1: Advisor Reference Image Management

#### FR1.1: Store Reference Images
- **Requirement**: System SHALL store reference images for each advisor in a structured directory
- **Location**: `mondrian/source/advisor/{type}/{advisor_name}/`
  - Example: `mondrian/source/advisor/photographer/ansel/`
- **Supported formats**: `.jpg`, `.jpeg`, `.png`
- **Test**: Verify directory exists and contains images
  ```bash
  ls -la mondrian/source/advisor/photographer/ansel/
  # Expected: 10+ reference images
  ```

#### FR1.2: Compute Dimensional Profiles for Reference Images
- **Requirement**: System SHALL analyze all advisor reference images and extract dimensional scores
- **Dimensions**: 8 scores from rubric (0-10 scale)
  - `composition_score`
  - `lighting_score`
  - `focus_sharpness_score`
  - `color_harmony_score`
  - `subject_isolation_score`
  - `depth_perspective_score`
  - `visual_balance_score`
  - `emotional_impact_score`
- **Storage**: `dimensional_profiles` table
- **Test**: Verify all reference images have valid (non-NULL) scores
  ```bash
  sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles 
  WHERE advisor_id = 'ansel' 
  AND composition_score IS NOT NULL 
  AND lighting_score IS NOT NULL;"
  # Expected: Count equals number of reference images
  ```

#### FR1.3: Store Qualitative Comments
- **Requirement**: System SHALL store qualitative comments for each dimension
- **Fields**: 8 comment fields (one per dimension)
  - `composition_comment`
  - `lighting_comment`
  - `focus_sharpness_comment`
  - `color_harmony_comment`
  - `subject_isolation_comment`
  - `depth_perspective_comment`
  - `visual_balance_comment`
  - `emotional_impact_comment`
- **Test**: Verify comments are populated
  ```bash
  sqlite3 mondrian.db "SELECT composition_comment FROM dimensional_profiles 
  WHERE advisor_id = 'ansel' LIMIT 1;"
  # Expected: Non-empty text
  ```

#### FR1.4: Store Overall Grade and Description
- **Requirement**: System SHALL store overall grade and image description
- **Fields**:
  - `overall_grade` (REAL, 0-10)
  - `image_description` (TEXT)
- **Test**: Verify fields are populated
  ```bash
  sqlite3 mondrian.db "SELECT overall_grade, LENGTH(image_description) 
  FROM dimensional_profiles 
  WHERE advisor_id = 'ansel' LIMIT 1;"
  # Expected: Grade between 0-10, description length > 0
  ```

---

### FR2: User Image Analysis

#### FR2.1: Analyze User Uploaded Images
- **Requirement**: System SHALL analyze user-uploaded images using AI Advisor Service
- **Endpoint**: `POST /analyze` on AI Advisor Service (port 5100)
- **Input**: Image path, advisor ID
- **Output**: HTML analysis with dimensional scores
- **Test**: Upload image and verify analysis completes
  ```bash
  curl -X POST http://localhost:5100/analyze \
    -H 'Content-Type: application/json' \
    -d '{"advisor": "ansel", "image_path": "source/test.jpg", "enable_rag": "false"}'
  # Expected: HTTP 200, HTML response
  ```

#### FR2.2: Extract Dimensional Scores from Analysis
- **Requirement**: System SHALL automatically extract dimensional scores from analysis output
- **Method**: Parse JSON response from vision model
- **Function**: `extract_dimensional_profile_from_json()`
- **Test**: Verify extraction produces valid scores
  ```python
  # In ai_advisor_service.py
  json_data = parse_json_response(model_output)
  dimensional_data = extract_dimensional_profile_from_json(json_data)
  assert dimensional_data['composition_score'] is not None
  assert 0 <= dimensional_data['composition_score'] <= 10
  ```

#### FR2.3: Store User Image Dimensional Profiles
- **Requirement**: System SHALL store dimensional profiles for user images in database
- **Table**: `dimensional_profiles`
- **Timing**: Automatically after analysis completes
- **Test**: Verify profile is created
  ```bash
  sqlite3 mondrian.db "SELECT composition_score, lighting_score 
  FROM dimensional_profiles 
  WHERE image_path LIKE '%user_image.jpg%' 
  ORDER BY created_at DESC LIMIT 1;"
  # Expected: Valid scores (not NULL)
  ```

---

### FR3: Dimensional Comparison (RAG)

#### FR3.1: Find Similar Advisor Images
- **Requirement**: System SHALL find advisor reference images with similar dimensional profiles when `enable_rag=true`
- **Method**: Euclidean distance in 8-dimensional space
- **Formula**: `distance = sqrt(Σ(user_score_i - advisor_score_i)²)`
- **Function**: `find_similar_by_dimensions()`
- **Test**: Verify similar images are returned
  ```python
  similar_images = get_similar_images_from_rag(
      image_path="source/test.jpg",
      top_k=3,
      advisor_id="ansel"
  )
  assert len(similar_images) > 0
  assert all('distance' in img for img in similar_images)
  ```

#### FR3.2: Calculate Dimensional Deltas
- **Requirement**: System SHALL calculate score differences for each dimension
- **Formula**: `delta = advisor_score - user_score`
- **Interpretation**:
  - Positive delta: Advisor image is stronger in this dimension
  - Negative delta: User image is stronger in this dimension
- **Test**: Verify deltas are calculated correctly
  ```python
  for similar_img in similar_images:
      deltas = similar_img['deltas']
      assert 'composition' in deltas
      assert isinstance(deltas['composition'], float)
      # Verify delta = advisor - user
      expected_delta = similar_img['dimensional_profile']['composition_score'] - user_score
      assert abs(deltas['composition'] - expected_delta) < 0.01
  ```

#### FR3.3: Filter by Advisor ID
- **Requirement**: System SHALL only compare to reference images from the same advisor
- **Filter**: `WHERE advisor_id = ?`
- **Test**: Verify filtering works
  ```bash
  # Upload image with advisor=ansel
  curl -X POST http://localhost:5005/upload \
    -F "image=@source/test.jpg" \
    -F "advisor=ansel" \
    -F "enable_rag=true"
  
  # Check logs for:
  # [RAG] Finding dimensionally similar images (advisor_id=ansel)
  # [RAG] Retrieved X dimensionally similar images
  
  # Verify only Ansel images are returned (not O'Keeffe, Mondrian, etc.)
  ```

#### FR3.4: Return Top-K Similar Images
- **Requirement**: System SHALL return the top-k most similar images, sorted by distance
- **Default**: k=3
- **Configurable**: Via `top_k` parameter
- **Test**: Verify correct number returned
  ```python
  similar_images = get_similar_images_from_rag(image_path, top_k=5, advisor_id="ansel")
  assert len(similar_images) <= 5
  # Verify sorted by distance (ascending)
  distances = [img['distance'] for img in similar_images]
  assert distances == sorted(distances)
  ```

#### FR3.5: Exclude Current Image from Results
- **Requirement**: System SHALL exclude the current image from similarity search
- **Parameter**: `exclude_image_path`
- **Test**: Verify current image is not in results
  ```python
  similar_images = get_similar_images_from_rag(
      image_path="source/test.jpg",
      top_k=3,
      advisor_id="ansel"
  )
  assert all(img['image_path'] != "source/test.jpg" for img in similar_images)
  ```

---

### FR4: Comparative Feedback Generation

#### FR4.1: Augment Prompt with Dimensional Comparisons
- **Requirement**: System SHALL augment advisor prompt with dimensional comparison context
- **Function**: `augment_prompt_with_rag_context()`
- **Content**: Quantitative tables + qualitative insights
- **Test**: Verify prompt is augmented
  ```python
  original_prompt_len = len(advisor_prompt)
  augmented_prompt = augment_prompt_with_rag_context(advisor_prompt, similar_images)
  assert len(augmented_prompt) > original_prompt_len
  assert "Dimensional Comparison" in augmented_prompt
  ```

#### FR4.2: Include Quantitative Comparison Tables
- **Requirement**: System SHALL include comparison tables with scores and deltas
- **Format**:
  ```
  | Dimension           | User Score | Reference Score | Delta  | Insight                    |
  |---------------------|------------|-----------------|--------|----------------------------|
  | Composition         | 7.0/10     | 9.0/10          | +2.0   | Reference +2.0 stronger    |
  | Lighting            | 8.0/10     | 7.5/10          | -0.5   | User +0.5 stronger         |
  ```
- **Test**: Verify table is in prompt
  ```python
  assert "| Dimension" in augmented_prompt
  assert "| Composition" in augmented_prompt
  assert "+2.0" in augmented_prompt or "-0.5" in augmented_prompt
  ```

#### FR4.3: Include Qualitative Insights
- **Requirement**: System SHALL include qualitative comments from reference images
- **Format**:
  ```
  **What Worked in Reference #1:**
  - **Composition**: The sweeping S-curve of dunes creates powerful leading lines...
  - **Lighting**: Dramatic side-lighting emphasizes texture and depth...
  ```
- **Test**: Verify insights are included
  ```python
  assert "What Worked in Reference" in augmented_prompt
  assert any(dim in augmented_prompt for dim in ['Composition', 'Lighting', 'Focus'])
  ```

#### FR4.4: Include Analysis Instructions
- **Requirement**: System SHALL include instructions for comparative analysis
- **Instructions**:
  1. Reference dimensional comparisons when analyzing each dimension
  2. Explain what reference did better (for negative deltas)
  3. Acknowledge what user did well (for positive deltas)
  4. Use comparative language ("Unlike Reference #1...", "Similar to...")
- **Test**: Verify instructions are present
  ```python
  assert "comparative" in augmented_prompt.lower()
  assert "reference" in augmented_prompt.lower()
  ```

#### FR4.5: Generate Advisor-Specific Recommendations
- **Requirement**: System SHALL generate recommendations specific to the advisor's style
- **Context**: Uses advisor's prompt + dimensional comparisons from advisor's reference images
- **Test**: Verify recommendations reference advisor's work
  ```bash
  # Check analysis output for advisor-specific language
  # For Ansel: "Zone System", "tonal range", "landscape composition"
  # For O'Keeffe: "organic forms", "abstraction", "color relationships"
  ```

#### FR4.6: Generate Image-Specific Recommendations
- **Requirement**: System SHALL generate recommendations specific to the user's image
- **Context**: Uses dimensional deltas to identify specific areas for improvement
- **Test**: Verify recommendations address specific weaknesses
  ```bash
  # If user composition is 2.0 points weaker than reference:
  # Expected: Specific composition recommendations
  # "To match the level shown in Reference #1, consider using S-curves..."
  ```

---

### FR5: Two-Pass Analysis with RAG

#### FR5.1: Pass 1 - Initial Analysis
- **Requirement**: When `enable_rag=true`, system SHALL perform initial analysis without RAG
- **Purpose**: Extract dimensional profile of user's image
- **Output**: Dimensional scores + comments
- **Test**: Verify Pass 1 completes
  ```bash
  # Check logs for:
  # [RAG] Pass 1: Analyzing image to extract dimensional profile...
  # [RAG] Pass 1 complete, parsing JSON response...
  ```

#### FR5.2: Save Temporary Profile
- **Requirement**: System SHALL save temporary dimensional profile after Pass 1
- **Purpose**: Enable similarity search
- **Test**: Verify profile is saved
  ```bash
  # Check logs for:
  # [RAG] Temporary dimensional profile saved: <uuid>
  ```

#### FR5.3: Query for Similar Images
- **Requirement**: System SHALL query for similar images using Pass 1 profile
- **Function**: `get_similar_images_from_rag()`
- **Test**: Verify query executes
  ```bash
  # Check logs for:
  # [RAG] Finding dimensionally similar images (top_k=3)...
  # [RAG] Current image dimensional profile:
  # [RAG]   composition: 7.0
  # [RAG]   lighting: 8.0
  # [RAG] Retrieved 3 dimensionally similar images
  ```

#### FR5.4: Pass 2 - Comparative Analysis
- **Requirement**: System SHALL re-analyze with dimensional comparison context
- **Input**: Original prompt + RAG context
- **Output**: Analysis with comparative feedback
- **Test**: Verify Pass 2 completes
  ```bash
  # Check logs for:
  # [RAG] Pass 2: Re-analyzing with dimensional comparison context...
  # [DEBUG] RAG-augmented advisor prompt length: XXXX chars
  ```

#### FR5.5: Fallback to Pass 1 if RAG Fails
- **Requirement**: System SHALL return Pass 1 results if RAG query fails
- **Conditions**: No similar images found, extraction failed, etc.
- **Test**: Verify fallback works
  ```python
  # If no similar images:
  # Expected: Pass 1 results returned
  # Check logs for:
  # [WARN] No dimensionally similar images found, using Pass 1 analysis
  ```

---

## Non-Functional Requirements

### NFR1: Performance

#### NFR1.1: Analysis Completion Time
- **Requirement**: Single image analysis SHALL complete within 30 seconds
- **Target**: 10-15 seconds with MLX
- **Test**: Measure analysis time
  ```bash
  time curl -X POST http://localhost:5100/analyze \
    -H 'Content-Type: application/json' \
    -d '{"advisor": "ansel", "image_path": "source/test.jpg"}'
  # Expected: < 30 seconds
  ```

#### NFR1.2: RAG Query Time
- **Requirement**: Dimensional similarity search SHALL complete within 5 seconds
- **Target**: 2-3 seconds
- **Test**: Measure query time
  ```python
  import time
  start = time.time()
  similar_images = get_similar_images_from_rag(image_path, top_k=3, advisor_id="ansel")
  duration = time.time() - start
  assert duration < 5.0
  ```

#### NFR1.3: Two-Pass Analysis Time
- **Requirement**: Complete two-pass RAG analysis SHALL complete within 60 seconds
- **Target**: 30-40 seconds
- **Test**: Measure end-to-end time
  ```bash
  time curl -X POST http://localhost:5005/upload \
    -F "image=@source/test.jpg" \
    -F "advisor=ansel" \
    -F "enable_rag=true"
  # Expected: < 60 seconds
  ```

### NFR2: Scalability

#### NFR2.1: Multiple Advisors Support
- **Requirement**: System SHALL support multiple advisors simultaneously
- **Advisors**: ansel, okeefe, mondrian, gehry, vangogh
- **Test**: Verify each advisor has reference images and profiles
  ```bash
  for advisor in ansel okeefe mondrian gehry vangogh; do
    count=$(sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id = '$advisor' AND composition_score IS NOT NULL;")
    echo "$advisor: $count profiles"
  done
  # Expected: Each advisor has 10+ profiles
  ```

#### NFR2.2: Reference Image Capacity
- **Requirement**: System SHALL support 100+ reference images per advisor
- **Performance**: Euclidean distance calculation is O(n) where n = number of reference images
- **Test**: Benchmark with 100 reference images
  ```python
  # Add 100 test profiles
  # Measure query time
  # Expected: < 5 seconds even with 100 images
  ```

#### NFR2.3: Concurrent Analysis
- **Requirement**: System SHALL handle multiple concurrent analysis requests
- **Target**: 5+ concurrent requests
- **Test**: Simulate concurrent uploads
  ```bash
  for i in {1..5}; do
    curl -X POST http://localhost:5005/upload \
      -F "image=@source/test$i.jpg" \
      -F "advisor=ansel" &
  done
  wait
  # Expected: All complete successfully
  ```

### NFR3: Accuracy

#### NFR3.1: Dimensional Score Consistency
- **Requirement**: Analyzing the same image multiple times SHALL produce consistent scores (±0.5)
- **Test**: Analyze same image 3 times, compare scores
  ```python
  scores = []
  for i in range(3):
      result = analyze_image("source/test.jpg", "ansel")
      scores.append(result['composition_score'])
  
  # Check variance
  import statistics
  stdev = statistics.stdev(scores)
  assert stdev < 0.5
  ```

#### NFR3.2: Similar Images Have Similar Scores
- **Requirement**: Images with similar visual characteristics SHALL have similar dimensional scores
- **Test**: Analyze visually similar images, verify scores are close
  ```python
  # Analyze two similar landscape images
  result1 = analyze_image("source/landscape1.jpg", "ansel")
  result2 = analyze_image("source/landscape2.jpg", "ansel")
  
  # Compare composition scores
  comp_diff = abs(result1['composition_score'] - result2['composition_score'])
  assert comp_diff < 2.0  # Within 2 points
  ```

#### NFR3.3: Delta Calculation Accuracy
- **Requirement**: Dimensional deltas SHALL be calculated accurately (advisor_score - user_score)
- **Test**: Verify delta calculation
  ```python
  user_score = 7.0
  advisor_score = 9.0
  delta = calculate_delta(user_score, advisor_score)
  assert delta == 2.0  # Advisor is 2.0 points stronger
  ```

### NFR4: Reliability

#### NFR4.1: Graceful Degradation
- **Requirement**: System SHALL continue to function if RAG fails
- **Behavior**: Return non-RAG analysis if RAG query fails
- **Test**: Simulate RAG failure
  ```python
  # Disable RAG service
  # Upload image with enable_rag=true
  # Expected: Analysis completes without RAG context
  # Check logs for: [WARN] No similar images found, proceeding without RAG
  ```

#### NFR4.2: Error Handling
- **Requirement**: System SHALL handle errors gracefully without crashing
- **Scenarios**:
  - Invalid image path
  - Corrupted image file
  - Model timeout
  - Database connection failure
- **Test**: Verify error responses
  ```bash
  curl -X POST http://localhost:5100/analyze \
    -H 'Content-Type: application/json' \
    -d '{"advisor": "ansel", "image_path": "nonexistent.jpg"}'
  # Expected: HTTP 404 or 400, not 500
  ```

#### NFR4.3: Data Integrity
- **Requirement**: System SHALL maintain data integrity in database
- **Constraints**:
  - Scores must be between 0-10
  - All 8 dimensions must be present
  - Foreign key relationships maintained
- **Test**: Verify constraints
  ```bash
  sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles 
  WHERE composition_score < 0 OR composition_score > 10;"
  # Expected: 0
  ```

---

## Database Schema Requirements

### Table: dimensional_profiles

```sql
CREATE TABLE dimensional_profiles (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    advisor_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    
    -- Quantitative Dimensions (0-10)
    composition_score REAL,
    lighting_score REAL,
    focus_sharpness_score REAL,
    color_harmony_score REAL,
    subject_isolation_score REAL,
    depth_perspective_score REAL,
    visual_balance_score REAL,
    emotional_impact_score REAL,
    
    -- Qualitative Comments
    composition_comment TEXT,
    lighting_comment TEXT,
    focus_sharpness_comment TEXT,
    color_harmony_comment TEXT,
    subject_isolation_comment TEXT,
    depth_perspective_comment TEXT,
    visual_balance_comment TEXT,
    emotional_impact_comment TEXT,
    
    -- Overall Analysis
    overall_grade REAL,
    image_description TEXT,
    analysis_html TEXT,
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (composition_score IS NULL OR (composition_score >= 0 AND composition_score <= 10)),
    CHECK (lighting_score IS NULL OR (lighting_score >= 0 AND lighting_score <= 10)),
    CHECK (focus_sharpness_score IS NULL OR (focus_sharpness_score >= 0 AND focus_sharpness_score <= 10)),
    CHECK (color_harmony_score IS NULL OR (color_harmony_score >= 0 AND color_harmony_score <= 10)),
    CHECK (subject_isolation_score IS NULL OR (subject_isolation_score >= 0 AND subject_isolation_score <= 10)),
    CHECK (depth_perspective_score IS NULL OR (depth_perspective_score >= 0 AND depth_perspective_score <= 10)),
    CHECK (visual_balance_score IS NULL OR (visual_balance_score >= 0 AND visual_balance_score <= 10)),
    CHECK (emotional_impact_score IS NULL OR (emotional_impact_score >= 0 AND emotional_impact_score <= 10)),
    CHECK (overall_grade IS NULL OR (overall_grade >= 0 AND overall_grade <= 10))
);

-- Indexes for performance
CREATE INDEX idx_dimensional_profiles_advisor ON dimensional_profiles(advisor_id);
CREATE INDEX idx_dimensional_profiles_image_path ON dimensional_profiles(image_path);
CREATE INDEX idx_dimensional_profiles_created_at ON dimensional_profiles(created_at);
```

---

## API Requirements

### POST /analyze (AI Advisor Service)

#### Request
```json
{
  "advisor": "ansel",
  "image_path": "/path/to/image.jpg",
  "enable_rag": "true"
}
```

#### Response (Success)
```html
<div class="analysis">
  <h2>Image Description</h2>
  <p>A striking desert landscape...</p>
  
  <h2>Dimensional Analysis</h2>
  <div class="dimension">
    <h3>Composition (7.0/10)</h3>
    <p>Your composition follows rule of thirds, but unlike Reference #1...</p>
    <p><strong>Recommendation:</strong> To match the level shown in Reference #1...</p>
  </div>
  ...
</div>
```

#### Response (Error)
```html
<div class="analysis">
  <h2>Error</h2>
  <p>Failed to analyze image: [error message]</p>
</div>
```

### POST /upload (Job Service)

#### Request
```bash
curl -X POST http://localhost:5005/upload \
  -F "image=@source/test.jpg" \
  -F "advisor=ansel" \
  -F "auto_analyze=true" \
  -F "enable_rag=true"
```

#### Response
```json
{
  "job_id": "uuid-here",
  "status": "pending",
  "advisor": "ansel",
  "filename": "test.jpg"
}
```

---

## Testing Requirements

### Unit Tests

#### Test: Dimensional Profile Extraction
```python
def test_extract_dimensional_profile():
    json_data = {
        "dimensions": [
            {"name": "Composition", "score": 7.0, "comment": "Good use of rule of thirds"},
            {"name": "Lighting", "score": 8.0, "comment": "Nice golden hour light"}
        ],
        "overall_grade": 7.5,
        "image_description": "A desert landscape"
    }
    
    profile = extract_dimensional_profile_from_json(json_data)
    
    assert profile['composition_score'] == 7.0
    assert profile['lighting_score'] == 8.0
    assert profile['overall_grade'] == 7.5
    assert profile['composition_comment'] == "Good use of rule of thirds"
```

#### Test: Dimensional Similarity Search
```python
def test_find_similar_by_dimensions():
    target_scores = {
        'composition': 7.0,
        'lighting': 8.0,
        'focus_sharpness': 9.0,
        'color_harmony': 7.5,
        'subject_isolation': 8.0,
        'depth_perspective': 7.0,
        'visual_balance': 8.5,
        'emotional_impact': 7.5
    }
    
    results = find_similar_by_dimensions(
        db_path='mondrian.db',
        advisor_id='ansel',
        target_scores=target_scores,
        top_k=3
    )
    
    assert len(results) <= 3
    assert all('distance' in r for r in results)
    assert results[0]['distance'] <= results[-1]['distance']  # Sorted ascending
```

#### Test: Delta Calculation
```python
def test_calculate_deltas():
    user_scores = {'composition': 7.0, 'lighting': 8.0}
    advisor_scores = {'composition': 9.0, 'lighting': 7.5}
    
    deltas = calculate_deltas(user_scores, advisor_scores)
    
    assert deltas['composition'] == 2.0  # Advisor stronger
    assert deltas['lighting'] == -0.5    # User stronger
```

### Integration Tests

#### Test: End-to-End RAG Analysis
```python
def test_rag_analysis_end_to_end():
    # Upload image with RAG enabled
    response = requests.post(
        'http://localhost:5005/upload',
        files={'image': open('source/test.jpg', 'rb')},
        data={'advisor': 'ansel', 'enable_rag': 'true', 'auto_analyze': 'true'}
    )
    
    assert response.status_code == 200
    job_id = response.json()['job_id']
    
    # Wait for analysis to complete
    time.sleep(30)
    
    # Check dimensional profile was created
    conn = sqlite3.connect('mondrian.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT composition_score, lighting_score 
        FROM dimensional_profiles 
        WHERE job_id = ?
    """, (job_id,))
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    assert result[0] is not None  # composition_score
    assert result[1] is not None  # lighting_score
```

#### Test: Batch Indexing
```python
def test_batch_index_advisor_images():
    # Run batch analysis
    result = subprocess.run(
        ['python', 'batch_analyze_advisor_images.py', '--advisor', 'ansel'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    
    # Verify all images have profiles
    conn = sqlite3.connect('mondrian.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM dimensional_profiles 
        WHERE advisor_id = 'ansel' 
        AND composition_score IS NOT NULL
    """)
    count = cursor.fetchone()[0]
    conn.close()
    
    # Should match number of images in directory
    image_count = len(list(Path('mondrian/source/advisor/photographer/ansel').glob('*.jpg')))
    assert count >= image_count
```

### Acceptance Tests

#### Test: Advisor-Specific Recommendations
```
GIVEN: User uploads a landscape photo
WHEN: Analysis is requested with advisor=ansel and enable_rag=true
THEN: 
  - Analysis completes successfully
  - Output includes comparative language ("Unlike Reference #1...")
  - Output references Ansel Adams' techniques
  - Output includes dimensional deltas
  - Recommendations are specific to landscape photography
```

#### Test: Image-Specific Recommendations
```
GIVEN: User's image has weak composition (score: 5.0)
  AND: Reference image has strong composition (score: 9.0)
WHEN: RAG analysis is performed
THEN:
  - Output identifies composition as area for improvement
  - Output includes specific composition recommendations
  - Output references what the reference image did better
  - Delta of +4.0 is mentioned
```

---

## Acceptance Criteria

### System is considered WORKING when:

1. ✅ **All advisor reference images have valid dimensional profiles**
   ```bash
   sqlite3 mondrian.db "SELECT advisor_id, COUNT(*) 
   FROM dimensional_profiles 
   WHERE composition_score IS NOT NULL 
   GROUP BY advisor_id;"
   # Expected: ansel: 14+, okeefe: 10+, etc.
   ```

2. ✅ **RAG returns similar images for user uploads**
   ```bash
   # Check logs for:
   [RAG] Retrieved 3 dimensionally similar images
   ```

3. ✅ **Analysis includes comparative feedback**
   ```
   Output contains phrases like:
   - "Unlike Reference #1 which..."
   - "Your composition (7.0/10) is weaker than..."
   - "To match the level shown in..."
   - "+2.0 delta"
   ```

4. ✅ **Dimensional deltas are accurate**
   ```
   Verify: delta = advisor_score - user_score
   ```

5. ✅ **Performance meets targets**
   - Single analysis: < 30 seconds
   - RAG query: < 5 seconds
   - Two-pass analysis: < 60 seconds

6. ✅ **System handles errors gracefully**
   - Invalid image → Error message (not crash)
   - No similar images → Falls back to non-RAG analysis
   - Model timeout → Returns error

---

## Implementation Checklist

### Phase 1: Fix Critical Issues (CURRENT)
- [ ] Verify advisor reference images exist
- [ ] Run batch analysis on all advisor images
- [ ] Verify all profiles have valid (non-NULL) scores
- [ ] Test end-to-end RAG with user upload
- [ ] Verify comparative feedback is generated

### Phase 2: Expand Coverage
- [ ] Index all 5 advisors (ansel, okeefe, mondrian, gehry, vangogh)
- [ ] Add more reference images (20+ per advisor)
- [ ] Verify cross-advisor filtering works

### Phase 3: Optimize Performance
- [ ] Benchmark analysis time
- [ ] Benchmark RAG query time
- [ ] Add caching for frequently accessed profiles
- [ ] Optimize database queries

### Phase 4: Enhance Accuracy
- [ ] Test dimensional score consistency
- [ ] Validate delta calculations
- [ ] Tune similarity threshold
- [ ] A/B test RAG vs non-RAG feedback quality

### Phase 5: Add Monitoring
- [ ] Log RAG query results
- [ ] Track analysis success/failure rates
- [ ] Monitor performance metrics
- [ ] Add alerts for failures

---

## Maintenance Requirements

### Regular Tasks

#### Weekly
- [ ] Verify all services are running
- [ ] Check for failed analyses in logs
- [ ] Review dimensional profile counts

#### Monthly
- [ ] Re-index advisor images if prompts change
- [ ] Review and update reference images
- [ ] Analyze performance trends
- [ ] Update documentation

#### Quarterly
- [ ] Add new advisor reference images
- [ ] Tune RAG parameters based on feedback
- [ ] Review and optimize database schema
- [ ] Conduct user acceptance testing

---

## References

- **Architecture**: See `docs/architecture.md`
- **API Documentation**: See `docs/API.md`
- **Dimensional RAG Implementation**: See `DIMENSIONAL_RAG_IMPLEMENTATION.md`
- **Batch Analysis Script**: See `batch_analyze_advisor_images.py`
- **Next Steps**: See `NEXT_STEPS.md`

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-12-19 | 1.0 | Initial requirements document | System |




