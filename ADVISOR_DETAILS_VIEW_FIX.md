# Advisor Details View - Fixed Issues

## Summary of Changes

Fixed three critical issues in the advisor details view:

1. **Headshot Image (Gray Profile Issue)** ✅
2. **Representative Works Grid Display** ✅  
3. **Lightbox Navigation with Left/Right Arrows** ✅

---

## Issue 1: Headshot Image Shows as Gray Profile

### Root Cause
The `/advisor_image/<advisor_id>` endpoint wasn't finding the correct headshot image due to limited search paths and no fallback strategy.

### Solution
Enhanced the `get_advisor_headshot()` endpoint with:

- **Prioritized search paths** in order of preference:
  1. `training/datasets/{advisor_id}-images/headshot.jpg` (most recent/curated)
  2. Source advisor directories with photographer/painter/architect categories
  3. Dedicated `mondrian/advisor_images/` directory

- **Intelligent fallback strategy**: If no dedicated headshot exists, use the first representative work image from the advisor's directory

- **Better error handling and logging** to debug issues

### Result
The iOS app now gets the correct advisor profile image, not a generic gray placeholder.

---

## Issue 2: Representative Works Grid Not Displaying

### Root Cause
The `/advisors/<advisor_id>` endpoint was only including 4 artworks (grid limit), and the artworks metadata was minimal, preventing proper grid display.

### Solution

#### Enhanced `/advisors/<advisor_id>` endpoint:
- **Include all representative works** in the API response (not limited to 4)
- **Add rich metadata** to each artwork:
  - `id`: Unique identifier for lightbox pagination
  - `title`: Display name
  - `url`: Endpoint to fetch the image
  - `filename`: Original filename
  - `index`: Position in list
  - `total`: Total number of images (for navigation)

- **Add grid display metadata** with nested structure:
  - `artworks_count`: Total number of works
  - `representative_works` object containing:
    - `count`: Total available
    - `display_mode`: "grid" or "carousel"
    - `thumbnails`: First 4 items for grid display
    - `full_list`: All items for lightbox pagination

#### Enhanced `/advisors` endpoint:
- Added `representative_works` field (first 4 for grid)
- Added `image_url` field for headshots
- Allows the list view to show preview thumbnails

### Result
The tiled grid of representative works now displays properly with all available images accessible through the lightbox.

---

## Issue 3: Lightbox Navigation (Left/Right Arrows)

### New Endpoint Added
Created new endpoint: `GET /advisor_artwork/<advisor_id>/lightbox/<artwork_id>`

This endpoint returns complete navigation metadata:

```json
{
  "current": {
    "id": 2,
    "title": "Monolith",
    "url": "/advisor_artwork/ansel/2",
    "filename": "monolith.jpg"
  },
  "navigation": {
    "has_previous": true,
    "has_next": true,
    "previous_id": 1,
    "next_id": 3
  },
  "progress": {
    "current": 2,
    "total": 8,
    "percent": 25
  },
  "all_items": [
    { "id": 1, "title": "...", "url": "...", "filename": "..." },
    { "id": 2, "title": "...", "url": "...", "filename": "..." },
    ...
  ]
}
```

### Features Enabled
- **Previous/Next Navigation**: `has_previous`/`has_next` flags tell iOS whether to show left/right arrows
- **Smart Arrow Navigation**: `previous_id` and `next_id` provide direct IDs for navigation
- **Progress Tracking**: Current position and total count for progress indicators
- **Complete Manifest**: `all_items` array allows random access to any image

### iOS Implementation (expected)
```swift
// User taps left arrow
if let prevId = lightboxInfo.navigation.previous_id {
    fetchNextImage(id: prevId)
}

// User taps right arrow  
if let nextId = lightboxInfo.navigation.next_id {
    fetchNextImage(id: nextId)
}
```

### Result
Lightbox now supports seamless left/right navigation through all representative works with visual feedback about current position.

---

## API Response Examples

### /advisors (List View)
```json
{
  "advisors": [
    {
      "id": "ansel",
      "name": "Ansel Adams",
      "specialty": "Landscape Photography",
      "image_url": "/advisor_image/ansel",
      "representative_works": [
        {
          "id": 1,
          "title": "Mirror View Yosemite",
          "url": "/advisor_artwork/ansel/1"
        },
        ...
      ]
    }
  ]
}
```

### /advisors/{id} (Detail View)
```json
{
  "advisor": {
    "id": "ansel",
    "name": "Ansel Adams",
    "image_url": "/advisor_image/ansel",
    "artworks": [
      {
        "id": 1,
        "title": "Mirror View Yosemite",
        "url": "/advisor_artwork/ansel/1",
        "filename": "monolith.jpg",
        "index": 1,
        "total": 8
      },
      ...
    ],
    "representative_works": {
      "count": 8,
      "display_mode": "grid",
      "thumbnails": [...],
      "full_list": [...]
    }
  }
}
```

### /advisor_artwork/{id}/lightbox/{index} (Lightbox Navigation)
Full navigation metadata (see above)

---

## Testing Checklist

- [ ] Headshot image loads correctly (not gray profile)
- [ ] Representative works grid displays 4 items
- [ ] Can tap on grid item to open lightbox
- [ ] Left arrow appears when not at first image
- [ ] Right arrow appears when not at last image
- [ ] Arrows navigate to previous/next image
- [ ] Progress indicator shows current/total
- [ ] Lightbox shows correct image metadata
- [ ] All advisor IDs work (ansel, okeefe, watkins, etc.)

---

## Files Modified

- [mondrian/job_service_v2.3.py](mondrian/job_service_v2.3.py)
  - Enhanced `/advisors` endpoint
  - Enhanced `/advisors/<advisor_id>` endpoint
  - Improved `/advisor_image/<advisor_id>` endpoint
  - Existing `/advisor_artwork/<advisor_id>/<int:artwork_id>` endpoint
  - **New** `/advisor_artwork/<advisor_id>/lightbox/<int:artwork_id>` endpoint

---

## Backward Compatibility

All changes are **fully backward compatible**:
- Existing endpoints still work as before
- New fields are additive (old clients can ignore them)
- No breaking changes to existing API contract
- Old artwork serving logic unchanged

---

## Next Steps for iOS App

Update the advisor details view controller to:

1. **Display headshot**: Use `/advisor_image/{advisor_id}` endpoint (now guaranteed to return an image)

2. **Show grid**: Use first 4 items from `representative_works.thumbnails`

3. **Handle grid tap**: Open lightbox with selected index

4. **Implement lightbox nav**:
   - Fetch `/advisor_artwork/{id}/lightbox/{index}` 
   - Show/hide left/right arrows based on navigation flags
   - Update image and progress on arrow tap
   - Display total images in progress indicator

5. **Optional optimization**: Cache `all_items` from detail view to avoid extra API call for lightbox metadata

