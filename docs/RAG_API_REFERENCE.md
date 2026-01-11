# RAG API Reference for iOS App

## Overview

The Mondrian API supports two analysis modes:
1. **Baseline Mode** (default): Standard photography analysis without RAG
2. **RAG Mode**: Analysis enhanced with dimensionally similar examples from the database

## API Parameter: `enable_rag`

### Request Parameter

**Name:** `enable_rag`
**Type:** Form data (multipart/form-data)
**Required:** No
**Default:** `false`

### Accepted Values

The API accepts multiple value formats (case-insensitive):

**Enable RAG:**
- `'true'` (recommended)
- `'True'`
- `'TRUE'`
- `'1'`
- `'yes'`

**Disable RAG (Baseline):**
- `'false'` (recommended)
- `'False'`
- `'FALSE'`
- `'0'`
- `'no'`
- _omit parameter_ (defaults to baseline)

## iOS Implementation

### Environment Variable

In your iOS app's configuration, add:

```swift
// Config.swift or similar
struct MondrianConfig {
    static let enableRAG = ProcessInfo.processInfo.environment["ENABLE_RAG"] == "true"
}
```

### API Request

```swift
// Example using URLSession
func uploadImage(image: UIImage, advisor: String) {
    let url = URL(string: "\(baseURL)/upload")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"

    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

    var body = Data()

    // Add image
    body.append("--\(boundary)\r\n")
    body.append("Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n")
    body.append("Content-Type: image/jpeg\r\n\r\n")
    if let imageData = image.jpegData(compressionQuality: 0.8) {
        body.append(imageData)
    }
    body.append("\r\n")

    // Add advisor
    body.append("--\(boundary)\r\n")
    body.append("Content-Disposition: form-data; name=\"advisor\"\r\n\r\n")
    body.append("\(advisor)\r\n")

    // Add enable_rag - THIS IS THE KEY PARAMETER
    body.append("--\(boundary)\r\n")
    body.append("Content-Disposition: form-data; name=\"enable_rag\"\r\n\r\n")
    body.append(MondrianConfig.enableRAG ? "true" : "false")
    body.append("\r\n")

    body.append("--\(boundary)--\r\n")

    request.httpBody = body

    // Send request...
}
```

### Using Alamofire (if applicable)

```swift
import Alamofire

func uploadImage(image: UIImage, advisor: String) {
    let parameters: [String: String] = [
        "advisor": advisor,
        "enable_rag": MondrianConfig.enableRAG ? "true" : "false"  // <-- KEY PARAMETER
    ]

    AF.upload(
        multipartFormData: { multipartFormData in
            if let imageData = image.jpegData(compressionQuality: 0.8) {
                multipartFormData.append(imageData, withName: "image", fileName: "photo.jpg", mimeType: "image/jpeg")
            }
            for (key, value) in parameters {
                multipartFormData.append(value.data(using: .utf8)!, withName: key)
            }
        },
        to: "\(baseURL)/upload"
    )
    .responseJSON { response in
        // Handle response...
    }
}
```

## API Response

### Upload Response

When you upload an image, the response includes the `enable_rag` value that was used:

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "photo_20260110_123456.jpg",
  "advisor": "ansel",
  "advisors_used": ["ansel"],
  "status": "queued",
  "enable_rag": true,  // <-- Confirms RAG is enabled
  "status_url": "http://127.0.0.1:5005/status/123e4567-e89b-12d3-a456-426614174000",
  "stream_url": "http://127.0.0.1:5005/stream/123e4567-e89b-12d3-a456-426614174000"
}
```

### Verifying RAG Usage

You can verify RAG was used by checking the response `enable_rag` field:

```swift
struct UploadResponse: Codable {
    let jobId: String
    let filename: String
    let advisor: String
    let status: String
    let enableRag: Bool  // <-- Check this
    let statusUrl: String
    let streamUrl: String

    enum CodingKeys: String, CodingKey {
        case jobId = "job_id"
        case filename
        case advisor
        case status
        case enableRag = "enable_rag"  // Maps to enable_rag
        case statusUrl = "status_url"
        case streamUrl = "stream_url"
    }
}
```

## Data Flow

```
iOS App (enable_rag=true)
    ↓
Job Service (/upload endpoint)
    → Receives enable_rag parameter
    → Queues job with enable_rag flag
    ↓
Job Service (process_job)
    → Calls AI Advisor Service with enable_rag
    ↓
AI Advisor Service (/analyze endpoint)
    → Receives enable_rag parameter
    → If true: Calls RAG Service for similar images
    → If false: Skips RAG, uses baseline analysis
    ↓
Analysis Result
```

## Testing

### cURL Examples

**Baseline Mode (no RAG):**
```bash
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@photo.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=false"
```

**RAG Mode:**
```bash
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@photo.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

**Default (baseline):**
```bash
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@photo.jpg" \
  -F "advisor=ansel"
  # enable_rag omitted = defaults to false
```

### Unit Tests

Run the comprehensive unit tests:

```bash
# Using pytest
pytest test/test_rag_baseline_unit.py -v

# Or run directly
python3 test/test_rag_baseline_unit.py
```

### E2E Comparison Test

Compare RAG vs Baseline outputs:

```bash
python3 test/test_ios_e2e_rag_comparison.py
```

This generates comparison HTML showing differences between RAG and baseline analysis.

## Troubleshooting

### RAG Not Working?

1. **Check the response:** Verify `enable_rag: true` in the upload response
2. **Check RAG service:** Ensure RAG service is running on port 5400
3. **Check logs:** Look for `[RAG]` prefixed messages in AI Advisor Service logs
4. **Check database:** Ensure dimensional profiles exist in the database

```bash
# Check if RAG service is running
curl http://127.0.0.1:5400/health

# Check if dimensional profiles exist
sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles;"
```

### Response Missing `enable_rag` Field?

This can happen when `auto_analyze=false`. The field is included in the response when the job is queued for analysis.

## Environment Variables

The AI Advisor Service also supports a default RAG setting via environment variable:

```bash
# In .env file or environment
RAG_ENABLED=true  # Default: false
```

If `RAG_ENABLED=true` is set in the AI Advisor Service environment:
- Requests WITHOUT `enable_rag` parameter will use RAG
- Requests WITH `enable_rag` parameter override the default

**For iOS app:** It's recommended to explicitly pass `enable_rag` in each request rather than relying on service defaults.

## Code Locations

- **Job Service:** [mondrian/job_service_v2.3.py:664](../mondrian/job_service_v2.3.py#L664) - Receives `enable_rag` parameter
- **Job Service:** [mondrian/job_service_v2.3.py:431](../mondrian/job_service_v2.3.py#L431) - Passes to AI service
- **AI Advisor Service:** [mondrian/ai_advisor_service.py:617](../mondrian/ai_advisor_service.py#L617) - Processes `enable_rag`
- **AI Advisor Service:** [mondrian/ai_advisor_service.py:707](../mondrian/ai_advisor_service.py#L707) - Conditionally calls RAG

## Summary

**To enable RAG from iOS app:**

1. Add environment variable: `ENABLE_RAG=true` (or make it configurable)
2. Pass `enable_rag` parameter in upload request:
   ```swift
   "enable_rag": Config.enableRAG ? "true" : "false"
   ```
3. Verify response includes `"enable_rag": true`
4. RAG will be used for analysis automatically

**Default behavior:** If you omit the `enable_rag` parameter, the system uses **baseline mode** (no RAG).
