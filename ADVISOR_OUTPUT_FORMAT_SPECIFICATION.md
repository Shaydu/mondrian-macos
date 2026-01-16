# Advisor Output Format Specification
**Source:** `origin/20250111-rag-metadata` branch - RAG Integration

---

## Complete JSON/Structure Format Summary

Based on the iOS API documentation and RAG integration guide from the `origin/20250111-rag-metadata` branch, here are all the expected JSON structures:

---

## 1. GET /advisors - Fetch Available Advisors

**Endpoint:** `GET /advisors`

**Request:**
```swift
let url = URL(string: "\(jobServiceURL)/advisors")!
let (data, _) = try await URLSession.shared.data(from: url)
let response = try JSONDecoder().decode(AdvisorsResponse.self, from: data)
```

**Response JSON Structure:**
```json
{
  "advisors": [
    {
      "id": "ansel",
      "name": "Ansel Adams",
      "specialty": "Landscape Photography",
      "focus_areas": ["composition", "lighting", "technical_execution"],
      "image_url": "http://10.0.0.227:5005/advisor_image/ansel.jpg",
      "artworks": [
        {
          "title": "Monolith, the Face of Half Dome",
          "year": "1927",
          "url": "http://10.0.0.227:5005/advisor_artwork/ansel/monolith.jpg"
        }
      ]
    },
    {
      "id": "okeefe",
      "name": "Georgia O'Keeffe",
      "specialty": "Abstract & Close-up Photography",
      "focus_areas": ["abstraction", "close-up", "color_theory"],
      "image_url": "http://10.0.0.227:5005/advisor_image/okeefe.jpg",
      "artworks": [
        {
          "title": "Flower Series #1",
          "year": "1920s",
          "url": "http://10.0.0.227:5005/advisor_artwork/okeefe/flower_series.jpg"
        }
      ]
    }
  ]
}
```

**Swift Models:**
```swift
struct AdvisorsResponse: Decodable {
    let advisors: [Advisor]
}

struct Advisor: Decodable {
    let id: String
    let name: String
    let specialty: String
    let focus_areas: [String]
    let image_url: String?
    let artworks: [Artwork]?
}

struct Artwork: Decodable {
    let title: String
    let year: String
    let url: String
}
```

---

## 2. POST /upload - Upload Image and Start Analysis

**Endpoint:** `POST /upload`

**Request Form Data:**
```
- image (file, required) - The image to analyze
- advisor (string, required) - Advisor ID: "ansel", "all", "random", or comma-separated list
- auto_analyze (string, optional) - "true" to start analysis immediately (default: "true")
- enable_rag (string, optional) - "true" to use RAG semantic search (default: "false")
```

**Response JSON Structure:**
```json
{
  "job_id": "abc123-def456-789",
  "filename": "photo-a1b2c3d4.jpg",
  "advisor": "ansel",
  "advisors_used": ["ansel"],
  "status": "queued",
  "enable_rag": false,
  "status_url": "http://10.0.0.227:5005/status/abc123-def456-789",
  "stream_url": "http://10.0.0.227:5005/stream/abc123-def456-789"
}
```

**Swift Models:**
```swift
struct UploadResponse: Decodable {
    let job_id: String
    let filename: String
    let advisor: String
    let advisors_used: [String]
    let status: String
    let enable_rag: Bool
    let status_url: String
    let stream_url: String
}
```

---

## 3. GET /stream/{job_id} - Server-Sent Events (SSE) Stream

**Endpoint:** `GET /stream/{job_id}`

Multiple events sent over SSE connection:

### 3.1 connected Event
```json
{
  "type": "connected",
  "job_id": "abc123-def456-789"
}
```

### 3.2 status_update Event
```json
{
  "type": "status_update",
  "job_data": {
    "status": "analyzing",
    "progress_percentage": 45,
    "current_step": "Conjuring Ansel Adams",
    "current_advisor": 1,
    "total_advisors": 1,
    "step_phase": "advisor_analysis"
  }
}
```

