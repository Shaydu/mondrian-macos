# Mondrian iOS API Integration Guide

Complete guide for integrating the Mondrian photography analysis API with RAG (Retrieval-Augmented Generation) semantic search into your iOS application.

---

## Overview

Mondrian provides a complete photography analysis and semantic search system with the following capabilities:

1. **Image Analysis** - AI-powered feedback from photography masters
2. **Real-time Progress** - SSE streaming for live updates
3. **Semantic Search** - Find similar images using natural language (RAG)
4. **Multi-advisor Support** - Choose from 9 different artistic perspectives

---

## Quick Start

### Base URLs

```swift
let jobServiceURL = "http://10.0.0.227:5005"    // Image analysis
let ragServiceURL = "http://10.0.0.227:5400"     // Semantic search
```

Replace `10.0.0.227` with your Mac's IP address (shown when you start the services).

### Required Services

The monitoring service starts all required services automatically:

```bash
cd /Users/shaydu/dev/mondrian-macos
./mondrian.sh
```

This starts:
- **Job Service** (5005) - Upload and analysis
- **AI Advisor** (5100) - MLX vision analysis
- **Caption Service** (5200) - Image captioning
- **Embedding Service** (5300) - Vector embeddings
- **RAG Service** (5400) - Semantic search

---

## Complete API Flow

### Step 1: Fetch Available Advisors

Get the list of available photography advisors before allowing upload.

**Endpoint:** `GET /advisors`

**Request:**
```swift
let url = URL(string: "\(jobServiceURL)/advisors")!
let (data, _) = try await URLSession.shared.data(from: url)
let response = try JSONDecoder().decode(AdvisorsResponse.self, from: data)
```

**Response:**
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
      "specialty": "Abstract & Close-up Photography"
    }
  ]
}
```

**Models:**
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

### Step 2: Upload Image and Start Analysis

Upload an image with advisor selection to start automatic analysis.

**Endpoint:** `POST /upload`

**Request:**
```swift
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
body.append("ansel\r\n")

// Add auto_analyze
body.append("--\(boundary)\r\n")
body.append("Content-Disposition: form-data; name=\"auto_analyze\"\r\n\r\n")
body.append("true\r\n")
body.append("--\(boundary)--\r\n")

let (data, _) = try await URLSession.shared.upload(for: request, from: body)
let response = try JSONDecoder().decode(UploadResponse.self, from: data)
```

**Form Parameters:**
- `image` (file, required) - The image to analyze
- `advisor` (string, required) - Advisor ID: `"ansel"`, `"all"`, `"random"`, or comma-separated list
- `auto_analyze` (string, optional) - `"true"` to start analysis immediately (default: `"true"`)

**Response:**
```json
{
  "job_id": "abc123-def456-789",
  "filename": "photo-a1b2c3d4.jpg",
  "advisor": "ansel",
  "advisors_used": ["ansel"],
  "status": "queued",
  "status_url": "http://10.0.0.227:5005/status/abc123-def456-789",
  "stream_url": "http://10.0.0.227:5005/stream/abc123-def456-789"
}
```

**Models:**
```swift
struct UploadResponse: Decodable {
    let job_id: String
    let filename: String
    let advisor: String
    let advisors_used: [String]
    let status: String
    let status_url: String
    let stream_url: String
}
```

---

### Step 3: Listen to SSE Stream

Connect to Server-Sent Events stream for real-time progress updates.

**Endpoint:** `GET /stream/{job_id}`

**Implementation:**

Use an SSE library like [IKEventSource](https://github.com/inaka/EventSource) or implement EventSource support.

```swift
import EventSource

