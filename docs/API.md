# Mondrian API Reference

Complete API documentation for the Mondrian photography analysis system with support for multiple analysis modes.

**Current Version**: v2.3 (Job Service) + v1.13 (AI Advisor Service)  
**Backend**: MLX with Qwen3-VL-4B-Instruct (4-bit quantized)  
**Last Updated**: 2026-01-16

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [Core Endpoints](#core-endpoints)
   - [Advisor Endpoints](#advisor-endpoints)
   - [Job Service Endpoints](#job-service-endpoints)
5. [Analysis Modes](#analysis-modes)
6. [Mode in API Responses](#mode-in-api-responses)
7. [Examples](#examples)

---

## Overview

The Mondrian API provides three main services:

- **Job Service** (port 5005): File upload, job management, status tracking
- **AI Advisor Service** (port 5100): Image analysis with strategy pattern
- **Monitoring Service** (port 5200): System health and statistics

### Supported Analysis Modes

- `baseline` - Standard single-pass analysis (default)
- `rag` - Two-pass analysis with portfolio comparison
- `lora` - Fine-tuned model analysis
- `rag+lora` - Combining RAG and LoRA
- `ab_test` - A/B testing mode

---

## Authentication

Currently, no authentication is required for API access. All endpoints are public.

---

## Base URLs

| Service | URL | Port |
|---------|-----|------|
| Job Service | `http://localhost:5005` | 5005 |
| AI Advisor | `http://localhost:5100` | 5100 |
| Monitoring | `http://localhost:5200` | 5200 |

For production/iOS, use the appropriate server IP and port.

---

## Core Endpoints

### Advisor Endpoints

#### 1. List All Advisors

**Endpoint:** `GET /advisors`

**Description:** Retrieve a list of all available advisors with their bio, specialty, and focus areas.

**Response:**
```json
{
  "advisors": [
    {
      "id": "ansel",
      "name": "Ansel Adams",
      "specialty": "Photographer",
      "bio": "Legendary landscape photographer known for his black and white work and Zone System...",
      "focus_areas": [
        {
          "title": "Tonal Range & Zone System",
          "description": "Master of the full spectrum from pure black to pure white..."
        },
        {
          "title": "Composition & Perspective",
          "description": "Precise framing that emphasizes geometric elements, leading lines..."
        }
      ]
    },
    {
      "id": "okeefe",
      "name": "Georgia O'Keeffe",
      "specialty": "Painter",
      "bio": "American modernist painter known for her paintings of enlarged flowers...",
      "focus_areas": []
    }
  ],
  "count": 9,
  "timestamp": "2026-01-16T12:15:09.155619"
}
```

**Response Fields:**
- `id` (string): Unique advisor identifier (used for analysis requests)
- `name` (string): Full name of the advisor
- `specialty` (string): Category (Photographer, Painter, Architect, etc.)
- `bio` (string): Extended biography
- `focus_areas` (array): List of areas of expertise with title and description
- `count` (integer): Total number of advisors
- `timestamp` (string): ISO 8601 timestamp of response

**cURL Example:**
```bash
curl http://localhost:5005/advisors | jq '.advisors[].name'
```

**iOS Swift Example:**
```swift
struct FocusArea: Codable {
    let title: String
    let description: String
}

struct Advisor: Codable {
    let id: String
    let name: String
    let specialty: String
    let bio: String
    let focus_areas: [FocusArea]
}

struct AdvisorsResponse: Codable {
    let advisors: [Advisor]
    let count: Int
    let timestamp: String
}

// Fetch advisors
func fetchAdvisors() async throws -> [Advisor] {
    let url = URL(string: "http://10.0.0.227:5005/advisors")!
    let (data, _) = try await URLSession.shared.data(from: url)
    let response = try JSONDecoder().decode(AdvisorsResponse.self, from: data)
    return response.advisors
}
```

---

#### 2. Get Advisor Details

**Endpoint:** `GET /advisors/<advisor_id>`

**Description:** Retrieve detailed information for a specific advisor including headshot, bio, focus areas, and representative works. Includes URLs to serve headshot image and artwork thumbnails.

**Parameters:**
- `advisor_id` (path, required): Advisor identifier (e.g., "ansel", "okeefe", "mondrian", "watkins")

**Response:**
```json
{
  "advisor": {
    "id": "watkins",
    "name": "Carleton Watkins",
    "specialty": "Photographer",
    "bio": "Watkins was a pioneer of large-format landscape photography in the 19th century, producing monumental images of Yosemite and the American frontier...",
    "years": "1829-1916",
    "wikipedia_url": "https://en.wikipedia.org/wiki/Carleton_Watkins",
    "commons_url": "https://commons.wikimedia.org/wiki/Carleton_Watkins",
    "focus_areas": [
      {
        "title": "Conservation Impact",
        "description": "Assesses ability to inspire preservation"
      },
      {
        "title": "Pioneering Technique",
        "description": "Focuses on large-format precision and clarity"
      }
    ],
    "image_url": "/advisor_image/watkins",
    "artworks": [
      {
        "title": "Mirror View Yosemite",
        "url": "/advisor_artwork/watkins/1"
      },
      {
        "title": "The Grizzly Giant",
        "url": "/advisor_artwork/watkins/2"
      }
    ]
  },
  "timestamp": "2026-01-16T12:30:11.636168"
}
```

**Response Fields:**
- `id` (string): Unique advisor identifier
- `name` (string): Full name
- `specialty` (string): Professional category (Photographer, Painter, Architect)
- `bio` (string): Extended biography
- `years` (string): Birth-death years or active period (e.g., "1829-1916")
- `wikipedia_url` (string): Link to Wikipedia profile
- `commons_url` (string): Link to Wikimedia Commons collection
- `focus_areas` (array): Areas of expertise with title and description
- `image_url` (string): Endpoint to fetch advisor headshot (circular image for profile)
- `artworks` (array): Representative works with title and image URL

**Image URLs:**

The `image_url` and `artworks[].url` fields are relative endpoints that return image files:

- **Headshot:** `GET /advisor_image/<advisor_id>` - Returns JPEG/PNG headshot for circular avatar display
- **Artwork:** `GET /advisor_artwork/<advisor_id>/<index>` - Returns representative work image (1-indexed)

**HTTP Status Codes:**
- `200 OK` - Advisor found and returned
- `404 Not Found` - Advisor ID does not exist, or image file not found

**Error Response (404):**
```json
{
  "error": "Advisor 'invalid_id' not found"
}
```

**cURL Examples:**
```bash
# Get advisor profile with images and works
curl http://localhost:5005/advisors/watkins | jq '.advisor'

# Download headshot
curl http://localhost:5005/advisor_image/watkins -o watkins_headshot.jpg

# Download first artwork
curl http://localhost:5005/advisor_artwork/watkins/1 -o watkins_work_1.jpg

# Get all advisor data and pipe to parse
curl -s http://localhost:5005/advisors/ansel | jq '.advisor.years'
```

**iOS Swift Implementation:**

```swift
struct FocusArea: Codable {
    let title: String
    let description: String
}

struct Artwork: Codable {
    let title: String
    let url: String  // Relative endpoint like "/advisor_artwork/watkins/1"
}

struct Advisor: Codable {
    let id: String
    let name: String
    let specialty: String
    let bio: String
    let years: String
    let wikipedia_url: String
    let commons_url: String
    let focus_areas: [FocusArea]
    let image_url: String  // Endpoint for headshot
    let artworks: [Artwork]  // Representative works
}

struct AdvisorDetail: Codable {
    let advisor: Advisor
    let timestamp: String
}

// Fetch advisor profile with images
func fetchAdvisorProfile(id: String, baseURL: String = "http://10.0.0.227:5005") async throws -> Advisor {
    let url = URL(string: "\(baseURL)/advisors/\(id)")!
    let (data, response) = try await URLSession.shared.data(from: url)
    
    guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
        throw URLError(.resourceUnavailable)
    }
    
    let detail = try JSONDecoder().decode(AdvisorDetail.self, from: data)
    return detail.advisor
}

// Download advisor headshot for circular display
func downloadAdvisorHeadshot(advisor: Advisor, baseURL: String) async throws -> UIImage {
    guard let url = URL(string: baseURL + advisor.image_url) else {
        throw URLError(.badURL)
    }
    let (data, _) = try await URLSession.shared.data(from: url)
    guard let image = UIImage(data: data) else {
        throw URLError(.badServerResponse)
    }
    return image
}

// Download representative works grid
func downloadAdvisorArtworks(advisor: Advisor, baseURL: String) async throws -> [UIImage] {
    var images: [UIImage] = []
    for artwork in advisor.artworks {
        guard let url = URL(string: baseURL + artwork.url) else { continue }
        let (data, _) = try await URLSession.shared.data(from: url)
        if let image = UIImage(data: data) {
            images.append(image)
        }
    }
    return images
}

// Display advisor detail view
func displayAdvisorProfile(id: String) async {
    do {
        let advisor = try await fetchAdvisorProfile(id: id)
        
        // Display header
        print("📸 \(advisor.name) - \(advisor.specialty)")
        print("📅 \(advisor.years)")
        
        // Download and display headshot (circular)
        let headshot = try await downloadAdvisorHeadshot(advisor: advisor, baseURL: "http://10.0.0.227:5005")
        // avatarImageView.image = headshot.circularImage()
        
        // Display bio
        print("ℹ️ \(advisor.bio)")
        
        // Display focus areas
        print("🎯 Review Focus:")
        for focusArea in advisor.focus_areas {
            print("  • \(focusArea.title): \(focusArea.description)")
        }
        
        // Display representative works grid
        print("🖼️ Representative Works:")
        let artworks = try await downloadAdvisorArtworks(advisor: advisor, baseURL: "http://10.0.0.227:5005")
        for (index, artwork) in advisor.artworks.enumerated() {
            print("  \(index + 1). \(artwork.title)")
        }
        
        // Display Wikipedia link
        if !advisor.wikipedia_url.isEmpty {
            print("🔗 Wikipedia: \(advisor.wikipedia_url)")
        }
        
    } catch {
        print("❌ Failed to load advisor: \(error)")
    }
}
```

---

### Job Service Endpoints

#### 1. Upload Image & Queue Analysis

**Endpoint:** `POST /upload`

**Description:** Upload an image file and optionally queue it for analysis.

**Parameters:**
- `file` (file, required): Image file (JPEG, PNG)
- `advisor` (string, required): Advisor ID (e.g., "ansel", "mondrian")
- `mode` (string, optional): Analysis mode (default: "baseline")
  - `baseline` - Standard analysis
  - `rag` - Portfolio comparison
  - `lora` - Fine-tuned model
  - `rag+lora` - Combined approach
- `enable_rag` (boolean, optional): Enable RAG feature (default: false)
- `auto_analyze` (boolean, optional): Start analysis immediately (default: false)

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag)",
  "filename": "photo.jpg",
  "advisor": "ansel",
  "advisors_used": ["ansel"],
  "status": "queued",
  "enable_rag": true,
  "status_url": "http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000",
  "stream_url": "http://localhost:5005/stream/550e8400-e29b-41d4-a716-446655440000"
}
```

**Mode in Response:**
- `job_id` includes mode suffix: `(baseline)`, `(rag)`, `(lora)`, etc.

**cURL Example:**
```bash
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag" \
     -F "enable_rag=true" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload
```

---

#### 2. Get Job Status

**Endpoint:** `GET /status/<job_id>`

**Description:** Get current status and progress of a job. Returns complete mode information.

**Parameters:**
- `job_id` (path, required): Job ID (UUID, with or without mode suffix)

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag)",
  "filename": "photo.jpg",
  "advisor": "ansel",
  "status": "done",
  "current_step": "Completed",
  "progress_percentage": 100,
  "mode": "rag",
  "enable_rag": true,
  "current_advisor": 1,
  "total_advisors": 1,
  "step_phase": "done",
  "llm_thinking": "",
  "analysis_url": "http://localhost:5005/analysis/550e8400-e29b-41d4-a716-446655440000",
  "status_url": "http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000",
  "stream_url": "http://localhost:5005/stream/550e8400-e29b-41d4-a716-446655440000"
}
```

**Mode Fields:**
- `mode` (string): The analysis mode used (baseline, rag, lora, etc.)
- `enable_rag` (boolean): Whether RAG feature is enabled
- `job_id` (string): Includes mode suffix for reference

**Status Values:**
- `pending` - Waiting to start (just queued)
- `queued` - In job processor queue
- `started` - Processing beginning
- `processing` - Image optimization in progress
- `analyzing` - Advisor analysis in progress
- `finalizing` - Results being compiled
- `done` - Complete, ready to view
- `completed` - ✓ Alias for done
- `error` - Analysis failed

**Important: Wait for `done` or `completed` Status**

For LoRA mode, do not fetch analysis until status is `done` or `completed`. Earlier statuses indicate the job is still processing.

**iOS Implementation Note:**

Always check `status !== "done"` before displaying analysis results:

```swift
if status.status == "done" || status.status == "completed" {
    // Safe to display analysis_html and other content
} else {
    // Still processing - show loading spinner
}
```

**cURL Example:**
```bash
curl http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000
```

---

#### 3. Get Analysis HTML

**Endpoint:** `GET /analysis/<job_id>`

**Description:** Retrieve the complete analysis as HTML. Includes mode badge.

**Response:** HTML document with embedded mode badge at top

**Mode Badge Display:**
- **BASELINE** (Blue): #3d5a80 - Standard analysis
- **RAG** (Brown): #5a4a3d - Portfolio comparison
- **LORA** (Green): #3d5a3d - Fine-tuned model
- **AB_TEST** (Purple): #5a3d5a - Experimental

**cURL Example:**
```bash
curl http://localhost:5005/analysis/550e8400-e29b-41d4-a716-446655440000 > analysis.html
```

---

#### 4. Get Complete Job Data

**Endpoint:** `GET /job/<job_id>/full-data`

**Description:** Retrieve all job metadata, prompt, and outputs.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "photo.jpg",
  "advisor": "ansel",
  "status": "done",
  "mode": "rag",
  "enable_rag": true,
  "prompt": "Analyze this image...",
  "prompt_length": 2048,
  "llm_outputs": {
    "ansel": {
      "composition": 8.5,
      "lighting": 7.5,
      "focus_sharpness": 8.0,
      "mode_used": "rag"
    }
  },
  "analysis_markdown": "<div>...</div>",
  "timestamps": {
    "created_at": "2026-01-14T10:30:00",
    "started_at": "2026-01-14T10:30:05",
    "completed_at": "2026-01-14T10:35:30"
  }
}
```

**Mode in Response:**
- `mode`: The analysis mode (baseline, rag, lora, etc.)
- `enable_rag`: RAG feature flag
- `llm_outputs[advisor].mode_used`: Mode used per advisor

**cURL Example:**
```bash
curl http://localhost:5005/job/550e8400-e29b-41d4-a716-446655440000/full-data | jq '.mode'
```

---

#### 5. Stream Analysis Updates

**Endpoint:** `GET /stream/<job_id>`

**Description:** Server-Sent Events (SSE) stream for real-time analysis updates. Sends status, progress, and LLM thinking every 3-5 seconds for iOS UI updates.

**Events:**
- `connected` - Initial connection established
- `status_update` - Status changed or periodic thinking update (every 3 seconds during analyzing)
- `analysis_complete` - Analysis finished with HTML results
- `done` - Job fully complete

**Status Update Event (with LLM Thinking):**
```json
{
  "type": "status_update",
  "job_id": "abc123-def456-789",
  "timestamp": 1768592178.262955,
  "job_data": {
    "status": "analyzing",
    "progress_percentage": 45,
    "current_step": "Analyzing with Ansel...",
    "llm_thinking": "The composition shows strong leading lines... The lighting creates dramatic contrast...",
    "current_advisor": 1,
    "total_advisors": 1,
    "step_phase": "analyzing"
  }
}
```

**LLM Thinking Updates:**
- `llm_thinking` field contains the AI's step-by-step reasoning
- Sent every 3-5 seconds during analysis phase for real-time iOS UI updates
- Allows UI to show "thinking" animation/text as analysis progresses
- Character length increases as model processes image

**Complete SSE Stream Example:**
```
event: connected
data: {"type":"connected","job_id":"abc123-def456-789"}

event: status_update
data: {"type":"status_update","job_id":"abc123-def456-789","timestamp":1768592100.123,"job_data":{"status":"analyzing","progress_percentage":10,"current_step":"Summoning Ansel Adams...","llm_thinking":"","current_advisor":1,"total_advisors":1,"step_phase":"analyzing"}}

event: status_update
data: {"type":"status_update","job_id":"abc123-def456-789","timestamp":1768592103.456,"job_data":{"status":"analyzing","progress_percentage":30,"current_step":"Analyzing with Ansel...","llm_thinking":"The photograph shows a well-composed landscape with strong diagonal lines...","current_advisor":1,"total_advisors":1,"step_phase":"analyzing"}}

event: status_update
data: {"type":"status_update","job_id":"abc123-def456-789","timestamp":1768592106.789,"job_data":{"status":"analyzing","progress_percentage":45,"current_step":"Analyzing with Ansel...","llm_thinking":"The composition demonstrates masterful use of the Zone System. Tonality ranges from pure black to pure white with excellent midtone separation...","current_advisor":1,"total_advisors":1,"step_phase":"analyzing"}}

event: analysis_complete
data: {"type":"analysis_complete","job_id":"abc123-def456-789","analysis_html":"<html>...</html>"}

event: done
data: {"type":"done","job_id":"abc123-def456-789"}
```

**iOS Implementation:**
```swift
// Connect to SSE stream
func connectToStream(jobId: String, baseURL: String = "http://10.0.0.227:5005") {
    guard let url = URL(string: "\(baseURL)/stream/\(jobId)") else { return }
    
    var request = URLRequest(url: url)
    request.timeoutInterval = 300  // 5 minute timeout for long analyses
    
    let session = URLSession.shared
    let task = session.dataTask(with: request) { data, response, error in
        guard let data = data, error == nil else { return }
        
        let lines = String(data: data, encoding: .utf8)?.split(separator: "\n") ?? []
        var eventType: String?
        var eventData: String?
        
        for line in lines {
            if line.starts(with: "event:") {
                eventType = line.replacingOccurrences(of: "event: ", with: "").trimmingCharacters(in: .whitespaces)
            } else if line.starts(with: "data:") {
                eventData = line.replacingOccurrences(of: "data: ", with: "")
            } else if line.isEmpty, let type = eventType, let data = eventData {
                handleStreamEvent(type: type, data: data)
                eventType = nil
                eventData = nil
            }
        }
    }
    task.resume()
}

// Handle stream events
func handleStreamEvent(type: String, data: String) {
    guard let jsonData = data.data(using: .utf8),
          let json = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any] else {
        return
    }
    
    switch type {
    case "connected":
        print("📱 Connected to stream")
        
    case "status_update":
        if let jobData = json["job_data"] as? [String: Any],
           let status = jobData["status"] as? String,
           let thinking = jobData["llm_thinking"] as? String {
            let progress = jobData["progress_percentage"] as? Int ?? 0
            let step = jobData["current_step"] as? String ?? ""
            
            // Update iOS UI
            DispatchQueue.main.async {
                self.statusLabel.text = status
                self.progressView.progress = Float(progress) / 100.0
                self.stepLabel.text = step
                if !thinking.isEmpty {
                    self.thinkingLabel.text = thinking  // Show LLM thinking
                    self.thinkingLabel.isHidden = false
                }
            }
        }
        
    case "analysis_complete":
        if let html = json["analysis_html"] as? String {
            DispatchQueue.main.async {
                self.webView.loadHTMLString(html, baseURL: nil)
            }
        }
        
    case "done":
        print("✅ Analysis complete")
        
    default:
        break
    }
}
```

**cURL Example:**
```bash
# Connect to stream and show updates
curl -N http://localhost:5005/stream/abc123-def456-789

# Or pipe to jq for JSON formatting
curl -N http://localhost:5005/stream/abc123-def456-789 | grep "data:" | jq -R 'split("data: ")[1] | fromjson'
```

---

### AI Advisor Service Endpoints

#### 1. Direct Image Analysis

**Endpoint:** `POST /analyze`

**Description:** Send image directly for analysis (bypasses Job Service queue).

**Parameters:**
- `file` (file, required): Image file
- `advisor` (string, required): Advisor ID
- `mode` (string, optional): Analysis mode (default: "baseline")
- `response_format` (string, optional): "html" or "json" (default: "html")

**Response:**
```json
{
  "html": "<div class='analysis'>...</div>",
  "mode_used": "rag",
  "metadata": {
    "mode_used": "rag",
    "requested_mode": "rag",
    "effective_mode": "rag",
    "fallback_occurred": false,
    "overall_grade": "A",
    "advisor_id": "ansel"
  }
}
```

**Mode in Response:**
- `mode_used`: The actual mode used
- `metadata.requested_mode`: The requested mode
- `metadata.effective_mode`: The mode after any fallback
- `metadata.fallback_occurred`: Whether fallback occurred

**cURL Example:**
```bash
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=lora" \
     http://localhost:5100/analyze
```

---

## Analysis Modes

### Mode Comparison

| Mode | Pass | Portfolio | Model | Speed | Detail |
|------|------|-----------|-------|-------|--------|
| `baseline` | 1 | No | Base | Fast | Standard |
| `rag` | 2 | Yes | Base | Slower | Detailed |
| `lora` | 1 | No | Fine-tuned | Fast | Optimized |
| `rag+lora` | 2 | Yes | Fine-tuned | Slower | Enhanced |
| `ab_test` | 2 | Both | Both | Slowest | Comparative |

### Mode Selection

**Use `baseline` when:**
- Speed is critical
- Running on limited hardware
- Basic analysis is sufficient
- First-time user experience

**Use `rag` when:**
- Comparing to advisor's work is important
- Need detailed portfolio analysis
- Time is not critical
- Want dimensional comparison

**Use `lora` when:**
- Fine-tuned model is available for advisor
- Want optimized results for specific style
- Speed is needed with better accuracy
- Model is pre-trained

**Use `rag+lora` when:**
- Want best of both approaches
- Portfolio comparison AND fine-tuned model
- Have enough time
- Want maximum insight

---

## Mode in API Responses

### Summary Table

| Endpoint | Mode Field | Format | Location |
|----------|-----------|--------|----------|
| `/upload` | `job_id` suffix | `"uuid (rag)"` | Response body |
| `/status` | `mode` | `"rag"` | Response body |
| `/analyze` | `mode_used` | `"rag"` | Response body + metadata |
| `/analysis` | Badge | Visual | HTML body |
| `/job/.../full-data` | `mode` | `"rag"` | Response body |
| `/stream` | `mode` | `"rag"` | SSE event data |

### Extracting Mode by Endpoint

#### From `/upload` Response
```python
# Mode in job_id suffix
job_id = response['job_id']  # "550e8400-e29b-41d4-a716-446655440000 (rag)"
mode = job_id.split('(')[1].rstrip(')')  # "rag"
```

#### From `/status` Response (Recommended)
```python
# Direct mode field
mode = response['mode']  # "rag"
enable_rag = response['enable_rag']  # true
```

#### From `/analyze` Response
```python
# In metadata
mode_used = response['metadata']['mode_used']  # "rag"
fallback = response['metadata']['fallback_occurred']  # false
```

#### From `/analysis` Response
```html
<!-- Mode badge in HTML -->
<div style="background: #5a4a3d; padding: 6px 12px;">
  RAG
</div>
```

#### From `/job/.../full-data` Response
```python
# Complete data
mode = response['mode']  # "rag"
enable_rag = response['enable_rag']  # true
llm_mode = response['llm_outputs']['ansel']['mode_used']  # "rag"
```

---

## Examples

### Example 1: Complete Workflow with Mode Tracking

```bash
# 1. Upload image with RAG mode
RESPONSE=$(curl -s -F "file=@image.jpg" \
                   -F "advisor=ansel" \
                   -F "mode=rag" \
                   -F "auto_analyze=true" \
                   http://localhost:5005/upload)

JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "Uploaded: $JOB_ID"  # 550e8400-e29b-41d4-a716-446655440000 (rag)

# 2. Poll status and check mode
while true; do
  STATUS=$(curl -s http://localhost:5005/status/550e8400-e29b-41d4-a716-446655440000)
  
  MODE=$(echo $STATUS | jq -r '.mode')
  PROGRESS=$(echo $STATUS | jq -r '.progress_percentage')
  STATUS_VAL=$(echo $STATUS | jq -r '.status')
  
  echo "Mode: $MODE | Progress: $PROGRESS% | Status: $STATUS_VAL"
  
  if [ "$STATUS_VAL" == "done" ]; then
    break
  fi
  
  sleep 2
done

# 3. Get analysis with mode badge
curl http://localhost:5005/analysis/550e8400-e29b-41d4-a716-446655440000 > analysis.html

# 4. Get complete data for archiving
curl http://localhost:5005/job/550e8400-e29b-41d4-a716-446655440000/full-data | jq '.mode'
```

---

### Example 2: iOS Swift Implementation

```swift
import Foundation

struct JobStatus: Codable {
    let job_id: String
    let mode: String
    let enable_rag: Bool
    let status: String
    let progress_percentage: Int
    let current_step: String
    let analysis_url: String
}

// Fetch status with mode
func getJobStatus(jobId: String) async throws -> JobStatus {
    let url = URL(string: "http://localhost:5005/status/\(jobId)")!
    let (data, _) = try await URLSession.shared.data(from: url)
    return try JSONDecoder().decode(JobStatus.self, from: data)
}

// Monitor analysis
func monitorAnalysis(jobId: String) async {
    var status = try await getJobStatus(jobId: jobId)
    
    while status.status != "done" {
        print("Mode: \(status.mode)")  // ✨ Direct access
        print("Progress: \(status.progress_percentage)%")
        print("Step: \(status.current_step)")
        
        try await Task.sleep(nanoseconds: 2_000_000_000)  // 2 seconds
        status = try await getJobStatus(jobId: jobId)
    }
    
    print("✓ Analysis complete in \(status.mode) mode")
}
```

---

### Example 3: Check Mode Without String Parsing

```python
import requests

def get_analysis_mode(job_id):
    """Get the analysis mode directly from API"""
    
    # Method 1: From /status (recommended)
    response = requests.get(f'http://localhost:5005/status/{job_id}')
    status = response.json()
    mode = status['mode']  # Direct field
    
    return mode

def compare_modes():
    """Compare results from different modes"""
    
    modes = ['baseline', 'rag', 'lora']
    results = {}
    
    for mode in modes:
        # Upload in this mode
        files = {'file': open('image.jpg', 'rb')}
        data = {'advisor': 'ansel', 'mode': mode, 'auto_analyze': 'true'}
        response = requests.post('http://localhost:5005/upload', files=files, data=data)
        job_id = response.json()['job_id'].split(' ')[0]  # Extract UUID
        
        # Wait and get result
        status = requests.get(f'http://localhost:5005/status/{job_id}').json()
        while status['status'] != 'done':
            status = requests.get(f'http://localhost:5005/status/{job_id}').json()
            time.sleep(1)
        
        # Retrieve full data
        full_data = requests.get(f'http://localhost:5005/job/{job_id}/full-data').json()
        results[mode] = full_data
    
    return results
```

---

## Error Responses

### Common Error Status Codes

| Code | Error | Cause | Solution |
|------|-------|-------|----------|
| 400 | Bad Request | Missing required parameter | Check all required fields |
| 404 | Not Found | Job ID doesn't exist | Verify job ID is correct |
| 500 | Server Error | Analysis failed | Check server logs |
| 202 | Accepted | Job still processing | Poll `/status` again |

### Error Response Format

```json
{
  "error": "Job not found",
  "job_id": "invalid-uuid"
}
```

---

## Best Practices

### ✅ DO

- Use explicit `mode` field from `/status` endpoint
- Check `enable_rag` along with `mode`
- Poll `/status` at reasonable intervals (2-5 seconds)
- Handle network timeouts gracefully
- Save mode with analysis results

### ❌ DON'T

- Parse mode from `job_id` string when explicit field exists
- Assume `mode` implies RAG is enabled
- Poll too frequently (causes CPU spike)
- Ignore fallback information
- Assume one mode is always available

---

## Rate Limiting

No rate limiting is currently implemented. Reasonable polling intervals are recommended:
- Status polling: Every 2-5 seconds
- Analysis complete check: Every 5-10 seconds

---

## Support

For API issues or questions, please refer to:
- **Mode Documentation**: See `MODE_DATA_AVAILABILITY_QUICK_REF.md`
- **Integration Guide**: See `API_MODE_RESPONSE_GUIDE.md`
- **Debug Markers**: See `MODE_VERIFICATION_GUIDE.md`

---

**Last Updated**: 2026-01-14  
**Version**: 2.3 (with mode support)