### 3.3 analysis_complete Event
```json
{
  "type": "analysis_complete",
  "job_id": "abc123-def456-789",
  "analysis_html": "<html>...</html>"
}
```

### 3.4 done Event
```json
{
  "type": "done",
  "job_id": "abc123-def456-789"
}
```

**Swift Models:**
```swift
struct ConnectedEvent: Decodable {
    let type: String
    let job_id: String
}

struct StatusUpdateEvent: Decodable {
    let type: String
    let job_data: JobData
}

struct JobData: Decodable {
    let status: String
    let progress_percentage: Int
    let current_step: String?
    let current_advisor: Int?
    let total_advisors: Int?
    let step_phase: String?
}

struct AnalysisCompleteEvent: Decodable {
    let type: String
    let job_id: String
    let analysis_html: String
}

struct DoneEvent: Decodable {
    let type: String
    let job_id: String
}
```

---

## 4. GET /analysis/{job_id} - Get Analysis Results (Fallback)

**Endpoint:** `GET /analysis/{job_id}`

**Response:** HTML document containing:
- Image preview
- Analysis table with 8 dimensions
- Scores (e.g., "Composition (7/10)")
- Feedback and recommendations
- Overall grade

**Usage in iOS:**
```swift
import WebKit

func displayAnalysis(html: String) {
    let webView = WKWebView(frame: view.bounds)
    webView.loadHTMLString(html, baseURL: URL(string: jobServiceURL))
    view.addSubview(webView)
}
```

---

## 5. POST /index - Index Image for RAG (Semantic Search)

**Endpoint:** `POST http://10.0.0.227:5400/index`

**Request JSON Structure:**
```json
{
  "job_id": "abc123-def456-789",
  "image_path": "source/photo-a1b2c3d4.jpg"
}
```

**Swift Request Model:**
```swift
struct IndexRequest: Encodable {
    let job_id: String
    let image_path: String
}
```

**Response JSON Structure:**
```json
{
  "success": true,
  "id": "caption-uuid-12345",
  "caption": "A striking landscape photograph featuring dramatic lighting and strong compositional elements with a focus on geometric patterns and natural textures.",
  "embedding_dim": 384
}
```

**Swift Response Model:**
```swift
struct IndexResponse: Decodable {
    let success: Bool
    let id: String
    let caption: String
    let embedding_dim: Int
}
```

---

## 6. POST /search - Search for Similar Images (RAG)

**Endpoint:** `POST http://10.0.0.227:5400/search`

**Request JSON Structure:**
```json
{
  "query": "sunset over mountains with dramatic lighting",
  "top_k": 10
}
```

**Swift Request Model:**
```swift
struct SearchRequest: Encodable {
    let query: String
    let top_k: Int
}
```

**Response JSON Structure:**
```json
{
  "query": "sunset over mountains with dramatic lighting",
  "results": [
    {
      "id": "caption-uuid-1",
      "job_id": "abc123-def456-789",
      "image_path": "source/photo-a1b2c3d4.jpg",
      "caption": "A striking landscape with dramatic sunset over mountain peaks, featuring strong compositional elements and warm golden hour lighting.",
      "similarity": 0.92
    },
    {
      "id": "caption-uuid-2",
      "job_id": "xyz789-abc123-456",
      "image_path": "source/mountain-sunset.jpg",
      "caption": "Mountain range at golden hour with vibrant orange and purple hues in the sky.",
      "similarity": 0.87
    }
  ],
  "total": 2
}
```

**Swift Models:**
```swift
struct SearchRequest: Encodable {
    let query: String
    let top_k: Int
}

struct SearchResponse: Decodable {
    let query: String
    let results: [SearchResult]
    let total: Int
}

struct SearchResult: Decodable {
    let id: String
    let job_id: String
    let image_path: String
    let caption: String
    let similarity: Double  // 0.0 to 1.0
}
```

---

## 7. Health Check Endpoints