func connectToStream(streamUrl: String) {
    let eventSource = EventSource(url: URL(string: streamUrl)!)
    
    // Connection opened
    eventSource.onOpen {
        print("SSE Connected")
    }
    
    // Handle errors
    eventSource.onError { error in
        print("SSE Error: \(error?.localizedDescription ?? "unknown")")
    }
    
    // Listen for 'connected' event
    eventSource.addEventListener("connected") { id, event, data in
        if let data = data?.data(using: .utf8),
           let event = try? JSONDecoder().decode(ConnectedEvent.self, from: data) {
            print("Connected to job: \(event.job_id)")
        }
    }
    
    // Listen for 'status_update' events
    eventSource.addEventListener("status_update") { id, event, data in
        if let data = data?.data(using: .utf8),
           let event = try? JSONDecoder().decode(StatusUpdateEvent.self, from: data) {
            DispatchQueue.main.async {
                self.updateProgress(event.job_data)
            }
        }
    }
    
    // Listen for 'thinking_update' events (NEW! - Real-time LLM feedback)
    eventSource.addEventListener("thinking_update") { id, event, data in
        if let data = data?.data(using: .utf8),
           let event = try? JSONDecoder().decode(ThinkingUpdateEvent.self, from: data) {
            DispatchQueue.main.async {
                // Display thinking message that updates every ~5 seconds
                // Example: "💭 Generating analysis... (150 tokens, 44.1 tps)"
                self.updateThinkingStatus(event.thinking)
            }
        }
    }
    
    // Listen for 'analysis_complete' event
    eventSource.addEventListener("analysis_complete") { id, event, data in
        if let data = data?.data(using: .utf8),
           let event = try? JSONDecoder().decode(AnalysisCompleteEvent.self, from: data) {
            DispatchQueue.main.async {
                self.displayAnalysis(html: event.analysis_html)
            }
        }
    }
    
    // Listen for 'done' event
    eventSource.addEventListener("done") { id, event, data in
        DispatchQueue.main.async {
            self.analysisFinished()
        }
        eventSource.close()
    }
    
    eventSource.connect()
}
```

**SSE Event Types:**

1. **connected** - Connection established
```json
{
  "type": "connected",
  "job_id": "abc123-def456-789"
}
```

2. **status_update** - Progress and status changes
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

3. **thinking_update** - Real-time LLM generation feedback (NEW!)
Sent every 5 seconds during analysis to show active processing with token count and generation speed.
```json
{
  "type": "thinking_update",
  "job_id": "abc123-def456-789",
  "thinking": "Generating analysis... (150 tokens, 44.1 tps)"
}
```

4. **analysis_complete** - Analysis finished with HTML
```json
{
  "type": "analysis_complete",
  "job_id": "abc123-def456-789",
  "analysis_html": "<html>...</html>"
}
```

5. **done** - Stream complete
```json
{
  "type": "done",
  "job_id": "abc123-def456-789"
}
```

**Models:**
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

struct ThinkingUpdateEvent: Decodable {
    let type: String
    let job_id: String
    let thinking: String  // e.g., "Generating analysis... (150 tokens, 44.1 tps)"
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

### Real-Time "Thinking" Updates (NEW!)

The `thinking_update` event provides real-time feedback showing the LLM's generation progress with token count and speed.

**What You'll Receive:**
```
💭 "Generating analysis... (50 tokens, 40.0 tps)"    [at 5 seconds]
💭 "Generating analysis... (100 tokens, 42.5 tps)"   [at 10 seconds]
💭 "Generating analysis... (150 tokens, 44.1 tps)"   [at 15 seconds]
```

**Implementation Example:**

```swift
@State private var thinkingMessage: String = ""
@State private var isThinking: Bool = false

// In your SSE listener:
func updateThinkingStatus(_ thinking: String) {
    thinkingMessage = thinking
    isThinking = true
    
    // Optional: Auto-fade after 10 seconds if no new updates
    DispatchQueue.main.asyncAfter(deadline: .now() + 10.0) {
        if thinkingMessage == thinking {
            withAnimation {
                isThinking = false
            }
        }
    }
}

