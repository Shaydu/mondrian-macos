#!/bin/bash
# Test script to query the running Qwen3-VL-4B model via AI Advisor Service

# Check if service is running
echo "Checking if AI Advisor Service is running on port 5100..."
curl -s http://localhost:5100/health
echo ""
echo ""

# Test with a sample image (you need to provide an image path)
if [ -z "$1" ]; then
    echo "Usage: $0 <image_path> [advisor_name]"
    echo ""
    echo "Example:"
    echo "  $0 /path/to/image.jpg 'Describe what you see'"
    echo ""
    echo "The service is running with model: NexaAI/qwen3vl-4B-Thinking-4bit-mlx"
    exit 1
fi

IMAGE_PATH="$1"
ADVISOR="${2:-default}"

if [ ! -f "$IMAGE_PATH" ]; then
    echo "Error: Image file not found: $IMAGE_PATH"
    exit 1
fi

echo "Sending request to AI Advisor Service..."
echo "Image: $IMAGE_PATH"
echo "Advisor: $ADVISOR"
echo ""

curl -X POST http://localhost:5100/analyze \
  -F "image=@$IMAGE_PATH" \
  -F "advisor=$ADVISOR" \
  -F "job_id=test_$(date +%s)"

echo ""
