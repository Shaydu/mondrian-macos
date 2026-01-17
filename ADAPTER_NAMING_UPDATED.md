# Updated Adapter Naming Convention

## New Structure

**Pattern:** `adapters/{advisor_id}/{model_name}-adapter`

Example with `--advisor ansel --model qwen3-4b-thinking`:
```
/home/doo/dev/mondrian-macos/adapters/ansel/qwen3-4b-thinking-adapter/
```

---

## Naming Mapping

All model presets now map to clear adapter names:

| Command | Model | Adapter Name | Full Path |
|---------|-------|-------------|-----------|
| `--model qwen3-4b` | Qwen/Qwen3-VL-4B-Instruct | `qwen3-4b-adapter` | `adapters/ansel/qwen3-4b-adapter/` |
| `--model qwen3-4b-thinking` | Qwen/Qwen3-VL-4B-Thinking | `qwen3-4b-thinking-adapter` | `adapters/ansel/qwen3-4b-thinking-adapter/` |
| `--model qwen2-2b` | Qwen/Qwen2-VL-2B-Instruct | `qwen2-2b-adapter` | `adapters/ansel/qwen2-2b-adapter/` |
| `--model qwen2-7b` | Qwen/Qwen2-VL-7B-Instruct | `qwen2-7b-adapter` | `adapters/ansel/qwen2-7b-adapter/` |

---

## Directory Structure

### Old Structure (Confusing)
```
adapters/
├── ansel/                 ← ambiguous (which model?)
├── ansel_thinking/        ← "thinking" suffix unclear
├── ansel_qwen2_2b/        ← inconsistent naming
└── ansel_qwen3_4b_10ep/   ← epoch in path confusing
```

### New Structure (Clear)
```
adapters/
├── ansel/
│   ├── qwen3-4b-adapter/
│   │   ├── epoch_1/
│   │   ├── epoch_2/
│   │   └── epoch_10/
│   │       ├── adapter_config.json
│   │       ├── adapter_model.safetensors
│   │       └── README.md
│   ├── qwen3-4b-thinking-adapter/
│   │   ├── epoch_1/
│   │   └── epoch_10/
│   ├── qwen2-2b-adapter/
│   └── qwen2-7b-adapter/
├── someotherAd visor/
│   ├── qwen3-4b-adapter/
│   └── qwen3-4b-thinking-adapter/
```

---

## Benefits of New Naming

1. **Model-Aligned** - Name matches model ID (qwen3-4b-thinking-adapter ↔ Qwen3-VL-4B-Thinking)
2. **Advisor-Scoped** - Each advisor has their own adapters subdirectory
3. **Clear Intent** - `-adapter` suffix makes it obvious these are LoRA adapters
4. **Scalable** - Easy to have multiple models per advisor
5. **Searchable** - Can grep for "-adapter" to find all adapters

---

## Using New Adapter Paths

### In model_config.json
```json
{
  "defaults": {
    "model_preset": "qwen3-4b-instruct"
  },
  "models": {
    "qwen3-4b-thinking": {
      "adapter": "./adapters/ansel/qwen3-4b-thinking-adapter/epoch_10"
    }
  }
}
```

### In Training Script
```bash
python training/train_lora_pytorch.py --advisor ansel --model qwen3-4b-thinking
# Output: /home/doo/dev/mondrian-macos/adapters/ansel/qwen3-4b-thinking-adapter/
```

### In AI Service
```bash
python mondrian/ai_advisor_service_linux.py \
    --model Qwen/Qwen3-VL-4B-Thinking \
    --adapter ./adapters/ansel/qwen3-4b-thinking-adapter/epoch_10
```

---

## Migration Guide

### If You Have Old Adapters
The old adapter directories will still work until you retrain. When you retrain:

```bash
# Old location (no longer used after update):
# adapters/ansel_thinking/

# New location (will be created by updated script):
# adapters/ansel/qwen3-4b-thinking-adapter/
```

### To Keep Using Old Adapters Temporarily
Update `model_config.json` to point to old paths:
```json
{
  "qwen3-4b-thinking": {
    "adapter": "./adapters/ansel_thinking/epoch_10"
  }
}
```

### To Migrate to New Structure
1. Retrain with updated script: `python training/train_lora_pytorch.py --advisor ansel --model qwen3-4b-thinking`
2. New adapter saves to: `adapters/ansel/qwen3-4b-thinking-adapter/epoch_10`
3. Update `model_config.json` to use new path
4. Restart services

---

## Code Changes

### File: `training/train_lora_pytorch.py`

#### Change 1: Model Presets (lines 42-63)
```python
# OLD:
"adapter_suffix": "_thinking"

# NEW:
"adapter_name": "qwen3-4b-thinking-adapter"
```

#### Change 2: Adapter Resolution (lines 285-288)
```python
# OLD:
adapter_suffix = preset["adapter_suffix"]

# NEW:
adapter_name = preset["adapter_name"]
```

#### Change 3: Output Path (line 299)
```python
# OLD:
output_path = PROJECT_ROOT / "adapters" / f"{advisor_id}{adapter_suffix}"

# NEW:
output_path = PROJECT_ROOT / "adapters" / advisor_id / adapter_name
```

---

## Example: Training New Adapter

```bash
# Command
python training/train_lora_pytorch.py --advisor ansel --model qwen3-4b-thinking --epochs 10

# Output:
# Training Configuration shows:
# Advisor:      ansel
# Model:        Qwen/Qwen3-VL-4B-Thinking
# Output:       /home/doo/dev/mondrian-macos/adapters/ansel/qwen3-4b-thinking-adapter
#
# Results in:
# adapters/ansel/qwen3-4b-thinking-adapter/
# ├── epoch_1/
# ├── epoch_2/
# ├── ...
# └── epoch_10/  ← Use this path in model_config.json
```

---

## Clear Hierarchy

```
PROJECT_ROOT
├── adapters/              "All adapters"
│   ├── ansel/             "All Ansel's adapters"
│   │   ├── qwen3-4b-adapter/           "Ansel trained on Qwen3-4B"
│   │   └── qwen3-4b-thinking-adapter/  "Ansel trained on Qwen3-4B-Thinking"
│   ├── someoneelse/       "Another advisor's adapters"
│   │   ├── qwen3-4b-adapter/
│   │   └── qwen3-4b-thinking-adapter/
│
├── training/
│   ├── train_lora_pytorch.py  (Updated to use new naming)
│   └── datasets/
│       └── ansel_image_training_fixed.jsonl
│
└── mondrian/
    └── ai_advisor_service_linux.py (Uses adapter paths from config)
```

---

## Summary

- **Clear naming** - `{model}-adapter` clearly identifies what each adapter is for
- **Organized** - `adapters/{advisor}/{adapter_name}/` keeps things organized by person and model
- **Discoverable** - Easy to see at a glance what adapters exist for each advisor
- **Standard** - Matches HuggingFace conventions for adapter naming
- **Scalable** - Works with multiple advisors and models

