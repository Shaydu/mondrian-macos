# Quick Testing Guide: All 4 Bug Fixes

## Issue #1: Reference Images Rendering ✅

### Check in HTML Output
```bash
# Get analysis HTML and check for reference gallery
curl http://localhost:5005/analysis/{job_id} | grep -A 5 "Reference Images Gallery"
```

**Expected Result:**
- Section titled "Reference Images Gallery" appears at end of output
- Each reference shows image with title, year, location, metadata
- Images are visible (not broken links)

---

## Issue #2: HTML Using Full Width ✅

### Check Layout in Browser
1. Open analysis HTML in browser
2. Right-click → Inspect → Toggle device toolbar (iOS)
3. Scroll horizontally

**Expected Result:**
- No horizontal scroll bar at bottom of analysis
- Content spans full width of screen
- Padding reduced on all sides
- Clean look with minimal borders

---

## Issue #3: No More 100% Similarity ✅

### Check in HTML Output
```bash
# Search for similarity metric
curl http://localhost:5005/analysis/{job_id} | grep -i "similarity"
```

**Expected Result:**
- No "Dimensional Profile Similarity: 100%" text
- Only dimensional score comparisons shown (bullet lists)
- Reference images section clean without confusion

---

## Issue #4: Advisor Images Not Flickering ✅

### Test 1: Endpoint Health
```bash
curl -I http://localhost:5005/advisor_image/ansel.jpg

# Expected headers:
# HTTP/1.1 200 OK
# Content-Type: image/jpeg
# Cache-Control: public, max-age=86400
# Access-Control-Allow-Origin: *
# ETag: "..."
```

### Test 2: CORS Preflight
```bash
curl -X OPTIONS http://localhost:5005/advisor_image/ansel.jpg -v

# Expected in response headers:
# < Access-Control-Allow-Origin: *
# < Access-Control-Allow-Methods: GET, OPTIONS
# < Access-Control-Max-Age: 86400
```

### Test 3: Image Availability Check
```bash
curl http://localhost:5005/advisor_image/ansel/check

# Expected JSON response:
# {
#   "advisor_id": "ansel",
#   "available": true,
#   "exists": true,
#   "size_bytes": 45000,
#   "url": "/advisor_image/ansel.jpg"
# }
```

### Test 4: Caching with ETag
```bash
# First request - capture ETag
ETAG=$(curl -s -I http://localhost:5005/advisor_image/ansel.jpg | grep ETag | cut -d'"' -f2)
echo "ETag: $ETAG"

# Second request with If-None-Match
curl -i -H "If-None-Match: \"$ETAG\"" http://localhost:5005/advisor_image/ansel.jpg

# Expected: HTTP/1.1 304 Not Modified
```

### Test 5: From Browser DevTools
1. Open browser DevTools (F12)
2. Go to Network tab
3. Load page with advisor profile image
4. Watch image load:
   - First request: Full image downloaded (200 OK)
   - Subsequent requests: Use cache (304 Not Modified)
   - No flickering or re-rendering

### Test 6: From iOS App
```swift
// Add logging to your image loading code
AsyncImage(url: URL(string: "\(baseURL)/advisor_image/ansel.jpg")) { phase in
    switch phase {
    case .success(let image):
        print("✅ Advisor image loaded successfully")
        return AnyView(image.resizable())
    case .failure(let error):
        print("❌ Failed to load: \(error)")
        return AnyView(Image(systemName: "photo"))
    case .empty:
        print("⏳ Loading advisor image...")
        return AnyView(ProgressView())
    @unknown default:
        return AnyView(EmptyView())
    }
}
```

Expected Console Output:
```
⏳ Loading advisor image...
✅ Advisor image loaded successfully
```

No repeated "Loading" messages (no flickering)

---

## Reference Image URLs

### Before Fix ❌
```
http://localhost:5005/advisor_image/ansel/filename.jpg  (BROKEN)
```

### After Fix ✅
```
http://localhost:5005/advisor_artwork/ansel/filename.jpg  (CORRECT)
```

---

## Restart Services

If you made changes to the code:

```bash
cd /Users/shaydu/dev/mondrian-macos

# Option 1: Full restart
./mondrian.sh

# Option 2: Restart individual service
# For job_service_v2.3.py changes:
pkill -f "python.*job_service"
python mondrian/job_service_v2.3.py --port 5005 &
```

---

## Check Service Logs

```bash
# Monitor all logs
tail -f mondrian/logs/*.log

# Or specific service
tail -f mondrian/logs/job_service.log
```

Look for entries like:
- `[OK] Serving advisor image: ansel (45000 bytes)`
- `[OK] Serving advisor artwork: ansel/filename.jpg (120000 bytes)`

---

## All Fixes Summary

| # | Issue | File | Status | Test |
|---|-------|------|--------|------|
| 1 | Broken reference image links | json_to_html_converter.py | ✅ Fixed | Check gallery renders |
| 2 | Not using full width | json_to_html_converter.py | ✅ Fixed | Check horizontal scroll |
| 3 | 100% similarity metric | json_to_html_converter.py | ✅ Fixed | Grep for "similarity" |
| 4 | Flickering advisor images | job_service_v2.3.py | ✅ Fixed | CORS test + iOS app |

---

## Troubleshooting

### Images still not loading?
1. Check CORS headers with `curl -I`
2. Verify file exists: `ls -la mondrian/advisor_images/`
3. Check file size: `ls -lh mondrian/advisor_images/`
4. Check logs: `tail -f mondrian/logs/job_service.log`

### Still seeing 100% similarity?
1. Clear browser cache (Cmd+Shift+Delete)
2. Restart service
3. Regenerate analysis

### Horizontal scroll still visible?
1. Check CSS in HTML output
2. Look for any `max-width` constraints
3. Verify no tables with `table-layout: fixed`

---

**All 4 bugs fixed and ready to test!** ✅
