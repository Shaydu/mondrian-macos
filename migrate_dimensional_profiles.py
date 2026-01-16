#!/usr/bin/env python3
"""
Create dimensional_profiles table for RAG functionality

This table stores dimensional analysis scores for both:
- Advisor reference images (e.g., Ansel Adams photos)
- User uploaded images

The RAG system uses these profiles to find similar images and provide
comparative feedback.
"""

import sqlite3
import os
import sys

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "mondrian.db")

def create_dimensional_profiles_table():
    """Create the dimensional_profiles table if it doesn't exist."""
    
    print("=" * 70)
    print("Creating dimensional_profiles table for RAG")
    print("=" * 70)
    print(f"Database: {DB_PATH}")
    print()
    
    if not os.path.exists(DB_PATH):
        print(f"[✗] Database not found: {DB_PATH}")
        sys.exit(1)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='dimensional_profiles'
        """)
        
        if cursor.fetchone():
            print("[INFO] dimensional_profiles table already exists")
            print()
            
            # Show count of existing profiles
            cursor.execute("SELECT COUNT(*) FROM dimensional_profiles")
            count = cursor.fetchone()[0]
            print(f"  Current profiles: {count}")
            
            # Show breakdown by advisor
            cursor.execute("""
                SELECT advisor_id, COUNT(*) 
                FROM dimensional_profiles 
                GROUP BY advisor_id
            """)
            for advisor_id, adv_count in cursor.fetchall():
                print(f"    {advisor_id}: {adv_count} images")
            
            conn.close()
            print()
            print("[✓] Table exists and is ready for use")
            return
        
        # Create the table
        print("[INFO] Creating dimensional_profiles table...")
        
        cursor.execute('''
            CREATE TABLE dimensional_profiles (
                -- Identity
                id TEXT PRIMARY KEY,
                job_id TEXT,
                advisor_id TEXT NOT NULL,
                image_path TEXT NOT NULL,
                
                -- 8 Dimensional Scores (0-10)
                composition_score REAL,
                lighting_score REAL,
                focus_sharpness_score REAL,
                color_harmony_score REAL,
                subject_isolation_score REAL,
                depth_perspective_score REAL,
                visual_balance_score REAL,
                emotional_impact_score REAL,
                
                -- 8 Dimensional Comments
                composition_comment TEXT,
                lighting_comment TEXT,
                focus_sharpness_comment TEXT,
                color_harmony_comment TEXT,
                subject_isolation_comment TEXT,
                depth_perspective_comment TEXT,
                visual_balance_comment TEXT,
                emotional_impact_comment TEXT,
                
                -- Summary
                overall_grade TEXT,
                image_description TEXT,
                analysis_html TEXT,
                
                -- Rich Metadata (for reference images)
                image_title TEXT,
                date_taken TEXT,
                location TEXT,
                image_significance TEXT,
                
                -- Technique Data (JSON)
                techniques TEXT,
                
                -- Timestamp
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Indexes for fast RAG queries
                UNIQUE(advisor_id, image_path)
            )
        ''')
        
        # Create indexes for fast similarity search
        cursor.execute('''
            CREATE INDEX idx_dimensional_advisor 
            ON dimensional_profiles(advisor_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX idx_dimensional_scores 
            ON dimensional_profiles(
                composition_score, lighting_score, 
                focus_sharpness_score, color_harmony_score
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("[✓] Table created successfully")
        print()
        print("Next steps:")
        print("  1. Index Ansel Adams reference images:")
        print("     python3 tools/rag/index_ansel_dimensional_profiles.py")
        print()
        print("  2. Test RAG with a user image:")
        print("     curl -X POST http://localhost:5005/upload \\")
        print("       -F 'image=@my_photo.jpg' \\")
        print("       -F 'advisor=ansel' \\")
        print("       -F 'enable_rag=true'")
        print()
        
    except Exception as e:
        print(f"[✗] Error creating table: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_dimensional_profiles_table()




