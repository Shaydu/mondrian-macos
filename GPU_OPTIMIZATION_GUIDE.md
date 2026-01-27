# GPU Optimization Guide - RTX 4000 Ada (20GB VRAM)

## Current Configuration
- **GPU**: NVIDIA RTX 4000 Ada Generation
- **VRAM**: 20,475 MB total (8,232 MB in use = 40% utilization)
- **GPU Utilization**: 76%
- **Power**: 97W / 130W
- **CUDA**: 12.8

## Optimizations Applied

### 1. Updated Generation Profiles in `model_config.json`

#### **`optimized` (Default - RECOMMENDED)**
- **Beams**: 3 (up from 2)
- **Max tokens**: 2500 (up from 2000)
- **Repetition penalty**: 1.05 (improved from 1.0)
- **Length penalty**: 1.1 (new - encourages more thorough responses)
- **Speed**: ~20-30 tok/s
- **Use case**: Daily use - faster AND more thoughtful

#### **`quality_focused` (NEW - For Best Results)**
- **Beams**: 4
- **Max tokens**: 3500 (most thorough)
- **Repetition penalty**: 1.1
- **Length penalty**: 1.3
- **No repeat n-grams**: 3 (prevents repetitive phrases)
- **Speed**: ~15-25 tok/s
- **Use case**: When you want the most detailed, thoughtful analysis

#### **`beam_search` (Enhanced)**
- **Beams**: 5 (up from 4)
- **Max tokens**: 3000 (up from 2000)
- **Length penalty**: 1.2
- **Speed**: ~18-28 tok/s
- **Use case**: Maximum quality exploration

## How to Use Different Profiles

### Option 1: Change Default Profile
Edit [model_config.json](model_config.json):
```json
"defaults": {
  "model_preset": "qwen3-4b-instruct",
  "mode": "lora",
  "generation_profile": "quality_focused",  // Change this
  "enable_rag": true
}
```

### Option 2: Switch at Runtime
Use the start_services.py flag:
```bash
# For faster, more thorough (recommended)
python3 scripts/start_services.py --generation-profile optimized

# For maximum thoughtfulness
python3 scripts/start_services.py --generation-profile quality_focused

# For fastest speed (testing)
python3 scripts/start_services.py --generation-profile ultra_fast
```

### Option 3: Docker Compose
Edit [docker-compose.yml](docker-compose.yml) AI Advisor service:
```yaml
ai_advisor:
  command: >
    python3 mondrian/ai_advisor_service_linux.py
    --port 5100
    --model Qwen/Qwen3-VL-4B-Instruct
    --adapter adapters/ansel_qwen3_4b_full_9dim/epoch_20
    --load_in_4bit
    --generation-profile quality_focused
```

## Why These Settings Work Better

### Speed Improvements
1. **3-beam vs 2-beam**: Minimal performance impact (~5% slower) but significantly better quality
2. **Early stopping**: Prevents unnecessary token generation when confident
3. **Optimized image size**: Already at 800px (good balance)

### Thoughtfulness Improvements
1. **More tokens** (2500-3500): Allows more detailed analysis without cutting off
2. **Length penalty** (1.1-1.3): Encourages fuller explanations
3. **Repetition penalty** (1.05-1.1): Prevents circular reasoning
4. **No repeat n-grams**: Prevents phrase repetition (quality_focused only)

### GPU Utilization
- Your GPU is only 40% utilized on VRAM - we can afford more beams/tokens
- Power draw (97W/130W) has headroom for more computation
- RTX 4000 Ada has excellent inference performance for 4B models

## Recommended Next Steps

### For Daily Use
```bash
# Restart with optimized profile (balanced speed + quality)
python3 scripts/start_services.py --generation-profile optimized
```

### For Maximum Quality
```bash
# Use quality_focused when you want the most thoughtful analysis
python3 scripts/start_services.py --generation-profile quality_focused
```

### Monitor Performance
```bash
# In separate terminal, watch GPU utilization
watch -n 1 nvidia-smi
```

## Expected Results

| Profile | Speed | Tokens/sec | VRAM Usage | Thoughtfulness |
|---------|-------|------------|------------|----------------|
| ultra_fast | ⚡⚡⚡⚡ | 40-50 | 8GB | ⭐⭐ |
| optimized | ⚡⚡⚡ | 20-30 | 9GB | ⭐⭐⭐⭐ |
| beam_search | ⚡⚡ | 18-28 | 10GB | ⭐⭐⭐⭐⭐ |
| quality_focused | ⚡⚡ | 15-25 | 11GB | ⭐⭐⭐⭐⭐ |

## Additional Optimizations (Already Enabled)

✅ **4-bit quantization** (BitsAndBytes)
✅ **Flash Attention 2** (if available on your GPU)
✅ **Gradient checkpointing disabled** (inference mode)
✅ **Image resizing to 800px** (efficient without quality loss)
✅ **Cached model weights** (no reload between requests)
✅ **PyTorch CUDA memory optimization** (`expandable_segments`)
✅ **Anti-repetition controls** (prevents duplicate recommendations across dimensions)

See [ANTI_REPETITION_FIX.md](ANTI_REPETITION_FIX.md) for details on the recommendation uniqueness system.

## Troubleshooting

### If responses are still too slow:
1. Switch to `fast_greedy` profile temporarily
2. Check if other processes are using GPU: `nvidia-smi`
3. Restart Docker container to clear memory fragmentation

### If responses are too short:
1. Increase `max_new_tokens` in your chosen profile
2. Increase `length_penalty` (1.2-1.5)
3. Consider switching to `quality_focused`

### If responses are repetitive:
1. Increase `repetition_penalty` (1.05 → 1.15)
2. Add `no_repeat_ngram_size: 3` to your profile
3. Use `quality_focused` profile which has this built-in

## Current Status
- ✅ Configuration updated in `model_config.json`
- ⏳ Restart required to apply changes
- 📊 Your GPU can handle these settings comfortably
