#!/bin/bash
# Quick Start Script for LoRA Fine-tuning
# This script helps you get started with fine-tuning Qwen3-VL-4B

set -e

echo "=========================================="
echo "LoRA Fine-tuning Quick Start"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "train_lora_qwen3vl.py" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Step 1: Install dependencies
echo "Step 1: Installing training dependencies..."
if [ ! -f "requirements_training.txt" ]; then
    echo "Error: requirements_training.txt not found"
    exit 1
fi

pip install -r requirements_training.txt

echo ""
echo "✓ Dependencies installed"
echo ""

# Step 2: Prepare training data
echo "Step 2: Preparing training data..."
echo "This will scan your analysis outputs and create training dataset"
echo ""

read -p "Analysis directory [./analysis_output]: " ANALYSIS_DIR
ANALYSIS_DIR=${ANALYSIS_DIR:-./analysis_output}

read -p "Source images directory [./source]: " SOURCE_DIR
SOURCE_DIR=${SOURCE_DIR:-./source}

read -p "Prompts directory [./scripts/prompts]: " PROMPTS_DIR
PROMPTS_DIR=${PROMPTS_DIR:-./scripts/prompts}

read -p "Output directory for training data [./training_data]: " OUTPUT_DIR
OUTPUT_DIR=${OUTPUT_DIR:-./training_data}

read -p "Advisor name (optional, e.g., 'ansel'): " ADVISOR

if [ -n "$ADVISOR" ]; then
    python prepare_training_data.py \
        --analysis_dir "$ANALYSIS_DIR" \
        --source_dir "$SOURCE_DIR" \
        --prompts_dir "$PROMPTS_DIR" \
        --output_dir "$OUTPUT_DIR" \
        --advisor "$ADVISOR"
else
    python prepare_training_data.py \
        --analysis_dir "$ANALYSIS_DIR" \
        --source_dir "$SOURCE_DIR" \
        --prompts_dir "$PROMPTS_DIR" \
        --output_dir "$OUTPUT_DIR"
fi

echo ""
echo "✓ Training data prepared"
echo ""

# Step 3: Check training data
TRAINING_FILE=""
if [ -n "$ADVISOR" ]; then
    TRAINING_FILE="$OUTPUT_DIR/training_data_${ADVISOR}.json"
else
    TRAINING_FILE="$OUTPUT_DIR/training_data.json"
fi

if [ ! -f "$TRAINING_FILE" ]; then
    echo "Error: Training data file not created: $TRAINING_FILE"
    exit 1
fi

EXAMPLE_COUNT=$(python -c "import json; data = json.load(open('$TRAINING_FILE')); print(len(data) if isinstance(data, list) else 1)")
echo "Found $EXAMPLE_COUNT training examples"

if [ "$EXAMPLE_COUNT" -lt 10 ]; then
    echo "Warning: You have fewer than 10 examples. Consider adding more training data."
    read -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 0
    fi
fi

echo ""

# Step 4: Training configuration
echo "Step 3: Training configuration"
echo ""

read -p "Base model [Qwen/Qwen3-VL-4B-Instruct]: " BASE_MODEL
BASE_MODEL=${BASE_MODEL:-Qwen/Qwen3-VL-4B-Instruct}

read -p "Output directory for model [./models/qwen3-vl-4b-lora]: " MODEL_OUTPUT
MODEL_OUTPUT=${MODEL_OUTPUT:-./models/qwen3-vl-4b-lora}

read -p "Number of epochs [3]: " EPOCHS
EPOCHS=${EPOCHS:-3}

read -p "Batch size [2]: " BATCH_SIZE
BATCH_SIZE=${BATCH_SIZE:-2}

read -p "Learning rate [2e-4]: " LEARNING_RATE
LEARNING_RATE=${LEARNING_RATE:-2e-4}

echo ""
echo "=========================================="
echo "Ready to start training!"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Base model: $BASE_MODEL"
echo "  Training data: $TRAINING_FILE"
echo "  Output: $MODEL_OUTPUT"
echo "  Epochs: $EPOCHS"
echo "  Batch size: $BATCH_SIZE"
echo "  Learning rate: $LEARNING_RATE"
echo ""

read -p "Start training now? (y/n): " START_TRAINING

if [ "$START_TRAINING" != "y" ]; then
    echo "Training cancelled. You can start it manually with:"
    echo ""
    echo "python train_lora_qwen3vl.py \\"
    echo "    --base_model $BASE_MODEL \\"
    echo "    --data_dir $TRAINING_FILE \\"
    echo "    --output_dir $MODEL_OUTPUT \\"
    echo "    --epochs $EPOCHS \\"
    echo "    --batch_size $BATCH_SIZE \\"
    echo "    --learning_rate $LEARNING_RATE"
    exit 0
fi

echo ""
echo "Starting training..."
echo ""

python train_lora_qwen3vl.py \
    --base_model "$BASE_MODEL" \
    --data_dir "$TRAINING_FILE" \
    --output_dir "$MODEL_OUTPUT" \
    --epochs "$EPOCHS" \
    --batch_size "$BATCH_SIZE" \
    --learning_rate "$LEARNING_RATE"

echo ""
echo "=========================================="
echo "Training completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test your model:"
echo "   python test_lora_model.py \\"
echo "       --lora_path $MODEL_OUTPUT \\"
echo "       --image_path <test_image.jpg>"
echo ""
echo "2. View training logs:"
echo "   tensorboard --logdir $MODEL_OUTPUT/logs"
echo ""
echo "3. Merge LoRA weights (optional):"
echo "   python merge_lora_weights.py \\"
echo "       --lora_path $MODEL_OUTPUT \\"
echo "       --output_path ${MODEL_OUTPUT}_merged"
echo ""


