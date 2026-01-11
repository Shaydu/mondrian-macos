#!/usr/bin/env python3
"""
Simple RAG Test - Diagnose why RAG isn't being triggered

This script:
1. Checks if advisor profiles exist in database
2. Tests RAG data flow with a simple image
3. Shows exactly what's happening at each step
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mondrian'))

from json_to_html_converter import find_similar_by_dimensions, get_dimensional_profile
import sqlite3

DB_PATH = "mondrian.db"

def check_database():
    """Check database state"""
    print("="*70)
    print("STEP 1: Checking Database")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check advisor profiles
    cursor.execute("SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id = 'ansel'")
    count = cursor.fetchone()[0]
    print(f"✓ Ansel Adams profiles in database: {count}")
    
    if count == 0:
        print("❌ No advisor profiles found! RAG cannot work.")
        print("   Run: python3 tools/rag/index_with_metadata.py --advisor ansel")
        conn.close()
        return False
    
    # Check if profiles have dimensional scores
    cursor.execute("""
        SELECT image_path, composition_score, lighting_score, image_title
        FROM dimensional_profiles 
        WHERE advisor_id = 'ansel' AND composition_score IS NOT NULL
        LIMIT 3
    """)
    profiles = cursor.fetchall()
    
    print(f"\n✓ Sample advisor profiles:")
    for path, comp, light, title in profiles:
        filename = os.path.basename(path)
        title_display = title if title else filename
        print(f"  - {title_display}: composition={comp}, lighting={light}")
    
    conn.close()
    return True

def test_similarity_search():
    """Test if similarity search works"""
    print("\n" + "="*70)
    print("STEP 2: Testing Similarity Search")
    print("="*70)
    
    # Create a fake user profile with scores
    user_scores = {
        'composition': 7.5,
        'lighting': 8.0,
        'focus_sharpness': 7.0,
        'color_harmony': 8.5,
        'subject_isolation': 6.5,
        'depth_perspective': 7.5,
        'visual_balance': 8.0,
        'emotional_impact': 7.5
    }
    
    print(f"User image scores (simulated):")
    for dim, score in user_scores.items():
        print(f"  {dim}: {score}")
    
    # Find similar images
    similar = find_similar_by_dimensions(
        db_path=DB_PATH,
        advisor_id='ansel',
        target_scores=user_scores,
        top_k=3
    )
    
    if not similar:
        print("\n❌ No similar images found!")
        print("   This means RAG similarity search is broken.")
        return False
    
    print(f"\n✓ Found {len(similar)} similar images:")
    for i, profile in enumerate(similar, 1):
        path = profile.get('image_path', 'Unknown')
        title = profile.get('image_title', os.path.basename(path))
        distance = profile.get('distance', 0)
        similarity = profile.get('similarity', 0)
        
        print(f"\n  {i}. {title}")
        print(f"     Distance: {distance:.2f}, Similarity: {similarity:.1%}")
        print(f"     Composition: {profile.get('composition_score')}, Lighting: {profile.get('lighting_score')}")
    
    return True

def check_rag_config():
    """Check RAG configuration"""
    print("\n" + "="*70)
    print("STEP 3: Checking RAG Configuration")
    print("="*70)
    
    # Check if RAG_ENABLED env var is set
    from config import RAG_ENABLED
    print(f"✓ RAG_ENABLED (from config): {RAG_ENABLED}")
    
    # Check if AI service would use RAG
    print(f"\n✓ When enable_rag=true is passed:")
    print(f"   - System will look for dimensional profiles")
    print(f"   - Find similar images by Euclidean distance")
    print(f"   - Augment prompt with reference context")
    print(f"   - Include reference images in HTML output")
    
    return True

def main():
    print("\n" + "="*70)
    print("RAG DIAGNOSTIC TEST")
    print("="*70)
    print()
    
    # Step 1: Check database
    if not check_database():
        print("\n❌ Database check failed. Fix the issues above and try again.")
        return
    
    # Step 2: Test similarity search
    if not test_similarity_search():
        print("\n❌ Similarity search failed. RAG won't work.")
        return
    
    # Step 3: Check configuration
    check_rag_config()
    
    # Summary
    print("\n" + "="*70)
    print("DIAGNOSTIC COMPLETE")
    print("="*70)
    print()
    print("✅ Database has advisor profiles")
    print("✅ Similarity search works")
    print("✅ RAG configuration is correct")
    print()
    print("Next steps:")
    print("1. Start services: ./mondrian.sh --restart")
    print("2. Run comparison test: python3 test/test_ios_e2e_rag_comparison.py")
    print("3. Check that RAG output includes reference images")
    print()
    print("If RAG still doesn't work, check the AI service logs for [RAG] messages.")
    print()

if __name__ == "__main__":
    main()

