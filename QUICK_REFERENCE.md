# Quick Reference: Mode Testing Cheatsheet

## Stop All Services
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 start_services.py --stop
```

## Start Services

### Option 1: Baseline (Default)
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 start_services.py
```

### Option 2: LoRA Fine-tuned
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py --port 5100 --model_mode fine_tuned --lora_path ./adapters/ansel &
python3 job_service_v2.3.py --port 5005 &
```

### Option 3: A/B Test (50/50 split)
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py --port 5100 --model_mode ab_test --lora_path ./adapters/ansel --ab_test_split 0.5 &
python3 job_service_v2.3.py --port 5005 &
```

## Test Commands

```bash
cd /Users/shaydu/dev/mondrian-macos

# Test LORA mode (requires LoRA service running with fine_tuned mode)
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode lora

# Test RAG mode
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode rag

# Test Baseline mode
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode baseline

# Test RAG+LORA (requires LoRA service)
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode rag_lora

# Compare LORA vs Baseline side-by-side
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --compare
```

## View Results

```bash
# Open analysis output directory
open /Users/shaydu/dev/mondrian-macos/analysis_output/

# View logs
tail -f /Users/shaydu/dev/mondrian-macos/logs/ai_advisor_service_*.log
tail -f /Users/shaydu/dev/mondrian-macos/logs/job_service_v2.3_*.log
```

## Troubleshooting

### 500 Error on /analyze
Check logs for `[STRATEGY ERROR]` or `NameError`. The RAG fix should prevent this now.

### N/A Grades in Output
The JSON conversion should handle this. Check logs for `[*_DEBUG]` output showing dimension conversion.

### Port Already in Use
```bash
lsof -i :5005
lsof -i :5100
# Kill the PIDs shown
kill -9 <PID>
```

### Model Loading Issues
Check that adapters exist:
```bash
ls -la /Users/shaydu/dev/mondrian-macos/adapters/ansel/adapters.safetensors
```

## Environment Variables

```bash
# Enable RAG by default
export RAG_ENABLED=true

# Disable RAG by default
export RAG_ENABLED=false

# Check current setting
echo $RAG_ENABLED
```

## Key Files

| File | Purpose |
|------|---------|
| `mondrian/strategies/lora.py` | LoRA fine-tuned analysis |
| `mondrian/strategies/rag.py` | RAG with base model |
| `mondrian/strategies/rag_lora.py` | RAG with LoRA adapter |
| `mondrian/strategies/baseline.py` | Base model only |
| `test_lora_e2e.py` | End-to-end test script |
| `adapters/ansel/adapters.safetensors` | LoRA weights for Ansel |

## Success Indicators

✅ **LORA mode working:**
- No 500 errors
- Grade appears as "A", "B+", etc. (not "N/A")
- Summary shows "Top 3 Recommendations"
- HTML renders with feedback cards

✅ **RAG mode working:**
- No "undefined variable" errors
- Generates dimensional analysis
- Summary displays recommendations

✅ **Baseline working:**
- Fast analysis (should complete in 30-60 seconds)
- Clean JSON output
- HTML displays with scores and recommendations
