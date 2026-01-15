# Complete Fix Summary: LORA/RAG Modes Debug

## Issues Found and Fixed

### Issue 1: Missing JSON Response Format Conversion (PRIMARY BUG)
**Files:** `mondrian/strategies/lora.py`, `mondrian/strategies/rag.py`, `mondrian/strategies/rag_lora.py`

**Problem:**
- LORA, RAG, and RAG+LORA modes were completing analysis but producing no summary/detailed output
- Overall grades were showing as "N/A" instead of proper letter grades
- The root cause: strategies were looking for `dimensional_analysis` dict and `overall_grade` fields, but the model outputs `dimensions` array and `overall_score` numeric values
- Only the baseline strategy had the conversion logic; the others were missing it

**Solution:**
- Added dimension array-to-dict conversion: transforms `dimensions` array to `dimensional_analysis` dict keyed by normalized dimension name
- Added numeric-to-letter grade conversion: converts `overall_score` (0-10) to `overall_grade` (A+ through F)
- Added debug logging to help diagnose future issues

**Score to Grade Mapping:**
- 9.5+ → A+
- 9.0+ → A
- 8.5+ → A-
- 8.0+ → B+
- 7.5+ → B
- 7.0+ → B-
- 6.5+ → C+
- 6.0+ → C
- 5.5+ → C-
- 5.0+ → D
- Below 5.0 → F

### Issue 2: Undefined Variable in RAG Strategy (SECONDARY BUG)
**File:** `mondrian/strategies/rag.py`

**Problem:**
- RAG strategy was throwing internal server error (500): `NameError: name 'similar_images' is not defined`
- The variable was referenced in the metadata section but was never defined
- This occurred because RAG retrieval is not fully implemented yet (see TODO comment in code)

**Solution:**
- Removed the undefined reference to `similar_images_count` from the metadata dictionary
- Now only returns `raw_response_length` in metadata

## Files Modified
1. `mondrian/strategies/lora.py` - Added JSON conversion logic
2. `mondrian/strategies/rag.py` - Added JSON conversion logic + fixed undefined variable
3. `mondrian/strategies/rag_lora.py` - Added JSON conversion logic

## Documentation Created
- `LORA_MODE_FIX.md` - Detailed explanation of primary fix
- `RAG_STRATEGY_FIX.md` - Details of secondary fix
- `START_SERVICES_GUIDE.md` - Complete guide on starting services with different modes

## Testing

### Quick Test
```bash
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode lora
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode rag
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode baseline
```

### Expected Results After Fix
- ✅ LORA mode: Generates HTML with proper grades and recommendations
- ✅ RAG mode: Generates HTML without 500 error
- ✅ Baseline mode: Continues to work as before
- ✅ Summary endpoint: Returns top 3 recommendations with scores
- ✅ Detailed endpoint: Returns full analysis HTML

## How to Start Services

### LORA Mode (Fine-tuned)
```bash
cd mondrian
python3 ai_advisor_service.py --port 5100 --model_mode fine_tuned --lora_path ./adapters/ansel &
python3 job_service_v2.3.py --port 5005 &
```

### Baseline Mode (Default)
```bash
cd mondrian
python3 start_services.py
```

### RAG Mode (Base model + similar images)
```bash
cd mondrian
python3 start_services.py
```

Then test with `--mode rag` flag in test script.

## Validation
All modified files have been validated:
- ✅ Python syntax is correct
- ✅ No import errors
- ✅ JSON conversion logic works correctly
- ✅ Grade conversion mapping is complete

## Next Steps
If you experience any issues:
1. Check the AI Advisor Service logs: `/Users/shaydu/dev/mondrian-macos/logs/ai_advisor_service_*.log`
2. Look for debug output with `[LORA DEBUG]`, `[RAG DEBUG]`, or `[STRATEGY ERROR]` prefixes
3. Verify the adapter exists: `ls -la adapters/ansel/adapters.safetensors`
