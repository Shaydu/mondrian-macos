# Test Suite Index

Complete index of end-to-end tests for embedding support and RAG+LoRA strategy.

## 📂 File Structure

```
mondrian-macos/
├── test/
│   ├── test_embeddings_e2e.py          ← Embedding workflow tests
│   ├── test_embeddings_unit.py         ← Embedding unit tests
│   ├── test_rag_lora_e2e.py           ← RAG+LoRA strategy tests
│   ├── run_embedding_tests.sh          ← Master test runner
│   └── TEST_SUITE_README.md            ← Test documentation
│
├── TESTING_GUIDE.md                    ← Comprehensive testing guide
├── TEST_FILES_SUMMARY.md               ← Inventory of test files
├── E2E_TESTS_COMPLETE.md               ← Quick start summary
├── TEST_CREATION_SUMMARY.txt           ← Creation details
└── TEST_INDEX.md                       ← This file
```

## 📋 Test Files at a Glance

| File | Type | Size | Purpose |
|------|------|------|---------|
| `test/test_embeddings_e2e.py` | E2E | 19 KB | Complete embedding workflow testing |
| `test/test_embeddings_unit.py` | Unit | 16 KB | Isolated embedding function testing |
| `test/test_rag_lora_e2e.py` | E2E | 23 KB | RAG+LoRA strategy validation |
| `test/run_embedding_tests.sh` | Runner | 5.3 KB | Master test orchestration |
| `test/TEST_SUITE_README.md` | Docs | 8.3 KB | Test suite documentation |

## 📚 Documentation Files

| File | Focus | Pages | Content |
|------|-------|-------|---------|
| `TESTING_GUIDE.md` | Complete Guide | ~20 | All scenarios and troubleshooting |
| `TEST_FILES_SUMMARY.md` | Inventory | ~9 | File details and integration |
| `E2E_TESTS_COMPLETE.md` | Quick Start | ~8 | Summary and next steps |
| `TEST_CREATION_SUMMARY.txt` | Overview | ~4 | Creation details |

## 🚀 Quick Start

### Step 1: Run Unit Tests (No Service Required)

```bash
cd /Users/shaydu/dev/mondrian-macos
python3 test/test_embeddings_unit.py -v
```

**Expected:** ~30 seconds, all tests passing

### Step 2: Start Services

```bash
./start_mondrian.sh
```

### Step 3: Run E2E Tests

In another terminal:

```bash
# Embedding tests
python3 test/test_embeddings_e2e.py

# RAG+LoRA tests
python3 test/test_rag_lora_e2e.py

# Or all tests together
test/run_embedding_tests.sh
```

**Expected:** ~10-15 minutes total

## 📊 Test Coverage

### Unit Tests (`test/test_embeddings_unit.py`)

6 test classes covering:
- ✅ CLIP embedding computation
- ✅ Embedding normalization
- ✅ Similarity calculations
- ✅ Database operations
- ✅ Error handling
- ✅ Integration workflows

### E2E Tests - Embeddings (`test/test_embeddings_e2e.py`)

7 test scenarios:
- ✅ RAG with embeddings
- ✅ RAG without embeddings
- ✅ RAG+LoRA with embeddings
- ✅ RAG+LoRA without embeddings
- ✅ Embedding metadata
- ✅ Result consistency
- ✅ Performance comparison

### E2E Tests - RAG+LoRA (`test/test_rag_lora_e2e.py`)

5 test scenarios:
- ✅ Basic two-pass workflow
- ✅ With embeddings
- ✅ Metadata validation
- ✅ Dimensional scoring
- ✅ Mode comparison

## 📖 How to Read Documentation

### For First Time Users

1. **Start here:** `E2E_TESTS_COMPLETE.md`
   - Quick overview
   - Summary of what was created
   - Quick start instructions

2. **Then read:** `TESTING_GUIDE.md` (first 50 lines)
   - Quick start section
   - Running all tests

### For Different Scenarios

