# Mode Information Availability - Quick Reference

## Where to Find Mode Information

### 📤 Immediately After Upload

```
POST /upload
↓
Response includes: job_id (with mode suffix), mode not explicitly returned
↓
job_id format: "uuid (baseline|rag|lora)"
```

**Example:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag)"
}
```

**How to extract:**
```python
# Python
job_id = "550e8400-e29b-41d4-a716-446655440000 (rag)"
mode = job_id.split("(")[1].rstrip(")")  # "rag"

# Swift
let mode = String(jobId.split(separator: "(").last ?? "baseline").dropLast()
```

---

### 📊 During Analysis (Polling /status)

```
GET /status/uuid
↓
Response includes: 
  - mode (explicit field) ✨ NEW
  - enable_rag (explicit field) ✨ NEW
  - job_id (with suffix in parentheses)
  - progress_percentage
  - status (analyzing, processing, done, etc.)
```

**Example:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000 (rag)",
  "mode": "rag",
  "enable_rag": true,
  "status": "analyzing",
  "progress_percentage": 45,
  "current_step": "Pass 2: Comparing with portfolio"
}
```

**Use Case:** Show user which mode is running + progress

---

### ✅ After Analysis Complete

```
GET /status/uuid (when status == "done")
↓
Response includes:
  - mode: "rag"
  - enable_rag: true
  - analysis_url: where to fetch HTML with badge
```

**Example:**
```json
{
  "mode": "rag",
  "status": "done",
  "analysis_url": "http://localhost:5005/analysis/550e8400-e29b-41d4-a716-446655440000"
}
```

**Use Case:** Display mode badge, fetch HTML for viewing

---

### 🎨 HTML Analysis View

```
GET /analysis/uuid
↓
Response includes:
  - HTML with mode badge at top
  - Badge color: mode-specific
  - Badge text: BASELINE | RAG | LORA | AB_TEST
```

**Example:**
```html
<div class="analysis">
  <div style="background: #5a4a3d; padding: 6px 12px; font-weight: bold;">
    RAG
  </div>
  <!-- Rest of analysis -->
</div>
```

**Use Case:** Visual indication in UI

---

### 📋 Complete Job Data

```
GET /job/uuid/full-data
↓
Response includes:
  - mode: "rag"
  - enable_rag: true
  - llm_outputs (with individual advisor modes)
  - prompt, analysis_markdown, timestamps
```

**Example:**
```json
{
  "mode": "rag",
  "enable_rag": true,
  "llm_outputs": {
    "ansel": {
      "composition": 8.5,
      "mode_used": "rag"
    }
  }
}
```

**Use Case:** Archive, detailed logging, analytics

---

## Data Available at Each Step

```
┌─────────────────────────────────────────────────────┐
│ Step 1: Upload                                      │
├─────────────────────────────────────────────────────┤
│ ✓ job_id (with mode suffix)                         │
│ ✗ explicit mode field                               │
│ ✗ enable_rag                                        │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ Step 2: During Analysis (GET /status)               │
├─────────────────────────────────────────────────────┤
│ ✓ mode (explicit) ← NEW!                            │
│ ✓ enable_rag (explicit) ← NEW!                      │
│ ✓ status                                            │
│ ✓ progress_percentage                               │
│ ✓ current_step (showing what's happening)           │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ Step 3: After Analysis (GET /analysis)              │
├─────────────────────────────────────────────────────┤
│ ✓ HTML with mode badge                              │
│ ✓ Color-coded by mode                               │
│ ✓ Complete analysis content                         │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ Step 4: Complete Data (GET /job/.../full-data)      │
├─────────────────────────────────────────────────────┤
│ ✓ mode                                              │
│ ✓ enable_rag                                        │
│ ✓ llm_outputs with mode_used per advisor            │
│ ✓ All metadata, timestamps                          │
└─────────────────────────────────────────────────────┘
```

---

## iOS Implementation Examples

### Example 1: Show Mode During Analysis

