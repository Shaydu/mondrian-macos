#!/usr/bin/env python3
"""
Database Backup Script

Creates a timestamped backup of mondrian.db in the backups/ directory.
Usage: python scripts/backup_database.py
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Paths
DB_PATH = PROJECT_ROOT / "mondrian.db"
BACKUP_DIR = PROJECT_ROOT / "backups"

def backup_database():
    """Create a timestamped backup of the database"""
    
    # Ensure backup directory exists
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Check if database exists
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return False
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"mondrian.db.{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    
    # Copy database
    try:
        print(f"📦 Backing up database...")
        print(f"   Source: {DB_PATH}")
        print(f"   Backup: {backup_path}")
        
        shutil.copy2(DB_PATH, backup_path)
        
        # Verify backup
        if backup_path.exists():
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            print(f"✅ Backup created successfully ({size_mb:.2f} MB)")
            print(f"   Location: {backup_path}")
            return True
        else:
            print(f"❌ Backup verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

if __name__ == "__main__":
    success = backup_database()
    exit(0 if success else 1)
