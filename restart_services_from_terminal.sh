#!/bin/bash
# Restart Mondrian services from Terminal.app (with GPU access)
# Run this from Terminal.app, NOT from Cursor

echo "========================================="
echo "Restarting Mondrian Services"
echo "========================================="
echo ""

cd /Users/shaydu/dev/mondrian-macos/mondrian

echo "[1/3] Stopping existing services..."
python3 start_services.py --stop
sleep 2

echo ""
echo "[2/3] Starting services with GPU access..."
python3 start_services.py &
SERVICE_PID=$!

echo "Services starting (PID: $SERVICE_PID)"
echo ""
echo "Waiting for services to initialize (30 seconds)..."
sleep 30

echo ""
echo "[3/3] Testing AI Advisor Service..."
curl -s http://localhost:5100/health | python3 -m json.tool

echo ""
echo "========================================="
echo "Services Status"
echo "========================================="
echo ""
echo "✓ Services are running in background"
echo "✓ Logs: scripts/logs/monitoring_service.log"
echo ""
echo "To test MLX:"
echo "  cd /Users/shaydu/dev/mondrian-macos"
echo "  python3 batch_analyze_advisor_images.py --advisor ansel"
echo ""
echo "To stop services:"
echo "  cd mondrian && python3 start_services.py --stop"
echo ""


