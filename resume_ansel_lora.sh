#!/bin/bash
# Resume Ansel Adams LoRA training from epoch 15
# Continues training for 5 more epochs (16-20)

set -e

cd /home/doo/dev/mondrian-macos

echo "================================"
echo "Resuming Ansel Adams LoRA Training"
echo "================================"
echo ""
echo "Checkpoint: adapters/ansel_qwen3_4b_v2/epoch_15"
echo "Continuing for 5 more epochs (16-20)"
echo ""

# Verify checkpoint exists
if [ ! -d "adapters/ansel_qwen3_4b_v2/epoch_15" ]; then
    echo "ERROR: Checkpoint not found at adapters/ansel_qwen3_4b_v2/epoch_15"
    exit 1
fi

# Verify training data exists
if [ ! -f "training/datasets/ansel_image_training_fixed.jsonl" ]; then
    echo "ERROR: Training data not found!"
    exit 1
fi

echo "Training Parameters:"
echo "  Model: qwen3-4b (Qwen/Qwen3-VL-4B-Instruct)"
echo "  Resume from: epoch 15"
echo "  Additional epochs: 5"
echo "  Learning Rate: 5e-5"
echo "  Batch Size: 1"
echo "  LoRA Rank: 4 (memory-optimized)"
echo "  LoRA Alpha: 8 (memory-optimized)"
echo ""

read -p "Resume training? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Training cancelled."
    exit 0
fi

echo ""
echo "Starting training resume..."
echo "================================"
echo ""

# Activate venv if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run resume training
python3 training/resume_lora_pytorch.py \
    --checkpoint "adapters/ansel_qwen3_4b_v2/epoch_15" \
    --advisor ansel \
    --model qwen3-4b \
    --dataset "training/datasets/ansel_image_training_fixed.jsonl" \
    --epochs 5 \
    --lr 5e-5 \
    --batch-size 1

echo ""
echo "================================"
echo "Training resume completed!"
echo "================================"
echo ""
echo "Checkpoint saved to: adapters/ansel_qwen3_4b_v2/epoch_20"
