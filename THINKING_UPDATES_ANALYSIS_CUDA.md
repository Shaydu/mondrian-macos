# LLM Thinking Updates Issue Analysis (CUDA RTX3060 Setup)

## Problem Summary

With the thinking model (Qwen3-VL-4B-Thinking) and LoRA adapter running on CUDA/RTX3060, the API is not sending `llm_thinking` updates to clients. The iOS app reports empty `llm_thinking` field in status responses, and shows a missing `analysis_url` field causing decode errors.

**Current Status from iOS:**
```
"llm_thinking": "",
"analysis_url": missing (CodingError)
```

---

## Root Causes Identified

### 1. **Thinking Field Set to Complete Response (Not Extracted Thinking)**
**File:** `/home/doo/dev/mondrian-macos/mondrian/ai_advisor_service_linux.py:768`

```python
"llm_thinking": response,  # Complete response (should be extracted thinking)
```

**Problem:**
- The code stores the **entire LLM response** as `llm_thinking`
- For Qwen3-VL-4B-Thinking model, extended thinking is embedded in the response but NOT extracted
- Qwen3's thinking format includes `<thinking>...</thinking>` tags that need to be parsed
- Currently, the JSON extraction (lines 699-730) finds only the JSON payload, discarding the thinking tags

**Expected behavior for thinking model:**
```
Response format:
<thinking>
Step 1: Analyze composition...
Step 2: Consider lighting...
Step 3: Evaluate focus...
</thinking>
{
  "image_description": "...",
  "dimensions": [...]
}
```

**Current behavior:**
- Only the JSON part is extracted and stored
- Thinking tags are lost during parsing
- `llm_thinking` field gets the full response string, but later gets cleared

---

### 2. **Thinking Field Cleared Before Sending to Client**
**File:** `/home/doo/dev/mondrian-macos/mondrian/job_service_v2.3.py:1066`

```python
"job_data": {
    "status": current_status,
    "progress_percentage": current_progress,
    "current_step": current_step,
    "llm_thinking": current_thinking,  # Fetched from database (likely empty)
    ...
}
```

**Problem:**
- The thinking is fetched from the database after processing
- Database stores the response after JSON extraction (only JSON, no thinking tags)
- By the time iOS polls for updates, `llm_thinking` field is empty or contains full response

**Database Update (line 1358):**
```python
UPDATE jobs SET ...
    llm_thinking = ?
    ...
WHERE id = ?
```

The value stored is whatever `analysis_data.get('llm_thinking')` returns from ai_advisor_service.

---

### 3. **Missing `analysis_url` Field in Status Response**
**File:** `/home/doo/dev/mondrian-macos/mondrian/job_service_v2.3.py:576`

```python
"analysis_url": f"{base_url}/analysis/{job_id}"
```

**Problem:**
- The upload response includes `analysis_url` (line 576)
- But the **status response** (lines 1049-1072) doesn't include it
- iOS client expects this field based on error: `keyNotFound(CodingKeys(stringValue: "analysis_url"))`

**Status Update Event (lines 1066-1068):**
```python
status_update_event = {
    "type": "status_update",
    "job_data": {
        "status": current_status,
        "llm_thinking": current_thinking,
        # Missing: "analysis_url"
    }
}
```

---

### 4. **Mode Parameter Bug (Secondary Issue)**
**File:** `/home/doo/dev/mondrian-macos/mondrian/ai_advisor_service_linux.py:902-904`

```python
# WRONG - reads enable_rag instead of mode
mode = request.form.get('enable_rag', 'false').lower() == 'true'
mode_str = 'rag' if mode else 'baseline'

# Should be:
mode = request.form.get('mode', 'baseline')
mode_str = mode
```

**Problem:**
- Mode is always converted to either 'rag' or 'baseline'
- Never actually uses 'lora' mode
- LoRA adapter is loaded in code but mode parameter is ignored

---

## How Qwen Thinking Model Works (on CUDA)

### Model Configuration
**File:** `model_config.json`

```json
"qwen3-4b-thinking": {
  "name": "Qwen3-VL-4B-Thinking",
  "model_id": "Qwen/Qwen3-VL-4B-Thinking",
  "adapter": "./adapters/ansel_qwen3_4b_thinking",
  "reasoning": true,
  "tokens_per_sec": "15-25 (BF16)"
}
```

### Current Inference Flow (ai_advisor_service_linux.py:302-320)

1. **Prepare inputs** (lines 283-294): Image + text → tokenized
2. **Move to CUDA** (lines 297-298): Send to GPU
3. **Generate** (lines 303-311): Model produces extended thinking + JSON
4. **Decode** (lines 314-320): Convert token IDs back to text
5. **Parse** (lines 699-730): Extract JSON only, discard thinking tags
6. **Store** (line 768): Save full response as `llm_thinking`

### What We're Missing

The Qwen3-VL-4B-Thinking model produces output like:

```
<thinking>
The photograph shows a landscape with mountains in the background.
The composition uses the rule of thirds effectively. The lighting
appears to be golden hour, creating warm tones. Let me analyze
each dimension...
</thinking>
{
  "image_description": "A mountain landscape photo...",
  "dimensions": [...]
}
```

**Current code (lines 699-730):**
- Finds first `{` and last `}`
- Extracts JSON between them
- **Discards everything before first `{`** (the thinking tags)

---

## Why LoRA + Thinking Doesn't Work Currently

