# RAG vs Baseline API Fix - Complete Guide

## Overview

This guide explains how to toggle between RAG (Retrieval-Augmented Generation) and baseline analysis modes in the Mondrian photography analysis system.

## What's Been Fixed

✅ **Database Storage**: `enable_rag` parameter is now stored in the database
✅ **API Response**: Upload and full-data endpoints return `enable_rag` flag
✅ **Web Interface**: Jobs list shows RAG/Baseline badges
✅ **Job Details**: Individual job pages display analysis mode
✅ **Comparison View**: Side-by-side comparison of RAG vs baseline analyses

## Architecture

```
iOS App (environment variable MONDRIAN_ENABLE_RAG)
  ↓
  HTTP POST /upload with enable_rag parameter
  ↓
Job Service (stores enable_rag in database)
  ↓
  Passes to AI Advisor Service
  ↓
AI Advisor Service (augments prompt with RAG context if enabled)
  ↓
Database (stores analysis with enable_rag flag)
  ↓
Web Interface (displays RAG badges and comparisons)
```

## iOS Client Integration

### Step 1: Configure Environment Variable in Xcode

1. In Xcode, select your scheme: **Product → Scheme → Edit Scheme...**
2. Go to **Run → Arguments** tab
3. In the **Environment Variables** section, click **+**
4. Add:
   - **Name**: `MONDRIAN_ENABLE_RAG`
   - **Value**: `true` (for RAG) or `false` (for baseline)

### Step 2: Update Your iOS Code

#### Option A: Simple Environment Variable Reading

```swift
// Config.swift
struct MondrianConfig {
    static let enableRAG: Bool = {
        ProcessInfo.processInfo.environment["MONDRIAN_ENABLE_RAG"] == "true"
    }()
}
```

#### Option B: With Default Fallback

```swift
// Config.swift
struct MondrianConfig {
    static let enableRAG: Bool = {
        guard let value = ProcessInfo.processInfo.environment["MONDRIAN_ENABLE_RAG"] else {
            return false  // Default to baseline if not set
        }
        return value.lowercased() == "true"
    }()
}
```

#### Update Network Service

```swift
// MondrianNetworkService.swift
import Foundation

class MondrianNetworkService {
    let baseURL: String

    init(baseURL: String = "http://127.0.0.1:5005") {
        self.baseURL = baseURL
    }

    func uploadImage(
        _ image: UIImage,
        advisor: String = "ansel",
        completion: @escaping (Result<UploadResponse, Error>) -> Void
    ) {
        guard let url = URL(string: "\(baseURL)/upload") else {
            completion(.failure(NetworkError.invalidURL))
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)",
                         forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Image data
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n")
        body.append("Content-Type: image/jpeg\r\n\r\n")
        if let imageData = image.jpegData(compressionQuality: 0.8) {
            body.append(imageData)
        }
        body.append("\r\n")

        // Advisor parameter
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"advisor\"\r\n\r\n")
        body.append("\(advisor)\r\n")

        // ⭐ RAG flag from environment variable ⭐
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"enable_rag\"\r\n\r\n")
        body.append(MondrianConfig.enableRAG ? "true" : "false")
        body.append("\r\n")

        body.append("--\(boundary)--\r\n")

        request.httpBody = body

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let data = data else {
                completion(.failure(NetworkError.noData))
                return
            }

            do {
                let uploadResponse = try JSONDecoder().decode(UploadResponse.self, from: data)
                print("✅ RAG Mode: \(uploadResponse.enableRag ? "Enabled" : "Baseline")")
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

// Error types
enum NetworkError: Error {
    case invalidURL
    case noData
}
```

### Step 3: Usage Example

```swift
// ViewController.swift
class PhotoAnalysisViewController: UIViewController {
    let networkService = MondrianNetworkService()

    func analyzePhoto(_ image: UIImage) {
        networkService.uploadImage(image, advisor: "ansel") { result in
            switch result {
            case .success(let response):
                print("Job ID: \(response.jobId)")
                print("RAG Enabled: \(response.enableRag)")
                // Start streaming updates from response.streamUrl
                self.startStreamingUpdates(streamUrl: response.streamUrl)

            case .failure(let error):
                print("Upload failed: \(error.localizedDescription)")
            }
        }
    }

    func startStreamingUpdates(streamUrl: String) {
        // Implement SSE streaming to get real-time updates
        // See existing iOS documentation for streaming implementation
    }
}
```

## Testing the Integration

### Test 1: Verify Environment Variable

