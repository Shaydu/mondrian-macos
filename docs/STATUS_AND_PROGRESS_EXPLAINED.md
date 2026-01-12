# Status Percentage and Messages - Explained

This document explains how status percentages and messages are generated in the Mondrian system.

## 1. Progress Percentage Calculation

### Location
The progress percentage is calculated in `mondrian/job_service_v2.3.py` in the `calculate_progress_percentage()` function (lines 219-243).

### How It Works

The percentage is calculated based on three factors:
1. **Status** - Current job status (queued, processing, analyzing, finalizing, done, error)
2. **Step Phase** - Current phase within the status (image_processing, advisor_preparation, advisor_analysis, finalizing)
3. **Advisor Progress** - Which advisor is being processed (current_advisor / total_advisors)

### Percentage Breakdown

```python
def calculate_progress_percentage(status, step_phase, current_advisor, total_advisors):
    if status == "done":
        return 100
    elif status == "error":
        return 0
    elif status == "started" or status == "queued":
        return 0
    elif status == "processing":
        return 5  # Image processing started
    elif status == "analyzing":
        if step_phase == "advisor_preparation":
            return 10  # Advisors prepared
        elif step_phase == "advisor_analysis" and total_advisors > 0:
            # Base progress for advisor analysis: 10-90%
            # Calculate based on COMPLETED advisors, not current advisor starting
            advisor_progress_range = 80  # 10% to 90%
            advisor_progress = current_advisor * (advisor_progress_range / total_advisors)
            return 10 + int(advisor_progress)
        else:
            return 10
    elif status == "finalizing":
        return 95  # Almost done
    else:
        return 0
```

### Progress Flow Example (1 advisor)

| Status | Phase | Current Advisor | Total Advisors | Percentage | Explanation |
|--------|-------|----------------|----------------|------------|-------------|
| `queued` | - | 0 | 1 | **0%** | Job queued |
| `processing` | `image_processing` | 0 | 1 | **5%** | Image processing started |
| `analyzing` | `advisor_preparation` | 0 | 1 | **10%** | Advisors prepared |
| `analyzing` | `advisor_analysis` | 1 | 1 | **90%** | Advisor analysis (10 + 80 = 90%) |
| `finalizing` | `finalizing` | 1 | 1 | **95%** | Finalizing results |
| `done` | `done` | 1 | 1 | **100%** | Complete |

### Progress Flow Example (3 advisors)

| Status | Phase | Current Advisor | Total Advisors | Percentage | Explanation |
|--------|-------|----------------|----------------|------------|-------------|
| `queued` | - | 0 | 3 | **0%** | Job queued |
| `processing` | `image_processing` | 0 | 3 | **5%** | Image processing |
| `analyzing` | `advisor_preparation` | 0 | 3 | **10%** | Advisors prepared |
| `analyzing` | `advisor_analysis` | 1 | 3 | **36%** | Advisor 1 (10 + 26.67 = 36%) |
| `analyzing` | `advisor_analysis` | 2 | 3 | **63%** | Advisor 2 (10 + 53.33 = 63%) |
| `analyzing` | `advisor_analysis` | 3 | 3 | **90%** | Advisor 3 (10 + 80 = 90%) |
| `finalizing` | `finalizing` | 3 | 3 | **95%** | Finalizing |
| `done` | `done` | 3 | 3 | **100%** | Complete |

### Key Points

- **Progress never goes backward** - The system uses `max(new_progress, last_progress)` to prevent regression
- **Advisor progress is based on COMPLETED advisors** - `current_advisor` represents advisors that have started/finished
- **80% of progress (10-90%) is allocated to advisor analysis** - This is the main work
- **Progress is recalculated automatically** when status, step_phase, or advisor counts change

### Where It's Updated

Progress is automatically calculated in `update_job_status()` (line 245) whenever:
- Status changes
- Step phase changes  
- Current advisor changes
- Total advisors changes

It's **NOT** recalculated when only `llm_thinking` is updated (to prevent progress jumps during thinking updates).

---

## 2. Status Messages (current_step)

### Location
Status messages come from two sources:
1. **`current_step`** - Set in `job_service_v2.3.py` via `update_job_status()`
2. **`llm_thinking`** - Set from `ai_advisor_service.py` via `send_thinking_update()`

### Current Step Messages

These are set in `mondrian/job_service_v2.3.py` in the `process_job()` function:

#### Image Processing Phase
```python
update_job_status(job_id, status="processing", current_step="Processing image", step_phase="image_processing")
```
- **Message**: "Processing image"
- **When**: Image optimization/resizing

