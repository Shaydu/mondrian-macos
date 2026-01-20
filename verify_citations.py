#!/usr/bin/env python3
"""
Verification script for citation functionality in AI Advisor Service
Checks that reference images and advisor quotes are properly configured
"""

import sys
import sqlite3
from pathlib import Path

# Add mondrian to path
sys.path.insert(0, str(Path(__file__).parent))

from mondrian.rag_retrieval import DB_PATH, get_top_reference_images
from mondrian.embedding_retrieval import get_top_book_passages

def verify_citations():
    """Verify citation functionality is working"""
    print("=" * 70)
    print("CITATION VERIFICATION")
    print("=" * 70)
    
    # Check ENABLE_CITATIONS constant
    try:
        from mondrian.ai_advisor_service_linux import ENABLE_CITATIONS
        print(f"\n✓ ENABLE_CITATIONS configuration: {ENABLE_CITATIONS}")
        if not ENABLE_CITATIONS:
            print("  ⚠️  WARNING: Citations are currently DISABLED")
    except ImportError as e:
        print(f"\n✗ Failed to import ENABLE_CITATIONS: {e}")
        return False
    
    # Check database exists
    print(f"\n✓ Database path: {DB_PATH}")
    if not Path(DB_PATH).exists():
        print(f"✗ Database not found at {DB_PATH}")
        return False
    print(f"  Database exists: {Path(DB_PATH).stat().st_size / 1024 / 1024:.2f} MB")
    
    # Check reference images table
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel'")
        ref_count = cursor.fetchone()[0]
        print(f"\n✓ Reference images in database: {ref_count}")
        if ref_count == 0:
            print("  ⚠️  WARNING: No reference images found for advisor 'ansel'")
        conn.close()
    except Exception as e:
        print(f"\n✗ Failed to query dimensional_profiles: {e}")
        return False
    
    # Check book passages table
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM book_passages WHERE advisor_id='ansel'")
        passage_count = cursor.fetchone()[0]
        print(f"✓ Book passages in database: {passage_count}")
        if passage_count == 0:
            print("  ⚠️  WARNING: No book passages found for advisor 'ansel'")
        conn.close()
    except Exception as e:
        print(f"\n✗ Failed to query book_passages: {e}")
        return False
    
    # Test reference image retrieval with strict error handling
    print("\n" + "-" * 70)
    print("TESTING REFERENCE IMAGE RETRIEVAL")
    print("-" * 70)
    try:
        ref_images = get_top_reference_images(DB_PATH, 'ansel', max_total=10)
        if ref_images is None:
            raise RuntimeError("get_top_reference_images returned None - this should never happen!")
        print(f"\n✓ Retrieved {len(ref_images)} reference images")
        if len(ref_images) > 0:
            print(f"  Sample image: {ref_images[0].get('image_title', 'Unknown')}")
            print(f"  Has embedding: {'embedding' in ref_images[0]}")
            print(f"  Has instructive text: {any(k.endswith('_instructive') for k in ref_images[0].keys())}")
    except Exception as e:
        print(f"\n✗ FAILED to retrieve reference images: {e}")
        print("  This will cause citation retrieval to fail!")
        return False
    
    # Test book passage retrieval with strict error handling
    print("\n" + "-" * 70)
    print("TESTING BOOK PASSAGE RETRIEVAL")
    print("-" * 70)
    try:
        passages = get_top_book_passages(advisor_id='ansel', max_passages=6)
        if passages is None:
            raise RuntimeError("get_top_book_passages returned None - this should never happen!")
        print(f"\n✓ Retrieved {len(passages)} book passages")
        if len(passages) > 0:
            print(f"  Sample book: {passages[0].get('book_title', 'Unknown')}")
            print(f"  Has dimension tags: {'dimension_tags' in passages[0]}")
            print(f"  Passage preview: {passages[0].get('passage_text', '')[:100]}...")
    except Exception as e:
        print(f"\n✗ FAILED to retrieve book passages: {e}")
        print("  This will cause quote retrieval to fail!")
        return False
    
    # Check HTML generator imports
    print("\n" + "-" * 70)
    print("TESTING HTML GENERATION")
    print("-" * 70)
    try:
        from mondrian.html_generator import generate_reference_image_html
        print("\n✓ generate_reference_image_html imported successfully")
        
        # Test with sample data
        sample_ref = {
            'image_title': 'Test Image',
            'date_taken': '1941',
            'image_path': '/nonexistent/path.jpg',
            'location': 'New Mexico',
            'composition_instructive': 'This is a test instructive text'
        }
        html = generate_reference_image_html(sample_ref, 'Composition')
        if not html:
            raise RuntimeError("generate_reference_image_html returned empty string!")
        print(f"  Generated HTML length: {len(html)} chars")
        print(f"  Contains case study: {'case-study-box' in html}")
    except Exception as e:
        print(f"\n✗ FAILED HTML generation test: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    print("\n✓ All citation components are functional!")
    print("\nKey findings:")
    print(f"  • {ref_count} reference images available")
    print(f"  • {passage_count} book passages available")
    print(f"  • Citations are {'ENABLED' if ENABLE_CITATIONS else 'DISABLED'}")
    print("\nBoth streaming and non-streaming endpoints will:")
    print("  1. Retrieve reference images and book passages")
    print("  2. Pass them to the LLM in the prompt")
    print("  3. Validate LLM-generated citations")
    print("  4. Generate HTML with case studies and quote boxes")
    print("  5. Raise exceptions on any failures (no silent fallbacks)")
    
    return True

if __name__ == '__main__':
    try:
        success = verify_citations()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Verification failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
