#!/bin/bash
# Train Ansel Adams LoRA Adapter
# Uses fixed training data with correct image paths

set -e

cd /home/doo/dev/mondrian-macos

echo "================================"
echo "Training Ansel Adams LoRA Adapter"
echo "================================"
echo ""
echo "Model: Qwen/Qwen3-VL-4B-Instruct"
echo "Training Data: training/datasets/ansel_image_training_fixed.jsonl"
echo "Images: 21 examples with correct format"
echo "Output: adapters/ansel_qwen3_4b_v2/"
echo ""

# Verify training data exists
if [ ! -f "training/datasets/ansel_image_training_fixed.jsonl" ]; then
    echo "ERROR: Training data not found!"
    exit 1
fi

# Count examples
EXAMPLE_COUNT=$(wc -l < training/datasets/ansel_image_training_fixed.jsonl)
echo "Training examples: $EXAMPLE_COUNT"
echo ""
echo ""

# Training parameters - optimized for memory on RTX 3060 (12GB)
MODEL="qwen3-4b"
EPOCHS=20
LR="5e-5"
BATCH_SIZE=1
RANK=4
ALPHA=8
OUTPUT_DIR="adapters/ansel_qwen3_4b_v2"

echo "Training Parameters:"
echo "  Model: $MODEL (Qwen/Qwen3-VL-4B-Instruct)"
echo "  Epochs: $EPOCHS"
echo "  Learning Rate: $LR"
echo "  Batch Size: $BATCH_SIZE"
echo "  LoRA Rank: $RANK (memory-optimized)"
echo "  LoRA Alpha: $ALPHA (memory-optimized)"
echo "  Output: $OUTPUT_DIR"
echo ""
echo "Memory Optimizations:"
echo "  - Reduced rank from 8 to 4 (fewer trainable params)"
echo "  - Reduced alpha from 16 to 8"
echo "  - Using gradient checkpointing"
echo ""

read -p "Start training? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Training cancelled."
    exit 0
fi

echo ""
echo "Starting training..."
echo "================================"
echo ""

# Run training
python3 training/train_lora_pytorch.py \
    --model "$MODEL" \
    --dataset "training/datasets/ansel_image_training_fixed.jsonl" \
    --epochs "$EPOCHS" \
    --lr "$LR" \
    --batch-size "$BATCH_SIZE" \
    --rank "$RANK" \
    --alpha "$ALPHA" \
    --output "$OUTPUT_DIR" \
    --advisor ansel

# If training fails with OOM, automatically retry with smaller model
if [ $? -ne 0 ]; then
    echo ""
    echo "[!] Training failed - trying with smaller Qwen2-2B model..."
    echo ""
    python3 training/train_lora_pytorch.py \
        --model "qwen2-2b" \
        --dataset "training/datasets/ansel_image_training_fixed.jsonl" \
        --epochs "$EPOCHS" \
        --lr "$LR" \
        --batch-size "$BATCH_SIZE" \
        --rank "$RANK" \
        --alpha "$ALPHA" \
        --output "adapters/ansel_qwen2_2b_v2" \
        --advisor ansel
fi

echo ""
echo "================================"
echo "Training Complete!"
echo "================================"
echo ""
echo "Adapter saved to: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "1. Update model_config.json to point to new adapter"
echo "2. Restart services: ./mondrian.sh --restart --model-preset=qwen3-4b-instruct"
echo "3. Test with a sample image"
