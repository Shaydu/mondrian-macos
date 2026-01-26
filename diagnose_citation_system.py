#!/usr/bin/env python3
"""
Citation System Diagnostic Script

This script checks if the citation system is working by verifying:
1. Reference images are in the database with embeddings
2. Book passages are in the database with embeddings
3. The retrieval functions return data
4. Image paths can be resolved
"""

import sqlite3
import sys
from pathlib import Path

# Configuration
DB_PATH = 'mondrian.db'
ADVISOR_ID = 'ansel'

def check_database_connection():
    """Verify database exists and is accessible"""
    print("\n" + "="*70)
    print("1. DATABASE CONNECTION")
    print("="*70)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        if cursor.fetchone():
            print(f"✅ Database '{DB_PATH}' is accessible")
            return conn
        else:
            print(f"❌ Database '{DB_PATH}' is empty or corrupted")
            return None
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None

def check_reference_images(conn):
    """Check reference images in database"""
    print("\n" + "="*70)
    print("2. REFERENCE IMAGES (dimensional_profiles)")
    print("="*70)
    
    try:
        cursor = conn.cursor()
        
        # Count total profiles
        cursor.execute(
            "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id = ?",
            (ADVISOR_ID,)
        )
        total = cursor.fetchone()[0]
        print(f"Total profiles for '{ADVISOR_ID}': {total}")
        
        # Count profiles with embeddings
        cursor.execute(
            "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id = ? AND embedding IS NOT NULL",
            (ADVISOR_ID,)
        )
        with_embeddings = cursor.fetchone()[0]
        print(f"Profiles with embeddings: {with_embeddings}")
        
        if total == 0:
            print("⚠️  No reference images found - citations cannot work")
            return False
        
        if with_embeddings == 0:
            print("⚠️  No embeddings computed - retrieval will fail")
            return False
        
        # Show sample profiles
        cursor.execute(
            """SELECT id, image_title, image_path, 
                      composition_score, lighting_score, focus_sharpness_score,
                      embedding IS NOT NULL as has_embedding
               FROM dimensional_profiles 
               WHERE advisor_id = ? 
               LIMIT 3""",
            (ADVISOR_ID,)
        )
        
        print("\nSample profiles:")
        for row in cursor.fetchall():
            id_, title, path, comp, light, focus, has_emb = row
            print(f"  • {title}")
            print(f"    Path: {path}")
            print(f"    Scores: Composition={comp}, Lighting={light}, Focus={focus}")
            print(f"    Embedding: {'✅ Yes' if has_emb else '❌ No'}")
        
        return with_embeddings > 0
        
    except Exception as e:
        print(f"❌ Error checking reference images: {e}")
        return False

def check_book_passages(conn):
    """Check book passages in database"""
    print("\n" + "="*70)
    print("3. BOOK PASSAGES (Quotes)")
    print("="*70)
    
    try:
        cursor = conn.cursor()
        
        # Count total passages
        cursor.execute(
            "SELECT COUNT(*) FROM book_passages WHERE advisor_id = ?",
            (ADVISOR_ID,)
        )
        total = cursor.fetchone()[0]
        print(f"Total passages for '{ADVISOR_ID}': {total}")
        
        # Count passages with embeddings
        cursor.execute(
            "SELECT COUNT(*) FROM book_passages WHERE advisor_id = ? AND embedding IS NOT NULL",
            (ADVISOR_ID,)
        )
        with_embeddings = cursor.fetchone()[0]
        print(f"Passages with embeddings: {with_embeddings}")
        
        if total == 0:
            print("⚠️  No book passages found - quote citations cannot work")
            return False
        
        if with_embeddings == 0:
            print("⚠️  No embeddings computed - retrieval will fail")
            return False
        
        # Show sample passages
        cursor.execute(
            """SELECT id, book_title, passage_text, dimension_tags,
                      embedding IS NOT NULL as has_embedding
               FROM book_passages 
               WHERE advisor_id = ? 
               LIMIT 3""",
            (ADVISOR_ID,)
        )
        
        print("\nSample passages:")
        for row in cursor.fetchall():
            id_, book, text, dims, has_emb = row
            preview = text[:80] + "..." if len(text) > 80 else text
            print(f"  • [{id_}] {book}")
            print(f"    Text: {preview}")
            print(f"    Embedding: {'✅ Yes' if has_emb else '❌ No'}")
        
        return with_embeddings > 0
        
    except Exception as e:
        print(f"❌ Error checking book passages: {e}")
        return False

