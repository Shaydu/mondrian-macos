# Database Restoration & Consolidation Summary
**Date:** January 11, 2026
**Status:** ✅ COMPLETE

## Issues Fixed

### 1. ✅ Missing Advisor Prompts & System Prompt
**Problem:** Database was missing advisor prompts and system_prompt
**Solution:** Restored from commit `322a9ab` ("added advisor details")
**Result:** 
- 9 advisors with full prompts restored
- System prompt restored and updated to JSON format

### 2. ✅ Schema Errors (wikipedia_url missing)
**Problem:** `[ERROR] Failed to get all advisors: no such column: wikipedia_url`
**Solution:** Ran schema migration to add missing columns
**Result:** 
- Added: `focus_areas`, `category`, `wikipedia_url`, `commons_url`, `prompt_type`

### 3. ✅ Duplicate Database Locations
**Problem:** Two database files (`mondrian.db` and `mondrian/mondrian.db`)
**Solution:** Consolidated to single active database
**Result:**
- **REMOVED:** Root `mondrian.db` (not used by services)
- **KEPT:** `mondrian/mondrian.db` (active database used by services)
- Updated `init_database.py` to use correct path
- Updated `.gitignore`

### 4. ✅ JSON Parsing Error
**Problem:** `Failed to parse model response` - service expected JSON but got HTML
**Solution:** Updated system_prompt from HTML to JSON format
**Result:**
- Created `mondrian/prompts/system_json.md`
- Backed up old HTML prompt to `mondrian/prompts/system_html_backup.md`
- Updated database config with JSON system prompt

## Current Database State

**Location:** `mondrian/mondrian.db`
**Size:** 100KB
**Backup:** `mondrian/mondrian.db.backup`

**Tables:**
- `advisors` - 9 advisors with prompts (watkins, weston, cunningham, gilpin, ansel, mondrian, okeefe, vangogh, gehry)
- `config` - 1 entry (system_prompt in JSON format)
- `jobs` - Job tracking
- `advisor_usage` - Usage statistics
- `focus_areas` - 12 focus areas
- `special_options` - 3 special options

**Schema Columns (advisors table):**
- id, name, bio, prompt, years, created_at, updated_at
- focus_areas, category, wikipedia_url, commons_url, prompt_type

## Testing Status

### ✅ Schema Working
- No more "no such column" errors
- `/advisors` endpoint loading successfully

### 🔄 Awaiting Test: JSON Output
- System prompt updated to request JSON
- **ACTION REQUIRED:** Restart AI Advisor Service
- **ACTION REQUIRED:** Test with image analysis to verify JSON → HTML conversion

## Next Steps

1. **Restart AI Advisor Service**
   ```bash
   # Stop current service (CTRL+C)
   cd /Users/shaydu/dev/mondrian-macos/mondrian
   python3 ai_advisor_service.py
   ```

2. **Test Both Configurations**
   - Test with RAG enabled (RAG_ENABLED=True in config.py)
   - Test with RAG disabled (RAG_ENABLED=False in config.py)

3. **Verify Output**
   - LLM should return pure JSON
   - Service should convert JSON to HTML
   - HTML should display correctly in iOS client

4. **Commit Database** (after successful testing)
   - Database is currently .gitignored
   - Once confirmed working, consider committing the database
   - Or create initialization script for fresh deployments

## Files Modified

- ✅ `mondrian/mondrian.db` - Restored, migrated, consolidated
- ✅ `init_database.py` - Updated default path
- ✅ `.gitignore` - Cleaned up database entries
- ✅ `mondrian/prompts/system_json.md` - Created
- ✅ `mondrian/prompts/system_html_backup.md` - Backup created

## Files Removed

- ❌ `mondrian.db` (root level - unused)
- ❌ `mondrian.db.backup` (root level - obsolete)