### Job Service Health
```bash
curl http://10.0.0.227:5005/health
```

### RAG Service Health
```bash
curl http://10.0.0.227:5400/health
```

**Response:**
```json
{
  "status": "UP",
  "database": "UP (15 captions indexed)",
  "caption_service": "http://127.0.0.1:5200",
  "embedding_service": "http://127.0.0.1:5300"
}
```

---

## 8. Image Serving Endpoints

### Get Advisor Headshot
```
GET http://10.0.0.227:5005/advisor_image/{advisor_id}.jpg
```

Example:
```
GET http://10.0.0.227:5005/advisor_image/ansel.jpg
```

### Get Advisor Artwork
```
GET http://10.0.0.227:5005/advisor_artwork/{advisor_id}/{artwork_file}
```

Example:
```
GET http://10.0.0.227:5005/advisor_artwork/ansel/monolith.jpg
```

### Get Analyzed Image Thumbnail
```
GET http://10.0.0.227:5005/image/{image_path}
```

Example:
```
GET http://10.0.0.227:5005/image/source/photo-a1b2c3d4.jpg
```

---

## 9. Advisor Image Manifest (YAML Structure)

**File:** `advisor_image_manifest.yaml`

```yaml
advisors:
  - category: photographer
    advisor: ansel
    images:
      - filename: 2.jpg
        title: ""
        date_taken: ""
        description: ""
      - filename: 3.jpg
        title: ""
        date_taken: ""
        description: ""
      - filename: Ansel_Adams_-_National_Archives_79-AA-Q04.jpg
        title: ""
        date_taken: ""
        description: ""
      # ... more images
  - category: photographer
    advisor: okeefe
    images:
      # ... similar structure
```

---

## 10. Complete iOS Service Class Example

```swift
import Foundation
import EventSource

class MondrianAPIService {
    let jobServiceURL: String
    let ragServiceURL: String
    
    init(host: String = "10.0.0.227") {
        self.jobServiceURL = "http://\(host):5005"
        self.ragServiceURL = "http://\(host):5400"
    }
    
    // MARK: - Step 1: Get Advisors
    
    func fetchAdvisors() async throws -> AdvisorsResponse {
        let url = URL(string: "\(jobServiceURL)/advisors")!
        let (data, _) = try await URLSession.shared.data(from: url)
        return try JSONDecoder().decode(AdvisorsResponse.self, from: data)
    }
    
    // MARK: - Step 2: Upload Image
    
    func uploadImage(_ imageData: Data, advisor: String, enableRag: Bool = false) async throws -> UploadResponse {
        var request = URLRequest(url: URL(string: "\(jobServiceURL)/upload")!)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", 
                         forHTTPHeaderField: "Content-Type")
        
        var body = Data()
        
        // Add image
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n")
        body.append("Content-Type: image/jpeg\r\n\r\n")
        body.append(imageData)
        body.append("\r\n")
        
        // Add advisor
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"advisor\"\r\n\r\n")
        body.append("\(advisor)\r\n")
        
        // Add auto_analyze
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"auto_analyze\"\r\n\r\n")
        body.append("true\r\n")
        
        // Add enable_rag
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"enable_rag\"\r\n\r\n")
        body.append(enableRag ? "true" : "false\r\n")
        body.append("--\(boundary)--\r\n")
        
        let (data, _) = try await URLSession.shared.upload(for: request, from: body)
        return try JSONDecoder().decode(UploadResponse.self, from: data)
    }
    
    // MARK: - Step 3: Connect to SSE Stream
    
    func connectToStream(streamUrl: String, 
                        onProgress: @escaping (JobData) -> Void,
                        onComplete: @escaping (String) -> Void,
                        onError: @escaping (Error?) -> Void) -> EventSource {
        
        let eventSource = EventSource(url: URL(string: streamUrl)!)
        
        eventSource.onError { error in
            onError(error)
        }
        
        eventSource.addEventListener("status_update") { id, event, data in
            if let data = data?.data(using: .utf8),
               let event = try? JSONDecoder().decode(StatusUpdateEvent.self, from: data) {
                DispatchQueue.main.async {
                    onProgress(event.job_data)
                }
            }
        }
        
        eventSource.addEventListener("analysis_complete") { id, event, data in
            if let data = data?.data(using: .utf8),
               let event = try? JSONDecoder().decode(AnalysisCompleteEvent.self, from: data) {
                DispatchQueue.main.async {
                    onComplete(event.analysis_html)
                }
            }
        }
        
        eventSource.addEventListener("done") { id, event, data in
            eventSource.close()
        }
        
        eventSource.connect()
        return eventSource
    }
    
    // MARK: - Step 4: Get Analysis (Fallback)
    
    func fetchAnalysis(jobId: String) async throws -> String {
        let url = URL(string: "\(jobServiceURL)/analysis/\(jobId)")!
        let (data, _) = try await URLSession.shared.data(from: url)
        return String(data: data, encoding: .utf8) ?? ""
    }
    
    // MARK: - Step 5: Index Image (RAG)
    
    func indexImage(jobId: String, imagePath: String) async throws -> IndexResponse {
        let indexRequest = IndexRequest(job_id: jobId, image_path: imagePath)
        
        var request = URLRequest(url: URL(string: "\(ragServiceURL)/index")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(indexRequest)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(IndexResponse.self, from: data)
    }
    
    // MARK: - Step 6: Search Images (RAG)
    
    func searchImages(query: String, topK: Int = 10) async throws -> SearchResponse {
        let searchRequest = SearchRequest(query: query, top_k: topK)
        
        var request = URLRequest(url: URL(string: "\(ragServiceURL)/search")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(searchRequest)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(SearchResponse.self, from: data)
    }
}

// MARK: - Data Extension

extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}
```

