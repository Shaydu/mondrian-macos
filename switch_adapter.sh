#!/bin/bash
# Switch to the new 9-dimension adapter with Subject Matter scoring
# Usage: ./switch_adapter.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "Switching to 9-Dimension Adapter"
echo "=============================================="

# Define paths
NEW_ADAPTER="./adapters/ansel_qwen3_4b_full_9dim/epoch_20"
OLD_ADAPTER="./training/lora_adapters/ansel_qwen3_4b_v3"
ARCHIVE_DIR="./adapters/archive"
CONFIG_FILE="./model_config.json"

# Verify new adapter exists
if [ ! -d "$NEW_ADAPTER" ]; then
    echo "ERROR: New adapter not found at $NEW_ADAPTER"
    exit 1
fi

echo "✓ New adapter verified: $NEW_ADAPTER"

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Archive old adapter if it exists
if [ -d "$OLD_ADAPTER" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ARCHIVE_NAME="ansel_qwen3_4b_v3_8dim_${TIMESTAMP}"
    echo "Archiving old adapter to: $ARCHIVE_DIR/$ARCHIVE_NAME"
    mv "$OLD_ADAPTER" "$ARCHIVE_DIR/$ARCHIVE_NAME"
    echo "✓ Old adapter archived"
else
    echo "Note: Old adapter not found at $OLD_ADAPTER (may already be archived)"
fi

# Update model_config.json
echo "Updating $CONFIG_FILE..."

# Use python for reliable JSON manipulation
python3 << 'EOF'
import json

config_file = "model_config.json"
new_adapter = "./adapters/ansel_qwen3_4b_full_9dim/epoch_20"

with open(config_file, 'r') as f:
    config = json.load(f)

# Update the qwen3-4b-instruct adapter path
old_path = config['models']['qwen3-4b-instruct']['adapter']
config['models']['qwen3-4b-instruct']['adapter'] = new_adapter
config['models']['qwen3-4b-instruct']['description'] = "9-dimension analysis with Subject Matter scoring. Trained on 30 images including negative examples."

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✓ Updated adapter path: {old_path} -> {new_adapter}")
EOF

echo ""
echo "=============================================="
echo "Switch Complete!"
echo "=============================================="
echo ""
echo "New adapter: $NEW_ADAPTER"
echo "Features:"
echo "  - 9 dimensions (including Subject Matter)"
echo "  - Ruthless scoring (1-3) for off-topic images"
echo "  - Trained on 30 images (25 positive, 5 negative)"
echo ""
echo "To apply changes, restart Mondrian:"
echo "  ./mondrian.sh --restart"
echo ""
