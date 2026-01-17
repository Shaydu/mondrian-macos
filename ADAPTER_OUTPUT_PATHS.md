# LoRA Adapter Output Paths

## Command
```bash
python training/train_lora_pytorch.py --advisor ansel --model qwen3-4b-thinking
```

## Output Directory Structure

### Root Directory
```
/home/doo/dev/mondrian-macos/adapters/ansel_thinking/
```

### Full Path
```
/home/doo/dev/mondrian-macos/adapters/ansel_thinking/epoch_10/
```

### Files in Final Adapter (epoch_10)
```
adapter_config.json         (1.0 KB)
adapter_model.safetensors   (23 MB)
README.md                   (5.1 KB)
```

---

## How Output Path is Determined

### From `train_lora_pytorch.py` (line 299)
```python
output_path = PROJECT_ROOT / "adapters" / f"{advisor_id}{adapter_suffix}"
```

### Breakdown
- **PROJECT_ROOT** = `/home/doo/dev/mondrian-macos` (from line 39)
- **advisor_id** = `ansel` (from --advisor flag)
- **adapter_suffix** = `_thinking` (from MODEL_PRESETS, line 51)

### Result
```
PROJECT_ROOT / "adapters" / f"{ansel}{_thinking}"
= /home/doo/dev/mondrian-macos/adapters/ansel_thinking
```

---

## Training Checkpoints

Training saves a checkpoint at each epoch:

```
adapters/ansel_thinking/
├── epoch_1/
│   ├── adapter_config.json
│   ├── adapter_model.safetensors
│   └── README.md
├── epoch_2/
├── ...
├── epoch_9/
└── epoch_10/  ← FINAL (23 MB, most trained)
    ├── adapter_config.json
    ├── adapter_model.safetensors
    └── README.md
```

---

## Adapter Naming Convention

The adapter suffix is determined by the model preset:

| Command | Model | Suffix | Output Path |
|---------|-------|--------|-------------|
| `--model qwen3-4b` | Qwen3-VL-4B-Instruct | (empty) | `adapters/ansel` |
| `--model qwen3-4b-thinking` | Qwen3-VL-4B-Thinking | `_thinking` | `adapters/ansel_thinking` |
| `--model qwen2-2b` | Qwen2-VL-2B-Instruct | `_qwen2_2b` | `adapters/ansel_qwen2_2b` |
| `--model qwen2-7b` | Qwen2-VL-7B-Instruct | `_qwen2_7b` | `adapters/ansel_qwen2_7b` |

---

## Using the Adapter

### In Configuration (model_config.json)
```json
{
  "qwen3-4b-thinking": {
    "adapter": "./adapters/ansel_thinking/epoch_10"
  }
}
```

### In AI Service
```bash
python mondrian/ai_advisor_service_linux.py \
    --model Qwen/Qwen3-VL-4B-Thinking \
    --adapter ./adapters/ansel_thinking/epoch_10
```

### In Training
```bash
# To resume from epoch 10 (not implemented, but structure is there)
# Would be created if you rerun training
```

---

## Current Adapters on Disk

```
adapters/
├── ansel/                          (qwen3-4b, original)
├── ansel_4b/                       (qwen3-4b variant)
├── ansel_image/                    (old)
├── ansel_old_broken_20260114_153100/
├── ansel_original/                 (backup)
├── ansel_qwen25_10ep/              (qwen2.5 model)
├── ansel_qwen2_7b_10ep/            (qwen2-7b)
├── ansel_qwen3_4b/                 (qwen3-4b variant)
├── ansel_qwen3_4b_10ep/            (qwen3-4b, 10 epochs)
└── ansel_thinking/                 (qwen3-4b-thinking) ← YOUR LATEST
    ├── epoch_1/
    ├── epoch_2/
    ├── ...
    └── epoch_10/  ← This is what's in model_config.json
```

---

## File Sizes

```
adapter_model.safetensors   23 MB  (actual LoRA weights)
adapter_config.json         1 KB   (LoRA configuration)
README.md                   5 KB   (documentation)
```

Total: ~23 MB per adapter checkpoint

---

## Important Notes

1. **Auto-Generated Directory**: The output directory is automatically created based on `advisor_id` and `model_preset`
2. **No Manual --output needed**: You don't need to specify `--output` flag - it's calculated automatically
3. **Multiple Epochs**: Each epoch saves separately (allows resume or comparison)
4. **Final Epoch**: `epoch_10` is the most trained version and should be used (configured in model_config.json)
5. **Path is Relative**: `./adapters/ansel_thinking/epoch_10` is relative to project root

---

## Related Files

- **Training Script**: `training/train_lora_pytorch.py` (lines 298-299)
- **Model Config**: `model_config.json` (specifies which adapter to load)
- **AI Service**: `mondrian/ai_advisor_service_linux.py` (loads adapter via config)