#### Advisor Preparation Phase
```python
update_job_status(job_id, status="analyzing", current_step="Starting advisor analysis", step_phase="advisor_preparation")
```
- **Message**: "Starting advisor analysis"
- **When**: Before processing advisors

#### Advisor Analysis Phase
```python
adjective = random.choice(['Conjuring', 'Summoning', 'Beckoning', 'Invoking', 'Calling forth', 'Manifesting'])
status_message = f"{adjective} {adv.capitalize()}"
update_job_status(job_id, current_step=status_message, current_advisor=i, total_advisors=total_advisors_count, step_phase="advisor_analysis")
```
- **Messages**: 
  - "Conjuring Ansel"
  - "Summoning Ansel"
  - "Beckoning Ansel"
  - "Invoking Ansel"
  - "Calling forth Ansel"
  - "Manifesting Ansel"
- **When**: Starting each advisor analysis (randomly selected adjective)

#### Finalizing Phase
```python
update_job_status(job_id, status="finalizing", current_step="Finalizing analysis results", step_phase="finalizing")
```
- **Message**: "Finalizing analysis results"
- **When**: Combining advisor results and writing output

#### Completion
```python
update_job_status(job_id, status="done", current_step="Completed", step_phase="done")
```
- **Message**: "Completed"
- **When**: Job finished successfully

### LLM Thinking Messages

These are sent from `mondrian/ai_advisor_service.py` via the `send_thinking_update()` function and update the `llm_thinking` field (which also appears as `current_step` in some contexts).

#### Model Loading
```python
send_thinking_update(job_service_url, job_id, "Loading MLX model...")
```
- **Message**: "Loading MLX model..."
- **When**: MLX model is being loaded (first time or after cache clear)
- **Location**: `ai_advisor_service.py` line 456

#### Analysis Generation
```python
send_thinking_update(job_service_url, job_id, "Generating analysis...")
```
- **Message**: "Generating analysis..."
- **When**: Model is generating the analysis response
- **Location**: `ai_advisor_service.py` line 462

#### Analysis Complete
```python
send_thinking_update(job_service_url, job_id, "MLX analysis complete")
```
- **Message**: "MLX analysis complete"
- **When**: Model has finished generating
- **Location**: `ai_advisor_service.py` line 524

#### RAG-Specific Messages (if RAG enabled)
```python
send_thinking_update(job_service_url, job_id, "Detecting photographic techniques...")
send_thinking_update(job_service_url, job_id, "Finding similar master works by technique...")
send_thinking_update(job_service_url, job_id, f"Reviewing your image with {advisor_name}")
send_thinking_update(job_service_url, job_id, "Finding dimensionally similar master works...")
```
- **Messages**: Various RAG-related status updates
- **When**: During RAG context retrieval
- **Location**: `ai_advisor_service.py` lines 641, 650, 671, 715

### How Thinking Updates Work

1. **AI Advisor Service** calls `send_thinking_update(job_service_url, job_id, "Loading MLX model...")`
2. This sends a PUT request to `/job/<job_id>/thinking` endpoint
3. **Job Service** receives it and updates the `llm_thinking` field in the database
4. The thinking text is also copied to `current_step` for display (line 1965 in job_service_v2.3.py)
5. SSE clients receive the update via the streaming mechanism

### Thinking Endpoint

```python
@app.route("/job/<job_id>/thinking", methods=["PUT"])
def update_thinking(job_id):
    """Update thinking/status message from AI service"""
    # Updates llm_thinking field
    # Also updates current_step for immediate display
```

---

## Summary

### Progress Percentage
- **Calculated automatically** based on status, phase, and advisor progress
- **Range**: 0-100%
- **Formula**: 
  - 0%: Queued/started/error
  - 5%: Image processing
  - 10%: Advisor preparation
  - 10-90%: Advisor analysis (distributed across advisors)
  - 95%: Finalizing
  - 100%: Done

### Status Messages
- **`current_step`**: Set by job service during main workflow phases
- **`llm_thinking`**: Set by AI advisor service during model operations
- **Both** are sent to clients via Server-Sent Events (SSE)
- **Display**: iOS app shows `current_step` as the main status, `llm_thinking` as thinking text

### Key Files
- **Progress calculation**: `mondrian/job_service_v2.3.py` lines 219-243
- **Status updates**: `mondrian/job_service_v2.3.py` lines 245-325 (update_job_status function)
- **Thinking updates**: `mondrian/ai_advisor_service.py` lines 402-426 (send_thinking_update function)
- **Thinking endpoint**: `mondrian/job_service_v2.3.py` lines 1931-1965

---

**Last Updated**: 2025-01-09





