# Archived Training Scripts

These scripts have been archived as they are old/obsolete versions.

## Archived Files (January 21, 2026)

### Old Training Scripts
- **train_lora_qwen3vl.py** - Original root-level training script (replaced by CUDA version)
- **train_lora.py** - Old MLX-based training script (from training/ directory)
- **train_mlx_lora.py** - MLX-specific training (from training/mlx/)
- **quick_start_lora.sh** - Old setup/quick start shell script

## Current Active Scripts (Use These Instead)

### Primary Training Scripts
- **training/cuda/train_lora_pytorch.py** - **MAIN LoRA+RAG training script**
  - Default: 20 epochs
  - Supports multiple Qwen models (qwen3-4b, qwen3-4b-thinking, qwen2-2b, qwen2-7b)
  - CUDA/PyTorch based for NVIDIA GPUs
  
- **training/cuda/resume_lora_pytorch.py** - Resume training from checkpoint
  - Used to continue training from epoch 15 → epoch 20

### Helper Scripts
- **resume_ansel_lora.sh** - Shell wrapper to resume training (calls resume_lora_pytorch.py)

### Training Logs
- Check `training_log.txt` and `resume_training_log.txt` in project root for training history

## Last Training Run
- **Model**: Qwen/Qwen3-VL-4B-Instruct
- **Initial**: 15 epochs → saved to `adapters/ansel_qwen3_4b_v2/epoch_15`
- **Resumed**: +5 epochs (16-20) → saved to `adapters/ansel_qwen3_4b_v2/epoch_20`
- **Current Active Adapter**: `adapters/ansel_qwen3_4b_v2/epoch_20`

## Usage Example
```bash
# Train from scratch (20 epochs default)
python3 training/cuda/train_lora_pytorch.py \
    --advisor ansel \
    --model qwen3-4b \
    --epochs 20 \
    --lr 5e-5

# Resume from checkpoint
python3 training/cuda/resume_lora_pytorch.py \
    --checkpoint "adapters/ansel_qwen3_4b_v2/epoch_15" \
    --advisor ansel \
    --epochs 5
```
