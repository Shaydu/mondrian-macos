# Incremental Mode Testing Plan

This plan isolates which analysis modes work on your M1 Mac with 16GB RAM. We test each mode sequentially to identify which trigger out-of-memory crashes.

## Testing Strategy

Test each mode independently in this order:

1. **Baseline** - Base model, no RAG, no LoRA (smallest memory footprint)
2. **RAG** - Base model with RAG enabled
3. **LoRA** - Base model with LoRA adapter
4. **LoRA+RAG** - Both LoRA and RAG enabled (largest memory footprint)

## Prerequisites

- Mac must be freshly restarted
- Close all apps (Chrome, Slack, Discord, Cursor, etc.)
- Terminal.app only
- 16GB RAM available

## Running Individual Tests

Each test script is standalone. Run them in separate Terminal tabs:

### Tab 1: Start Service
```bash
cd /Users/shaydu/dev/mondrian-macos
source mondrian/venv/bin/activate

# Choose the mode to test
./mondrian.sh --restart --mode=base           # For baseline test
./mondrian.sh --restart --mode=rag            # For RAG test
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel  # For LoRA test
./mondrian.sh --restart --mode=lora+rag --lora-path=./adapters/ansel  # For LoRA+RAG test

# Wait for "All services are healthy!" message
```

### Tab 2: Run Test
```bash
cd /Users/shaydu/dev/mondrian-macos
source mondrian/venv/bin/activate

# Run the corresponding test
python3 test/rag-embeddings/test_mode_baseline.py    # Tests baseline mode
python3 test/rag-embeddings/test_mode_rag.py         # Tests RAG mode
python3 test/rag-embeddings/test_mode_lora.py        # Tests LoRA mode
python3 test/rag-embeddings/test_mode_lora_rag.py    # Tests LoRA+RAG mode
```

## Automated Testing (All Modes)

Run all tests in sequence with the automated runner:

```bash
cd /Users/shaydu/dev/mondrian-macos
source mondrian/venv/bin/activate
bash test/rag-embeddings/run_incremental_tests.sh
```

This script will:
1. Stop any running services
2. Test each mode one by one
3. Report which modes passed/failed
4. Generate a summary report

## Expected Memory Usage

- **Baseline**: ~6-7GB GPU (model only)
- **RAG**: ~7-8GB GPU (model + RAG embeddings)
- **LoRA**: ~6-7GB GPU (model + LoRA weights)
- **LoRA+RAG**: ~8-9GB GPU (all combined)

On 16GB unified memory, all should fit, but if fragmented or other apps are running, you'll see OOM crashes.

## Interpreting Results

### Success
- Test completes with ✓ PASS
- Returns JSON response with mode_used, overall_grade, dimensional_analysis
- Service stays running (can still see health checks)

### Failure
- Test shows Connection refused (service crashed)
- Logs show: `[METAL] Command buffer execution failed: Insufficient Memory`
- Service stopped unexpectedly

## Troubleshooting

### Service crashes on first test
- Reboot Mac completely
- Do NOT open any other apps
- Check `logs/ai_advisor_service_*.log` for exact error
- Try base mode first to confirm model itself works

### Baseline works but RAG/LoRA fails
- RAG needs extra embeddings loaded (more memory)
- LoRA needs adapter weights (more memory)
- Try reducing model size in ai_advisor_service.py

### All modes fail
- Check MLX/transformers versions (may have regression)
- Try updating packages: `pip install --upgrade mlx mlx-vlm mlx-lm`
- Check if other processes are consuming memory

## Output Files

Test results are saved to:
- `logs/tests/incremental_test_results.txt` - Summary of all tests
- Individual test logs in Terminal output

## Next Steps After Testing

Once you identify which modes work:
1. If baseline works: Focus on memory optimization for RAG/LoRA
2. If RAG works: Check LoRA adapter loading
3. If LoRA works: Check RAG service integration
4. If all fail: Investigate MLX/GPU memory leak
