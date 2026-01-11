#!/usr/bin/env python3
"""
Test script to verify RAG_ENABLED environment variable functionality
"""
import os
import sys

def test_rag_config():
    """Test RAG_ENABLED configuration with different scenarios"""

    print("="*60)
    print("Testing RAG_ENABLED Environment Variable")
    print("="*60)

    # Test 1: Default behavior (no env var set)
    print("\n[Test 1] No environment variable set")
    if 'RAG_ENABLED' in os.environ:
        del os.environ['RAG_ENABLED']

    # Need to reload the module to get fresh config
    if 'mondrian.config' in sys.modules:
        del sys.modules['mondrian.config']

    from mondrian.config import RAG_ENABLED
    print(f"  Result: RAG_ENABLED = {RAG_ENABLED}")
    assert RAG_ENABLED == False, "Default should be False"
    print("  ✓ PASS: Defaults to False")

    # Test 2: Env var set to 'true'
    print("\n[Test 2] RAG_ENABLED=true")
    os.environ['RAG_ENABLED'] = 'true'

    if 'mondrian.config' in sys.modules:
        del sys.modules['mondrian.config']

    from mondrian.config import RAG_ENABLED as RAG_ENABLED_TRUE
    print(f"  Result: RAG_ENABLED = {RAG_ENABLED_TRUE}")
    assert RAG_ENABLED_TRUE == True, "Should be True when set to 'true'"
    print("  ✓ PASS: Returns True")

    # Test 3: Env var set to '1'
    print("\n[Test 3] RAG_ENABLED=1")
    os.environ['RAG_ENABLED'] = '1'

    if 'mondrian.config' in sys.modules:
        del sys.modules['mondrian.config']

    from mondrian.config import RAG_ENABLED as RAG_ENABLED_ONE
    print(f"  Result: RAG_ENABLED = {RAG_ENABLED_ONE}")
    assert RAG_ENABLED_ONE == True, "Should be True when set to '1'"
    print("  ✓ PASS: Returns True")

    # Test 4: Env var set to 'yes'
    print("\n[Test 4] RAG_ENABLED=yes")
    os.environ['RAG_ENABLED'] = 'yes'

    if 'mondrian.config' in sys.modules:
        del sys.modules['mondrian.config']

    from mondrian.config import RAG_ENABLED as RAG_ENABLED_YES
    print(f"  Result: RAG_ENABLED = {RAG_ENABLED_YES}")
    assert RAG_ENABLED_YES == True, "Should be True when set to 'yes'"
    print("  ✓ PASS: Returns True")

    # Test 5: Env var set to 'false'
    print("\n[Test 5] RAG_ENABLED=false")
    os.environ['RAG_ENABLED'] = 'false'

    if 'mondrian.config' in sys.modules:
        del sys.modules['mondrian.config']

    from mondrian.config import RAG_ENABLED as RAG_ENABLED_FALSE
    print(f"  Result: RAG_ENABLED = {RAG_ENABLED_FALSE}")
    assert RAG_ENABLED_FALSE == False, "Should be False when set to 'false'"
    print("  ✓ PASS: Returns False")

    # Test 6: Env var set to random value
    print("\n[Test 6] RAG_ENABLED=random")
    os.environ['RAG_ENABLED'] = 'random'

    if 'mondrian.config' in sys.modules:
        del sys.modules['mondrian.config']

    from mondrian.config import RAG_ENABLED as RAG_ENABLED_RANDOM
    print(f"  Result: RAG_ENABLED = {RAG_ENABLED_RANDOM}")
    assert RAG_ENABLED_RANDOM == False, "Should be False for invalid values"
    print("  ✓ PASS: Returns False for invalid values")

    print("\n" + "="*60)
    print("ALL TESTS PASSED ✓")
    print("="*60)

    # Clean up
    if 'RAG_ENABLED' in os.environ:
        del os.environ['RAG_ENABLED']

if __name__ == "__main__":
    test_rag_config()
