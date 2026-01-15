#!/bin/bash
# Retrain LoRA Adapter with CORRECT Image Analysis Data
# 
# The current adapter was trained on philosophy text (wrong!)
# This script retrains it with actual image analysis examples
#
# Usage: bash retrain_lora_correct.sh
#

set -e

echo ""
echo "======================================================================"
echo "LORA ADAPTER RETRAINING - CORRECT IMAGE ANALYSIS DATA"
echo "======================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TRAINING_DATA="training/datasets/ansel_image_training_nuanced.jsonl"
ADAPTER_DIR="adapters/ansel"
OUTPUT_DIR="adapters/ansel_new"
EPOCHS=3
BATCH_SIZE=1
LEARNING_RATE="5e-05"

echo -e "${BLUE}Configuration:${NC}"
echo "  Training data: $TRAINING_DATA"
echo "  Output adapter: $OUTPUT_DIR"
echo "  Epochs: $EPOCHS"
echo "  Batch size: $BATCH_SIZE"
echo "  Learning rate: $LEARNING_RATE"
echo ""

# Step 1: Verify training data exists
echo -e "${BLUE}[1/4] Verifying training data...${NC}"
if [ ! -f "$TRAINING_DATA" ]; then
    echo -e "${RED}❌ Training data not found: $TRAINING_DATA${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Training data found${NC}"
LINES=$(wc -l < "$TRAINING_DATA")
echo "  Examples: $LINES"
echo ""

# Step 2: Check if services are running
echo -e "${BLUE}[2/4] Checking services...${NC}"
if lsof -Pi :5100 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠ AI Advisor Service is still running on port 5100${NC}"
    echo "  Recommendation: Stop the service before training to avoid GPU memory conflicts"
    echo "  You can continue anyway, but training may be slower or fail."
    echo ""
    read -p "  Continue with training? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  Training cancelled."
        exit 1
    fi
else
    echo -e "${GREEN}✓ Services not running (good for training)${NC}"
fi
echo ""

# Step 3: Run training
echo -e "${BLUE}[3/4] Starting LoRA training...${NC}"
echo "  This will take 10-20 minutes depending on GPU speed"
echo "  Training will use the CORRECT image analysis data with:"
echo "    - Full JSON structure (dimensional_analysis, overall_grade, etc.)"
echo "    - 8 photography dimensions scoring"
echo "    - Ansel Adams analysis style"
echo ""
echo "  Command:"
echo "    python3 train_mlx_lora.py \\"
echo "      --train_data $TRAINING_DATA \\"
echo "      --output_dir $OUTPUT_DIR \\"
echo "      --epochs $EPOCHS \\"
echo "      --batch_size $BATCH_SIZE \\"
echo "      --learning_rate $LEARNING_RATE"
echo ""
echo "  Press Enter to start training..."
read

python3 train_mlx_lora.py \
    --train_data "$TRAINING_DATA" \
    --output_dir "$OUTPUT_DIR" \
    --epochs "$EPOCHS" \
    --batch_size "$BATCH_SIZE" \
    --learning_rate "$LEARNING_RATE"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Training failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Training completed successfully!${NC}"
echo ""

# Step 4: Replace old adapter with new one
echo -e "${BLUE}[4/4] Installing new adapter...${NC}"
echo ""

if [ -d "$ADAPTER_DIR" ]; then
    echo "  Backing up old adapter..."
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="${ADAPTER_DIR}_backup_${TIMESTAMP}"
    mv "$ADAPTER_DIR" "$BACKUP_DIR"
    echo -e "  ${GREEN}✓ Old adapter backed up to: $BACKUP_DIR${NC}"
fi

echo "  Installing new adapter..."
mv "$OUTPUT_DIR" "$ADAPTER_DIR"
echo -e "  ${GREEN}✓ New adapter installed to: $ADAPTER_DIR${NC}"
echo ""

# Summary
echo "======================================================================"
echo -e "${GREEN}RETRAINING COMPLETE!${NC}"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Start the AI Advisor Service:"
echo "     python3 mondrian/start_services.py"
echo ""
echo "  2. Test the new LoRA adapter:"
echo "     python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --mode lora"
echo ""
echo "  3. Compare modes:"
echo "     python3 test_lora_e2e.py --image source/mike-shrub.jpg --advisor ansel --compare"
echo ""
echo "If the test still shows empty output, check the logs:"
echo "  tail -100 logs/ai_advisor_service_*.log | grep -A 5 'JSON PARSER'"
echo ""
