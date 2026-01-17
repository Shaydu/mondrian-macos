# Configuration System Changes Summary

## What Was Changed

### 1. **New File: `model_config.json`** ✅
   - Central configuration for all model presets
   - Defines: model ID, adapter path, description, capabilities
   - Easily extendable for new models
   - **Location**: `/home/doo/dev/mondrian-macos/model_config.json`

### 2. **Updated: `mondrian.sh`** ✅
   - Added `--model-preset=<name>` argument
   - Reads `model_config.json` to get model/adapter info
   - Extracts model ID and adapter path from config
   - Falls back to defaults if not specified
   - **Changes**: Lines 42-83

### 3. **Updated: `scripts/start_services.py`** ✅
   - Updated help text to document model presets
   - No code changes needed (already flexible)
   - **Changes**: Lines 780-838

### 4. **New File: `MODEL_SWITCHING_GUIDE.md`** ✅
   - Complete user guide for model switching
   - Examples for all use cases
   - Troubleshooting section
   - Architecture explanation

## Files Modified

| File | Type | Changes |
|------|------|---------|
| `model_config.json` | NEW | JSON config with 4 model presets |
| `mondrian.sh` | UPDATED | Added model preset loading logic |
| `scripts/start_services.py` | UPDATED | Updated help documentation |
| `MODEL_SWITCHING_GUIDE.md` | NEW | User guide and examples |

## Key Features Implemented

✅ **Configuration-Based**: All models defined in `model_config.json`
✅ **No Hard-Coding**: Model paths extracted from config at runtime
✅ **Easy Switching**: One flag to change between Instruct/Thinking models
✅ **Extensible**: Add new models by editing JSON config
✅ **Backward Compatible**: `--model` and `--lora-path` still work for overrides
✅ **Smart Defaults**: Falls back to default preset if not specified

## How the System Works

### Configuration File
```json
{
  "models": {
    "qwen3-4b-instruct": {
      "model_id": "Qwen/Qwen3-VL-4B-Instruct",
      "adapter": "./adapters/ansel_qwen3_4b_10ep",
      ...
    },
    "qwen3-4b-thinking": {
      "model_id": "Qwen/Qwen3-VL-4B-Thinking",
      "adapter": "./adapters/ansel_qwen3_4b_thinking",
      ...
    }
  },
  "defaults": {
    "model_preset": "qwen3-4b-instruct"
  }
}
```

### Usage
```bash
# Default preset
./mondrian.sh --restart

# Switch to thinking model
./mondrian.sh --restart --model-preset=qwen3-4b-thinking

# Override with custom model
./mondrian.sh --restart --model="Qwen/Custom" --lora-path=./custom
```

### Code Flow in `mondrian.sh`
1. Parse `--model-preset=<name>` from command line
2. Read `model_config.json`
3. Extract `model_id` and `adapter` for that preset
4. Pass to `start_services.py` as `--model` and `--adapter`
5. `start_services.py` passes to `ai_advisor_service_linux.py`

## Before vs After

### Before
```bash
# Had to hard-code in mondrian.sh
DEFAULT_LORA_PATH="./adapters/ansel_qwen3_4b_10ep"
MODEL_ARG="Qwen/Qwen3-VL-4B-Instruct"

# To switch models, had to edit scripts
# Or use long command line:
./mondrian.sh --restart --model="Qwen/Qwen3-VL-4B-Thinking" --lora-path=./adapters/ansel_qwen3_4b_thinking
```

### After
```bash
# All models in config file, easy to modify
# Just use a simple flag
./mondrian.sh --restart --model-preset=qwen3-4b-thinking

# Add new models by editing model_config.json
# No script changes needed
```

## Quick Commands

```bash
# Show help and available presets
./mondrian.sh --help

# Use default model (Qwen3-VL-4B-Instruct)
./mondrian.sh --restart

# Switch to thinking model
./mondrian.sh --restart --model-preset=qwen3-4b-thinking

# Switch to 8B model
./mondrian.sh --restart --model-preset=qwen3-8b-instruct

# A/B test between models
./mondrian.sh --restart --model-preset=qwen3-4b-thinking --mode=ab-test --ab-split=0.5
```

## Adding a New Model

1. **Train the LoRA adapter** (if needed)
   ```bash
   python train_lora_qwen3vl.py \
     --base_model "Qwen/Your-Model" \
     --data_dir ./training/datasets/ansel_combined_train.jsonl \
     --output_dir ./adapters/your_model_adapter
   ```

2. **Add to `model_config.json`**
   ```json
   "your-model": {
     "name": "Your Model Name",
     "model_id": "Qwen/Your-Model",
     "adapter": "./adapters/your_model_adapter",
     "description": "Your description",
     "speed": "fast",
     "quality": "excellent",
     "reasoning": true
   }
   ```

3. **Use immediately**
   ```bash
   ./mondrian.sh --restart --model-preset=your-model
   ```

## Configuration Hierarchy

1. **Command line arguments** (highest priority)
   - `--model="Qwen/Custom"` overrides preset
   - `--lora-path="./custom"` overrides preset

2. **Model preset** (from --model-preset)
   - Gets model_id and adapter from config

3. **Default preset** (from model_config.json defaults)
   - Used if no --model-preset specified

4. **Hard-coded defaults** (lowest priority)
   - Only if config file is missing

## Backward Compatibility

The system is fully backward compatible:
- Old commands still work: `./mondrian.sh --restart --model="..." --lora-path="..."`
- `--model` and `--lora-path` override preset system
- Defaults still apply if nothing specified

## Testing the New System

```bash
# Test default
./mondrian.sh --restart
# Verify: Uses qwen3-4b-instruct

# Test switching presets
./mondrian.sh --restart --model-preset=qwen3-4b-thinking
# Verify: Uses qwen3-4b-thinking

# Test help
./mondrian.sh --help
# Verify: Shows available presets

# Test override
./mondrian.sh --restart --model-preset=qwen3-4b-thinking --model="Qwen/Custom"
# Verify: Uses custom model, not preset
```

## Files to Review

1. **`model_config.json`** - Central configuration
2. **`mondrian.sh`** (lines 42-83) - Config loading logic
3. **`scripts/start_services.py`** (lines 780-838) - Updated help text
4. **`MODEL_SWITCHING_GUIDE.md`** - Complete user documentation

## Next Steps for User

1. Review `model_config.json` to understand available presets
2. Read `MODEL_SWITCHING_GUIDE.md` for usage examples
3. Try switching models: `./mondrian.sh --restart --model-preset=qwen3-4b-thinking`
4. Train new LoRA adapters as needed
5. Add them to `model_config.json` for easy switching

## Questions?

- **How to switch?** → See `MODEL_SWITCHING_GUIDE.md`
- **How to add a model?** → Edit `model_config.json`
- **How to change defaults?** → Edit `model_config.json` defaults section
- **How to override?** → Use `--model` and `--lora-path` arguments
