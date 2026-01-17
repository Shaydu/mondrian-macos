# Model Switching - Quick Reference

## Start Here

```bash
# Default (Qwen3-VL-4B-Instruct)
./mondrian.sh --restart

# Switch to Thinking Model (shows reasoning)
./mondrian.sh --restart --model-preset=qwen3-4b-thinking

# Switch to 8B Model (better quality)
./mondrian.sh --restart --model-preset=qwen3-8b-instruct
```

## All Commands

| Command | What It Does |
|---------|-------------|
| `./mondrian.sh --restart` | Use default model (4B Instruct) |
| `./mondrian.sh --restart --model-preset=qwen3-4b-thinking` | Use thinking model |
| `./mondrian.sh --restart --model-preset=qwen3-8b-instruct` | Use 8B model |
| `./mondrian.sh --restart --model-preset=qwen3-8b-thinking` | Use 8B thinking model |
| `./mondrian.sh --help` | Show all options |
| `./mondrian.sh --stop` | Stop services |
| `./mondrian.sh --status` | Show active jobs |

## Available Models

| Preset | Model | Speed | Reasoning? | Best For |
|--------|-------|-------|-----------|----------|
| `qwen3-4b-instruct` | 4B Instruct | Fast ⚡ | No | Default, real-time |
| `qwen3-4b-thinking` | 4B Thinking | Slow | Yes | Shows thinking |
| `qwen3-8b-instruct` | 8B Instruct | Fast | No | Better quality |
| `qwen3-8b-thinking` | 8B Thinking | Slow | Yes | Best quality + thinking |

## Configuration File

Edit `model_config.json` to:
- Add new models
- Change defaults
- Modify adapter paths

```json
{
  "models": {
    "qwen3-4b-thinking": {
      "model_id": "Qwen/Qwen3-VL-4B-Thinking",
      "adapter": "./adapters/ansel_qwen3_4b_thinking"
    }
  },
  "defaults": {
    "model_preset": "qwen3-4b-instruct"
  }
}
```

## Common Tasks

### Switch between Instruct and Thinking
```bash
# Fast, no reasoning
./mondrian.sh --restart --model-preset=qwen3-4b-instruct

# Slower, shows reasoning
./mondrian.sh --restart --model-preset=qwen3-4b-thinking
```

### Use larger model
```bash
./mondrian.sh --restart --model-preset=qwen3-8b-instruct
```

### Get best quality
```bash
./mondrian.sh --restart --model-preset=qwen3-8b-thinking
```

### Use custom model (override config)
```bash
./mondrian.sh --restart --model="Qwen/Custom" --lora-path=./custom_adapter
```

### A/B test models
```bash
./mondrian.sh --restart --model-preset=qwen3-4b-thinking --mode=ab-test --ab-split=0.5
```

## Scripts That Changed

✅ `model_config.json` - NEW (holds all model configs)
✅ `mondrian.sh` - UPDATED (reads config, accepts --model-preset)
✅ `scripts/start_services.py` - UPDATED (help text only)

## Key Features

- **No Hard-Coding**: All models in JSON config
- **Easy Switching**: One flag to change models
- **Extensible**: Add new models by editing JSON
- **Backward Compatible**: Old `--model` flag still works

## Troubleshooting

**Model takes too long to load**
- First time downloads from HuggingFace (~5-10 GB)
- Next time uses cached version
- Check GPU: `nvidia-smi`

**"Unknown model preset"**
- Check spelling
- See available presets: `./mondrian.sh --help`

**Adapter not found**
- Make sure it exists: `ls ./adapters/ansel_qwen3_4b_thinking/`
- Or train it: `python train_lora_qwen3vl.py --base_model "Qwen/Qwen3-VL-4B-Thinking" --data_dir ./training/datasets/ansel_combined_train.jsonl --output_dir ./adapters/ansel_qwen3_4b_thinking --epochs 3`

## Files to Know

| File | Purpose |
|------|---------|
| `model_config.json` | All model configurations |
| `mondrian.sh` | Launcher script (reads config) |
| `scripts/start_services.py` | Services startup |
| `MODEL_SWITCHING_GUIDE.md` | Detailed guide |
| `CONFIGURATION_CHANGES.md` | What changed |

## Next Steps

1. Try switching models: `./mondrian.sh --restart --model-preset=qwen3-4b-thinking`
2. Upload a test image to see thinking output
3. Train new adapters if needed
4. Add them to `model_config.json`

That's it! 🎉