### Adapter Loading (ai_advisor_service_linux.py:210-251)
✅ **This works correctly:**
```python
self.model = PeftModel.from_pretrained(
    self.model,
    str(adapter_path),
    offload_dir=offload_dir  # Temporary offload for RTX 3060 memory
)
```

### Model Inference (ai_advisor_service_linux.py:302-311)
✅ **This works:**
- Model is loaded with adapter
- Inference produces extended thinking in response
- Qwen3-VL-4B-Thinking has reasoning=true

### Problem: Thinking Extraction (ai_advisor_service_linux.py:699-730)
❌ **This doesn't work:**
- Code only looks for JSON (lines 700-701)
- Doesn't extract `<thinking>` tags
- Full response includes thinking but it's not separated/stored properly
- iOS sees empty `llm_thinking` field

### Mode Bug (ai_advisor_service_linux.py:902-904)
❌ **This doesn't work:**
- Mode is hardcoded to 'baseline' or 'rag'
- Never actually stores mode='lora' in database
- LoRA adapter loads, but status shows wrong mode

---

## Fix Required

### Priority 1: Extract Thinking from Model Response
**File:** `ai_advisor_service_linux.py`

**Location:** `_parse_response()` method, around line 686

**Change:**
```python
def _parse_response(self, response: str, advisor: str, mode: str, prompt: str) -> Dict[str, Any]:
    """Parse model response into structured format with iOS-compatible HTML"""

    # Extract thinking if present (for thinking models)
    thinking_text = ""
    json_text = ""

    # Check for <thinking> tags (Qwen thinking model format)
    thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
    if thinking_match:
        thinking_text = thinking_match.group(1).strip()
        logger.info(f"✓ Extracted extended thinking ({len(thinking_text)} chars)")

    # Find JSON (after or alongside thinking)
    start_idx = response.find('{')
    end_idx = response.rfind('}') + 1

    if start_idx != -1 and end_idx > start_idx:
        json_text = response[start_idx:end_idx]

    # ... rest of parsing ...

    result = {
        # ... other fields ...
        "full_response": response,        # Complete response with thinking tags
        "llm_thinking": thinking_text,    # EXTRACTED thinking (or empty if none)
        "analysis": analysis_data,        # JSON only
        # ... rest ...
    }
```

### Priority 2: Fix Mode Parameter Bug
**File:** `ai_advisor_service_linux.py:902-904`

**Change:**
```python
# CURRENT (WRONG):
mode = request.form.get('enable_rag', 'false').lower() == 'true'
mode_str = 'rag' if mode else 'baseline'

# SHOULD BE:
mode_str = request.form.get('mode', 'baseline')
```

### Priority 3: Add `analysis_url` to Status Response
**File:** `job_service_v2.3.py:1049-1072`

**Change:**
```python
status_update_event = {
    "type": "status_update",
    "job_id": job_id,
    "timestamp": datetime.now().timestamp(),
    "job_data": {
        "status": current_status,
        "progress_percentage": current_progress,
        "current_step": current_step,
        "llm_thinking": current_thinking,
        "current_advisor": 1,
        "total_advisors": 1,
        "step_phase": "analyzing" if current_status == "analyzing" else "processing",
        "analysis_url": f"{base_url}/analysis/{job_id}"  # ADD THIS
    }
}
```

### Priority 4: Ensure Thinking Persists in Database
**File:** `job_service_v2.3.py:1336-1366`

The thinking should already flow through:
```python
thinking = analysis_data.get('llm_thinking', '')  # Now has extracted thinking
conn.execute("""
    UPDATE jobs SET ... llm_thinking = ? ...
""", (..., thinking, ...))
```

Once Priority 1 is fixed, this should work correctly.

---

## Testing the Fix

### 1. Verify Thinking Extraction
Start service with thinking model:
```bash
python ai_advisor_service_linux.py \
    --model qwen3-4b-thinking \
    --adapter ./adapters/ansel_qwen3_4b_thinking
```

Upload image and check logs:
```
✓ Extracted extended thinking (342 chars)
```

### 2. Check Status Response
```bash
curl http://localhost:5005/status/<job_id>
```

Verify response includes:
- `llm_thinking`: (non-empty string with thinking)
- `analysis_url`: (valid URL)
- `mode`: 'lora' (not 'baseline' or 'rag')

### 3. iOS Client Test
Upload via iOS app, watch status polling:
- reportState should show "Analyzing..." → "Generating insights" (via thinking update)
- llm_thinking field should update with visible thinking
- No CodingError about missing analysis_url

---

## Summary of Changes Needed

| Issue | File | Lines | Fix Type |
|-------|------|-------|----------|
| Thinking not extracted | ai_advisor_service_linux.py | 686-781 | Add regex extraction for `<thinking>` tags |
| Mode parameter ignored | ai_advisor_service_linux.py | 902-904 | Read 'mode' form param instead of 'enable_rag' |
| Missing analysis_url | job_service_v2.3.py | 1049-1072 | Add field to status_update_event |
| Thinking not persisted | job_service_v2.3.py | 1336-1366 | Already works once #1 is fixed |

---

## CUDA-Specific Considerations

Your RTX 3060 setup (6GB VRAM) runs:
- Qwen3-VL-4B-Thinking: ~3.5GB with 4-bit quantization + LoRA
- Sufficient for inference with offload dir strategy

The CUDA setup is working correctly for model loading/inference. The issue is purely in how the thinking output is being processed and transmitted to the client.

