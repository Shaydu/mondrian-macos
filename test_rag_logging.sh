#!/bin/bash
# Test script to demonstrate RAG environment variable logging

echo "=========================================="
echo "Testing RAG Logging Output"
echo "=========================================="

echo ""
echo "[Test 1] Starting with RAG_ENABLED=false (or unset)"
echo "------------------------------------------"
unset RAG_ENABLED
python3 -c "
from mondrian.config import RAG_ENABLED
print(f'Config loaded: RAG_ENABLED = {RAG_ENABLED}')
print('[INFO] RAG Default: {}'.format('ENABLED' if RAG_ENABLED else 'DISABLED') + ' (from RAG_ENABLED env var)')
"

echo ""
echo "[Test 2] Starting with RAG_ENABLED=true"
echo "------------------------------------------"
RAG_ENABLED=true python3 -c "
from mondrian.config import RAG_ENABLED
print(f'Config loaded: RAG_ENABLED = {RAG_ENABLED}')
print('[INFO] RAG Default: {}'.format('ENABLED' if RAG_ENABLED else 'DISABLED') + ' (from RAG_ENABLED env var)')
"

echo ""
echo "[Test 3] Starting with RAG_ENABLED=1"
echo "------------------------------------------"
RAG_ENABLED=1 python3 -c "
from mondrian.config import RAG_ENABLED
print(f'Config loaded: RAG_ENABLED = {RAG_ENABLED}')
print('[INFO] RAG Default: {}'.format('ENABLED' if RAG_ENABLED else 'DISABLED') + ' (from RAG_ENABLED env var)')
"

echo ""
echo "=========================================="
echo "When services start, you will see:"
echo "  [INFO] RAG Default: ENABLED (from RAG_ENABLED env var)"
echo "or:"
echo "  [INFO] RAG Default: DISABLED (from RAG_ENABLED env var)"
echo ""
echo "During analysis, you will see:"
echo "  [DEBUG] Enable RAG: True"
echo "or:"
echo "  [DEBUG] Enable RAG: False"
echo "=========================================="
