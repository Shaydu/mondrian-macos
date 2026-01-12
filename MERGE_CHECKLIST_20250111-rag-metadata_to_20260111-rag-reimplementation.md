# Merge Checklist: 20250111-rag-metadata → 20260111-rag-reimplementation

## Branch Rename (First Step)
- [ ] Rename branch `20260111=rag-reimplementation` to `20260111-rag-reimplementation`
  - Command: `git branch -m "20260111=rag-reimplementation" "20260111-rag-reimplementation"`

## Database & RAG Fixes

### 1. UNIQUE Constraint Fix for dimensional_profiles
- [ ] **File**: `mondrian/json_to_html_converter.py`
- [ ] **Change**: Update `save_dimensional_profile()` to handle duplicate `(advisor_id, image_path)` pairs
- [ ] **Details**: 
  - Check if profile exists before inserting
  - Use UPDATE if exists, INSERT if new
  - Prevents `UNIQUE constraint failed: dimensional_profiles.advisor_id, dimensional_profiles.image_path` errors
- [ ] **Lines**: ~235-296

### 2. Database Locking Fixes
- [ ] **File**: `mondrian/job_service_v2.3.py`
- [ ] **Change**: Add retry logic with exponential backoff for database operations
- [ ] **Details**:
  - Added retry logic (up to 5 attempts) in `update_job_status()`
  - Added `timeout=10.0` and `PRAGMA busy_timeout = 5000` to all database connections
  - Prevents `database is locked` errors during concurrent writes
- [ ] **Lines**: ~252-360

- [ ] **File**: `mondrian/json_to_html_converter.py`
- [ ] **Change**: Add timeout and busy_timeout to all `sqlite3.connect()` calls
- [ ] **Details**:
  - All 3 `sqlite3.connect()` calls now have `timeout=10.0`
  - All connections set `PRAGMA busy_timeout = 5000`
- [ ] **Lines**: ~236, ~373, ~449

- [ ] **File**: `mondrian/job_service_v2.3.py`
- [ ] **Change**: Update `get_db_connection()` to include timeout settings
- [ ] **Details**:
  - Added `timeout=10.0` parameter
  - Added `PRAGMA busy_timeout = 5000`
- [ ] **Lines**: ~163-168

## Test Improvements

### 3. E2E Test - RAG Service Optional/Required Logic
- [ ] **File**: `test/test_ios_e2e_rag_comparison.py`
- [ ] **Change**: Make RAG Service optional for baseline tests, required for RAG tests
- [ ] **Details**:
  - Updated `check_services()` to accept `require_rag_service` parameter
  - RAG Service is optional for baseline tests
  - RAG Service is required when testing RAG functionality
  - Added service check before RAG test
- [ ] **Lines**: ~82-145, ~601-604

## GPU Optimization

### 4. GPU Synchronization for MLX
- [ ] **File**: `mondrian/ai_advisor_service.py`
- [ ] **Change**: Add explicit GPU synchronization after MLX generation
- [ ] **Details**:
  - Added `mx.synchronize()` after `generate()` calls
  - Added GPU device logging before generation
  - Ensures all GPU operations complete before returning
- [ ] **Lines**: ~507-511, ~523-527

## Summary of Changes

### Files Modified:
1. `mondrian/json_to_html_converter.py` - UNIQUE constraint fix + database timeouts
2. `mondrian/job_service_v2.3.py` - Database locking fixes + connection timeouts
3. `test/test_ios_e2e_rag_comparison.py` - RAG service optional/required logic
4. `mondrian/ai_advisor_service.py` - GPU synchronization

### Key Improvements:
- ✅ Fixed UNIQUE constraint errors when re-analyzing images
- ✅ Fixed database locking errors during concurrent operations
- ✅ Improved test reliability (RAG service optional for baseline)
- ✅ Better GPU utilization (explicit synchronization)

## Merge Strategy

1. **First**: Rename the branch (requires git write permissions)
2. **Then**: Checkout the target branch: `git checkout 20260111-rag-reimplementation`
3. **Merge or cherry-pick** changes from `20250111-rag-metadata`
4. **Test** all changes work together

## Testing After Merge

- [ ] Run E2E test: `python3 test/test_ios_e2e_rag_comparison.py`
- [ ] Verify no UNIQUE constraint errors in logs
- [ ] Verify no database locking errors
- [ ] Verify RAG service check works (optional for baseline, required for RAG)
- [ ] Verify GPU synchronization logs appear
- [ ] Test concurrent job processing
