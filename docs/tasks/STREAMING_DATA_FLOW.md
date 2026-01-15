# Streaming Token Generation - Data Flow Diagram

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONDRIAN STREAMING SYSTEM                    │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  iOS Client  │
│   / Browser  │
└──────┬───────┘
       │
       │ Connect to SSE Stream
       │ /stream/<job_id>
       ▼
┌──────────────────────────┐
│   Job Service (5000)     │
│  ├─ /submit              │
│  ├─ /stream/<job_id>  ◄──┼─── SSE Stream
│  └─ /job/<id>/thinking   │
└──────┬───────────┬────────┘
       │           │
       │ Submit    │ PUT /job/<id>/thinking
       │           ▼
       ▼    ┌──────────────────────┐
  ┌─────────┤ AI Advisor (5100)    │
  │         ├─ stream_generate()   │
  │         └─ send_thinking_update│
  │              every 5 seconds    │
  │         └──────────────────────┘
  │
  ▼
SQLite Database
├─ jobs table
│  ├─ id
│  ├─ status
│  ├─ llm_thinking ◄─── Updated every 5s
│  ├─ analysis_markdown
│  └─ ...
```

## Request/Response Timeline

```
t=0s:   User submits image
        ↓
        POST /submit
        Response: {"job_id": "abc123"}

t=0.5s: Client connects to SSE
        GET /stream/abc123
        ├─ data: {"type": "connection"}
        └─ data: {"type": "status_update", "status": "analyzing"}

t=1s:   AI Advisor starts loading model

t=2s:   Model loaded, MLX stream_generate() begins
        ├─ Token 1: "The"
        ├─ Token 2: " photograph"
        ├─ Token 3: " exhibits"
        └─ ... 40+ more tokens (4 seconds)

t=5s:   Token count = 50, Ready to send update
        PUT /job/abc123/thinking
        ├─ Payload: {"thinking": "Generating analysis... (50 tokens, 40.0 tps)"}
        ├─ Database updates llm_thinking
        └─ SSE clients receive:
           data: {"type": "thinking_update", "thinking": "Generating analysis... (50 tokens, 40.0 tps)"}

t=6s:   Token 51, 52, 53... continue streaming

t=10s:  Token count = 100
        PUT /job/abc123/thinking
        └─ SSE: "Generating analysis... (100 tokens, 42.5 tps)"

t=15s:  Token count = 150
        PUT /job/abc123/thinking
        └─ SSE: "Generating analysis... (150 tokens, 44.1 tps)"

t=20s:  Generation complete (assumed max_tokens or EOS)
        ├─ Final output: full analysis text
        ├─ Database updates with final response
        ├─ SSE: {"type": "analysis_complete"}
        └─ SSE: {"type": "done"}

Total time: ~20 seconds
Updates sent: 4 (every 5 seconds)
User perception: Active thinking with progress indicators
```

## Token Generation Stream Detail

```
stream_generate(model, processor, prompt, image)
│
├─ Yield GenerationResult #1
│  ├─ text: "The"
│  ├─ generation_tokens: 1
│  ├─ generation_tps: 35.2
│  └─ peak_memory: 2.1 GB
│
├─ Yield GenerationResult #2
│  ├─ text: " photograph"
│  ├─ generation_tokens: 2
│  ├─ generation_tps: 36.5
│  └─ peak_memory: 2.1 GB
│
├─ Yield GenerationResult #3
│  ├─ text: " exhibits"
│  ├─ generation_tokens: 3
│  ├─ generation_tps: 37.2
│  └─ peak_memory: 2.1 GB
│
├─ ... (tokens 4-49) ...
│
├─ Yield GenerationResult #50
│  ├─ text: "..."
│  ├─ generation_tokens: 50
│  ├─ generation_tps: 40.0  ◄─── UPDATE SENT HERE (every 5 seconds)
│  └─ peak_memory: 2.1 GB
│
└─ Continue until max_tokens or EOS token
```

## SSE Event Stream

```
CLIENT RECEIVES:
═══════════════════════════════════════════════════════════

1. Connection Established
   data: {"type": "connection"}
   
2. Job Status Update
   data: {"type": "status_update", "job_data": {"status": "analyzing", "current_step": "Starting advisor analysis"}}

3. First Thinking Update (t=5s)
   data: {"type": "thinking_update", "job_id": "abc123", "thinking": "Generating analysis... (50 tokens, 40.0 tps)"}
   
4. Second Thinking Update (t=10s)
   data: {"type": "thinking_update", "job_id": "abc123", "thinking": "Generating analysis... (100 tokens, 42.5 tps)"}

5. Third Thinking Update (t=15s)
   data: {"type": "thinking_update", "job_id": "abc123", "thinking": "Generating analysis... (150 tokens, 44.1 tps)"}

6. Final Analysis
   data: {"type": "analysis_complete", "job_id": "abc123", "analysis_markdown": "...full content..."}

