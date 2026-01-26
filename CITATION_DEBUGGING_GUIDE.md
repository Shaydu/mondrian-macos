# Citation Debugging Guide

Step-by-step guide to diagnose and fix citation issues.

---

## Quick Diagnosis (2 minutes)

### Step 1: Run Diagnostic Script
```bash
python3 diagnose_citation_system.py
```

This will check:
- ✅ Database connectivity
- ✅ Reference images in database
- ✅ Book passages in database
- ✅ Retrieval function outputs
- ✅ Image path resolution

**Expected output:** All checks pass with ✅

---

### Step 2: Check Database Directly
```bash
sqlite3 mondrian.db << 'EOF'
.headers on
.mode column

SELECT 
  'Dimensional Profiles' as table_name,
  COUNT(*) as total,
  SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) as with_embeddings
FROM dimensional_profiles WHERE advisor_id='ansel'

UNION ALL

SELECT 
  'Book Passages',
  COUNT(*),
  SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END)
FROM book_passages WHERE advisor_id='ansel';
EOF
```

**Expected output:**
```
table_name            | total | with_embeddings
Dimensional Profiles  |   12  |      12
Book Passages         |   20  |      20
```

**If total is 0:** Need to index/import data (see "Fix Missing Data" section)
**If with_embeddings is 0:** Need to compute embeddings (see "Fix Missing Embeddings" section)

---

## Detailed Diagnosis (5 minutes)

### Issue 1: No Reference Images

**Symptom:** `diagnose_citation_system.py` shows 0 reference images

**Check:**
```bash
sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel';"
```

**If returns 0:**

**Fix Step 1: Analyze reference images**
```bash
# Start AI Advisor Service if not running
python3 mondrian/ai_advisor_service_linux.py &

# Wait for service to start (check logs)
sleep 5

# Analyze all Ansel Adams reference images
python3 batch_analyze_advisor_images.py --advisor ansel

# This will:
# 1. Find all images in mondrian/source/advisor/photographer/ansel/
# 2. Send each to AI Advisor Service
# 3. Extract dimensional scores
# 4. Save to dimensional_profiles table
```

**Fix Step 2: Compute embeddings**
```bash
python3 tools/rag/compute_embeddings.py --advisor ansel

# This will:
# 1. Load all dimensional profiles
# 2. Compute CLIP visual embeddings
# 3. Save embeddings to database
```

**Verify:**
```bash
sqlite3 mondrian.db "
SELECT COUNT(*) as with_embeddings 
FROM dimensional_profiles 
WHERE advisor_id='ansel' AND embedding IS NOT NULL;
"
```

Should return > 0

---

### Issue 2: No Book Passages

**Symptom:** `diagnose_citation_system.py` shows 0 book passages

**Check:**
```bash
sqlite3 mondrian.db "SELECT COUNT(*) FROM book_passages WHERE advisor_id='ansel';"
```

**If returns 0:**

**Fix Step 1: Check if passage files exist**
```bash
find training/book_passages -type f -name "*.json" 2>/dev/null | head -10
```

**If files exist:**

**Fix Step 2: Import passages**
```bash
python3 tools/rag/import_book_passages.py --advisor ansel

# This will:
# 1. Read JSON files from training/book_passages/
# 2. Parse passages and dimension tags
# 3. Save to book_passages table
```

**If files don't exist:**

**Fix Step 2: Create passage files**

Create `training/book_passages/ansel_quotes.json`:
```json
{
  "advisor": "ansel",
  "book": "The Camera",
  "passages": [
    {
      "id": "camera_001",
      "text": "The camera is an instrument for recording. The photograph is the statement of the recording. A photograph has to fulfill the same criteria of honesty and genuine statement as a good paragraph does.",
      "dimensions": ["composition", "technical_precision"],
      "relevance_score": 8,
      "notes": "On photography basics"
    },
    {
      "id": "camera_002",
      "text": "Visualization is a conscious process of projecting the final photographic image in the mind before taking the first steps in actually photographing the subject.",
      "dimensions": ["composition", "focus_sharpness"],
      "relevance_score": 9,
      "notes": "On pre-visualization"
    }
  ]
}
```