// In your UI:
VStack {
    if isThinking {
        HStack(spacing: 8) {
            // Animated thinking indicator
            Image(systemName: "brain")
                .font(.title2)
                .foregroundColor(.blue)
                .transition(.scale.combined(with: .opacity))
            
            Text(thinkingMessage)
                .font(.body)
                .foregroundColor(.secondary)
                .lineLimit(1)
                .truncationMode(.tail)
            
            Spacer()
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(8)
        .transition(.move(edge: .top).combined(with: .opacity))
    }
}
.animation(.easeInOut(duration: 0.3), value: isThinking)
```

**Metrics Available in the Message:**

The `thinking` string contains:
- **Token count** - Total tokens generated so far (e.g., `150 tokens`)
- **Generation speed** - Tokens per second (e.g., `44.1 tps`)

You can parse these values if you want to display them separately:

```swift
// Parse the thinking message
func parseThinkingMetrics(_ message: String) -> (tokens: Int, speed: Double)? {
    // Extract: "Generating analysis... (150 tokens, 44.1 tps)"
    let pattern = #"\((\d+) tokens,\s*([\d.]+) tps\)"#
    if let regex = try? NSRegularExpression(pattern: pattern),
       let match = regex.firstMatch(in: message, range: NSRange(message.startIndex..., in: message)),
       let tokenRange = Range(match.range(at: 1), in: message),
       let speedRange = Range(match.range(at: 2), in: message),
       let tokens = Int(message[tokenRange]),
       let speed = Double(message[speedRange]) {
        return (tokens, speed)
    }
    return nil
}

// Use in UI for detailed display
if let (tokens, speed) = parseThinkingMetrics(thinkingMessage) {
    HStack(spacing: 12) {
        VStack(alignment: .leading) {
            Text("Tokens Generated").font(.caption).foregroundColor(.secondary)
            Text("\(tokens)").font(.headline)
        }
        
        Divider().frame(height: 24)
        
        VStack(alignment: .leading) {
            Text("Speed").font(.caption).foregroundColor(.secondary)
            Text(String(format: "%.1f tps", speed)).font(.headline)
        }
        
        Spacer()
    }
    .padding()
    .background(Color(.systemGray6))
    .cornerRadius(8)
}
```

**UI Display Options:**

1. **Simple Status Badge:**
   ```swift
   Text(thinkingMessage).font(.caption).foregroundColor(.blue)
   ```

2. **With Progress Indicator:**
   ```swift
   HStack {
       ProgressView()
       Text(thinkingMessage)
   }
   ```

3. **Animated Subtitle:**
   ```swift
   Text(thinkingMessage)
       .font(.subheadline)
       .foregroundColor(.secondary)
       .transition(.opacity)
   ```

4. **Fade In/Out Effect:**
   ```swift
   Text(thinkingMessage)
       .opacity(isThinking ? 1 : 0.5)
       .animation(.easeInOut(duration: 0.5), value: thinkingMessage)
   ```

---

### Step 4: Get Analysis Results (Fallback)

If `analysis_complete` event wasn't received, fetch the HTML directly.

**Endpoint:** `GET /analysis/{job_id}`

**Request:**
```swift
let url = URL(string: "\(jobServiceURL)/analysis/\(jobId)")!
let (data, _) = try await URLSession.shared.data(from: url)
let html = String(data: data, encoding: .utf8)
```

**Response:**
Returns complete HTML document with:
- Image preview
- Analysis table with 8 dimensions
- Scores (e.g., "Composition (7/10)")
- Feedback and recommendations
- Overall grade

**Display in WebView:**
```swift
import WebKit

func displayAnalysis(html: String) {
    let webView = WKWebView(frame: view.bounds)
    webView.loadHTMLString(html, baseURL: URL(string: jobServiceURL))
    view.addSubview(webView)
}
```

---

### Step 5: Index Image for Semantic Search (RAG)

After analysis completes, index the image for semantic search capabilities.

**Endpoint:** `POST http://10.0.0.227:5400/index`

**Request:**
```swift
struct IndexRequest: Encodable {
    let job_id: String
    let image_path: String
}

let indexRequest = IndexRequest(
    job_id: jobId,
    image_path: "source/\(uploadResponse.filename)"
)

var request = URLRequest(url: URL(string: "\(ragServiceURL)/index")!)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")
request.httpBody = try JSONEncoder().encode(indexRequest)

let (data, _) = try await URLSession.shared.data(for: request)
let response = try JSONDecoder().decode(IndexResponse.self, from: data)
```

**Response:**
```json
{
  "success": true,
  "id": "caption-uuid-12345",
  "caption": "A striking landscape photograph featuring dramatic lighting and strong compositional elements with a focus on geometric patterns and natural textures.",
  "embedding_dim": 384
}
```

**Models:**
```swift
struct IndexRequest: Encodable {
    let job_id: String
    let image_path: String
}

struct IndexResponse: Decodable {
    let success: Bool
    let id: String
    let caption: String
    let embedding_dim: Int
}
```

**Purpose:**
- Generates detailed caption using MLX vision model
- Creates 384-dimensional vector embedding
- Stores in database for semantic search

---

### Step 6: Search for Similar Images (RAG)

Search for similar images using natural language queries.

**Endpoint:** `POST http://10.0.0.227:5400/search`

**Request:**
```swift
struct SearchRequest: Encodable {
    let query: String
    let top_k: Int
}

let searchRequest = SearchRequest(
    query: "sunset over mountains with dramatic lighting",
    top_k: 10
)

var request = URLRequest(url: URL(string: "\(ragServiceURL)/search")!)
request.httpMethod = "POST"
request.setValue("application/json", forHTTPHeaderField: "Content-Type")
request.httpBody = try JSONEncoder().encode(searchRequest)

let (data, _) = try await URLSession.shared.data(for: request)
let response = try JSONDecoder().decode(SearchResponse.self, from: data)
```

**Response:**
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

**Models:**
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
    let similarity: Double
}
```

**UI Display:**
```swift
func displaySearchResults(_ results: [SearchResult]) {
    for result in results {
        // Display thumbnail from job_id
        let thumbnailURL = "\(jobServiceURL)/image/\(result.image_path)"
        
        // Show similarity as percentage
        let percentage = Int(result.similarity * 100)
        
        print("\(result.caption) - \(percentage)% match")
    }
}
```

---

## Complete Service Class

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
    
    func uploadImage(_ imageData: Data, advisor: String) async throws -> UploadResponse {
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

## Example Usage

```swift
class AnalysisViewController: UIViewController {
    let api = MondrianAPIService(host: "10.0.0.227")
    var eventSource: EventSource?
    
