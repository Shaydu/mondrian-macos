# Jobs Viewer - Mode Column Addition

## Summary

Added a **Mode column** to the HTML jobs viewer endpoint (`http://localhost:5005/jobs?format=html`) to display the analysis mode used for each job.

## Changes Made (in mondrian/job_service_v2.3.py)

### 1. **Database Query Enhancement**
- Added `mode` column to SELECT query
- Now fetches: `id, filename, advisor, status, created_at, enable_rag, mode, critical_recommendations`

### 2. **Mode Counting in Stats**
- Updated stats calculation to count jobs by mode:
  - `baseline` count
  - `rag` count  
  - `lora` count
- Changed stats display from "RAG Enabled / Baseline" to individual mode counts

### 3. **CSS Styling for Mode Badges**
Added color-coded badge styles:
```css
.mode-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}
.mode-baseline { background: #3d5a80; color: #fff; }    /* Blue */
.mode-rag { background: #5a4a3d; color: #fff; }         /* Brown */
.mode-lora { background: #3d5a3d; color: #fff; }        /* Green */
.mode-rag-lora { background: #5a3d5a; color: #fff; }    /* Purple */
.mode-ab-test { background: #6a4a3d; color: #fff; }     /* Dark Brown */
```

### 4. **Table Structure Updates**

**New Headers:**
```
Job ID | Filename | Advisor | Status | Mode | RAG | Created | Actions
```

**Mode Display Logic:**
- Extracts mode from database: `baseline`, `rag`, `lora`, etc.
- Creates badge with appropriate color class
- Displays uppercase text: `BASELINE`, `RAG`, `LORA`

**RAG Column Separation:**
- Now shows `Enabled` or `Disabled` instead of mode name
- Separated from Mode column for clarity

### 5. **Updated Stats Dashboard**

Before:
```
Total Jobs | RAG Enabled | Baseline | Done | Processing
```

After:
```
Total Jobs | Baseline | RAG | LoRA | Done | Processing
```

Shows count of each mode type for better visibility.

## Visual Result

### Table Header
```
┌──────────┬──────────┬─────────┬────────┬────────┬─────┬──────────┬─────────┐
│ Job ID   │ Filename │ Advisor │ Status │ Mode   │ RAG │ Created  │ Actions │
├──────────┼──────────┼─────────┼────────┼────────┼─────┼──────────┼─────────┤
│ 550e8400 │ photo.jpg│ ansel   │ Done   │ RAG    │ Enab│ 2026-01-14 | View... │
│          │          │         │        │(Brown) │ led │  10:30 AM │         │
├──────────┼──────────┼─────────┼────────┼────────┼─────┼──────────┼─────────┤
│ abc12345 │ image.jpg│ ansel   │ Done   │ LORA   │Disab│ 2026-01-14 | View... │
│          │          │         │        │(Green) │ led │  09:15 AM │         │
└──────────┴──────────┴─────────┴────────┴────────┴─────┴──────────┴─────────┘
```

### Stats Dashboard
```
Total Jobs: 42
Baseline: 18
RAG: 15
LoRA: 9
Done: 40
Processing: 2
```

## Mode Badge Colors

| Mode | Color | Hex Value | Meaning |
|------|-------|-----------|---------|
| BASELINE | Blue | #3d5a80 | Standard analysis |
| RAG | Brown | #5a4a3d | Portfolio comparison |
| LORA | Green | #3d5a3d | Fine-tuned model |
| RAG+LORA | Purple | #5a3d5a | Combined approach |
| AB_TEST | Dark Brown | #6a4a3d | Experimental |

## Benefits

✅ **At a Glance Mode Visibility**
- See exactly which mode each job used
- Color-coded for quick identification
- No string parsing needed

✅ **Better Statistics**
- Track usage of each mode
- Monitor feature adoption (baseline vs RAG vs LoRA)
- Understand model usage patterns

✅ **Clearer Interface**
- Separate Mode and RAG status
- Less ambiguous display
- Consistent with other UI badges

✅ **Usage Tracking**
- Dashboard shows mode distribution
- Can help with performance planning
- Identifies which modes are most used

## Usage

Access the jobs viewer:
```
http://localhost:5005/jobs?format=html
```

Features:
- Shows last 100 jobs
- Color-coded mode badges
- Stats by mode at top
- Search/filter with browser tools
- Direct links to analysis and summary

## Backward Compatibility

✅ JSON response (`/jobs` without format parameter) unchanged
✅ All existing fields still available
✅ Mode field now also available in JSON if requested
✅ No API breaking changes

## Implementation Notes

- Mode is fetched from database `jobs.mode` column
- If mode is NULL or missing, defaults to 'baseline'
- Badge class is dynamically generated from mode value
- RAG column now shows boolean status instead of mode name
- Stats are recalculated from jobs data each request

## Testing

To verify the mode column works:

1. Upload jobs in different modes:
```bash
curl -F "file=@image.jpg" -F "advisor=ansel" -F "mode=rag" -F "auto_analyze=true" http://localhost:5005/upload
curl -F "file=@image.jpg" -F "advisor=ansel" -F "mode=lora" -F "auto_analyze=true" http://localhost:5005/upload
curl -F "file=@image.jpg" -F "advisor=ansel" -F "mode=baseline" -F "auto_analyze=true" http://localhost:5005/upload
```

2. View the jobs list:
```
http://localhost:5005/jobs?format=html
```

3. Verify:
   - Mode column displays correctly
   - Color badges match the mode
   - Stats show correct counts
   - RAG column shows correct enabled/disabled status

## Files Modified

**mondrian/job_service_v2.3.py:**
- Lines 1152-1157: Updated SELECT query to include mode
- Lines 1186-1197: Added mode_counts tracking
- Lines 1304-1323: Added mode badge CSS styles
- Lines 1337-1357: Updated stats dashboard with mode counts
- Lines 1369-1371: Updated table headers to include Mode
- Lines 1380-1390: Updated no-jobs colspan
- Lines 1403-1433: Updated table row generation with mode badge

## Future Enhancements

Potential improvements:
- Add mode filter/search capability
- Click mode badge to filter by mode
- Export mode data with statistics
- Add mode trends over time
- Mode performance comparison charts

---

The mode column is now visible in the jobs viewer, making it easy to see which analysis flow was used for each job at a glance! 🎯
