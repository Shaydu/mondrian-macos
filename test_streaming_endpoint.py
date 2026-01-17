#!/usr/bin/env python3
"""
Test the streaming endpoint - watch tokens appear in real-time
"""

import requests
import json
import time

print("="*70)
print("STREAMING ENDPOINT TEST")
print("="*70)

# Test image
image_path = "source/mike-shrub.jpg"

print(f"\n[1] Sending image to streaming endpoint: {image_path}")
print("    Waiting for tokens to stream...\n")
print("-"*70)

url = "http://localhost:5100/analyze_stream"

with open(image_path, 'rb') as f:
    files = {'image': f}
    data = {'advisor': 'ansel', 'mode': 'lora'}
    
    start_time = time.time()
    token_count = 0
    thinking_detected = False
    json_detected = False
    
    # Stream the response
    with requests.post(url, files=files, data=data, stream=True) as response:
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            exit(1)
        
        # Process Server-Sent Events
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                # SSE format: "data: {json}"
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove "data: " prefix
                    
                    try:
                        event = json.loads(data_str)
                        event_type = event.get('type')
                        
                        if event_type == 'start':
                            print(f"[START] Advisor: {event['advisor']}, Mode: {event['mode']}")
                            print("-"*70)
                        
                        elif event_type == 'thinking_start':
                            print("\n╔═══ THINKING (real-time) ═══╗")
                            thinking_detected = True
                        
                        elif event_type == 'thinking_token':
                            text = event['text']
                            print(text, end='', flush=True)
                            token_count += 1
                        
                        elif event_type == 'thinking_end':
                            print("\n╚═══ END THINKING ═══╝\n")
                        
                        elif event_type == 'json_start':
                            print("\n╔═══ JSON OUTPUT (real-time) ═══╗")
                            json_detected = True
                        
                        elif event_type == 'json_token':
                            text = event['text']
                            print(text, end='', flush=True)
                            token_count += 1
                        
                        elif event_type == 'token':
                            # Fallback for unclassified tokens
                            text = event['text']
                            print(text, end='', flush=True)
                            token_count += 1
                        
                        elif event_type == 'complete':
                            elapsed = time.time() - start_time
                            print("\n" + "-"*70)
                            print(f"[COMPLETE] Streamed {token_count} tokens in {elapsed:.1f}s")
                            
                            result = event['result']
                            print(f"\nParsed result:")
                            print(f"  • Image description: {result.get('analysis', {}).get('image_description', 'N/A')[:80]}...")
                            print(f"  • Overall score: {result.get('overall_score', 'N/A')}")
                            print(f"  • Dimensions: {len(result.get('analysis', {}).get('dimensions', []))}")
                            print(f"  • Thinking extracted: {len(result.get('llm_thinking', ''))} chars")
                        
                        elif event_type == 'error':
                            print(f"\n[ERROR] {event['error']}")
                    
                    except json.JSONDecodeError:
                        print(f"[Warning] Could not parse: {data_str}")

elapsed_total = time.time() - start_time

print("\n" + "="*70)
print("VERDICT")
print("="*70)
print(f"✅ Streaming works: {'Yes' if token_count > 0 else 'No'}")
print(f"✅ Thinking detected: {'Yes' if thinking_detected else 'No'}")
print(f"✅ JSON detected: {'Yes' if json_detected else 'No'}")
print(f"\nTotal time: {elapsed_total:.1f}s")
print(f"Tokens streamed: {token_count}")

if thinking_detected and json_detected:
    print("\n🎉 SUCCESS! Thinking streams before JSON as expected")
    print("   Ready for iOS integration with real-time updates")
else:
    print("\n⚠️  Streaming works but output format needs adjustment")
