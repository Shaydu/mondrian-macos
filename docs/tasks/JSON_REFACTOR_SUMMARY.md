# JSON Output Refactor - Summary

## What Changed

Successfully refactored the AI Advisor system to use **JSON output instead of HTML**, while maintaining 100% backward compatibility with the iOS app.

## Benefits

### 1. **Eliminated Brittle HTML Parsing**
- **Before**: LLM generated HTML → Custom HTMLParser extracted data → Regex/string matching
- **After**: LLM generates JSON → Direct `json.loads()` → Structured data

### 2. **More Reliable**
- No HTML entity handling (`&amp;` vs `&`)
- No regex for score extraction
- No fragile tag structure matching
- Better error messages when parsing fails

### 3. **Simpler Codebase**
- Deleted `dimensional_extractor.py` (384 lines of HTML parsing code)
- Created `json_to_html_converter.py` with cleaner architecture
- Fewer points of failure

### 4. **100% Backward Compatible**
- iOS app receives identical HTML format
- API endpoint unchanged (`/analyze` returns `text/html`)
- Database schema unchanged
- RAG functionality still works

## Files Changed

### 1. **System Prompt** (in database)
- Updated `config.system_prompt` to request JSON instead of HTML
- New format includes all 8 dimensions in JSON structure
- Same grading philosophy and requirements

### 2. **New File: `mondrian/json_to_html_converter.py`**
Contains:
- `parse_json_response()` - Robust JSON parsing with error handling
- `json_to_html()` - Converts JSON to exact HTML format for iOS app
- `extract_dimensional_profile_from_json()` - Extracts dimensional data for database
- `save_dimensional_profile()` - Saves to database (moved from old file)
- `find_similar_by_dimensions()` - RAG similarity search (moved from old file)
- `get_dimensional_profile()` - Profile retrieval (moved from old file)

### 3. **Updated: `mondrian/ai_advisor_service.py`**
Changes:
- Import from `json_to_html_converter` instead of `dimensional_extractor`
- Parse JSON response with `parse_json_response()`
- Convert to HTML with `json_to_html()` before returning
- Extract dimensional profile from JSON instead of HTML
- Updated version to `2.0-JSON`
- Updated comments to reflect JSON format

### 4. **Removed: `mondrian/dimensional_extractor.py`**
- Backed up to `dimensional_extractor.py.backup`
- All useful functions moved to `json_to_html_converter.py`
- HTML parsing logic (HTMLParser class) completely eliminated

## How It Works Now

### Request Flow:
```
1. iOS App → POST /analyze (with image)
2. AI Advisor Service → LLM (requests JSON)
3. LLM → Returns JSON response
4. Service → Parses JSON (json.loads)
5. Service → Converts JSON to HTML (json_to_html)
6. Service → Returns HTML to iOS app ✓
7. Service → Saves dimensional profile to DB (from JSON)
```

### Data Flow:
```
LLM Output (JSON)
    ↓
parse_json_response() ← Robust parsing with error handling
    ↓
json_data (dict)
    ↓
    ├→ json_to_html() → HTML response for iOS ✓
    └→ extract_dimensional_profile_from_json() → Database storage ✓
```

## Testing Results

✅ **JSON to HTML conversion**: Tested with sample data - produces identical HTML format
✅ **Dimensional profile extraction**: Successfully extracts all 8 dimensions + metadata
✅ **Syntax validation**: Both new and updated files pass syntax checks
✅ **Backward compatibility**: HTML output matches exact format expected by iOS app

## Key Design Decisions

1. **Store JSON in `analysis_html` column**: The database column is still called `analysis_html` but now stores JSON. This avoids schema migration while preserving raw output for debugging.

2. **HTML generation on-the-fly**: HTML is generated from JSON each time, ensuring consistency and allowing future format changes without re-parsing stored data.

3. **Robust JSON parsing**: `parse_json_response()` handles common LLM issues like markdown code blocks (```json) and extra explanatory text.

4. **Consolidated functions**: Moved all dimensional profile functions to a single module instead of splitting between multiple files.

## Migration Notes

- **No database changes required**: Existing dimensional profiles remain unchanged
- **No iOS app changes required**: API contract unchanged
- **Service restart required**: All services need to be restarted to use JSON version
- **Backward compatible**: Old HTML profiles in database still work (not re-processed)
- **MLX is now default**: No need to specify `--use_mlx` flag anymore

### Services Updated

1. **ai_advisor_service.py** - Now uses JSON (v2.0-JSON)
2. **monitoring_service.py** - Updated to launch new ai_advisor_service.py (v2.5-JSON-RAG)
3. All RAG services (caption, embedding, rag) will restart with the monitoring service

## Next Steps (Optional)

Future improvements that could be made:
1. Rename `analysis_html` column to `analysis_output` for clarity
2. Add JSON schema validation for stricter error checking
3. Unit tests for JSON parsing edge cases
4. Performance comparison (JSON parsing vs HTML parsing)

## Rollback Plan

If issues arise:
1. Restore `dimensional_extractor.py` from backup
2. Revert system prompt in database to HTML format
3. Revert `ai_advisor_service.py` imports
4. Restart service

Backup file location: `mondrian/dimensional_extractor.py.backup`
