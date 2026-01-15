# Embedding Support & RAG+LoRA Test Suite

Comprehensive end-to-end and unit tests for embedding support and RAG+LoRA strategy implementation.

## Test Files

### 1. `test_embeddings_e2e.py` - Embedding E2E Tests

Tests the complete embedding workflow across RAG and RAG+LoRA modes.

**Features:**
- Service health checks
- Image analysis with/without embeddings
- Response structure validation
- Dimensional analysis completeness
- Similar images retrieval
- Performance comparison
- Consistency checks

**Usage:**

```bash
# Run all embedding tests
python3 test/test_embeddings_e2e.py

# Test specific mode
python3 test/test_embeddings_e2e.py --mode rag
python3 test/test_embeddings_e2e.py --mode rag_lora

# Test without embeddings (baseline)
python3 test/test_embeddings_e2e.py --no-embeddings

# Verbose output
python3 test/test_embeddings_e2e.py --verbose
```

**Expected Output:**

```
==========================================
Embedding Support E2E Tests
==========================================

Prerequisites
==========================================
[TEST] Service Health Check... ✓ PASS Service running at http://localhost:5200
[TEST] Test Image Availability... ✓ PASS Found at .../photo-*.jpg (XXX bytes)

Running Tests
==========================================

Test 1: RAG with Embeddings
================================================================================
[TEST] Analyze with rag mode (embeddings=true)... ✓ PASS Duration: X.XXs
[TEST] Response Structure Validation... ✓ PASS All required fields present
[TEST] Mode Verification... ✓ PASS Mode correctly set to 'rag'
[TEST] Dimensional Analysis Validation... ✓ PASS All 8 dimensions present
[TEST] Overall Grade Validation... ✓ PASS Grade: A

Test Summary
================================================================================
✓ Passed:  X
✗ Failed:  0
⊘ Skipped: 0
```

### 2. `test_embeddings_unit.py` - Embedding Unit Tests

Isolated unit tests for embedding functions.

**Test Classes:**
- `TestEmbeddingComputation` - CLIP embedding computation
- `TestEmbeddingSimilarity` - Similarity search algorithms
- `TestHybridAugmentation` - Prompt augmentation
- `TestEmbeddingDatabase` - Database operations
- `TestEmbeddingGracefulDegradation` - Error handling
- `TestEmbeddingIntegration` - Integration workflows

**Usage:**

```bash
# Run all unit tests
python3 test/test_embeddings_unit.py

# Run specific test class
python3 test/test_embeddings_unit.py TestEmbeddingComputation

# Run specific test method
python3 test/test_embeddings_unit.py TestEmbeddingComputation.test_clip_embedding_import

# Verbose output
python3 test/test_embeddings_unit.py -v
```

**Test Coverage:**

- ✅ CLIP embedding import and availability
- ✅ Embedding computation from images
- ✅ Embedding normalization (unit vectors)
- ✅ Consistency across multiple computations
- ✅ Cosine similarity calculations
- ✅ Similarity ranking/sorting
- ✅ Hybrid augmentation structure
- ✅ Database storage and retrieval
- ✅ Embedding indices
- ✅ Graceful degradation when dependencies missing
- ✅ Fallback behavior

### 3. `test_rag_lora_e2e.py` - RAG+LoRA E2E Tests

End-to-end tests specifically for RAG+LoRA strategy.

**Test Coverage:**
- Basic two-pass workflow
- LoRA adapter loading
- Dimensional profile extraction
- RAG retrieval with similarity
- Embeddings integration (optional)
- Hybrid augmentation
- Metadata and timing information
- Dimensional score validation
- Mode comparison (RAG vs RAG+LoRA)

**Usage:**

```bash
# Run all RAG+LoRA tests
python3 test/test_rag_lora_e2e.py

# Include embedding tests
python3 test/test_rag_lora_e2e.py --with-embeddings

# Include timing measurements
python3 test/test_rag_lora_e2e.py --timing

# Verbose output
python3 test/test_rag_lora_e2e.py --verbose

# Combined
python3 test/test_rag_lora_e2e.py --with-embeddings --timing --verbose
```

## Running Tests

### Prerequisites

1. **Start services:**
   ```bash
   ./start_mondrian.sh
   ```

2. **Install CLIP dependencies (optional but recommended for embedding tests):**
   ```bash
   pip install torch clip
   ```

3. **Populate embeddings (optional):**
   ```bash
   python tools/rag/index_with_metadata.py \
     --advisor ansel \
     --metadata-file advisor_image_manifest.yaml
   ```

### Run All Tests

```bash
# Run embedding tests
python3 test/test_embeddings_e2e.py

# Run unit tests
python3 test/test_embeddings_unit.py -v

# Run RAG+LoRA tests
python3 test/test_rag_lora_e2e.py
```