```swift
// Polling /status endpoint
Task {
    while true {
        let response = try await statusAPI.fetchStatus(jobId: jobID)
        
        // ✨ NEW: Direct mode access (no string parsing needed)
        updateModeIndicator(mode: response.mode)
        updateProgress(response.progress_percentage)
        updateStatus(response.current_step)
        
        if response.status == "done" {
            break
        }
        
        try await Task.sleep(nanoseconds: 1_000_000_000) // 1 second
    }
}

func updateModeIndicator(mode: String) {
    switch mode {
    case "baseline":
        modeLabel.text = "BASELINE"
        modeLabel.backgroundColor = UIColor(hex: "#3d5a80")  // Blue
    case "rag":
        modeLabel.text = "RAG"
        modeLabel.backgroundColor = UIColor(hex: "#5a4a3d")  // Brown
    case "lora":
        modeLabel.text = "LORA"
        modeLabel.backgroundColor = UIColor(hex: "#3d5a3d")  // Green
    default:
        modeLabel.text = mode.uppercased()
    }
}
```

### Example 2: Save Mode with Result

```swift
// After analysis complete
struct AnalysisResult: Codable {
    let jobID: String
    let advisor: String
    let mode: String  // ✨ NEW: Store the mode
    let enable_rag: Bool  // ✨ NEW: Store RAG flag
    let analysis: String
    let timestamp: Date
}

let result = AnalysisResult(
    jobID: status.job_id,
    advisor: status.advisor,
    mode: status.mode,  // ✨ Direct access
    enable_rag: status.enable_rag,  // ✨ Direct access
    analysis: htmlContent,
    timestamp: Date()
)

// Save for offline access, history, analytics
try saveToDiskOrDatabase(result)
```

### Example 3: Analytics Tracking

```swift
// Track which modes are used most
Analytics.log(event: "analysis_completed", parameters: [
    "mode": response.mode,              // ✨ NEW: explicit mode
    "enable_rag": response.enable_rag,  // ✨ NEW: RAG flag
    "advisor": response.advisor,
    "duration_seconds": Int(Date().timeIntervalSince(startTime)),
    "status": response.status
])
```

---

## API Response Cheat Sheet

| Endpoint | Mode Field | Enable_RAG Field | Format |
|----------|-----------|------------------|--------|
| `/upload` | In job_id suffix | No | "(rag)" |
| `/status` | ✅ Yes | ✅ Yes | "rag" |
| `/analyze` | ✅ Yes (in metadata) | No | "rag" |
| `/analysis` | ✅ Yes (in HTML badge) | No | Visual |
| `/job/.../full-data` | ✅ Yes | ✅ Yes | "rag" |

---

## Best Practices for iOS

### ✅ DO: Use Explicit Fields

```swift
// Good - Direct field access
let mode = status.mode
```

### ❌ DON'T: Parse from job_id

```swift
// Avoid - String parsing
let mode = status.job_id
    .split(separator: "(")
    .last?
    .dropLast()
```

### ✅ DO: Check Both mode and enable_rag

```swift
// Proper way to understand analysis method
if status.mode == "rag" && status.enable_rag {
    print("2-pass RAG analysis")
} else if status.mode == "rag" && !status.enable_rag {
    print("LoRA only (no RAG)")
}
```

### ❌ DON'T: Assume mode means RAG

```swift
// Wrong - mode and enable_rag can be independent
let isRAG = status.mode.contains("rag")  // Could be wrong
```

---

## Summary

| Need | Endpoint | Field | When Available |
|------|----------|-------|-----------------|
| Track analysis progress | `/status` | `mode`, `progress_percentage` | During analysis |
| Show final result | `/analysis` | Badge in HTML | When done |
| Save with result | `/job/.../full-data` | `mode`, `enable_rag` | When done |
| Display to user | Any | `mode` field | After upload |

**Bottom Line:** Use the explicit `mode` and `enable_rag` fields from `/status` endpoint for easiest iOS integration! 🎯
