#!/usr/bin/env python3
"""
Test script to verify case study selection provides variety
"""
import random

# Test the weighted sampling logic
candidates = [
    {'name': 'visual_balance', 'gap': 3.0, 'relevance': 0.8, 'weight': 2.4},
    {'name': 'emotional_impact', 'gap': 2.5, 'relevance': 0.7, 'weight': 1.75},
    {'name': 'composition', 'gap': 2.0, 'relevance': 0.6, 'weight': 1.2},
    {'name': 'lighting', 'gap': 1.5, 'relevance': 0.5, 'weight': 0.75},
]

# Simulate selection 10 times to show variety
print('Simulating case study selection 10 times:')
print('=' * 60)
for run in range(10):
    selected = [candidates[0]]  # Always take top
    remaining = candidates[1:]
    total_weight = sum(c['weight'] for c in remaining)
    weights = [c['weight'] / total_weight for c in remaining]
    
    # Sample 2 more
    sampled_indices = random.choices(range(len(remaining)), weights=weights, k=2)
    seen = set()
    for idx in sampled_indices:
        if idx not in seen and len(selected) < 3:
            seen.add(idx)
            selected.append(remaining[idx])
    
    names = [c['name'] for c in selected]
    print(f'Run {run+1:2d}: {names}')
    
print('\n' + '=' * 60)
print('Expected behavior:')
print('- visual_balance ALWAYS appears (highest weight)')
print('- emotional_impact appears most often (2nd highest weight)')
print('- composition appears less often (3rd highest weight)')
print('- lighting appears least often (lowest weight)')
print('- But ALL dimensions CAN appear, providing variety!')