**Local Development:**
- See `TESTING_GUIDE.md` → "Scenario 1: Local Development Testing"

**Full Integration:**
- See `TESTING_GUIDE.md` → "Scenario 2: Full Integration Testing"

**Debugging Failed Tests:**
- See `TESTING_GUIDE.md` → "Debugging Failed Tests"
- Or `test/TEST_SUITE_README.md` → "Common Issues"

**CI/CD Integration:**
- See `TESTING_GUIDE.md` → "Continuous Integration"

## 🔍 Detailed File Descriptions

### `test/test_embeddings_e2e.py`

**Lines:** 563
**Classes:** 7 functions
**Tests:** 7 scenarios

Tests the complete embedding pipeline:
1. Service health check
2. Test image validation
3. RAG with embeddings
4. RAG without embeddings
5. RAG+LoRA with embeddings
6. RAG+LoRA without embeddings
7. Embedding metadata
8. Result consistency
9. Performance comparison

**Run:** `python3 test/test_embeddings_e2e.py --mode rag`

### `test/test_embeddings_unit.py`

**Lines:** 463
**Classes:** 6
**Tests:** 32+ methods

Isolated tests for:
- CLIP import and usage
- Embedding computation
- Embedding normalization
- Similarity calculations
- Database operations
- Error handling

**Run:** `python3 test/test_embeddings_unit.py -v`

### `test/test_rag_lora_e2e.py`

**Lines:** 607
**Functions:** 5 main tests

Tests RAG+LoRA specific:
- Two-pass workflow
- Metadata collection
- Score validation
- Mode comparison
- Embedding integration

**Run:** `python3 test/test_rag_lora_e2e.py --timing`

### `test/run_embedding_tests.sh`

**Lines:** 234
**Phases:** 3+1 (summary)

Master orchestrator:
- Checks prerequisites
- Runs unit tests
- Runs E2E tests
- Generates report

**Run:** `test/run_embedding_tests.sh --verbose`

## 📈 Statistics

```
Total Test Code:        1,867 lines
Total Documentation:    1,579 lines
────────────────────────────────
Total Content:          3,446 lines

Test Classes:           6
Test Methods:           32+
Test Scenarios:         12+

Files Created:          9
Total Size:             ~110 KB
```

## ⚙️ Test Execution Flow

```
START
  ↓
[Unit Tests] (30 seconds)
  ├── TestEmbeddingComputation
  ├── TestEmbeddingSimilarity
  ├── TestHybridAugmentation
  ├── TestEmbeddingDatabase
  ├── TestEmbeddingGracefulDegradation
  └── TestEmbeddingIntegration
  ↓
[Embedding E2E] (3-4 minutes)
  ├── RAG with embeddings
  ├── RAG without embeddings
  ├── RAG+LoRA with embeddings
  ├── RAG+LoRA without embeddings
  ├── Embedding metadata
  ├── Result consistency
  └── Performance comparison
  ↓
[RAG+LoRA E2E] (4-5 minutes)
  ├── Basic workflow
  ├── With embeddings
  ├── Metadata validation
  ├── Dimensional scoring
  └── Mode comparison
  ↓
[Summary Report]
  ├── Pass count
  ├── Fail count
  ├── Skip count
  └── Statistics
  ↓
END
```

## 🎯 Common Test Commands

### Unit Tests Only

```bash
# All unit tests
python3 test/test_embeddings_unit.py -v

# Specific test class
python3 test/test_embeddings_unit.py TestEmbeddingComputation -v

# Specific test method
python3 test/test_embeddings_unit.py TestEmbeddingComputation.test_embedding_computation -v
```

### E2E Tests

```bash
# All embedding E2E
python3 test/test_embeddings_e2e.py

# RAG mode only
python3 test/test_embeddings_e2e.py --mode rag

# RAG+LoRA mode only
python3 test/test_embeddings_e2e.py --mode rag_lora

# Verbose output
python3 test/test_embeddings_e2e.py --verbose
```

