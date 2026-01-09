# Next Steps: Fix Dimensional RAG System

## Summary

✅ **Your system architecture is CORRECT** - it does exactly what you described:
- Computes dimensional scores for advisor reference images
- Compares user images to advisor images
- Makes advisor-specific and image-specific recommendations

❌ **But it's not working because**: Advisor reference images have NULL scores in the database

---

## Immediate Actions (60 minutes)

### Step 1: Verify Current State (5 minutes)

```bash
# Check how many advisor images have NULL scores
python batch_analyze_advisor_images.py --advisor ansel --verify-only

# Expected output:
# ✅ Valid profiles:   0/14
# ⚠️  NULL scores:      12/14
# ❌ Missing profiles: 2/14
```

### Step 2: Start AI Advisor Service (if not running)

```bash
# Check if running
curl http://localhost:5100/health

# If not running, start it
cd /Users/shaydu/dev/mondrian-macos
python mondrian/ai_advisor_service.py --use_mlx --port 5100
```

### Step 3: Batch Analyze Ansel Reference Images (45 minutes)

```bash
# This will analyze all 14 Ansel images
# Takes ~3-5 minutes per image = 45-70 minutes total
python batch_analyze_advisor_images.py --advisor ansel

# Expected output:
# [1/14] af.jpg
#   [INFO] Analyzing: af.jpg
#   [OK] Analysis complete: af.jpg
#   [OK] Valid profile: comp=8.5, light=9.0, overall=8.7
# 
# [2/14] 2.jpg
#   [INFO] Analyzing: 2.jpg
#   ...
# 
# ✅ Analysis succeeded: 14/14
# ✅ Profiles verified:  14/14
```

### Step 4: Verify Profiles Are Valid (2 minutes)

```bash
# Check database
sqlite3 mondrian.db "SELECT image_path, composition_score, lighting_score, overall_grade 
FROM dimensional_profiles 
WHERE image_path LIKE '%advisor%' 
AND composition_score IS NOT NULL 
ORDER BY overall_grade DESC 
LIMIT 5;"

# Expected output:
# /Users/.../ansel/af.jpg|8.5|9.0|8.7
# /Users/.../ansel/5.jpg|8.2|8.8|8.5
# /Users/.../ansel/2.jpg|7.8|8.5|8.1
# ...
```

### Step 5: Test End-to-End RAG (5 minutes)

```bash
# Upload user image with RAG enabled
curl -X POST http://localhost:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "auto_analyze=true" \
  -F "enable_rag=true"

# Monitor AI Advisor Service logs for:
# [RAG] Finding dimensionally similar images (top_k=3)...
# [RAG] Current image dimensional profile:
# [RAG]   composition: 7.0
# [RAG]   lighting: 8.0
# [RAG]   ...
# [RAG] Retrieved 3 dimensionally similar images
# [RAG] Augmented prompt with 3 dimensional comparisons

# Check job output for comparative feedback:
# "Your composition (7.0/10) follows rule of thirds, but unlike 
#  Reference #1 (af.jpg, Composition: 8.5/10, +1.5 delta) which uses..."
```

---

## Troubleshooting

### Issue: AI Advisor Service not responding

```bash
# Check if service is running
curl http://localhost:5100/health

# Check logs
tail -f mondrian/logs/ai_advisor_out.log

# Restart service
pkill -f ai_advisor_service
python mondrian/ai_advisor_service.py --use_mlx --port 5100
```

### Issue: Analysis fails with timeout

```bash
# Increase timeout in batch script (edit batch_analyze_advisor_images.py)
# Change: timeout=120 to timeout=300

# Or analyze images one at a time manually:
curl -X POST http://localhost:5100/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "advisor": "ansel",
    "image_path": "/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/af.jpg",
    "enable_rag": "false"
  }'
```

### Issue: Dimensional profiles have NULL scores

```bash
# Check if analysis_html was saved
sqlite3 mondrian.db "SELECT image_path, LENGTH(analysis_html) 
FROM dimensional_profiles 
WHERE image_path LIKE '%af.jpg%' 
ORDER BY created_at DESC 
LIMIT 1;"

# If analysis_html is NULL → Analysis failed
# If analysis_html exists → Extraction failed

# Check extraction logic in ai_advisor_service.py
# Look for extract_dimensional_profile_from_json() function
```

### Issue: RAG returns no similar images