Then import:
```bash
python3 tools/rag/import_book_passages.py --advisor ansel
```

**Fix Step 3: Compute embeddings**
```bash
python3 tools/rag/compute_embeddings.py --type passages --advisor ansel
```

**Verify:**
```bash
sqlite3 mondrian.db "SELECT COUNT(*) FROM book_passages WHERE advisor_id='ansel';"
```

Should return > 0

---

### Issue 3: Embeddings Missing or Null

**Symptom:** Data exists but embeddings column is NULL

**Check:**
```bash
sqlite3 mondrian.db "
SELECT COUNT(*) as with_null_embeddings
FROM dimensional_profiles 
WHERE advisor_id='ansel' AND embedding IS NULL;
"
```

**If returns > 0:**

**Fix: Compute or recompute embeddings**
```bash
# For reference images
python3 tools/rag/compute_embeddings.py --advisor ansel --force

# For book passages
python3 tools/rag/compute_embeddings.py --type passages --advisor ansel --force

# The --force flag will recompute even if embeddings exist
```

**Verify:**
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('mondrian.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id=\"ansel\" AND embedding IS NOT NULL')
print(f'Reference images with embeddings: {c.fetchone()[0]}')
c.execute('SELECT COUNT(*) FROM book_passages WHERE advisor_id=\"ansel\" AND embedding IS NOT NULL')
print(f'Book passages with embeddings: {c.fetchone()[0]}')
conn.close()
"
```

---

### Issue 4: Image Paths Cannot Be Resolved

**Symptom:** References exist but images show as empty in HTML

**Check with debug logging:**
```bash
# Run with debug logging enabled
python3 mondrian/ai_advisor_service_linux.py --log-level DEBUG 2>&1 | grep -i "path resolve"
```

**Look for messages like:**
```
[Path Resolve] ❌ Not found: /path/to/image.jpg
```

**Fix Step 1: Verify image files exist**
```bash
# Check if images are in the expected directory
ls -la mondrian/source/advisor/photographer/ansel/ | head -10

# Should show .jpg or .png files
```

**Fix Step 2: Update database paths if needed**

If images were moved, update paths:
```bash
sqlite3 mondrian.db << 'EOF'
UPDATE dimensional_profiles 
SET image_path = './mondrian/source/advisor/photographer/ansel/image_name.jpg'
WHERE advisor_id='ansel' AND image_path LIKE '%image_name%';
EOF
```

**Fix Step 3: Re-analyze images**

If paths are incorrect, re-analyze:
```bash
python3 batch_analyze_advisor_images.py --advisor ansel --force

# This will re-index all images with correct paths
```

---

## Advanced Diagnosis (10+ minutes)

### Full Citation Flow Test

Run this test to trace citations end-to-end:

```bash
python3 test_enhanced_single_pass_citations.py
```

This script:
1. Submits a test image
2. Waits for analysis
3. Checks if citations are present
4. Verifies HTML output
5. Reports success/failure

**Output shows:**
- Number of image citations found
- Number of quote citations found
- Whether HTML boxes render
- Whether citations match weak dimensions

---

### Enable Debug Logging

For maximum detail, enable debug logging:

```bash
# Redirect to file for analysis
python3 mondrian/ai_advisor_service_linux.py --log-level DEBUG > /tmp/advisor.log 2>&1 &

# Then run a test
python3 test_enhanced_single_pass_citations.py

