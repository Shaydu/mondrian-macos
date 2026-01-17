# Adapter Naming Convention Update - Complete Summary

## What Changed

Updated LoRA adapter naming to be **model-based and advisor-scoped** for clarity:

**Old:** `adapters/{advisor_id}{model_suffix}/` (confusing suffixes)
**New:** `adapters/{advisor_id}/{model_name}-adapter/` (clear and consistent)

---

## Files Modified

### 1. training/train_lora_pytorch.py
**Changes:**
- Line 46: `"adapter_suffix": ""` → `"adapter_name": "qwen3-4b-adapter"`
- Line 51: `"adapter_suffix": "_thinking"` → `"adapter_name": "qwen3-4b-thinking-adapter"`
- Line 56: `"adapter_suffix": "_qwen2_2b"` → `"adapter_name": "qwen2-2b-adapter"`
- Line 61: `"adapter_suffix": "_qwen2_7b"` → `"adapter_name": "qwen2-7b-adapter"`
- Lines 285-288: Use `adapter_name` instead of `adapter_suffix`
- Line 299: `output_path = PROJECT_ROOT / "adapters" / advisor_id / adapter_name`

**Impact:** All future training runs will save to new locations

### 2. model_config.json
**Changes:**
- `./adapters/ansel_qwen3_4b_10ep` → `./adapters/ansel/qwen3-4b-adapter/epoch_10`
- `./adapters/ansel_thinking/epoch_10` → `./adapters/ansel/qwen3-4b-thinking-adapter/epoch_10`
- `./adapters/ansel/qwen3-8b-adapter/epoch_10` (for 8B model)
- `./adapters/ansel/qwen3-8b-thinking-adapter/epoch_10` (for 8B thinking model)

**Impact:** Services will now load from new adapter paths

---

## New Adapter Structure

```bash
# Before
adapters/ansel_qwen3_4b_10ep/
adapters/ansel_thinking/epoch_10/
adapters/ansel_qwen2_7b_10ep/

# After
adapters/ansel/qwen3-4b-adapter/epoch_10/
adapters/ansel/qwen3-4b-thinking-adapter/epoch_10/
adapters/ansel/qwen2-7b-adapter/epoch_10/
adapters/ansel/qwen3-8b-adapter/epoch_10/
adapters/ansel/qwen3-8b-thinking-adapter/epoch_10/
```

---

## Usage Examples

### Training a New Adapter
```bash
# Command (unchanged)
python training/train_lora_pytorch.py --advisor ansel --model qwen3-4b-thinking --epochs 10

# Output (new location)
# Saving checkpoints to: /home/doo/dev/mondrian-macos/adapters/ansel/qwen3-4b-thinking-adapter/
# ├── epoch_1/
# ├── epoch_2/
# ...
# └── epoch_10/  ← Configured in model_config.json
```

### Using in AI Service
```bash
# Service auto-loads from model_config.json paths
python mondrian/ai_advisor_service_linux.py --model qwen3-4b-thinking

# Reads from model_config.json:
# "adapter": "./adapters/ansel/qwen3-4b-thinking-adapter/epoch_10"
```

### Direct Service Launch
```bash
python mondrian/ai_advisor_service_linux.py \
    --model Qwen/Qwen3-VL-4B-Thinking \
    --adapter ./adapters/ansel/qwen3-4b-thinking-adapter/epoch_10
```

---

## Migration Status

### ✅ Services Updated
- `model_config.json` - Uses new paths (config will load correct adapters)
- `training/train_lora_pytorch.py` - Creates new paths when retraining

### ⚠️ Old Adapters Still Exist
The old adapter directories remain:
- `adapters/ansel_qwen3_4b_10ep/` (old)
- `adapters/ansel_thinking/` (old)

These can be:
1. **Deleted** if you've migrated to new adapters
2. **Kept** for reference or as backups
3. **Updated manually** if you need to use them temporarily

### 📋 Current State
- **New paths in config** ✅ (model_config.json updated)
- **New training script** ✅ (train_lora_pytorch.py updated)
- **Old adapters** - Still exist, not actively used (safe to clean up)

---

## Testing the Update

### Verify Config Changes
```bash
cat model_config.json | grep "adapter"
# Should show:
# "adapter": "./adapters/ansel/qwen3-4b-adapter/epoch_10",
# "adapter": "./adapters/ansel/qwen3-4b-thinking-adapter/epoch_10",
```

### Check Existing Adapters
```bash
ls -la adapters/ansel/
# New structure (will see this after next training):
# qwen3-4b-adapter/
# qwen3-4b-thinking-adapter/
# qwen3-8b-adapter/
# qwen3-8b-thinking-adapter/
```

### Start Service and Verify Loading
```bash
# AI service should load without errors
python mondrian/ai_advisor_service_linux.py --model qwen3-4b-thinking
# Logs should show:
# Loading LoRA adapter from ./adapters/ansel/qwen3-4b-thinking-adapter/epoch_10
# LoRA adapter loaded successfully
```

---

## Benefits of New Naming

| Aspect | Old | New |
|--------|-----|-----|
| **Clarity** | `ansel_thinking` (what's thinking?) | `qwen3-4b-thinking-adapter` (clear!) |
| **Organization** | Flat: `adapters/ansel_*` | Hierarchical: `adapters/ansel/{model}/` |
| **Discovery** | Hard to see all models | Easy: `ls adapters/ansel/` |
| **Consistency** | Mixed conventions | All follow: `{model}-adapter` |
| **Scalability** | Limited | Support unlimited models |
| **Documentation** | Ambiguous | Self-documenting names |

---

## Timeline

| Date | Action | Status |
|------|--------|--------|
| 2026-01-16 | Update training script & config | ✅ Complete |
| 2026-01-16 | Document new naming | ✅ Complete |
| Next training | New adapters created in new locations | ⏳ Pending |
| When ready | Delete old adapter dirs (optional) | 📋 Manual |

---

## Quick Reference

### Default Adapter Locations After Training

```bash
# Single model (qwen3-4b)
adapters/ansel/qwen3-4b-adapter/epoch_10/

# Thinking model (qwen3-4b-thinking)
adapters/ansel/qwen3-4b-thinking-adapter/epoch_10/

# Larger models
adapters/ansel/qwen3-8b-adapter/epoch_10/
adapters/ansel/qwen3-8b-thinking-adapter/epoch_10/

# Alternative models
adapters/ansel/qwen2-2b-adapter/epoch_10/
adapters/ansel/qwen2-7b-adapter/epoch_10/
```

### Config Reference
Just update `model_config.json` adapter field to point to epoch_10 of desired adapter.

---

## Next Steps

1. **No action needed** - Config is updated, services will work
2. **Next training** - New adapters will go to correct locations
3. **Optional cleanup** - Delete old `adapters/ansel_*` dirs when ready
4. **Document done** - Migration complete and documented

