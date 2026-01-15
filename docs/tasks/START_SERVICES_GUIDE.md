# How to Start Services with Different Modes

The Mondrian services can be started with different analysis modes. Here's the complete guide:

## Overview

There are 4 main analysis modes available:
1. **baseline** - Fast, base model only (default)
2. **rag** - Base model + retrieval-augmented generation with similar images
3. **lora** - LoRA fine-tuned adapter (requires trained adapter)
4. **rag_lora** - LoRA fine-tuned adapter + RAG (best quality, slowest)

And 3 model strategies for the service itself:
- **base** - Always use base model (default)
- **fine_tuned** - Always use LoRA adapter (requires `--lora_path`)
- **ab_test** - Random split between base and fine-tuned (A/B testing)

## Starting Services

### Stop Running Services (if any)
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 start_services.py --stop
```

### 1. BASELINE Mode (Default - Fastest)
Base model without any fine-tuning or RAG:
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 start_services.py
```

Then test with:
```bash
cd /Users/shaydu/dev/mondrian-macos
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode baseline
```

### 2. RAG Mode (Base model + Similar Images)
Base model with retrieval-augmented generation:
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 start_services.py
```

The AI Advisor Service will use RAG by default if the environment variable is set. To test:
```bash
cd /Users/shaydu/dev/mondrian-macos
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode rag
```

### 3. LORA Mode (Fine-tuned adapter only)
**Important**: This requires a trained LoRA adapter at `adapters/ansel/adapters.safetensors`

Start the service with LoRA enabled:
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py --port 5100 --model_mode fine_tuned --lora_path ./adapters/ansel &
python3 job_service_v2.3.py --port 5005 &
```

Or use the helper (if you modify start_services.py):
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 start_services.py
```

Then test with:
```bash
cd /Users/shaydu/dev/mondrian-macos
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode lora
```

### 4. RAG + LORA Mode (Fine-tuned + Similar Images - Best Quality)
Combines LoRA fine-tuning with RAG retrieval:
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py --port 5100 --model_mode fine_tuned --lora_path ./adapters/ansel &
python3 job_service_v2.3.py --port 5005 &
```

Then test with (the test script will automatically combine them):
```bash
cd /Users/shaydu/dev/mondrian-macos
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode rag_lora
```

## Manual Service Commands

### Start Job Service
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 job_service_v2.3.py --port 5005
```

### Start AI Advisor Service (Baseline)
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py --port 5100
```

### Start AI Advisor Service (LoRA Fine-tuned)
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py \
  --port 5100 \
  --model_mode fine_tuned \
  --lora_path ./adapters/ansel
```

### Start AI Advisor Service (A/B Testing)
Route 50% of requests to fine-tuned, 50% to base:
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py \
  --port 5100 \
  --model_mode ab_test \
  --lora_path ./adapters/ansel \
  --ab_test_split 0.5
```

Route 70% to fine-tuned, 30% to base:
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 ai_advisor_service.py \
  --port 5100 \
  --model_mode ab_test \
  --lora_path ./adapters/ansel \
  --ab_test_split 0.7
```

## Testing Different Modes

### Full E2E Comparison Test
Compare baseline vs LoRA side-by-side:
```bash
cd /Users/shaydu/dev/mondrian-macos
python3 test_lora_e2e.py \
  --image source/mike-shrub-01004b68.jpg \
  --advisor ansel \
  --compare
```

This will:
1. Start LoRA analysis
2. Wait 5 seconds
3. Start baseline analysis
4. Generate side-by-side comparison HTML

### Test with Different Advisors
If you have adapters for other advisors:
```bash
python3 test_lora_e2e.py --image source/test.jpg --advisor adams --mode lora
python3 test_lora_e2e.py --image source/test.jpg --advisor cartier --mode lora
```

## Available LoRA Adapters

Check which advisors have trained adapters:
```bash
ls -la /Users/shaydu/dev/mondrian-macos/adapters/
```

Each advisor directory should contain:
- `adapters.safetensors` - The LoRA adapter weights
- `training_config.json` - Configuration from training
- `adapter_config.json` - LoRA configuration

## Environment Variables

### RAG Control
```bash
export RAG_ENABLED=true   # Enable RAG by default
export RAG_ENABLED=false  # Disable RAG by default
```

### MLX Configuration
```bash
export MLX_USE_CPU=1           # Force CPU mode (slower)
# Don't set this - use Metal GPU by default on Mac
```

## Troubleshooting

### LORA mode returns N/A grades
Check the logs to see if the adapter is loading:
```bash
tail -f /Users/shaydu/dev/mondrian-macos/logs/ai_advisor_service_*.log
```

Look for lines like:
```
[INFO] Model Strategy: FINE-TUNED
[INFO] Loading LoRA adapter from: ./adapters/ansel
[LoRA] Applying adapter from: /path/to/adapters/ansel
```

### No summary/detailed output
This usually means the JSON response format wasn't converted properly. With the recent fix, this should be resolved. Check the debug logs:
```
[LoRA DEBUG] Parsed JSON keys: [...]
[LoRA DEBUG] dimensions type: ...
```

### Services won't start
Make sure ports 5005 and 5100 are not in use:
```bash
# Kill old processes
python3 /Users/shaydu/dev/mondrian-macos/mondrian/start_services.py --stop

# Or manually
lsof -i :5005
lsof -i :5100
```

### Out of memory with LoRA
The fine-tuned model uses more VRAM. If you run out of memory:
1. Close other applications
2. Try baseline mode instead
3. Use smaller images

## Quick Commands Reference

| Mode | Command |
|------|---------|
| Baseline | `python3 test_lora_e2e.py --image source/test.jpg --advisor ansel --mode baseline` |
| RAG | `python3 test_lora_e2e.py --image source/test.jpg --advisor ansel --mode rag` |
| LoRA | `python3 test_lora_e2e.py --image source/test.jpg --advisor ansel --mode lora` |
| RAG+LoRA | `python3 test_lora_e2e.py --image source/test.jpg --advisor ansel --mode rag_lora` |
| Compare | `python3 test_lora_e2e.py --image source/test.jpg --advisor ansel --compare` |

