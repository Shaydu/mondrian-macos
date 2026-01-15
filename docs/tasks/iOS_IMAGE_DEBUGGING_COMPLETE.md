# iOS Reference Image Debugging - Complete Implementation

## Summary of Changes

We've added comprehensive logging to track exactly what URLs are being used for reference images on iOS.

### Files Modified

#### 1. `mondrian/job_service_v2.3.py` (Lines 269-370)
**Enhanced the `/api/reference-image/<filename>` endpoint with detailed iOS debugging**

Logs for every request:
- **Request info**: filename, IP address, User-Agent, request URL
- **File lookup**: Whether file was found, full filepath, file size
- **Response**: Status (success/not_found/error), content-type, content-length

Console output example:
```
[iOS DEBUG] Reference image request:
  Filename: ansel-old-faithful-geyser-1944.png
  From: 192.168.1.100
  User-Agent: Mozilla/5.0 (iPhone OS 17_2_1)
  Full URL: http://192.168.1.100:5005/api/reference-image/ansel-old-faithful-geyser-1944.png
  Found at: /Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/ansel-old-faithful-geyser-1944.png
  File size: 118475 bytes
  ✓ Serving image successfully
```

#### 2. `mondrian/json_to_html_converter.py` (Lines 616-622 and 636-643)
**Enhanced HTML generation with iOS debugging**

Logs when reference images are embedded:
- Display URL (absolute URL that will be in the HTML)
- Original URL (before conversion)
- Image title and filename
- Whether absolute or relative URL is being used

## Debug Logs Location

### Console Logs (Real-time)
```bash
# Watch the job service console output
tail -f /tmp/job_service_ios_debug.log
```

### JSON Logs (Structured data)
```bash
# Watch the structured debug logs
tail -f /Users/shaydu/dev/mondrian-macos/.cursor/debug.log | grep -i "ios-image-debug"

# Or filter for specific events
grep "Reference image request" /Users/shaydu/dev/mondrian-macos/.cursor/debug.log
grep "Found reference image" /Users/shaydu/dev/mondrian-macos/.cursor/debug.log
grep "Reference image not found" /Users/shaydu/dev/mondrian-macos/.cursor/debug.log
```

## How to Debug iOS Issues

### Step 1: Run Analysis from iOS
1. Open your iOS app
2. Run an analysis with an image
3. Wait for it to complete

### Step 2: Check Console Logs
```bash
tail -50 /tmp/job_service_ios_debug.log
```

Look for:
- `[iOS DEBUG] Reference image request` - confirms request reached server
- `Found at: /path/to/file` - confirms file exists
- `File size: XXX bytes` - confirms file was readable
- `✓ Serving image successfully` - confirms image was sent

### Step 3: Check JSON Logs for URL Details
```bash
grep "ios-image-debug" /Users/shaydu/dev/mondrian-macos/.cursor/debug.log | tail -20
```

Look for in the `display_url` field:
- Should be: `http://192.168.x.x:5005/api/reference-image/filename.png`
- NOT: `http://localhost:5005/api/reference-image/filename.png` (won't work on iOS)
- NOT: `/api/reference-image/filename.png` (relative URL won't work)

### Step 4: Verify the URL Works Directly
Test from iOS Safari or directly from the app:
```
http://192.168.x.x:5005/api/reference-image/ansel-old-faithful-geyser-1944.png
```

## What Each Log Entry Tells You

### REQUEST RECEIVED
```json
{
  "message": "[iOS DEBUG] Reference image request",
  "data": {
    "filename": "ansel-old-faithful-geyser-1944.png",
    "remote_addr": "192.168.1.100",  // iOS device IP
    "user_agent": "Mozilla/5.0 (iPhone OS...",
    "request_url": "http://192.168.1.100:5005/api/reference-image/..."
  }
}
```
✅ **Good**: Request reached the server from iOS device

❌ **Bad**: No requests appearing = network issue or wrong IP

### FILE FOUND
```json
{
  "message": "[iOS DEBUG] Found reference image file",
  "data": {
    "filename": "ansel-old-faithful-geyser-1944.png",
    "filepath": "/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/ansel-old-faithful-geyser-1944.png",
    "exists": true,
    "file_size_bytes": 118475
  }
}
```
✅ **Good**: File exists and is readable

❌ **Bad**: `"exists": false` = file not in expected location

### SERVING SUCCESS
```json
{
  "message": "[iOS DEBUG] Serving reference image successfully",
  "data": {
    "filename": "ansel-old-faithful-geyser-1944.png",
    "content_type": "image/png",
    "content_length": "118475",
    "status": "success"
  }
}
```
✅ **Good**: Image was served successfully

### NOT FOUND
```json
{
  "message": "[iOS DEBUG] Reference image not found",
  "data": {
    "filename": "nonexistent-file.png",
    "search_directory": "/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor",
    "status": "not_found"
  }
}
```
❌ **Bad**: File being requested doesn't exist in the search directory

### IN HTML
```json
{
  "message": "[iOS DEBUG] Reference image embedded in HTML",
  "data": {
    "filename": "ansel-old-faithful-geyser-1944.png",
    "display_url": "http://192.168.1.100:5005/api/reference-image/ansel-old-faithful-geyser-1944.png",
    "img_title": "Old Faithful Geyser"
  }
}
```
✅ **Good**: Absolute URL embedded (will work on iOS)

❌ **Bad**: `display_url` is relative (starts with `/`) = won't work on iOS

## Common Issues & Solutions

### Images not rendering on iOS but work on web

**Likely cause**: Relative URLs in HTML

**Check**:
```bash
grep "display_url" /Users/shaydu/dev/mondrian-macos/.cursor/debug.log | tail -1
```

**Should show**: `"http://192.168.x.x:5005/api/reference-image/..."`

**Not**: `"/api/reference-image/..."`

### "View full size" link doesn't work

**Check**: The log shows what URL is embedded in the link
```bash
grep "Creating view full size link" /Users/shaydu/dev/mondrian-macos/.cursor/debug.log
```

Should show `display_url` with `http://` prefix

### File not found on server

**Check**: Where are the reference images stored?
```bash
find /Users/shaydu/dev/mondrian-macos/mondrian/source/advisor -name "*.png" | head -5
```

**Expected**: Files in `/source/advisor/photographer/ansel/`

### Network unreachable from iOS

**Check**: Can you ping the Mac from iOS?
```bash
# From iOS device
ping 192.168.x.x
```

**Check**: Is firewall blocking port 5005?
```bash
# On Mac
lsof -i :5005
```

## Next Steps

1. **Run an analysis from iOS** with these logs enabled
2. **Check the logs** for any "Reference image request" entries
3. **Verify the display_url** contains the correct IP address
4. **Test the URL directly** from iOS Safari
5. **Report** any errors or missing logs

The logging will help identify whether the issue is:
- Network connectivity (no requests reaching server)
- File system (files not found on server)
- URL generation (wrong URLs embedded in HTML)
- Image serving (error when trying to send image)
