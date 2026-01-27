#!/bin/bash

# Script to test the Mondrian container locally with RTX 3060 constraints
# Uses model_config.json with ultra_fast profile (greedy, 1500 tokens)

set -e

echo "=========================================="
echo "Testing Mondrian Container: shaydu/mondrian:14.5.21"
echo "RTX 3060 Mode - Resource Constrained"
echo "=========================================="
echo ""

# Clean up any existing container
if docker ps -a | grep -q mondrian-test; then
    echo "Stopping existing container..."
    docker stop mondrian-test 2>/dev/null || true
    docker rm mondrian-test 2>/dev/null || true
    echo ""
fi

# Check if container is built
if ! docker image inspect shaydu/mondrian:14.5.21 > /dev/null 2>&1; then
    echo "❌ Container image not found: shaydu/mondrian:14.5.21"
    echo "Run: docker build -t shaydu/mondrian:14.5.21 ."
    exit 1
fi

echo "✓ Container image found"
echo ""

# Run container with GPU support and port mappings
echo "Starting container with reduced resources for RTX 3060..."
docker run -d \
    --name mondrian-test \
    --gpus '"device=0"' \
    --memory="8g" \
    --memory-swap="8g" \
    --cpus="4" \
    --shm-size="2g" \
    -e PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 \
    -e CUDA_VISIBLE_DEVICES=0 \
    -p 5005:5005 \
    -p 5100:5100 \
    -v /home/doo/dev/mondrian-macos/mondrian.db:/app/mondrian.db \
    -v /home/doo/dev/mondrian-macos/adapters:/app/adapters \
    -v /home/doo/dev/mondrian-macos/model_config.json:/app/model_config.json \
    shaydu/mondrian:14.5.21 \
    python3 /app/mondrian/job_service_v2.3.py --port 5005 --db mondrian.db

echo "✓ Container started"
echo ""
echo "Container configuration:"
echo "  - Generation profile: ultra_fast (greedy, 1500 tokens)"
echo "  - RAG references: 2 images, 2 quotes"
echo "  - Memory limit: 8GB RAM, 2GB shared"
echo "  - GPU: Single device with fragmentation optimization"
echo ""

# Wait for service to be ready
echo "Waiting for service to start (45 seconds - model loading)..."
sleep 15
echo "  30 seconds remaining..."
sleep 15
echo "  15 seconds remaining..."
sleep 15

# Check health
echo ""
echo "Checking service health..."
if curl -s http://localhost:5005/health > /dev/null; then
    echo "✓ Service is running on port 5005"
else
    echo "⚠ Service health check failed"
    echo "Container logs:"
    docker logs mondrian-test | tail -20
    exit 1
fi

echo ""
echo "=========================================="
echo "Container is ready for testing!"
echo "=========================================="
echo ""
echo "Using ultra_fast configuration:"
echo "  - Greedy decoding (no beam search)"
echo "  - 1500 max tokens (vs 2500 production)"
echo "  - 2 RAG references (vs 3 production)"
echo ""
echo "To test the API:"
echo "  curl http://localhost:5005/health"
echo ""
echo "To view logs:"
echo "  docker logs -f mondrian-test"
echo ""
echo "To monitor GPU usage:"
echo "  watch -n 1 nvidia-smi"
echo ""
echo "To stop the container:"
echo "  docker stop mondrian-test && docker rm mondrian-test"
echo ""
echo "NOTE: To restore production settings, edit model_config.json"
echo "      and uncomment the PRODUCTION lines in defaults and rag sections"
echo ""