# Check the log
grep -i citation /tmp/advisor.log | head -50
```

**Look for these success messages:**
```
[Citations] Validated: 2 images, 1 quote
✓ Valid image citation: IMG_1 in Composition
✓ Valid quote citation: QUOTE_2 in Lighting
[HTML Gen] ✅ Successfully embedded reference image: ...
[Citation Service] Rendered quote for Composition from '...'
```

**Look for these failure messages:**
```
❌ Invalid image citation: IMG_1 not in candidates
❌ Could not resolve image path: /path/to/image
[Path Resolve] ❌ Not found: ...
```

---

### Check LLM Response

Enable logging to see what LLM returns:

```bash
# In ai_advisor_service_linux.py, add after LLM response parsing:
logger.info(f"[DEBUG] LLM returned dimensions: {json.dumps(dimensions, indent=2)}")
```

Look for these fields:
- `case_study_id: "IMG_1"` - LLM wants to cite image 1
- `quote_id: "QUOTE_2"` - LLM wants to cite quote 2

If these fields are missing:
- LLM prompt might not mention citations
- LLM might not be including them in response
- Check `_build_rag_prompt()` function

---

## Recovery Procedures

### Complete Reset (Nuclear Option)

If everything is broken:

```bash
# 1. Backup database
cp mondrian.db mondrian.db.backup_$(date +%s)

# 2. Delete old analysis data
sqlite3 mondrian.db << 'EOF'
DELETE FROM dimensional_profiles WHERE advisor_id='ansel';
DELETE FROM book_passages WHERE advisor_id='ansel';
VACUUM;
EOF

# 3. Re-index everything
python3 batch_analyze_advisor_images.py --advisor ansel

# 4. Compute embeddings
python3 tools/rag/compute_embeddings.py --advisor ansel

# 5. Import passages
python3 tools/rag/import_book_passages.py --advisor ansel

# 6. Compute passage embeddings
python3 tools/rag/compute_embeddings.py --type passages --advisor ansel

# 7. Verify
python3 diagnose_citation_system.py
```

---

## Performance Tips

### Speed Up Citation Retrieval

If retrieval is slow, check:

```bash
# 1. Check if embeddings are indexed
sqlite3 mondrian.db << 'EOF'
.index dimensional_profiles
EOF
```

Should show indexes on `advisor_id` and other columns.

If no indexes:

```bash
sqlite3 mondrian.db << 'EOF'
CREATE INDEX idx_dim_advisor ON dimensional_profiles(advisor_id);
CREATE INDEX idx_passage_advisor ON book_passages(advisor_id);
VACUUM;
EOF
```

### Batch Operations Optimization

For large-scale re-indexing:

```bash
# Process multiple advisors in parallel
python3 batch_analyze_advisor_images.py --advisor ansel &
python3 batch_analyze_advisor_images.py --advisor okeefe &
python3 batch_analyze_advisor_images.py --advisor mondrian &

wait
```

---

## Validation Checklist

After implementing fixes, verify with:

```bash
✅ Diagnostic script passes all checks
✅ Database shows > 0 references with embeddings
✅ Database shows > 0 passages with embeddings
✅ Test script shows citations in output
✅ Logs show "Valid image citation" messages
✅ Logs show "Valid quote citation" messages
✅ HTML contains <div class="reference-citation">
✅ HTML contains <div class="advisor-quote-box">
✅ Images load in HTML (no broken base64)
✅ No error messages about path resolution
```

---

## Quick Reference Commands

```bash
# Check current state
python3 diagnose_citation_system.py

# Full database check
sqlite3 mondrian.db "SELECT COUNT(*) as profiles FROM dimensional_profiles; SELECT COUNT(*) as passages FROM book_passages;"

# Re-index everything
python3 batch_analyze_advisor_images.py --advisor ansel && python3 tools/rag/compute_embeddings.py --advisor ansel

# Test end-to-end
python3 test_enhanced_single_pass_citations.py

# Debug logs
python3 mondrian/ai_advisor_service_linux.py --log-level DEBUG 2>&1 | tee /tmp/advisor.log

# Search logs for citations
grep -i "citation\|IMG_\|QUOTE_" /tmp/advisor.log
```

---

## When to Get Help

Open an issue if:
1. ✅ Diagnostic script passes but citations still don't appear
2. ✅ Database has embeddings but retrieval returns empty
3. ✅ LLM returns valid citations but HTML is empty
4. ✅ Path resolution fails even though files exist
5. ✅ Embeddings computation fails with error

Include:
- Output of `diagnose_citation_system.py`
- Relevant log excerpts
- Database query results
- Screenshots of expected vs. actual output

