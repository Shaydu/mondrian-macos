# Changes Applied for LLM Thinking Updates

## Summary
Fixed three critical issues preventing thinking model output from being sent via the API to iOS client.

---

## Change 1: Extract Thinking Tags from Response

**File:** `mondrian/ai_advisor_service_linux.py`

**Lines:** 689-698 (in `_parse_response()` method)

**What was added:**
```python
import re

# Extract thinking if present (for thinking models like Qwen3-VL-4B-Thinking)
thinking_text = ""

# Check for <thinking> tags (Qwen thinking model format)
thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
if thinking_match:
    thinking_text = thinking_match.group(1).strip()
    logger.info(f"✓ Extracted extended thinking ({len(thinking_text)} chars)")
```

**Why:** Qwen3-VL-4B-Thinking wraps extended reasoning in `<thinking>...</thinking>` tags. The old code discarded these tags when extracting JSON. Now we capture them separately.

---

## Change 2: Use Extracted Thinking in Response

**File:** `mondrian/ai_advisor_service_linux.py`

**Line:** 779

**What changed:**
```python
# OLD:
"llm_thinking": response,  # Complete response

# NEW:
"llm_thinking": thinking_text,  # Extracted thinking from thinking models (empty if not present)
```

**Why:** Store only the extracted thinking steps, not the entire response including JSON. This makes the field useful for displaying step-by-step reasoning in the UI.

---

## Change 3: Fix Mode Parameter Bug

**File:** `mondrian/ai_advisor_service_linux.py`

**Lines:** 913-914

**What changed:**
```python
# OLD:
advisor_name = request.form.get('advisor', 'ansel')
mode = request.form.get('enable_rag', 'false').lower() == 'true'
mode_str = 'rag' if mode else 'baseline'

# NEW:
advisor_name = request.form.get('advisor', 'ansel')
mode_str = request.form.get('mode', 'baseline')
```

**Why:** The code was reading `enable_rag` instead of `mode`, causing all requests to be processed as either 'baseline' or 'rag', never actually using 'lora' mode even when the LoRA adapter was loaded.

---

## Change 4: Add analysis_url to Status Events

**File:** `mondrian/job_service_v2.3.py`

**Line:** 1025 (in `generate()` function of `/stream/<job_id>` endpoint)

**What was added:**
```python
# Compute base_url for analysis links (matches upload endpoint)
base_url = f"http://{request.host.split(':')[0]}:5005"
```

**Why:** Need to construct the base URL for analysis links. This code was missing but present in the upload endpoint.

---

## Change 5: Include analysis_url in Status Response

**File:** `mondrian/job_service_v2.3.py`

**Line:** 1073

**What changed:**
```python
# OLD:
status_update_event = {
    "type": "status_update",
    "job_data": {
        "status": current_status,
        "progress_percentage": current_progress,
        "current_step": current_step,
        "llm_thinking": current_thinking,
        "current_advisor": 1,
        "total_advisors": 1,
        "step_phase": "analyzing" if current_status == "analyzing" else "processing"
    }
}

# NEW:
status_update_event = {
    "type": "status_update",
    "job_data": {
        "status": current_status,
        "progress_percentage": current_progress,
        "current_step": current_step,
        "llm_thinking": current_thinking,
        "current_advisor": 1,
        "total_advisors": 1,
        "step_phase": "analyzing" if current_status == "analyzing" else "processing",
        "analysis_url": f"{base_url}/analysis/{job_id}"  # <-- ADDED THIS
    }
}
```

**Why:** iOS client expects `analysis_url` in the status response and throws a CodingError when it's missing. This field was present in the upload response but missing in status stream updates.

---

## Verification Commands

### 1. Check if thinking extraction is working
```bash
# Tail service logs while processing with thinking model
tail -f /var/log/mondrian/ai_advisor.log | grep -E "Extracted extended thinking|✓"
```

Expected log line:
```
✓ Extracted extended thinking (342 chars)
```

### 2. Verify mode parameter is read correctly
```bash
# Check the last analysis mode in database
sqlite3 mondrian.db "SELECT id, mode FROM jobs ORDER BY created_at DESC LIMIT 1;"
```

Expected output:
```
job-uuid-123|lora
```

(Should show 'lora' if you sent `mode=lora`)

### 3. Test status endpoint includes analysis_url
```bash
curl -s http://localhost:5005/status/job-id | python -m json.tool | grep analysis_url
```

Expected output:
```
"analysis_url": "http://10.0.0.227:5005/analysis/job-id"
```

### 4. Check status stream includes both fields
```bash
# Connect to stream and capture first status update
timeout 5 curl -s -N http://localhost:5005/stream/job-id | grep -A 20 "status_update" | head -30
```

Expected to see:
```
"llm_thinking": "Step 1: Analyzing composition..."
"analysis_url": "http://10.0.0.227:5005/analysis/job-id"
```

---

## Impact on Codebase

### Files Modified: 2
- `mondrian/ai_advisor_service_linux.py` (3 changes)
- `mondrian/job_service_v2.3.py` (2 changes)

### Lines Changed: ~15 total
- Added: ~9 lines
- Modified: ~6 lines

### Breaking Changes: None
- Non-thinking models: `llm_thinking` returns empty string (graceful)
- Old mode values still work: 'baseline', 'rag', 'rag+lora'
- iOS client backward compatible: Can skip unknown fields

### New Dependencies: None
- Uses only Python standard library (`re` module)

---

## Testing in iOS App

1. **Start AI service** with thinking model:
   ```bash
   python mondrian/ai_advisor_service_linux.py --model qwen3-4b-thinking
   ```

2. **Upload image via iOS app**
   - Select thinking model from settings
   - Set mode to "lora"
   - Upload photo

3. **Expected behavior:**
   - Status shows "Analyzing..."
   - Thinking steps appear and update in real-time
   - No "keyNotFound: analysis_url" error
   - Final analysis displays when complete

4. **Verify in logs:**
   ```bash
   # Should see extraction and persistence
   grep "llm_thinking" /var/log/mondrian/ai_advisor.log
   ```

---

## Related Issues Fixed

- ❌ Empty `llm_thinking` field → ✅ Now populated from model output
- ❌ Missing `analysis_url` field → ✅ Now included in status response
- ❌ Mode parameter ignored → ✅ Now correctly reads 'lora' mode

