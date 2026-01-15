# Fix: RAG+LoRA Jumping to "Analyzing Composition" Screen

## Problem

When using `mode=rag+lora`, the UI was jumping straight to "Analyzing composition and framing..." instead of staying on the status screen like `mode=lora` does.

## Root Cause

**File:** `mondrian/job_service_v2.3.py`, line 927

The job_service was hardcoding a status update BEFORE calling the AI service:

```python
update_job_status(job_id, llm_thinking="Analyzing composition and framing...")
job_service_callback = host_url or f"http://127.0.0.1:{PORT}"

# Then make the API call...
resp = requests.post(AI_SERVICE_URL, files=files, data=data, timeout=660)
```

This caused:
1. Status message sent immediately (before API request completes)
2. UI jumps to "Analyzing composition" screen
3. Strategy's real-time thinking callbacks are ignored or overridden

## Solution

**Remove the hardcoded thinking message.**

Change from:
```python
abs_resized_path = os.path.abspath(resized_path)
update_job_status(job_id, llm_thinking="Analyzing composition and framing...")
job_service_callback = host_url or f"http://127.0.0.1:{PORT}"
```

To:
```python
abs_resized_path = os.path.abspath(resized_path)
job_service_callback = host_url or f"http://127.0.0.1:{PORT}"
```

## Why This Works

The `thinking_callback` defined in ai_advisor_service.py (around line 1447) handles ALL status updates properly:

```python
def thinking_callback(message):
    if job_service_url and job_id:
        send_thinking_update(job_service_url, job_id, message)
```

The strategy calls this callback with:
- `"Preparing analysis model..."` (LoRA/RAG+LoRA)
- `"Analyzing composition..."` (Pass 1 for RAG+LoRA)
- `"Finding reference images..."` (Query for RAG+LoRA)
- `"Generating analysis..."` (Pass 2 for RAG+LoRA)

These real-time updates from the strategy are now properly sent to the client without being overridden.

## Result

✅ **RAG+LoRA now has the same UI flow as LoRA**
- Stays on status screen during initial processing
- Shows real-time thinking updates from the strategy
- Different content (more verbose for RAG+LoRA) but same flow
- Smooth progression through analysis steps

## Modes Comparison

### Before Fix
| Mode | Flow |
|------|------|
| baseline | ✅ Status → Analyzing → Complete |
| rag | ✅ Status → Analyzing → Complete |
| lora | ✅ Status → Analyzing → Complete |
| rag+lora | ❌ **Jumps to Analyzing immediately** |

### After Fix
| Mode | Flow |
|------|------|
| baseline | ✅ Status → Analyzing → Complete |
| rag | ✅ Status → Analyzing → Complete |
| lora | ✅ Status → Analyzing → Complete |
| rag+lora | ✅ **Status → Analyzing → Complete** |

All modes now have consistent UI flow!

## Technical Details

The strategy's `thinking_callback` is passed into the `analyze()` method and sends real-time updates:

```python
# In ai_advisor_service.py, line 1466:
result = context.analyze(
    image_path=abs_image_path,
    advisor_id=advisor,
    thinking_callback=thinking_callback  # ← Passes callback
)

# In strategy's analyze():
if thinking_callback:
    thinking_callback("Preparing analysis model...")
# ... model runs ...
if thinking_callback:
    thinking_callback("Analyzing composition...")
# ... more work ...
if thinking_callback:
    thinking_callback("Generating analysis...")
```

By removing the hardcoded message, the callback updates are the ONLY status messages sent, ensuring:
- No premature status changes
- Real-time visibility into strategy progress
- Consistent behavior across all modes
