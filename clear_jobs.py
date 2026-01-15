#!/usr/bin/env python3
"""
Clear all jobs from the Mondrian jobs database.
This will delete all job records but preserve the schema and advisor data.
"""
import os
import sqlite3
import sys

# Get database path from config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mondrian"))
from config import DATABASE_PATH

def clear_jobs():
    """Clear all jobs from the database"""
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Database not found at: {DATABASE_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get count before deletion
        cursor.execute("SELECT COUNT(*) FROM jobs")
        count_before = cursor.fetchone()[0]
        
        if count_before == 0:
            print("✓ Jobs table is already empty")
            conn.close()
            return True
        
        # Delete all jobs
        cursor.execute("DELETE FROM jobs")
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM jobs")
        count_after = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✓ Successfully cleared {count_before} job(s) from database")
        print(f"✓ Jobs remaining: {count_after}")
        print(f"✓ Database: {DATABASE_PATH}")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  Clear Mondrian Jobs Database")
    print("=" * 60)
    print()
    
    # Confirm action
    response = input("⚠️  This will delete ALL jobs. Continue? (yes/no): ").strip().lower()
    
    if response not in ["yes", "y"]:
        print("❌ Cancelled")
        sys.exit(0)
    
    print()
    success = clear_jobs()
    print()
    
    if success:
        print("✓ Done! You can now restart services with:")
        print("  ./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel")
    else:
        print("❌ Failed to clear jobs")
        sys.exit(1)
