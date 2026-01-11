#!/usr/bin/env python3
"""Test script to see actual AI Advisor Service errors"""
import sys
sys.path.insert(0, '/Users/shaydu/dev/mondrian-macos/mondrian')

# Set up args before importing
sys.argv = [
    'ai_advisor_service.py',
    '--port', '5100',
    '--db', '../mondrian.db',
    '--mlx_model', 'Qwen/Qwen2-VL-2B-Instruct',
    '--job_service_url', 'http://127.0.0.1:5005'
]

# Now import and run
try:
    print("[TEST] Importing AI Advisor Service...")
    import ai_advisor_service
    print("[TEST] Service imported successfully")
    
    # Try to make a test request
    print("[TEST] Creating test request...")
    from flask import Flask
    from werkzeug.test import Client
    
    client = Client(ai_advisor_service.app)
    
    print("[TEST] Making POST request to /analyze...")
    response = client.post('/analyze',
        json={
            'advisor': 'ansel',
            'image_path': '/Users/shaydu/dev/mondrian-macos/mondrian/source/advisor/photographer/ansel/af.jpg',
            'enable_rag': 'false'
        },
        content_type='application/json'
    )
    
    print(f"[TEST] Response status: {response.status_code}")
    print(f"[TEST] Response data: {response.data[:500]}")
    
except Exception as e:
    print(f"[TEST] ERROR: {e}")
    import traceback
    traceback.print_exc()

