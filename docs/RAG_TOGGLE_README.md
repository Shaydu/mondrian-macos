# RAG Toggle - Complete Guide

## Quick Answer

**To toggle between RAG and baseline from your iOS app, pass the `enable_rag` parameter:**

```swift
// Baseline (no RAG) - Default
"enable_rag": "false"

// RAG-enhanced analysis
"enable_rag": "true"
```

---

## What You Need to Know

### 1. The Parameter

| Property | Value |
|----------|-------|
| **Parameter name** | `enable_rag` |
| **Type** | Form data (multipart/form-data) |
| **Required** | No |
| **Default** | `false` (baseline mode) |
| **Values** | `'true'` or `'false'` (case-insensitive) |

### 2. How It Works

```
iOS App
  ↓ (enable_rag='true')
Job Service (/upload)
  ↓ (passes enable_rag to AI service)
AI Advisor Service
  ↓ (if enable_rag=true)
RAG Service
  ↓ (retrieves similar images)
Enhanced Analysis Result
```

### 3. The Response

When you upload an image, the response confirms which mode was used:

```json
{
  "job_id": "abc-123",
  "enable_rag": true,  // ← Confirms RAG is enabled
  "status_url": "...",
  "stream_url": "..."
}
```

---

## iOS Implementation

See **[iOS_RAG_INTEGRATION.md](iOS_RAG_INTEGRATION.md)** for complete Swift examples.

**Quick snippet:**

```swift
// Add to your multipart form data
body.append("--\(boundary)\r\n")
body.append("Content-Disposition: form-data; name=\"enable_rag\"\r\n\r\n")
body.append(Config.enableRAG ? "true" : "false")  // ← THE KEY LINE
body.append("\r\n")
```

---

## Testing

### Before Testing

**Start the services:**

```bash
cd mondrian-macos
./mondrian.sh --restart

# Wait a few seconds, then verify:
curl http://127.0.0.1:5005/health  # Job service
curl http://127.0.0.1:5100/health  # AI advisor service
curl http://127.0.0.1:5400/health  # RAG service
```

### Quick Test (30 seconds)

Just verifies the parameter is accepted:

```bash
python3 test/test_rag_quick.py
```

**Output:**
```
✓ Job Service is running
Testing: No enable_rag parameter (default)
  ✓ Upload successful
  enable_rag in response: False
Testing: enable_rag='false' (baseline)
  ✓ Upload successful
  enable_rag in response: False
Testing: enable_rag='true' (RAG enabled)
  ✓ Upload successful
  enable_rag in response: True
✓ ALL TESTS PASSED
```

### Full Unit Tests (~5 minutes)

Runs complete analysis jobs to verify end-to-end:

```bash
python3 test/test_rag_baseline_unit.py
```

This actually runs the analysis and waits for completion.

### E2E Comparison Test (~10 minutes)

Runs both RAG and baseline, generates side-by-side HTML comparison:

```bash
python3 test/test_ios_e2e_rag_comparison.py
```

Creates comparison files in `analysis_output/`.

---

## Testing with cURL

### Baseline Mode

```bash
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=false"
```

### RAG Mode

```bash
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

### Default (Baseline)

```bash
curl -X POST http://127.0.0.1:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel"
  # enable_rag omitted = defaults to false
```

---

## Files Created

### Documentation
- **[docs/iOS_RAG_INTEGRATION.md](iOS_RAG_INTEGRATION.md)** - Complete iOS Swift examples
- **[docs/RAG_API_REFERENCE.md](RAG_API_REFERENCE.md)** - Full API documentation
- **[docs/RAG_TOGGLE_README.md](RAG_TOGGLE_README.md)** - This file

### Tests
- **[test/test_rag_quick.py](../test/test_rag_quick.py)** - Quick 30-second test
- **[test/test_rag_baseline_unit.py](../test/test_rag_baseline_unit.py)** - Full unit tests
- **[test/test_ios_e2e_rag_comparison.py](../test/test_ios_e2e_rag_comparison.py)** - E2E comparison (already existed)

---

## Troubleshooting

### Services Not Running

**Error:** `Connection refused on port 5005`

**Solution:**
```bash
./mondrian.sh --restart
# Wait 10 seconds
curl http://127.0.0.1:5005/health
```

### RAG Not Working

**Check RAG service:**
```bash
curl http://127.0.0.1:5400/health
```

**Check database has dimensional profiles:**
```bash
sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles;"
# Should return > 0
```

**Check server logs for `[RAG]` messages:**
```bash
tail -f mondrian/logs/ai_advisor_service.log | grep RAG
```

### Test Image Not Found

**Error:** `Test image not found: source/mike-shrub.jpg`

**Solution:**
```bash
ls -la source/mike-shrub.jpg
# If missing, use a different image:
export TEST_IMAGE="source/your-image.jpg"
python3 test/test_rag_quick.py
```

---

## Code Locations

Where the RAG toggle is implemented:

| Service | File | Line | What It Does |
|---------|------|------|--------------|
| Job Service | [job_service_v2.3.py](../mondrian/job_service_v2.3.py) | 664 | Receives `enable_rag` parameter from iOS |
| Job Service | [job_service_v2.3.py](../mondrian/job_service_v2.3.py) | 431 | Passes `enable_rag` to AI service |
| AI Advisor | [ai_advisor_service.py](../mondrian/ai_advisor_service.py) | 617 | Reads `enable_rag` parameter |
| AI Advisor | [ai_advisor_service.py](../mondrian/ai_advisor_service.py) | 707 | Conditionally calls RAG service |

---

## Summary Checklist

For your iOS app to use RAG:

- [ ] Add environment variable or config: `ENABLE_RAG`
- [ ] Pass `enable_rag` parameter in multipart form data
- [ ] Verify `enable_rag` in upload response
- [ ] Test with `test/test_rag_quick.py`
- [ ] Deploy and verify in logs

**That's it!** The backend handles everything else automatically.

---

## Next Steps

1. **Test the API** - Run `python3 test/test_rag_quick.py` to verify it works
2. **Implement in iOS** - See [iOS_RAG_INTEGRATION.md](iOS_RAG_INTEGRATION.md) for code examples
3. **Compare outputs** - Run `python3 test/test_ios_e2e_rag_comparison.py` to see RAG vs baseline
4. **Add to your app** - Add the `enable_rag` parameter to your upload request

---

## Questions?

- **How does RAG work?** See [NEXT_STEPS.md](../NEXT_STEPS.md) and [RAG_API_REFERENCE.md](RAG_API_REFERENCE.md)
- **iOS code examples?** See [iOS_RAG_INTEGRATION.md](iOS_RAG_INTEGRATION.md)
- **API details?** See [RAG_API_REFERENCE.md](RAG_API_REFERENCE.md)
- **Tests failing?** Check "Troubleshooting" section above