### RAG+LoRA Tests

```bash
# All tests
python3 test/test_rag_lora_e2e.py

# With embeddings focus
python3 test/test_rag_lora_e2e.py --with-embeddings

# With timing
python3 test/test_rag_lora_e2e.py --timing

# Verbose + timing
python3 test/test_rag_lora_e2e.py --verbose --timing
```

### Master Runner

```bash
# All tests
test/run_embedding_tests.sh

# Unit tests only
test/run_embedding_tests.sh --unit-only

# E2E tests only
test/run_embedding_tests.sh --e2e-only

# Verbose
test/run_embedding_tests.sh --verbose
```

## 📚 Documentation Navigation

```
TESTING_GUIDE.md
├── Quick Start
├── Test Files Overview
├── Running Tests
│   ├── Scenario 1: Local Development
│   ├── Scenario 2: Full Integration
│   ├── Scenario 3: Embedding Focused
│   ├── Scenario 4: Performance
│   └── Scenario 5: CI/CD Pipeline
├── Understanding Test Output
├── Debugging Failed Tests
├── Common Issues & Solutions
├── Test Customization
├── Metrics & Benchmarks
├── CI/CD Integration
└── Test Report Generation

test/TEST_SUITE_README.md
├── Test Files
├── Running Tests
├── Prerequisites
├── Test Results Interpretation
├── Common Issues
├── Test Data
├── Debugging
└── Test Coverage Summary

E2E_TESTS_COMPLETE.md
├── Quick Start
├── Test Coverage
├── Test Execution Flow
├── Expected Results
└── Next Steps
```

## 🔧 Configuration

### Service URLs

- AI Advisor: `http://localhost:5200`
- Job Service: `http://localhost:5000` (optional)

### Test Image

- Path: `source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg`
- Size: ~100 KB
- Format: JPEG

### Test Advisor

- ID: `ansel`
- Name: Ansel Adams
- Modes: All (baseline, rag, lora, rag_lora)

## 🆘 Getting Help

### Quick Issues

| Issue | Solution |
|-------|----------|
| Service not found | Run `./start_mondrian.sh` |
| CLIP not installed | Run `pip install torch clip` |
| Test image missing | Check `source/` directory |
| RAG+LoRA unavailable | Check `adapters/ansel/` exists |

### Detailed Help

1. **Setup issues:** See `TESTING_GUIDE.md` → "Prerequisites"
2. **Test failures:** See `test/TEST_SUITE_README.md` → "Common Issues"
3. **Debugging:** See `TESTING_GUIDE.md` → "Debugging Failed Tests"
4. **Performance:** See `TESTING_GUIDE.md` → "Metrics & Benchmarks"

## ✅ Verification Checklist

- [ ] All 5 test files created and executable
- [ ] All 4 documentation files created
- [ ] Unit tests run without errors
- [ ] E2E tests run with services
- [ ] Documentation is comprehensive
- [ ] Master runner orchestrates correctly
- [ ] Ready for CI/CD integration

## 📝 File Manifest

```
test/test_embeddings_e2e.py ........... 563 lines, 19 KB
test/test_embeddings_unit.py ......... 463 lines, 16 KB
test/test_rag_lora_e2e.py ........... 607 lines, 23 KB
test/run_embedding_tests.sh ......... 234 lines, 5.3 KB
test/TEST_SUITE_README.md ........... 394 lines, 8.3 KB

TESTING_GUIDE.md ..................... 585 lines, 20 KB
TEST_FILES_SUMMARY.md ............... (inventory), 9 KB
E2E_TESTS_COMPLETE.md ............... (summary), 8 KB
TEST_CREATION_SUMMARY.txt ........... (details), ~4 KB
TEST_INDEX.md ........................ (this file)

Total: 9 files, 3,446 lines, ~110 KB
```

---

**Status:** ✅ Complete and Ready to Test

**Start with:** `python3 test/test_embeddings_unit.py -v`
