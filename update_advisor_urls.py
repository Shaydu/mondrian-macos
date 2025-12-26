#!/usr/bin/env python3
"""Update advisor database with Wikipedia and Commons URLs."""
import sqlite3
import os

ROOT = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, 'mondrian.db')

# Advisor metadata with Wikipedia and Commons URLs
ADVISOR_URLS = {
    'watkins': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Carleton_Watkins',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Carleton_Watkins'
    },
    'weston': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Edward_Weston',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Edward_Weston'
    },
    'cunningham': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Imogen_Cunningham',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Imogen_Cunningham'
    },
    'gilpin': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Laura_Gilpin',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Laura_Gilpin'
    },
    'ansel': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Ansel_Adams',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Ansel_Adams'
    },
    'mondrian': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Piet_Mondrian',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Piet_Mondrian'
    },
    'okeefe': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Georgia_O%27Keeffe',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Georgia_O%27Keeffe'
    },
    'vangogh': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Vincent_van_Gogh',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Vincent_van_Gogh'
    },
    'gehry': {
        'wikipedia_url': 'https://en.wikipedia.org/wiki/Frank_Gehry',
        'commons_url': 'https://commons.wikimedia.org/wiki/Category:Frank_Gehry'
    }
}

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for advisor_id, urls in ADVISOR_URLS.items():
        cursor.execute("""
            UPDATE advisors
            SET wikipedia_url = ?, commons_url = ?
            WHERE id = ?
        """, (urls['wikipedia_url'], urls['commons_url'], advisor_id))
        print(f"Updated {advisor_id} with Wikipedia and Commons URLs")

    conn.commit()
    conn.close()
    print("\nAll advisors updated successfully!")

if __name__ == '__main__':
    main()