    func analyzeImage(_ imageData: Data) async {
        do {
            // Step 1: Get advisors (optional, for UI)
            let advisors = try await api.fetchAdvisors()
            print("Available advisors: \(advisors.advisors.map { $0.name })")
            
            // Step 2: Upload image
            let uploadResponse = try await api.uploadImage(imageData, advisor: "ansel")
            let jobId = uploadResponse.job_id
            
            print("Job created: \(jobId)")
            
            // Step 3: Connect to SSE stream
            eventSource = api.connectToStream(
                streamUrl: uploadResponse.stream_url,
                onProgress: { jobData in
                    self.updateProgress(
                        percentage: jobData.progress_percentage,
                        status: jobData.current_step ?? "Processing..."
                    )
                },
                onComplete: { html in
                    self.displayAnalysis(html: html)
                    
                    // Step 5: Index for RAG (async)
                    Task {
                        try? await self.indexAndSearch(
                            jobId: jobId,
                            filename: uploadResponse.filename
                        )
                    }
                },
                onError: { error in
                    print("Stream error: \(error?.localizedDescription ?? "unknown")")
                }
            )
            
        } catch {
            print("Error: \(error)")
        }
    }
    
    func indexAndSearch(jobId: String, filename: String) async throws {
        // Step 5: Index image
        let imagePath = "source/\(filename)"
        let indexResponse = try await api.indexImage(jobId: jobId, imagePath: imagePath)
        
        print("Indexed: \(indexResponse.caption)")
        
        // Step 6: Search for similar images
        let searchResponse = try await api.searchImages(query: "landscape photography")
        
        print("Found \(searchResponse.results.count) similar images")
        for result in searchResponse.results.prefix(3) {
            let similarity = Int(result.similarity * 100)
            print("  \(similarity)%: \(result.caption.prefix(60))...")
        }
    }
    