```swift
// Add to your app delegate or initial view controller
print("MONDRIAN_ENABLE_RAG: \(ProcessInfo.processInfo.environment["MONDRIAN_ENABLE_RAG"] ?? "not set")")
print("Config.enableRAG: \(MondrianConfig.enableRAG)")
```

Expected output:
- With env var set to `true`: `Config.enableRAG: true`
- With env var set to `false`: `Config.enableRAG: false`
- Without env var: `Config.enableRAG: false` (default)

### Test 2: Backend Testing with curl

```bash
# Test baseline mode
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@test_photo.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=false"

# Expected response:
{
  "job_id": "abc-123...",
  "filename": "test_photo-xyz.jpg",
  "advisor": "ansel",
  "status": "queued",
  "enable_rag": false,  # ← Confirms baseline mode
  "status_url": "...",
  "stream_url": "..."
}

# Test RAG mode
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@test_photo.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"

# Expected response:
{
  "job_id": "def-456...",
  "filename": "test_photo-xyz.jpg",
  "advisor": "ansel",
  "status": "queued",
  "enable_rag": true,  # ← Confirms RAG mode
  "status_url": "...",
  "stream_url": "..."
}
```

### Test 3: Verify Database Storage

```bash
# Check that enable_rag is stored
sqlite3 mondrian.db "SELECT id, filename, advisor, enable_rag FROM jobs ORDER BY rowid DESC LIMIT 5;"
```

Expected output:
```
def-456|test_photo-xyz.jpg|ansel|1
abc-123|test_photo-xyz.jpg|ansel|0
```

### Test 4: Full-Data Endpoint

```bash
curl http://127.0.0.1:5005/job/abc-123/full-data
```

Expected response includes:
```json
{
  "job_id": "abc-123",
  "filename": "test_photo.jpg",
  "advisor": "ansel",
  "status": "done",
  "enable_rag": false,
  "prompt": "...",
  "llm_outputs": {...}
}
```

## Viewing Results in Web Interface

### Step 1: Generate Web Pages

```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian/test
python3 view_all_jobs.py
```

This generates:
- `analysis_output/jobs_list.html` - List of all jobs with RAG badges
- `analysis_output/job_*.html` - Individual job detail pages

### Step 2: Open in Browser

```bash
open /Users/shaydu/dev/mondrian-macos/mondrian/analysis_output/jobs_list.html
```

**What to look for:**
- ✅ Each job has a RAG/Baseline badge in the "RAG Mode" column
- ✅ RAG-enabled jobs show green "RAG-Enabled" badge
- ✅ Baseline jobs show gray "Baseline" badge
- ✅ Stats show count of RAG vs Baseline jobs

### Step 3: View Job Details

Click any job link to see the detail page.

**What to look for:**
- ✅ "Analysis Mode" metadata shows RAG/Baseline badge
- ✅ "Full LLM Prompt" section shows the complete prompt
  - RAG prompts include "## Dimensional Comparison with Master Works:"
  - Baseline prompts only show standard advisor instructions

### Step 4: Generate Comparison Views

```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian/test
python3 create_comparison_view.py
```

This creates:
- `analysis_output/comparison_*.html` - Side-by-side RAG vs Baseline pages

**What to look for:**
- ✅ Left side: Baseline analysis
- ✅ Right side: RAG-enabled analysis
- ✅ Prompt length difference indicator
- ✅ Side-by-side output comparison

## Differences Between RAG and Baseline

### Baseline Mode (`enable_rag=false`)

**Prompt Structure:**
```
[System Prompt]
[Advisor Personality & Instructions]
Analyze the provided image.
```

**Characteristics:**
- Standard advisor analysis
- No reference to similar images
- Shorter prompts (~4,000-5,000 chars)
- Generic photography advice

### RAG Mode (`enable_rag=true`)

**Prompt Structure:**
```
[System Prompt]
[Advisor Personality & Instructions]

## Dimensional Comparison with Master Works:

The user's image has been compared to similar professional photographs...

### Reference Image #1: ansel-half-dome.jpg
**Dimensional Comparison:**
| Dimension | User Image | Reference | Delta | Insight |
|-----------|------------|-----------|-------|---------|
| Composition | TBD | 9.0/10 | -1.0 | Reference +1.0 stronger |
...

**What Worked in Reference:**
- Composition: Perfect application of rule of thirds...
- Lighting: Dramatic use of natural light...

[Similar context for 2-3 reference images]

**Instructions for Analysis:**
1. Reference how the user's image compares to these master works
2. If a dimension is weaker, explain what references did better
3. Provide actionable recommendations to reach reference level
...

Analyze the provided image.
```

