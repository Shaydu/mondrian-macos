#!/bin/bash
# Test script for embedding support in RAG modes
# Tests both RAG and RAG+LoRA with enable_embeddings=true

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Embedding Support Test Script"
echo "=========================================="
echo ""

# Check if services are running
echo -e "${YELLOW}Checking if services are running...${NC}"

# Check Job Service
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Job Service is running (port 5000)${NC}"
else
    echo -e "${RED}✗ Job Service is not running${NC}"
    echo "  Start it with: python mondrian/job_service_v2.3.py --port 5000"
    exit 1
fi

# Check AI Advisor Service
if curl -s http://localhost:5200/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ AI Advisor Service is running (port 5200)${NC}"
else
    echo -e "${RED}✗ AI Advisor Service is not running${NC}"
    echo "  Start it with: python mondrian/ai_advisor_service.py --port 5200"
    exit 1
fi

echo ""

# Check if test image exists
if [ ! -f "test_image.png" ]; then
    echo -e "${YELLOW}Warning: test_image.png not found. Using source/mike-shrub-01004b68.jpg instead${NC}"
    TEST_IMAGE="source/mike-shrub-01004b68.jpg"
else
    TEST_IMAGE="test_image.png"
fi

if [ ! -f "$TEST_IMAGE" ]; then
    echo -e "${RED}✗ No test image found. Please provide a test image.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Using test image: $TEST_IMAGE${NC}"
echo ""

# Test 1: RAG mode with embeddings
echo "=========================================="
echo "Test 1: RAG Mode with Embeddings"
echo "=========================================="
echo ""
echo "Sending request to RAG mode with enable_embeddings=true..."
echo ""

curl -X POST http://localhost:5200/analyze \
  -F "advisor=ansel" \
  -F "image=@$TEST_IMAGE" \
  -F "mode=rag" \
  -F "enable_embeddings=true" \
  -F "response_format=json" \
  -o test_rag_embeddings_output.json

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ RAG request completed${NC}"
    echo ""
    echo "Check logs for:"
    echo "  - [RAG EMBED] Computing CLIP embedding for visual similarity..."
    echo "  - [RAG EMBED] ✓ Embedding computed"
    echo "  - [RAG QUERY] Embeddings enabled - computing visual similarity..."
    echo "  - [EMBED] Found N advisor profiles with embeddings"
    echo "  - [RAG QUERY] ✓ Hybrid augmentation applied"
    echo ""
    echo "Output saved to: test_rag_embeddings_output.json"
else
    echo -e "${RED}✗ RAG request failed${NC}"
fi

echo ""
echo "Press Enter to continue to RAG+LoRA test..."
read

# Test 2: RAG+LoRA mode with embeddings
echo "=========================================="
echo "Test 2: RAG+LoRA Mode with Embeddings"
echo "=========================================="
echo ""
echo "Sending request to RAG+LoRA mode with enable_embeddings=true..."
echo ""

curl -X POST http://localhost:5200/analyze \
  -F "advisor=ansel" \
  -F "image=@$TEST_IMAGE" \
  -F "mode=rag+lora" \
  -F "enable_embeddings=true" \
  -F "response_format=json" \
  -o test_rag_lora_embeddings_output.json

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ RAG+LoRA request completed${NC}"
    echo ""
    echo "Check logs for:"
    echo "  - [RAG+LoRA EMBED] Computing CLIP embedding for visual similarity..."
    echo "  - [RAG+LoRA EMBED] ✓ Embedding computed"
    echo "  - [RAG+LoRA QUERY] Embeddings enabled - computing visual similarity..."
    echo "  - [EMBED] Found N advisor profiles with embeddings"
    echo "  - [RAG+LoRA QUERY] ✓ Hybrid augmentation applied"
    echo ""
    echo "Output saved to: test_rag_lora_embeddings_output.json"
else
    echo -e "${RED}✗ RAG+LoRA request failed${NC}"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "All tests completed. Review the output files and logs to verify:"
echo ""
echo "1. Embeddings were computed for user images"
echo "2. Visual similarity search was performed"
echo "3. Hybrid augmentation (visual + dimensional) was applied"
echo "4. Reference images include visually similar matches"
echo ""
echo "Output files:"
echo "  - test_rag_embeddings_output.json"
echo "  - test_rag_lora_embeddings_output.json"
echo ""
echo -e "${GREEN}Testing complete!${NC}"