```bash
# Check if advisor images have valid scores
sqlite3 mondrian.db "SELECT COUNT(*) 
FROM dimensional_profiles 
WHERE advisor_id = 'ansel' 
AND composition_score IS NOT NULL;"

# Should return 14 after batch analysis

# Check if user image has profile
sqlite3 mondrian.db "SELECT composition_score, lighting_score 
FROM dimensional_profiles 
WHERE image_path LIKE '%mike-shrub%' 
ORDER BY created_at DESC 
LIMIT 1;"

# Should return valid scores (not NULL)
```

---

## Future Enhancements (After RAG is Working)

### 1. Index Other Advisors (2-3 hours each)

```bash
# O'Keeffe
python batch_analyze_advisor_images.py --advisor okeefe

# Mondrian
python batch_analyze_advisor_images.py --advisor mondrian

# Gehry
python batch_analyze_advisor_images.py --advisor gehry

# Van Gogh
python batch_analyze_advisor_images.py --advisor vangogh

# Or all at once (10-15 hours)
python batch_analyze_advisor_images.py --advisor all
```

### 2. Add More Reference Images

```bash
# Add high-quality reference images to:
# mondrian/source/advisor/photographer/ansel/
# mondrian/source/advisor/painter/okeefe/
# etc.

# Then re-run batch analysis
python batch_analyze_advisor_images.py --advisor ansel --force
```

### 3. Tune RAG Parameters

Edit `ai_advisor_service.py`:

```python
# Change number of similar images returned
similar_images = get_similar_images_from_rag(abs_image_path, top_k=5, advisor_id=advisor)

# Add minimum similarity threshold
if profile.get('distance', 999) < 5.0:  # Only include if distance < 5.0
    results.append(profile)

# Weight dimensions differently
# Give more weight to composition and lighting
weighted_distance = sqrt(
    2.0 * (comp_delta ** 2) +  # 2x weight
    2.0 * (light_delta ** 2) +  # 2x weight
    1.0 * (focus_delta ** 2) +
    ...
)
```

### 4. Add Automated Re-indexing

Create file watcher to re-analyze when reference images change:

```python
# watch_advisor_images.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AdvisorImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(('.jpg', '.jpeg', '.png')):
            # Trigger analysis
            analyze_image(event.src_path, advisor_id)
```

---

## Success Criteria

✅ **System is working when**:

1. All advisor reference images have valid dimensional scores (not NULL)
   ```bash
   sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles 
   WHERE advisor_id = 'ansel' AND composition_score IS NOT NULL;"
   # Result: 14
   ```

2. RAG returns similar images when user uploads photo
   ```bash
   # Logs show:
   [RAG] Retrieved 3 dimensionally similar images
   ```

3. Analysis includes comparative feedback
   ```
   "Your composition (7.0/10) is weaker than Reference #1 (8.5/10, +1.5 delta)..."
   "Unlike the master work which uses sweeping S-curves..."
   "To match the level shown in Reference #2, consider..."
   ```

4. Dimensional deltas are accurate
   ```
   User composition: 7.0
   Reference composition: 8.5
   Delta: +1.5 (Reference stronger)
   ```

---

## Commands Quick Reference

```bash
# Verify current state
python batch_analyze_advisor_images.py --advisor ansel --verify-only

# Analyze all Ansel images
python batch_analyze_advisor_images.py --advisor ansel

# Force re-analyze all images
python batch_analyze_advisor_images.py --advisor ansel --force

# Analyze all advisors
python batch_analyze_advisor_images.py --advisor all

# Check database
sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE composition_score IS NOT NULL;"

# Test RAG
curl -X POST http://localhost:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

---

## Timeline

- **Now**: Verify current state (5 min)
- **+5 min**: Start batch analysis (45 min)
- **+50 min**: Verify profiles are valid (2 min)
- **+52 min**: Test end-to-end RAG (5 min)
- **+57 min**: ✅ System working!

Total: **~60 minutes** to get dimensional RAG fully operational

---

## Questions?

If you encounter any issues:

1. Check `REQUIREMENTS_ANALYSIS.md` for detailed diagnosis
2. Check `RAG_ARCHITECTURE_DIAGRAM.md` for system overview
3. Check logs: `tail -f mondrian/logs/ai_advisor_out.log`
4. Run verification: `python batch_analyze_advisor_images.py --advisor ansel --verify-only`

The system architecture is correct - we just need to populate the advisor reference data!
