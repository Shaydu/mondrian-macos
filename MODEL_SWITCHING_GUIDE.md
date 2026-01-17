# Model Configuration and Switching Guide

## Overview

Mondrian now supports easy model and adapter configuration through `model_config.json`. No more hard-coded model paths!

## Configuration File: `model_config.json`

The `model_config.json` file contains all available model presets with their corresponding adapters.

```json
{
  "models": {
    "qwen3-4b-instruct": {
      "model_id": "Qwen/Qwen3-VL-4B-Instruct",
      "adapter": "./adapters/ansel_qwen3_4b_10ep",
      "description": "Fast, optimized for speed",
      "reasoning": false
    },
    "qwen3-4b-thinking": {
      "model_id": "Qwen/Qwen3-VL-4B-Thinking",
      "adapter": "./adapters/ansel_qwen3_4b_thinking",
      "description": "Shows step-by-step reasoning",
      "reasoning": true
    }
  },
  "defaults": {
    "model_preset": "qwen3-4b-instruct"
  }
}
```

## Quick Start: Model Switching

### Default (No Arguments)
```bash
./mondrian.sh --restart
# Uses: Qwen3-VL-4B-Instruct + ansel_qwen3_4b_10ep LoRA
```

### Switch to Thinking Model (Visible Reasoning)
```bash
./mondrian.sh --restart --model-preset=qwen3-4b-thinking
# Uses: Qwen3-VL-4B-Thinking + ansel_qwen3_4b_thinking LoRA
```

### Switch to 8B Model (Better Quality)
```bash
./mondrian.sh --restart --model-preset=qwen3-8b-instruct
# Uses: Qwen3-VL-8B-Instruct + ansel_qwen3_8b_instruct LoRA
```

### Switch to 8B Thinking Model (Best Quality + Reasoning)
```bash
./mondrian.sh --restart --model-preset=qwen3-8b-thinking
# Uses: Qwen3-VL-8B-Thinking + ansel_qwen3_8b_thinking LoRA
```

## Understanding Model Presets

### Available Presets

| Preset | Model | Speed | Quality | Reasoning | Best For |
|--------|-------|-------|---------|-----------|----------|
| `qwen3-4b-instruct` | 4B Instruct | Fast | Good | No | Default, real-time |
| `qwen3-4b-thinking` | 4B Thinking | Slower | Good | Yes | Analysis with reasoning |
| `qwen3-8b-instruct` | 8B Instruct | Fast | Excellent | No | Better quality |
| `qwen3-8b-thinking` | 8B Thinking | Slower | Best | Yes | Best quality + reasoning |

### What Gets Configured?

When you specify a model preset, it automatically configures:
- **Model**: Which LLM to load (from HuggingFace)
- **Adapter**: Which LoRA weights to apply
- **Description**: What the preset does

```bash
./mondrian.sh --restart --model-preset=qwen3-4b-thinking
# This automatically sets:
#   Model: Qwen/Qwen3-VL-4B-Thinking
#   Adapter: ./adapters/ansel_qwen3_4b_thinking
```

## Advanced Usage

### Override Model (Ignore Preset)
```bash
./mondrian.sh --restart --model="Qwen/Custom-Model" --lora-path=./adapters/custom
# Ignores --model-preset, uses custom model
```

### Override Adapter (Keep Preset)
```bash
./mondrian.sh --restart --model-preset=qwen3-4b-thinking --lora-path=./adapters/custom_ansel
# Uses Thinking model with custom adapter
```

### Use Without LoRA (Base Model Only)
```bash
./mondrian.sh --restart --model-preset=qwen3-4b-thinking --mode=base
# Uses Thinking model without LoRA adapter
```

### Enable RAG with Model Preset
```bash
./mondrian.sh --restart --model-preset=qwen3-4b-thinking --mode=lora+rag
# Uses Thinking model + LoRA + RAG
```

### A/B Test Two Models
```bash
./mondrian.sh --restart --model-preset=qwen3-4b-thinking --mode=ab-test --ab-split=0.5
# 50% of requests get Thinking, 50% get base model
```

## Adding New Model Presets

To add a new model, edit `model_config.json`:

```json
{
  "models": {
    "my-new-model": {
      "name": "My Custom Model",
      "model_id": "Qwen/Custom-Model-ID",
      "description": "My model description",
      "adapter": "./adapters/my_custom_adapter",
      "speed": "fast",
      "quality": "excellent",
      "reasoning": true,
      "tokens_per_sec": "20-30 (BF16)"
    }
  }
}
```

Then use it:
```bash
./mondrian.sh --restart --model-preset=my-new-model
```

## Changing Defaults

Edit `model_config.json`:

```json
{
  "defaults": {
    "model_preset": "qwen3-4b-thinking",  # Change default here
    "mode": "lora"
  }
}
```

Then:
```bash
./mondrian.sh --restart
# Now uses qwen3-4b-thinking by default
```

## View Available Presets

```bash
./mondrian.sh --help
```

Shows all available model presets and their descriptions.

## Scripts That Were Updated

### 1. `mondrian.sh`
- Added `--model-preset` argument
- Loads `model_config.json` automatically
- Extracts model ID and adapter path from config
- Displays current configuration on startup

### 2. `scripts/start_services.py`
- Updated help text with model preset information
- No functional changes needed (already accepts `--model` and `--adapter`)
- Documentation updated to explain presets

## How It Works (Architecture)

```
User Command:
./mondrian.sh --restart --model-preset=qwen3-4b-thinking
    ↓
mondrian.sh reads model_config.json
    ↓
Extracts:
  - model_id: "Qwen/Qwen3-VL-4B-Thinking"
  - adapter: "./adapters/ansel_qwen3_4b_thinking"
    ↓
Passes to start_services.py:
  --model="Qwen/Qwen3-VL-4B-Thinking"
  --adapter="./adapters/ansel_qwen3_4b_thinking"
    ↓
start_services.py passes to ai_advisor_service_linux.py:
  --model="Qwen/Qwen3-VL-4B-Thinking"
  --adapter="./adapters/ansel_qwen3_4b_thinking"
    ↓
ai_advisor_service_linux.py loads model and adapter
    ↓
Service ready to analyze images
```

## Troubleshooting

### "ERROR: Unknown model preset"
Check the preset name in `model_config.json`:
```bash
./mondrian.sh --help
# Lists all available presets
```

### Model takes too long to load
- Check GPU is available: `nvidia-smi`
- Larger models (8B) take longer than 4B
- First load downloads model from HuggingFace

### Adapter path not found
Make sure the adapter exists:
```bash
ls -la ./adapters/ansel_qwen3_4b_thinking/
# Should show: adapter_model.safetensors
```

### Want to create new adapter?
Train it first:
```bash
python train_lora_qwen3vl.py \
  --base_model "Qwen/Qwen3-VL-4B-Thinking" \
  --data_dir ./training/datasets/ansel_combined_train.jsonl \
  --output_dir ./adapters/ansel_qwen3_4b_thinking \
  --epochs 3
```

Then add to `model_config.json`:
```json
{
  "models": {
    "qwen3-4b-thinking": {
      "model_id": "Qwen/Qwen3-VL-4B-Thinking",
      "adapter": "./adapters/ansel_qwen3_4b_thinking"
    }
  }
}
```

## Environment Variables

Model switching respects existing environment variables:
- `CUDA_VISIBLE_DEVICES` - GPU selection
- `ANALYSIS_MODE` - Set by start_services.py based on mode
- `PYTHONPATH` - Set by mondrian.sh

Example:
```bash
CUDA_VISIBLE_DEVICES=0 ./mondrian.sh --restart --model-preset=qwen3-4b-thinking
```

## Comparison: Before vs After

### Before (Hard-coded)
```bash
# Had to edit scripts to change models
# No easy way to switch between Instruct and Thinking
./mondrian.sh --restart --model="Qwen/Qwen3-VL-4B-Thinking" --lora-path=./adapters/ansel_qwen3_4b_thinking
```

### After (Configuration)
```bash
# Just specify the preset
./mondrian.sh --restart --model-preset=qwen3-4b-thinking
```

Much easier!

## Summary

- ✅ Edit `model_config.json` to add/modify model presets
- ✅ Use `--model-preset=<name>` to switch models
- ✅ No hard-coded paths anymore
- ✅ Easy to manage multiple models and adapters
- ✅ One command to switch between Instruct and Thinking
- ✅ Supports A/B testing between presets
