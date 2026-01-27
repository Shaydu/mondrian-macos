#!/bin/bash

# Script to test Mondrian container on RTX 3060 with reduced resources

set -e

echo "=========================================="
echo "Testing Mondrian Container: shaydu/mondrian:14.5.21"
echo "RTX 3060 Mode - Reduced Resources"
echo "=========================================="
echo ""

# Clean up any existing container
if docker ps -a | grep -q mondrian-test; then
    echo "Stopping existing container..."
    docker stop mondrian-test 2>/dev/null || true
    docker rm mondrian-test 2>/dev/null || true
fi

# Check if container is built
if ! docker image inspect shaydu/mondrian:14.5.21 > /dev/null 2>&1; then
    echo "❌ Container image not found: shaydu/mondrian:14.5.21"
    echo "Run: docker build -t shaydu/mondrian:14.5.21 ."
    exit 1
fi

echo "✓ Container image found"
echo ""

# Run container with reduced GPU resources for RTX 3060
echo "Starting container with RTX 3060 constraints..."
echo "  - Memory limit: 6GB RAM"
echo "  - CPUs: 4"
echo "  - GPU: Single device with memory fragment optimization"
echo "  - Shared memory: 2GB"
echo ""

docker run -d \
    --name mondrian-test \
    --gpus '"device=0"' \
    --memory="6g" \
    --memory-swap="6g" \
    --cpus="4" \
    --shm-size="2g" \
    -e PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 \
    -e CUDA_VISIBLE_DEVICES=0 \
    -p 5005:5005 \
    -p 5100:5100 \
    -v /home/doo/dev/mondrian-macos/mondrian.db:/app/mondrian.db \
    -v /home/doo/dev/mondrian-macos/adapters:/app/adapters \
    -v /home/doo/dev/mondrian-macos/model_config.test.json:/app/model_config.json \
    shaydu/mondrian:14.5.21 \
    python3 /app/mondrian/job_service_v2.3.py --port 5005 --db mondrian.db

echo "✓ Container started"
echo ""

# Wait for service to be ready
echo "Waiting for service to start (45 seconds - model loading takes time)..."
sleep 10
echo "  30 seconds remaining..."
sleep 15
echo "  15 seconds remaining..."
sleep 15
echo "  Checking health..."
sleep 5

# Check health
echo ""
echo "Checking service health..."
if curl -s http://localhost:5005/health > /dev/null; then
    echo "✓ Service is running on port 5005"
else
    echo "⚠ Service health check failed"
    echo ""
    echo "Container logs (last 30 lines):"
    docker logs mondrian-test 2>&1 | tail -30
    exit 1
fi

echo ""
echo "=========================================="
echo "Container is ready for testing!"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  - Using model_config.test.json (ultra_fast mode, 1500 tokens)"
echo "  - Reduced RAG references (2 images, 2 quotes)"
echo "  - Memory limited to 6GB"
echo ""
echo "To test the API:"
echo "  curl http://localhost:5005/health"
echo ""
echo "To view logs:"
echo "  docker logs -f mondrian-test"
echo ""
echo "To check GPU usage:"
echo "  watch -n 1 nvidia-smi"
echo ""
echo "To stop the container:"
echo "  docker stop mondrian-test && docker rm mondrian-test"
echo ""