**Characteristics:**
- Enhanced with similar image context
- References to master works
- Longer prompts (~8,000-12,000 chars)
- Comparative recommendations
- Specific dimensional improvements

## Troubleshooting

### Issue: enable_rag not working

**Symptoms:**
- Response shows `enable_rag: false` even when passing `true`
- All analyses look the same

**Solutions:**
1. Check request format:
   ```bash
   curl -X POST http://127.0.0.1:5005/upload \
     -F "enable_rag=true" \  # Must be form data, not JSON
     -F "image=@test.jpg" \
     -F "advisor=ansel"
   ```

2. Verify services are running:
   ```bash
   curl http://127.0.0.1:5005/health  # Job service
   curl http://127.0.0.1:5100/health  # AI advisor service
   curl http://127.0.0.1:5400/health  # RAG service (required for RAG mode)
   ```

3. Check logs:
   ```bash
   # Look for RAG-related messages
   tail -f logs/ai_advisor.log | grep RAG
   ```

### Issue: Web interface doesn't show badges

**Symptoms:**
- jobs_list.html doesn't have RAG/Baseline column
- Job detail pages missing analysis mode

**Solutions:**
1. Regenerate web pages:
   ```bash
   cd mondrian/test
   python3 view_all_jobs.py
   ```

2. Force refresh browser (Cmd+Shift+R)

3. Check if jobs have enable_rag in database:
   ```bash
   sqlite3 mondrian.db "SELECT COUNT(*) FROM jobs WHERE enable_rag = 1;"
   ```

### Issue: iOS uploads always use same mode

**Symptoms:**
- Changing Xcode environment variable doesn't affect uploads

**Solutions:**
1. **Clean and rebuild** the iOS app after changing environment variables
2. Verify environment variable is being read:
   ```swift
   print("RAG setting: \(MondrianConfig.enableRAG)")
   ```

3. Check if value is hardcoded instead of using config:
   ```swift
   // ❌ Wrong - hardcoded
   body.append("true")

   // ✅ Correct - uses config
   body.append(MondrianConfig.enableRAG ? "true" : "false")
   ```

### Issue: RAG analysis same as baseline

**Symptoms:**
- `enable_rag: true` in response
- But prompt doesn't include RAG context
- Output identical to baseline

**Solutions:**
1. Verify RAG service is running:
   ```bash
   curl http://127.0.0.1:5400/health
   ```

2. Check if dimensional profiles exist:
   ```bash
   sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles;"
   # Should return > 0
   ```

3. Index some reference images:
   ```bash
   cd mondrian
   python3 batch_analyze_advisor_images.py --advisor ansel
   ```

## Summary

### What Was Implemented

✅ **Phase 1**: Database schema with `enable_rag` column
✅ **Phase 2**: Job service stores `enable_rag` in database and responses
✅ **Phase 3**: Web interface displays RAG/Baseline badges and metadata
✅ **Phase 4**: Side-by-side comparison generator
✅ **Phase 5**: iOS integration documentation

### Files Modified

- `mondrian/job_service_v2.3.py` - Added enable_rag to /job/<id>/full-data endpoint
- `mondrian/test/view_all_jobs.py` - Added RAG badges to jobs list and detail pages

### Files Created

- `mondrian/test/create_comparison_view.py` - Side-by-side comparison generator
- `docs/fixes/rag.md` - This complete guide

### Quick Start Checklist

- [ ] Set `MONDRIAN_ENABLE_RAG` environment variable in Xcode
- [ ] Update iOS network service to read config and pass `enable_rag` parameter
- [ ] Rebuild iOS app
- [ ] Upload test image with RAG enabled
- [ ] Upload same image with RAG disabled
- [ ] Run `python3 view_all_jobs.py` to generate web pages
- [ ] Run `python3 create_comparison_view.py` to generate comparisons
- [ ] Open `jobs_list.html` in browser to verify

## Support

For issues or questions:
1. Check server logs: `mondrian/logs/`
2. Verify services health endpoints
3. Check database: `sqlite3 mondrian.db`
4. Review API responses with curl

## Related Documentation

- [iOS RAG Integration](../iOS_RAG_INTEGRATION.md) - Quick start guide
- [RAG API Reference](../RAG_API_REFERENCE.md) - Complete API documentation
- [RAG Architecture](../NEXT_STEPS.md) - How RAG works internally
