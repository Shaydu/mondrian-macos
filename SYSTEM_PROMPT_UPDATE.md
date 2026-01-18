# System Prompt Update Summary

## Changes Made

Updated the system prompt used by the AI Advisor Service to implement:

### 1. **Stricter Scoring Philosophy (3-10 Range)**
- **Previous behavior**: Scores clustered in 7-10 range (inflated scores)
- **New behavior**: 
  - Full 3-10 range with critical judgment
  - Most scores fall in 6-8 range (represents typical work)
  - Scores 9-10 reserved for exceptional excellence only
  - Scores 3-5 used for significant issues
  - Scores below 6 for clear weaknesses or misalignment

### 2. **Advisor Style & Subject Matter Alignment Penalty**
- If image's subject matter or style **drastically differs** from the selected advisor's characteristic work:
  - Apply **SERIOUS PENALTY** (reduce scores by 2-3 points)
  - Flag misalignment in `technical_notes` 
  - Reflect penalties proportionally across relevant dimensions
- Example: A vibrant abstract image scored by Ansel Adams would be penalized for deviating from his black & white landscape focus

## Files Modified

### Core Implementation
- **mondrian/ai_advisor_service_linux.py** - Updated `_get_default_system_prompt()` method
- **init_database.py** - Added system_prompt seeding to initialization script

### Update Utilities
- **quick_update_prompt.py** - Direct SQLite update script (already executed)
- **update_system_prompt.py** - Enhanced version with better error handling

## How to Apply

### For Existing Databases
```bash
python3 quick_update_prompt.py
```

### For New Databases
System prompt will be seeded automatically when running:
```bash
python3 init_database.py
```

## Next Steps

1. **Restart the AI Advisor Service** to load the new prompt
2. **Test with sample images** to verify stricter scoring
3. **Monitor advisor feedback** to ensure penalties are proportional

## Expected Impact

- More realistic score distribution across the 3-10 range
- Penalization of subject/style misalignment encourages appropriate advisor selection
- Improved critical judgment overall with fewer "automatic 8-10" scores
- Better differentiation between good and exceptional work

## Technical Notes

The prompt is stored in the database `config` table with key `system_prompt`. It serves as the system-level instruction for all Qwen vision model inferences. The advisor-specific prompt is appended after this system prompt to provide additional context.
