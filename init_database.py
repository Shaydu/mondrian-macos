#!/usr/bin/env python3
"""
Database initialization script for Mondrian services.
Creates all required tables and populates initial data.
"""

import sqlite3
import os
import json

def init_database(db_path):
    """Initialize the database with all required tables and data."""
    print(f"Initializing database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create advisors table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS advisors (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        bio TEXT NOT NULL,
        prompt TEXT,
        years TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create focus_areas table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS focus_areas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        advisor_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (advisor_id) REFERENCES advisors(id) ON DELETE CASCADE
    )
    ''')

    # Create special_options table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS special_options (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0
    )
    ''')

    # Create advisor_usage table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS advisor_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        advisor_id TEXT,
        special_option_id TEXT,
        request_count INTEGER DEFAULT 0,
        last_used TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (advisor_id) REFERENCES advisors(id) ON DELETE SET NULL,
        FOREIGN KEY (special_option_id) REFERENCES special_options(id) ON DELETE SET NULL
    )
    ''')

    # Create jobs table (matching sqlite_helper.py schema)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        filename TEXT,
        advisor TEXT,
        thresholds TEXT,
        thinking INTEGER,
        status TEXT,
        analysis_file TEXT,
        current_step TEXT,
        analysis_markdown TEXT,
        llm_thinking TEXT,
        current_advisor INTEGER,
        total_advisors INTEGER,
        step_phase TEXT,
        llm_outputs TEXT,
        status_history TEXT,
        created_at TEXT,
        started_at TEXT,
        completed_at TEXT,
        type TEXT,
        analysis_markup TEXT,
        llm_prompt TEXT,
        prompt TEXT,
        last_activity TEXT
    )
    ''')

    # Create config table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_focus_areas_advisor_id ON focus_areas(advisor_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_advisor_usage_advisor_id ON advisor_usage(advisor_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_advisor_usage_last_used ON advisor_usage(last_used)')

    # Populate initial advisor data if advisors table is empty
    cursor.execute('SELECT COUNT(*) FROM advisors')
    if cursor.fetchone()[0] == 0:
        print("Populating initial advisor data...")

        # Load advisor prompts and create advisor records
        prompts_dir = os.path.join(os.path.dirname(__file__), "mondrian", "prompts")

        if os.path.exists(prompts_dir):
            advisor_data = [
                ("ansel", "Ansel Adams", "Legendary landscape photographer known for his black and white work and Zone System.", None, "1902-1984"),
                ("okeefe", "Georgia O'Keeffe", "American modernist artist known for her paintings of enlarged flowers and New Mexico landscapes.", None, "1887-1986"),
                ("mondrian", "Piet Mondrian", "Dutch painter known for neoplasticism and geometric abstract art.", None, "1872-1944")
            ]

            for advisor_id, name, bio, prompt, years in advisor_data:
                prompt_file = os.path.join(prompts_dir, f"{advisor_id}.md")
                if os.path.exists(prompt_file):
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        prompt_content = f.read()
                else:
                    prompt_content = prompt

                cursor.execute('''
                INSERT INTO advisors (id, name, bio, prompt, years)
                VALUES (?, ?, ?, ?, ?)
                ''', (advisor_id, name, bio, prompt_content, years))

        # Add some focus areas
        focus_areas_data = [
            ("ansel", "Black & White Photography", "Mastery of contrast, tonality, and the Zone System"),
            ("ansel", "Landscape Composition", "Rule of thirds, leading lines, and natural light"),
            ("okeefe", "Color Theory", "Bold colors, contrast, and emotional impact"),
            ("okeefe", "Organic Forms", "Flowers, bones, and natural abstraction"),
            ("mondrian", "Geometric Abstraction", "Primary colors, straight lines, and balance"),
            ("mondrian", "Composition", "Grid systems and spatial relationships")
        ]

        for advisor_id, title, description in focus_areas_data:
            cursor.execute('''
            INSERT INTO focus_areas (advisor_id, title, description)
            VALUES (?, ?, ?)
            ''', (advisor_id, title, description))

    # Populate special options if empty
    cursor.execute('SELECT COUNT(*) FROM special_options')
    if cursor.fetchone()[0] == 0:
        special_options_data = [
            ("detailed", "Detailed Analysis", "Provides comprehensive feedback with specific recommendations"),
            ("quick", "Quick Review", "Fast assessment with key highlights"),
            ("technical", "Technical Focus", "Emphasizes camera settings and technical aspects")
        ]

        for option_id, name, description in special_options_data:
            cursor.execute('''
            INSERT INTO special_options (id, name, description)
            VALUES (?, ?, ?)
            ''', (option_id, name, description))

    conn.commit()
    conn.close()
    print("Database initialization complete!")

if __name__ == "__main__":
    # Default database path
    db_path = "mondrian.db"
    init_database(db_path)





