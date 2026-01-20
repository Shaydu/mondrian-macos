#!/bin/bash
# Quick build and test script for Docker image

set -e

echo "Building Mondrian Docker image..."
docker build -t mondrian:latest .

echo ""
echo "Build successful! Testing image..."
echo ""

# Test container startup
docker run --rm --gpus all \
  -p 5100:5100 -p 5005:5005 -p 5006:5006 \
  -e MODE=base \
  -e BACKEND=bnb \
  mondrian:latest &

CONTAINER_PID=$!
echo "Container started with PID: $CONTAINER_PID"
echo "Waiting for services to start (this may take 2-3 minutes)..."

# Wait and check health
sleep 90

echo ""
echo "Checking service health..."

# Check AI Advisor
if curl -sf http://localhost:5100/health > /dev/null 2>&1; then
    echo "✓ AI Advisor Service (5100): HEALTHY"
else
    echo "✗ AI Advisor Service (5100): UNHEALTHY"
fi

# Check Job Service
if curl -sf http://localhost:5005/health > /dev/null 2>&1; then
    echo "✓ Job Service (5005): HEALTHY"
else
    echo "✗ Job Service (5005): UNHEALTHY"
fi

# Check Summary Service
if curl -sf http://localhost:5006/health > /dev/null 2>&1; then
    echo "✓ Summary Service (5006): HEALTHY"
else
    echo "✗ Summary Service (5006): UNHEALTHY"
fi

echo ""
echo "Stopping test container..."
kill $CONTAINER_PID 2>/dev/null || docker stop $(docker ps -q --filter ancestor=mondrian:latest) 2>/dev/null

echo ""
echo "Build and test complete!"
echo ""
echo "To push to registry:"
echo "  docker tag mondrian:latest your-registry/mondrian:latest"
echo "  docker push your-registry/mondrian:latest"
echo ""
echo "To run locally:"
echo "  docker-compose up -d"