def check_retrieval_functions():
    """Test the retrieval functions"""
    print("\n" + "="*70)
    print("4. RETRIEVAL FUNCTIONS")
    print("="*70)
    
    try:
        from mondrian.rag_retrieval import get_top_reference_images
        from mondrian.embedding_retrieval import get_top_book_passages
        
        # Test reference image retrieval
        print(f"\nTesting get_top_reference_images('{DB_PATH}', '{ADVISOR_ID}', max_total=10)")
        ref_images = get_top_reference_images(DB_PATH, ADVISOR_ID, max_total=10)
        
        if ref_images is None:
            print("❌ get_top_reference_images returned None")
        elif len(ref_images) == 0:
            print("⚠️  get_top_reference_images returned empty list")
            print("   → Check if embeddings exist")
        else:
            print(f"✅ Retrieved {len(ref_images)} reference images")
            for idx, img in enumerate(ref_images[:3], 1):
                print(f"  IMG_{idx}: {img.get('image_title')}")
        
        # Test book passage retrieval
        print(f"\nTesting get_top_book_passages('{ADVISOR_ID}', max_passages=6)")
        passages = get_top_book_passages(advisor_id=ADVISOR_ID, max_passages=6)
        
        if passages is None:
            print("❌ get_top_book_passages returned None")
        elif len(passages) == 0:
            print("⚠️  get_top_book_passages returned empty list")
            print("   → Check if embeddings exist")
        else:
            print(f"✅ Retrieved {len(passages)} book passages")
            for idx, p in enumerate(passages[:3], 1):
                text_preview = p.get('passage_text', p.get('text', ''))[:50] + "..."
                print(f"  QUOTE_{idx}: {p.get('book_title')} - {text_preview}")
        
        return len(ref_images) > 0 and len(passages) > 0
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   → Check if mondrian modules are in Python path")
        return False
    except Exception as e:
        print(f"❌ Error testing retrieval functions: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_image_paths():
    """Check if image paths can be resolved"""
    print("\n" + "="*70)
    print("5. IMAGE PATH RESOLUTION")
    print("="*70)
    
    try:
        from mondrian.html_generator import resolve_image_path
        import os
        
        # Get sample image paths from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT image_path FROM dimensional_profiles WHERE advisor_id = ? LIMIT 3",
            (ADVISOR_ID,)
        )
        
        paths = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not paths:
            print("⚠️  No image paths in database to test")
            return True
        
        print(f"\nTesting resolution for {len(paths)} sample images:")
        all_resolved = True
        
        for path in paths:
            resolved = resolve_image_path(path)
            if resolved and os.path.exists(resolved):
                print(f"  ✅ {path}")
                print(f"     → {resolved}")
            else:
                print(f"  ❌ {path}")
                print(f"     → Could not resolve")
                all_resolved = False
        
        return all_resolved
        
    except Exception as e:
        print(f"❌ Error checking image paths: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic checks"""
    print("\n" + "="*70)
    print("CITATION SYSTEM DIAGNOSTIC")
    print("="*70)
    print(f"Database: {DB_PATH}")
    print(f"Advisor: {ADVISOR_ID}")
    
    # Check 1: Database
    conn = check_database_connection()
    if not conn:
        print("\n❌ Cannot proceed without database")
        return 1
    
    # Check 2: Reference images
    has_ref_images = check_reference_images(conn)
    
    # Check 3: Book passages
    has_passages = check_book_passages(conn)
    
    # Check 4: Retrieval functions
    retrieval_ok = check_retrieval_functions()
    
    # Check 5: Image paths
    paths_ok = check_image_paths()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    checks = {
        "Database accessible": conn is not None,
        "Reference images exist": has_ref_images,
        "Book passages exist": has_passages,
        "Retrieval functions work": retrieval_ok,
        "Image paths resolvable": paths_ok,
    }
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    for check, result in checks.items():
        symbol = "✅" if result else "❌"
        print(f"{symbol} {check}")
    
    print(f"\nPassed: {passed}/{total}")
    
    # Recommendations
    if passed < total:
        print("\n" + "="*70)
        print("RECOMMENDATIONS")
        print("="*70)
        
        if not has_ref_images:
            print("\n1. Reference images missing or not indexed:")
            print("   • Run: python3 batch_analyze_advisor_images.py --advisor ansel")
            print("   • Then: python3 tools/rag/compute_embeddings.py --advisor ansel")
        
        if not has_passages:
            print("\n2. Book passages missing:")
            print("   • Run: python3 tools/rag/import_book_passages.py --advisor ansel")
            print("   • Then: python3 tools/rag/compute_embeddings.py --advisor ansel")
        
        if not paths_ok:
            print("\n3. Image paths cannot be resolved:")
            print("   • Check if image files exist in mondrian/source/advisor/")
            print("   • Check database paths are correct")
            print("   • May need to rebuild database with correct paths")
    else:
        print("\n✅ Citation system is properly configured!")
        print("If citations still don't appear, check:")
        print("   • LLM prompt includes citation instructions")
        print("   • LLM response includes case_study_id and/or quote_id fields")
        print("   • Enable debug logging: --log-level DEBUG")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
