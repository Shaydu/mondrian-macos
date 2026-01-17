# Advisor API Base64 Images Update

## Summary
Updated both `/advisors` (list) and `/advisors/<advisor_id>` (detail) endpoints to embed representative artwork images as base64-encoded data URIs instead of relying on separate image serving endpoints.

## Changes Made

### 1. `/advisors` Endpoint (List View)
**Location**: [job_service_v2.3.py](job_service_v2.3.py#L204)

**What Changed**:
- Added `import base64` at the beginning of endpoint
- For each advisor, reads up to 4 artwork images from disk
- Encodes each image as base64 with proper MIME type
- Returns artwork data structure:
  ```json
  {
    "id": 1,
    "title": "Artwork Title",
    "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }
  ```
- Fallback to URL endpoint if base64 encoding fails

### 2. `/advisors/<advisor_id>` Endpoint (Detail View)
**Location**: [job_service_v2.3.py](job_service_v2.3.py#L290)

**What Changed**:
- Added `import base64` at the beginning of endpoint
- Reads ALL artwork images for the advisor (not just 4)
- Encodes each image as base64 with proper MIME type
- Maintains lightbox navigation metadata (index, total count)
- Returns comprehensive response with two structures:
  
  **Thumbnails** (first 4 for grid display):
  ```json
  {
    "id": 1,
    "title": "Artwork Title",
    "index": 1,
    "total": 23,
    "image_base64": "data:image/jpeg;base64,..."
  }
  ```
  
  **Full List** (all images for lightbox pagination):
  ```json
  {
    "id": 1,
    "title": "Artwork Title",
    "filename": "photo_001.jpg",
    "index": 1,
    "total": 23,
    "image_base64": "data:image/jpeg;base64,..."
  }
  ```

## Benefits
1. **Fixed Broken Links**: Images are now embedded in JSON responses, eliminating dependency on separate image serving endpoints
2. **Complete Lightbox Support**: All artworks available for lightbox navigation with proper pagination metadata
3. **Fallback Mechanism**: If base64 encoding fails, gracefully falls back to URL endpoint
4. **MIME Type Detection**: Automatically detects and sets correct MIME type (image/jpeg or image/png)
5. **iOS Compatible**: Data URIs work seamlessly on mobile devices without additional configuration

## Testing Endpoints

### List view (up to 4 images per advisor):
```bash
curl http://localhost:5005/advisors | jq '.advisors[0].artworks'
```

### Detail view (all images for lightbox):
```bash
curl http://localhost:5005/advisors/ansel_adams | jq '.advisor.representative_works.full_list'
```

## Response Structure Examples

### `/advisors` Response:
```json
{
  "advisors": [
    {
      "id": "ansel_adams",
      "name": "Ansel Adams",
      "specialty": "Photography",
      "bio": "...",
      "focus_areas": [...],
      "artworks": [
        {
          "id": 1,
          "title": "Moonrise Hernandez",
          "image_base64": "data:image/jpeg;base64,..."
        },
        ...
      ]
    }
  ]
}
```

### `/advisors/<advisor_id>` Response:
```json
{
  "advisor": {
    "id": "ansel_adams",
    "name": "Ansel Adams",
    "artworks": [...all images with base64...],
    "artworks_count": 23,
    "representative_works": {
      "count": 23,
      "display_mode": "grid",
      "thumbnails": [...first 4 with base64...],
      "full_list": [...all images with base64...]
    }
  }
}
```

## Image Directory Lookup Order
The endpoints search for images in this order:
1. `mondrian/source/advisor/photographer/{advisor_id}/`
2. `mondrian/source/advisor/painter/{advisor_id}/`
3. `mondrian/source/advisor/architect/{advisor_id}/`
4. `training/datasets/{advisor_id}-images/`

The first directory found is used to populate artworks.

## Error Handling
- If no images found: Returns single fallback artwork with URL endpoint
- If base64 encoding fails for individual image: Logs warning and uses URL fallback
- Graceful degradation ensures UI never breaks even if some images fail to encode

## Frontend Integration Notes
- Frontend can now use `image_base64` field directly in `<img src="...">` tags
- Data URIs eliminate CORS issues and external image dependencies
- Lightbox navigation can use `index` and `total` fields for pagination
- `filename` field available for reference if needed

## Database Queries
No database schema changes required. The implementation:
- Still queries the same `advisors` table
- Still reads images from the same directories
- No new tables or columns created
- Backward compatible with existing data

## Performance Considerations
- Base64 encoding adds ~30-40% size overhead compared to binary
- For typical advisor with 20 images, response size ~5-10MB (acceptable for API)
- Images are encoded on-demand (not cached), consider caching for high-traffic scenarios
- Consider image resizing for list view (first 4 artworks) to reduce response size
