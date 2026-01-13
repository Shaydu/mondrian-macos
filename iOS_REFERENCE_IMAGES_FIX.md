# iOS Reference Images Fix - Complete Solution

## The Problem (Now Fixed!)

Reference images were not rendering on iOS because:
1. The backend was hardcoded to use `http://localhost:5005/api/reference-image/...`
2. iOS device can't access `localhost` - it needs the actual IP address like `http://192.168.x.x:5005/...`

## The Solution ✅

The backend now accepts `MONDRIAN_API_BASE_URL` parameter from the iOS app. When iOS sends this parameter, all image URLs will use the correct IP address.

## iOS App Changes Required

When making requests to `/analyze` endpoint, include this form parameter:

```swift
// In your iOS app when submitting an analysis
var request = URLRequest(url: URL(string: "http://your-backend-ip:5100/analyze")!)
request.httpMethod = "POST"

let boundary = "Boundary-\(UUID().uuidString)"
request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

var body = Data()

// ... add image file ...

// ADD THIS LINE - tells backend what URL to use for image serving
let apiBaseUrl = "http://\(serverIP):5005"  // Must match the IP/port iOS is using
body.append("--\(boundary)\r\n".data(using: .utf8)!)
body.append("Content-Disposition: form-data; name=\"MONDRIAN_API_BASE_URL\"\r\n\r\n".data(using: .utf8)!)
body.append("\(apiBaseUrl)\r\n".data(using: .utf8)!)

// ... add other parameters (advisor, enable_rag, etc) ...

request.httpBody = body
```

## Backend Changes (Done ✅)

The backend now:
1. **Accepts `MONDRIAN_API_BASE_URL`** parameter from iOS
2. **Prioritizes** it over job_service_url and localhost
3. **Uses it to generate all image URLs** with the correct IP address

### Priority Order:
```
1. MONDRIAN_API_BASE_URL (from iOS app)  ← HIGHEST - Use this!
2. job_service_url (from job service)
3. http://localhost:5100 (fallback)
```

## What URLs Are Generated

### Before (broken on iOS):
```html
<img src="http://localhost:5005/api/reference-image/ansel-old-faithful-geyser-1944.png">
<a href="http://localhost:5005/api/reference-image/ansel-old-faithful-geyser-1944.png">View full size</a>
```

### After (works on iOS):
```html
<img src="http://192.168.1.100:5005/api/reference-image/ansel-old-faithful-geyser-1944.png">
<a href="http://192.168.1.100:5005/api/reference-image/ansel-old-faithful-geyser-1944.png">View full size</a>
```

## Debug Logging

Check if the parameter was received:

```bash
tail -f /tmp/ai_service_ios_fix.log | grep -i "MONDRIAN_API_BASE_URL"
```

Look for these messages:
- `[iOS DEBUG] Received MONDRIAN_API_BASE_URL from app: http://192.168.x.x:5005` ✓ Good
- `[iOS DEBUG] MONDRIAN_API_BASE_URL not provided in request` ✗ Parameter missing
- `[iOS DEBUG] [BASELINE] Using MONDRIAN_API_BASE_URL for base_url: http://192.168.x.x:5005` ✓ Using it

## Verification

After iOS app sends the parameter:

1. **Check backend logs** for the MONDRIAN_API_BASE_URL message
2. **View the HTML source** in Safari (long press → Inspect)
3. **Verify image URLs** contain the correct IP address (not localhost)
4. **Test image loading** - click on images or use "View full size" link

## Example Request from iOS

```
POST http://192.168.1.100:5100/analyze
Content-Type: multipart/form-data; boundary=----Boundary

------Boundary
Content-Disposition: form-data; name="advisor"

ansel
------Boundary
Content-Disposition: form-data; name="job_id"

abc123
------Boundary
Content-Disposition: form-data; name="enable_rag"

true
------Boundary
Content-Disposition: form-data; name="MONDRIAN_API_BASE_URL"

http://192.168.1.100:5005
------Boundary
Content-Disposition: form-data; name="image"; filename="photo.jpg"
Content-Type: image/jpeg

[BINARY IMAGE DATA]
------Boundary--
```

## Summary

**What to send from iOS:**
- Parameter name: `MONDRIAN_API_BASE_URL`
- Value: The base URL with IP address and port (e.g., `http://192.168.1.100:5005`)
- This tells the backend what IP address to use for serving reference images

**What the backend does:**
- Uses `MONDRIAN_API_BASE_URL` to generate image URLs
- All reference image `<img src>` and links will use this URL
- iOS device can now access images using its own IP address
