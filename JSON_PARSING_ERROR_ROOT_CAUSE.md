# JSON Parsing Error - Root Cause Analysis

## Error Summary
```
[2026-01-27 19:04:17] [ERROR] ❌ JSON parsing failed: Expecting ',' delimiter: line 26 column 23 (char 1194) at position 1194
[2026-01-27 19:04:17] [WARNING]    Response length: 1505, Error context: 
  "composition": 9.0,
  "lightning": 9.,
  "focus_shaarpness": 9..0,
```

## Root Causes Identified

### 1. **Malformed Float Values** (Primary Issue)
The LLM is generating invalid JSON with incomplete float literals:
- `"lightning": 9.` - Missing fractional digits after decimal point (should be `9.0`)
- `"focus_shaarpness": 9..0` - Double decimal point (invalid syntax)

### 2. **Field Name Typos**
- `"focus_shaarpness"` should be `"focus_sharpness"` (extra 'a')
- Expected field names are: `composition`, `lighting`, `focus_sharpness`, `color_harmony`, etc.

### 3. **Why This Happens**
- The model is **cutting off/truncating** decimal number generation mid-output
- This suggests:
  - Token limit being reached during generation
  - Model instruction/prompt issues causing malformed output
  - Potential LoRA adapter corruption or mismatch
  - Sampling temperature may be too high, causing unstable outputs

## Current Sanitization in Code

[ai_advisor_service_linux.py](ai_advisor_service_linux.py#L1420-L1428) has some sanitization:
```python
# SANITIZE: Replace Unicode quotes and special characters with ASCII equivalents
json_str = json_str.replace('"', '"').replace('"', '"')  # Unicode quotes
json_str = json_str.replace(''', "'").replace(''', "'")  # Unicode apostrophes  
json_str = json_str.replace('–', '-').replace('—', '-')  # Dashes
json_str = json_str.replace('…', '...')  # Ellipsis
```

**But this does NOT handle:**
- Incomplete float literals (e.g., `9.`)
- Double decimal points (e.g., `9..0`)
- Field name typos

## Solutions

### Option 1: Add JSON Repair Logic (Short-term)
Add regex-based repair before parsing to fix common float issues:

```python
# Repair malformed float values
import re
# Fix incomplete floats: "9." -> "9.0"
json_str = re.sub(r':\s*(\d+)\.$', r': \1.0', json_str)
# Fix double decimals: "9..0" -> "9.0"
json_str = re.sub(r':\s*(\d+)\.\.(\d+)', r': \1.\2', json_str)
# Fix typos in score field names
json_str = json_str.replace('shaarpness', 'sharpness')
```

### Option 2: Investigate Model/Prompt Issues (Root Solution)
1. **Check LoRA Adapter** - Is the adapter properly trained/merged?
2. **Review System Prompt** - Add explicit format constraints:
   ```
   ALL NUMERIC SCORES MUST BE FORMATTED AS: 1.0, 2.5, 9.0 (never 9., 9.., or 9)
   ```
3. **Check Token Limits** - Ensure model has enough tokens to complete output
4. **Temperature/Sampling** - Reduce temperature for more stable outputs
5. **Model State** - Verify model weights aren't corrupted

### Option 3: Hybrid Approach (Recommended)
1. Add JSON repair logic as a band-aid
2. Monitor frequency of these errors
3. If errors persist, investigate model setup
4. Once fixed, keep repair logic as defensive measure

## Files to Modify

- [mondrian/ai_advisor_service_linux.py](mondrian/ai_advisor_service_linux.py#L1420) - Add JSON repair before parsing

## Impact

- **Severity:** Medium - causes analysis to fail with score=0
- **Frequency:** Appears consistent based on log pattern
- **User Impact:** Invalid analysis responses, poor user experience

## Recommended Actions

1. ✅ **Immediate:** Apply Option 1 (JSON repair) as quick fix
2. 📊 **Follow-up:** Monitor error frequency after fix
3. 🔍 **Investigation:** Check model weights and prompt configuration
4. 🧪 **Testing:** Generate 10+ analyses to verify stability