---

## Key Points for iOS Implementation

### 1. Base URLs Configuration
```swift
let jobServiceURL = "http://10.0.0.227:5005"    // Image analysis
let ragServiceURL = "http://10.0.0.227:5400"     // Semantic search
```

### 2. Required Services
- **Job Service** (5005) - Upload and analysis
- **AI Advisor** (5100) - MLX vision analysis
- **Caption Service** (5200) - Image captioning
- **Embedding Service** (5300) - Vector embeddings
- **RAG Service** (5400) - Semantic search

### 3. Complete API Flow
1. **Fetch Advisors** - GET /advisors
2. **Upload Image** - POST /upload
3. **Listen to SSE** - GET /stream/{job_id}
4. **Get Analysis** - GET /analysis/{job_id} (fallback)
5. **Index Image** - POST /index (RAG)
6. **Search Images** - POST /search (RAG)

### 4. RAG Parameter
- **Parameter Name:** `enable_rag`
- **Accepted Values:** `'true'`, `'True'`, `'TRUE'`, `'1'`, `'yes'` (or omit for false)
- **Default:** `false` (baseline mode)

### 5. Similarity Scoring
- `> 0.8` - Very similar
- `0.6 - 0.8` - Moderately similar
- `0.4 - 0.6` - Somewhat similar
- `< 0.4` - Not very similar

### 6. Image Dimensions
- Vector embedding dimensions: **384** (sentence-bert model)
- Maximum recommended image size: **10MB**
- Supported formats: **JPEG, PNG, HEIC**

---

## Source Branch Details

**Branch:** `origin/20250111-rag-metadata`
**Latest Commit:** `f9a8e5291ad8828c9fb0c9d9d28677af6aa54db9`
**Commit Message:** "updated e2e test and rag comparision"

**Key Documentation Files:**
- `docs/ios/API_INTEGRATION.md` - Complete iOS API integration guide
- `docs/RAG_API_REFERENCE.md` - RAG parameter reference
- `docs/ios/RAG_INTEGRATION.md` - RAG semantic search implementation
- `advisor_image_manifest.yaml` - Advisor image catalog structure