7. Job Done
   data: {"type": "done", "job_id": "abc123", "status": "completed"}
```

## Database State Evolution

```
TIME     llm_thinking COLUMN           status      current_step
────────────────────────────────────────────────────────────────
t=0s     (NULL)                        pending     -
t=1s     "Loading model..."            analyzing   "Loading model..."
t=2s     "Generating analysis..."      analyzing   "Generating analysis..."
t=5s     "Generating analysis... (50   analyzing   "Generating analysis..."
         tokens, 40.0 tps)"
t=10s    "Generating analysis... (100  analyzing   "Generating analysis..."
         tokens, 42.5 tps)"
t=15s    "Generating analysis... (150  analyzing   "Generating analysis..."
         tokens, 44.1 tps)"
t=20s    "MLX analysis complete"       analyzing   "Finalizing..."
t=21s    (cleared)                     complete    "Analysis complete"
```

## Frontend Rendering Example (iOS)

```
┌─────────────────────────────────┐
│   Photo Analysis               │
├─────────────────────────────────┤
│                                 │
│     [Image Preview]             │
│                                 │
├─────────────────────────────────┤
│ Advisor: Ansel Adams            │
│                                 │
│ 💭 Generating analysis...       │◄── Updates every 5 seconds
│    (50 tokens, 40.0 tps)        │    Shows progress & speed
│                                 │
│ ▓▓▓▓▓▓░░░░░░░░░░░░  25%        │    Progress bar (optional)
│                                 │
└─────────────────────────────────┘

t=5s:  "💭 Generating analysis... (50 tokens, 40.0 tps)"
t=10s: "💭 Generating analysis... (100 tokens, 42.5 tps)"
t=15s: "💭 Generating analysis... (150 tokens, 44.1 tps)"
t=20s: [Full analysis appears]

User sees active work happening instead of spinning spinner!
```

## How Endpoints Interact

```
┌─ User Action ─────────────────────────┐
│                                        │
│ POST /submit (job_service:5000)       │
│ └─ Filename: "photo.jpg"              │
│ └─ Advisors: ["ansel"]                │
│ └─ Response: job_id = "abc123"        │
│                                        │
└────────────────────┬───────────────────┘
                     │
         ┌───────────▼──────────┐
         │ Job Service spawns   │
         │ AI Advisor process   │
         └───────────┬──────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                 │
    │        ┌───────▼────────┐       │
    │        │  AI Advisor    │       │
    │        │  - Load model  │       │
    │        │  - stream_gen()│       │
    │        └───────┬────────┘       │
    │                │                 │
    │         ┌──────▼───────┐        │
    │         │ Every 5 secs │        │
    │         │ PUT /job/    │        │
    │         │ abc123/      │        │
    │         │ thinking     │        │
    │         └──────┬───────┘        │
    │                │                 │
    └────────────────┼─────────────────┘
                     │
    ┌────────────────▼──────────────┐
    │   Job Service Database        │
    │   - Update llm_thinking       │
    │   - Stream to SSE clients     │
    └────────────────┬──────────────┘
                     │
    ┌────────────────▼──────────────┐
    │   SSE Stream (/stream/abc123) │
    │   - Send thinking_update      │
    │   - To iOS/Web clients        │
    └───────────────────────────────┘
```

## Comparison: Before vs After

```
BEFORE (Blocking generation):
═══════════════════════════════
Timeline: 0s ──────────────────────────────────── 20s
Action:   Submit ▶ [Long silence..................] ▶ Result
UI:       🔄     .........(nothing happens)........ ✓

AFTER (Streaming generation):
═════════════════════════════
Timeline: 0s ──────────────────────────────────── 20s
Action:   Submit ▶ 💭💭💭💭💭 [Stream] 💭💭💭 ▶ Result
UI:       🔄     💭 💭    💭     💭    💭    ✓
Events:   con   upd upd   upd    upd   done
          (every 5 seconds!)

User perceives: Active processing with visible progress
```

## Performance Metrics

```
GENERATION METRICS (Available in each thinking update):

generation_tokens: 150
├─ How many tokens generated so far

generation_tps: 44.1
├─ Tokens per second (generation speed)
├─ Typical range: 35-50 tps on M1/M2
├─ Slower = check GPU load
├─ Faster = amazing!

peak_memory: 2.1
├─ Peak GPU memory in GB
├─ Typical: 1.5-3.0 GB for Qwen or similar

prompt_tps: 42.5
├─ Speed of processing input tokens
├─ Usually faster than generation

total_tokens: 180
├─ prompt_tokens (30) + generation_tokens (150)
```

## Summary

The streaming token generation transforms the user experience from:
- **Silent wait** → **Active feedback every 5 seconds**
- **Unknown duration** → **Visible progress (tokens & speed)**
- **Perceived failure** → **Perceived active processing**

All through a simple architectural improvement leveraging MLX-VLM's built-in `stream_generate()` function!
