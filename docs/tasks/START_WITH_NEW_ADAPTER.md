# Start Services with New LoRA Adapter

Your command is **correct and perfect!** Here's exactly what to do:

## Command 1: Start Services with New LoRA Adapter

```bash
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel
```

**What this does:**
- ✓ Uses the new trained adapter at `./adapters/ansel`
- ✓ Starts in LoRA mode (fine-tuned model)
- ✓ Kills any existing services (`--restart`)
- ✓ Configures AI Advisor Service with LoRA settings

**Expected output:**
```
[MODE] LoRA fine-tuned model
[INFO] Loading LoRA adapter from: ./adapters/ansel
✓ LoRA adapter successfully applied to model
AI Advisor Service ready on http://0.0.0.0:5100
Job Service ready on http://127.0.0.1:5005
```

## Command 2: Run the Test

```bash
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora
```

**What this does:**
- ✓ Tests the LoRA model with a sample image
- ✓ Generates analysis outputs
- ✓ Verifies the adapter is working correctly

**Expected output:**
```
✓ End-to-End Test PASSED
✓ Mode used: lora
Generated files:
  - analysis_summary.html
  - analysis_detailed.html
```

## Full Workflow

```bash
# Terminal 1: Start services with new adapter
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

# Wait for: "AI Advisor Service ready on http://0.0.0.0:5100"

# Terminal 2 (once services are ready): Run the test
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora

# Optional: Compare all modes
python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare
```

## Alternative: Using Python Directly

If you prefer to use Python instead of the shell script:

```bash
python3 scripts/start_services.py --mode=lora --lora-path=./adapters/ansel
```

Or using the other startup script:

```bash
python3 -u scripts/start_services.py start-comprehensive
```

## Verify the Adapter

Before running the test, verify the adapter is correct:

```bash
cat adapters/ansel/training_config.json
```

Should show:
```json
{
  "epochs": 10,
  "num_examples": 21,
  "learning_rate": 5e-05
}
```

If this shows different values or the old philosophy text data, something went wrong.

## Mode Options

Your script supports multiple modes:

| Mode | Command | Use Case |
|------|---------|----------|
| Base | `./mondrian.sh --mode=base` | Base model only |
| RAG | `./mondrian.sh --mode=rag` | Base model + RAG |
| LoRA | `./mondrian.sh --mode=lora --lora-path=./adapters/ansel` | **Your new adapter** ✓ |
| LoRA+RAG | `./mondrian.sh --mode=lora+rag --lora-path=./adapters/ansel` | LoRA + retrieval |
| A/B Test | `./mondrian.sh --mode=ab-test --lora-path=./adapters/ansel` | Random split |

## Troubleshooting

### Services won't start
```bash
# Kill any existing services
pkill -f ai_advisor_service
pkill -f job_service

# Try again
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel
```

### Adapter not found error
```bash
# Verify adapter exists
ls -lh adapters/ansel/

# Should show:
# adapters.safetensors (23MB)
# adapter_config.json
# training_config.json
```

### Test says mode is not lora
Check the service was started with LoRA mode:
```bash
tail -50 logs/ai_advisor_service_*.log | grep "MODE\|model_mode\|LoRA"
```

Should see:
```
[MODE] LoRA fine-tuned model
model_mode=fine_tuned
LoRA adapter successfully applied
```

## Summary

**Your commands are correct!**

1. Start: `./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel`
2. Test: `python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora`
3. Verify: Look for ✓ in test output

You're all set! 🚀
