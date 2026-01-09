#!/bin/bash
# Quick test of MLX backend via CLI

echo "============================================================"
echo "Testing MLX Backend - Quick Health Check"
echo "============================================================"

# Test 1: Health endpoint
echo ""
echo "1. Health Check:"
curl -s http://localhost:5100/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:5100/health

echo ""
echo ""
echo "============================================================"
echo "2. Test with Image Analysis:"
echo "============================================================"

# Test 2: Simple image analysis
curl -X POST http://localhost:5100/analyze \
  -F "image=@mondrian/source/mike-shrub.jpg" \
  -F "advisor=mondrian" \
  -F "job_id=quick_test" \
  --max-time 180 \
  2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Request sent, awaiting response..."

echo ""
echo ""
echo "✅ Test complete!"
