# RAG+LoRA E2E Test Runner

This test runner ensures your RAG+LoRA tests work correctly by using the same Python 3.12 runtime as the services.

## Problem Solved

When running tests from a venv, you may see "services unavailable" errors because:
- Services run with **Python 3.12** (MLX backend requirement)
- venv uses **Python 3.9/3.10** (different runtime, different packages)
- Result: connection failures between tests and services

This runner eliminates that mismatch by using **Python 3.12** for both.

## Quick Start

```bash
# Start services (in one terminal)
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

# Run tests (in another terminal)
./test/rag-embeddings/run_rag_lora_tests.sh
```

## Usage

Run all tests:
```bash
./test/rag-embeddings/run_rag_lora_tests.sh
```

Run with specific options:
```bash
# Show timing information
./test/rag-embeddings/run_rag_lora_tests.sh --timing

# Test with embeddings enabled
./test/rag-embeddings/run_rag_lora_tests.sh --with-embeddings

# Verbose output
./test/rag-embeddings/run_rag_lora_tests.sh --verbose

# Combine options
./test/rag-embeddings/run_rag_lora_tests.sh --timing --with-embeddings
```

## What the Script Does

1. ✓ **Detects Python 3.12** - Uses the same Python version as services
2. ✓ **Verifies test image** - Ensures `photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg` exists
3. ✓ **Checks services** - Confirms AI Advisor (5100) and Job Service (5005) are running
4. ✓ **Runs tests** - Executes the test suite with Python 3.12
5. ✓ **Reports results** - Shows pass/fail/skip summary

## Troubleshooting

### "AI Advisor Service (5100) is NOT running"
Start the services first:
```bash
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel
```

### "Test image not found"
Make sure you're in the project root and the image exists:
```bash
ls source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg
```

### "Python 3.12 not found"
The script falls back to system `python3`, but you should install Python 3.12:
```bash
# Via Homebrew
brew install python@3.12

# Via python.org
# Download from https://www.python.org/downloads/
```

## Test Coverage

The test suite validates:
- ✓ Basic RAG+LoRA workflow
- ✓ Dimensional analysis accuracy
- ✓ Metadata generation (timing, reference images)
- ✓ Score validation (0-10 range)
- ✓ Comment presence for each dimension
- ✓ RAG+LoRA vs RAG mode comparison
- ✓ Optional embedding support

## Next Steps

After tests pass, you can:
1. Deploy the model with confidence
2. Monitor production quality using the same test suite
3. Compare mode performance (base vs RAG vs LoRA vs RAG+LoRA)