    func updateProgress(percentage: Int, status: String) {
        progressBar.progress = Float(percentage) / 100.0
        statusLabel.text = status
    }
    
    func displayAnalysis(html: String) {
        webView.loadHTMLString(html, baseURL: URL(string: api.jobServiceURL))
    }
}
```

---

## Testing

### End-to-End Test Script

Run the complete test that exercises all 6 steps:

```bash
cd /Users/shaydu/dev/mondrian-macos/test
./test_ios_api_flow.sh ansel ../source/test_image.jpg
```

This test script:
1. ✅ Fetches advisors (GET /advisors)
2. ✅ Uploads image (POST /upload)
3. ✅ Listens to SSE stream (GET /stream/{job_id})
4. ✅ Gets analysis HTML (GET /analysis/{job_id})
5. ✅ Indexes image (POST /index)
6. ✅ Searches similar images (POST /search)

### Health Checks

Verify all services are running:

```bash
# Job Service
curl http://10.0.0.227:5005/health

# RAG Service
curl http://10.0.0.227:5400/health

# Caption Service
curl http://10.0.0.227:5200/health

# Embedding Service
curl http://10.0.0.227:5300/health

# AI Advisor Service
curl http://10.0.0.227:5100/health
```

---

## Error Handling

```swift
enum MondrianError: Error {
    case networkError(Error)
    case invalidResponse
    case serviceUnavailable(String)
    case analysisTimeout
    case ragServiceUnavailable
}

extension MondrianAPIService {
    func fetchAdvisorsWithErrorHandling() async throws -> AdvisorsResponse {
        do {
            return try await fetchAdvisors()
        } catch {
            throw MondrianError.networkError(error)
        }
    }
    
    func checkRAGAvailability() async -> Bool {
        guard let url = URL(string: "\(ragServiceURL)/health") else {
            return false
        }
        
        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
}
```

---

## Performance Considerations

### Image Upload
- Maximum recommended size: 10MB
- Supported formats: JPEG, PNG, HEIC
- Server auto-resizes to manageable dimensions

### SSE Streaming
- Typically completes in 30-60 seconds
- Implement timeout after 5 minutes
- Reconnect logic for network interruptions

### RAG Operations
- Indexing: ~2-5 seconds per image
- Search: <1 second for queries
- Index images in background after analysis completes

---

## Troubleshooting

### Cannot Connect to Services

**Check network:**
```bash
ping 10.0.0.227
```

**Verify services are running:**
```bash
cd /Users/shaydu/dev/mondrian-macos
./mondrian.sh
```

### SSE Stream Not Receiving Events

- Ensure using proper SSE library (not standard URLSession)
- Check that `Accept: text/event-stream` header is set
- Verify firewall isn't blocking port 5005

### RAG Service Unavailable

- Check if all RAG services are running (ports 5200, 5300, 5400)
- Verify in logs: `/Users/shaydu/dev/mondrian-macos/mondrian/logs/`
- RAG is optional - core analysis works without it

---

## Next Steps

1. **Implement Upload Flow** - Start with Steps 1-4 (upload and analysis)
2. **Add SSE Support** - Real-time progress updates
3. **Integrate RAG** - Add semantic search feature (Steps 5-6)
4. **Polish UI** - Progress bars, status indicators, search interface
5. **Test Edge Cases** - Network failures, timeouts, error states

---

## Additional Resources

- **Complete Usage Guide**: `/docs/usage-guide.md`
- **RAG Quick Start**: `/docs/RAG_QUICKSTART.md`
- **Test Script**: `/test/test_ios_api_flow.sh`
- **Architecture**: `/docs/architecture.md`

---

**Questions?** Contact the Mondrian team or check the documentation in `/docs/ios/`
