# iOS RAG Integration - Quick Start

## TL;DR

To toggle between RAG and baseline analysis from your iOS app, pass the `enable_rag` parameter in the upload request:

```swift
// Baseline mode (default)
"enable_rag": "false"

// RAG mode
"enable_rag": "true"
```

## Complete iOS Example

```swift
import Foundation

struct MondrianAPI {
    let baseURL: String

    func uploadImage(
        image: UIImage,
        advisor: String = "ansel",
        enableRAG: Bool = false,
        completion: @escaping (Result<UploadResponse, Error>) -> Void
    ) {
        let url = URL(string: "\(baseURL)/upload")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Image
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n")
        body.append("Content-Type: image/jpeg\r\n\r\n")
        if let imageData = image.jpegData(compressionQuality: 0.8) {
            body.append(imageData)
        }
        body.append("\r\n")

        // Advisor
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"advisor\"\r\n\r\n")
        body.append("\(advisor)\r\n")

        // ⭐ THIS IS THE KEY PARAMETER ⭐
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"enable_rag\"\r\n\r\n")
        body.append(enableRAG ? "true" : "false")
        body.append("\r\n")

        body.append("--\(boundary)--\r\n")

        request.httpBody = body

        URLSession.shared.dataTask(with: request) { data, response, error in
            // Handle response...
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data else {
                completion(.failure(NSError(domain: "MondrianAPI", code: -1, userInfo: [NSLocalizedDescriptionKey: "No data received"])))
                return
            }

            do {
                let uploadResponse = try JSONDecoder().decode(UploadResponse.self, from: data)
                // ⭐ Verify RAG was enabled
                print("RAG enabled: \(uploadResponse.enableRag)")
                completion(.success(uploadResponse))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
}

// Response model
struct UploadResponse: Codable {
    let jobId: String
    let filename: String
    let advisor: String
    let status: String
    let enableRag: Bool  // ⭐ Confirms RAG setting
    let statusUrl: String
    let streamUrl: String

    enum CodingKeys: String, CodingKey {
        case jobId = "job_id"
        case filename
        case advisor
        case status
        case enableRag = "enable_rag"
        case statusUrl = "status_url"
        case streamUrl = "stream_url"
    }
}

// Data extension helper
extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}
```

## Usage in Your App

```swift
let api = MondrianAPI(baseURL: "http://127.0.0.1:5005")

// Baseline analysis (no RAG)
api.uploadImage(image: photo, advisor: "ansel", enableRAG: false) { result in
    switch result {
    case .success(let response):
        print("Job ID: \(response.jobId)")
        print("RAG enabled: \(response.enableRag)")  // Should be false
        // Start streaming updates from response.streamUrl
    case .failure(let error):
        print("Error: \(error)")
    }
}

// RAG-enhanced analysis
api.uploadImage(image: photo, advisor: "ansel", enableRAG: true) { result in
    switch result {
    case .success(let response):
        print("Job ID: \(response.jobId)")
        print("RAG enabled: \(response.enableRag)")  // Should be true
        // Start streaming updates from response.streamUrl
    case .failure(let error):
        print("Error: \(error)")
    }
}
```

## Environment Variable Approach

If you want to make RAG toggleable via environment variable:

```swift
// Config.swift
struct Config {
    static let enableRAG: Bool = {
        // Read from environment variable or build configuration
        #if DEBUG
        return ProcessInfo.processInfo.environment["ENABLE_RAG"] == "true"
        #else
        return false  // Default to baseline in production
        #endif
    }()
}

// Usage
api.uploadImage(image: photo, advisor: "ansel", enableRAG: Config.enableRAG) { ... }
```

### Setting Environment Variable in Xcode

1. Select your scheme (Product > Scheme > Edit Scheme)
2. Go to Run > Arguments
3. Add Environment Variable:
   - **Name:** `ENABLE_RAG`
   - **Value:** `true` or `false`

## Testing

### Quick Test Script

```bash
# Test baseline
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@test.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=false"

# Test RAG
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@test.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

### Unit Tests

```bash
# Run comprehensive unit tests
pytest test/test_rag_baseline_unit.py -v

# Or without pytest
python3 test/test_rag_baseline_unit.py
```

### E2E Comparison

```bash
# Compare RAG vs baseline outputs side-by-side
python3 test/test_ios_e2e_rag_comparison.py
```

## What Happens Internally

### Baseline Mode (`enable_rag=false`)
1. iOS app uploads image with `enable_rag=false`
2. Job service queues job
3. AI advisor service analyzes image directly
4. Returns standard photography advice

### RAG Mode (`enable_rag=true`)
1. iOS app uploads image with `enable_rag=true`
2. Job service queues job with RAG flag
3. AI advisor service:
   - Analyzes image to extract dimensional profile
   - Queries RAG service for similar images
   - Includes similar examples in the LLM prompt
   - Returns enhanced advice with comparisons

## Verifying RAG is Working

### 1. Check Upload Response
```swift
if response.enableRag {
    print("✓ RAG is enabled for this job")
} else {
    print("✗ Using baseline mode")
}
```

### 2. Check Server Logs
Look for `[RAG]` prefixed messages in the AI Advisor Service logs:
```
[RAG] Finding dimensionally similar images (top_k=3)...
[RAG] Current image dimensional profile:
[RAG]   composition: 7.0
[RAG]   lighting: 8.0
[RAG] Retrieved 3 dimensionally similar images
[RAG] Augmented prompt with 3 dimensional comparisons
```

### 3. Check Analysis Output
RAG-enabled analysis will include references to similar images and comparative recommendations.

## Troubleshooting

### RAG Not Working?

**Check services:**
```bash
# All services must be running
curl http://127.0.0.1:5005/health  # Job service
curl http://127.0.0.1:5100/health  # AI advisor service
curl http://127.0.0.1:5400/health  # RAG service ⭐ Required for RAG
```

**Check database:**
```bash
# Verify dimensional profiles exist
sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles;"
# Should return > 0
```

**Check response:**
```swift
print("enable_rag in response: \(response.enableRag)")
// Should be true when RAG is enabled
```

## Best Practices

1. **Always pass `enable_rag` explicitly** - Don't rely on server defaults
2. **Verify the response** - Check `response.enableRag` to confirm
3. **Use environment variables** - Make RAG toggleable without code changes
4. **Test both modes** - Ensure baseline and RAG both work
5. **Log RAG usage** - Track which mode was used for analytics

## Related Documentation

- [Complete API Reference](./RAG_API_REFERENCE.md) - Full API documentation
- [RAG Architecture](./NEXT_STEPS.md) - How RAG works internally
- Unit tests: [test/test_rag_baseline_unit.py](../test/test_rag_baseline_unit.py)
- E2E tests: [test/test_ios_e2e_rag_comparison.py](../test/test_ios_e2e_rag_comparison.py)

## Questions?

- API parameter not working? Check [RAG_API_REFERENCE.md](./RAG_API_REFERENCE.md)
- Services not running? Run `./mondrian.sh --restart`
- Tests failing? Run `python3 test/test_rag_baseline_unit.py` for diagnostics