### Quick Test Script

```bash
#!/bin/bash
# Run all embedding and RAG+LoRA tests

echo "Starting tests..."

# Unit tests (don't require services)
echo -e "\n=== Running Unit Tests ==="
python3 test/test_embeddings_unit.py -v

# E2E tests (require services)
echo -e "\n=== Running Embedding E2E Tests ==="
python3 test/test_embeddings_e2e.py

echo -e "\n=== Running RAG+LoRA E2E Tests ==="
python3 test/test_rag_lora_e2e.py --timing

echo -e "\nAll tests completed!"
```

## Test Results Interpretation

### Success Indicators

✅ **All Tests Passed**
- Embeddings are working correctly
- RAG+LoRA mode is functional
- All modes producing valid output

⚠️ **Some Tests Skipped**
- Normal if CLIP not installed
- Normal if RAG+LoRA adapter unavailable
- Normal if embeddings not populated

❌ **Tests Failed**
- Check service logs for errors
- Verify services are running
- Check database connectivity

### Common Issues

**Service not running:**
```bash
# Check if service is up
curl http://localhost:5200/health

# Start services
./start_mondrian.sh
```

**CLIP not installed:**
```bash
pip install torch clip
```

**RAG+LoRA not available:**
- Requires LoRA adapter in `adapters/ansel/`
- Requires dimensional profiles in database
- Check adapter path and permissions

**Embeddings not populated:**
```bash
# Run indexing to populate embeddings
python tools/rag/index_with_metadata.py \
  --advisor ansel \
  --metadata-file advisor_image_manifest.yaml
```

## Test Metrics

### Timing Expectations

| Operation | Expected Duration | Notes |
|-----------|-------------------|-------|
| Single embedding | 0.1-0.5s | One-time per analysis |
| Similarity search | 0.01-0.05s | Database query |
| RAG Pass 1 | 3-5s | Model inference |
| RAG Query | 0.5-2s | Retrieval + ranking |
| RAG Pass 2 | 3-5s | Model inference |
| Total RAG | 6-12s | End-to-end |
| RAG+LoRA Pass 1 | 2-4s | LoRA inference |
| RAG+LoRA Pass 2 | 2-4s | LoRA inference |
| Total RAG+LoRA | 5-10s | End-to-end |
| Embeddings overhead | <1s | Typically 0.1-0.5s |

## Test Data

### Test Image
- **Path:** `source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg`
- **Size:** ~100KB
- **Format:** JPEG
- **Dimensions:** Typical photography image

### Test Advisor
- **Advisor ID:** `ansel`
- **Name:** Ansel Adams
- **Mode Availability:** All modes (baseline, rag, lora, rag_lora)

## Debugging

### Enable Verbose Logging

```python
# In test files, set DEBUG flag
DEBUG = True  # Will print additional logs
```

### Check Service Logs

```bash
# Terminal 1: Watch logs
tail -f logs/*.log

# Terminal 2: Run tests
python3 test/test_embeddings_e2e.py --verbose
```

### Inspect API Response

```bash
# Direct API call to inspect response
curl -X POST http://localhost:5200/analyze \
  -F "advisor=ansel" \
  -F "image=@source/photo-*.jpg" \
  -F "mode=rag+lora" \
  -F "enable_embeddings=true" \
  -F "response_format=json" | jq .
```

## Test Coverage Summary

| Feature | Unit | E2E | RAG+LoRA | Status |
|---------|------|-----|----------|--------|
| Embedding computation | ✅ | ✅ | ✅ | Complete |
| Similarity search | ✅ | ✅ | ✅ | Complete |
| Hybrid augmentation | ✅ | ✅ | ✅ | Complete |
| Database operations | ✅ | - | - | Complete |
| RAG mode | - | ✅ | - | Complete |
| RAG+LoRA mode | - | - | ✅ | Complete |
| Graceful degradation | ✅ | ✅ | ✅ | Complete |
| Performance metrics | - | ✅ | ✅ | Complete |
| Error handling | ✅ | ✅ | ✅ | Complete |

## Contributing

When adding new tests:

1. Follow naming convention: `test_[feature]_[scenario].py`
2. Use descriptive test names
3. Include docstrings
4. Use color output for readability
5. Handle missing dependencies gracefully
6. Clean up resources in tearDown

## References

- [Embedding Implementation Plan](../EMBEDDING_IMPLEMENTATION_COMPLETE.md)
- [RAG+LoRA Strategy](../mondrian/strategies/rag_lora.py)
- [Embedding Functions](../mondrian/json_to_html_converter.py)
- [API Documentation](../docs/)
