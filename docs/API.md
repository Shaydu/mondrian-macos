# Mondrian API Reference

Complete API documentation for the Mondrian photography analysis system with support for multiple analysis modes.

**Current Version**: v2.3 (Job Service) + v1.13 (AI Advisor Service)  
**Backend**: MLX with Qwen3-VL-4B-Instruct (4-bit quantized)  
**Last Updated**: 2026-01-14

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [Core Endpoints](#core-endpoints)
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
- `queued` - Waiting to start
- `started` - Processing beginning
- `processing` - Image optimization in progress
- `analyzing` - Advisor analysis in progress
- `finalizing` - Results being compiled
- `done` - Complete, ready to view
- `error` - Analysis failed

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

**Description:** Server-Sent Events (SSE) stream for real-time updates.

**Events:**
- `status_update` - Status changed
- `progress_update` - Progress percentage changed
- `analysis_complete` - Analysis finished

**Response (streaming):**
```
data: {"type":"status_update","job_id":"uuid (rag)","status":"analyzing","mode":"rag"}
data: {"type":"progress_update","progress":45}
data: {"type":"analysis_complete","job_id":"uuid (rag)","mode":"rag"}
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
