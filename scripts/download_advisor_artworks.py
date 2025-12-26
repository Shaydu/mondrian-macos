#!/usr/bin/env python3
"""Download representative artworks/photographs for each advisor from Wikipedia/Commons.

Saves artwork to `mondrian/advisor_artworks/<advisor_id>/<filename>.jpg`
so they can be served at `/advisor_artwork/<advisor_id>/<filename>`.
"""
import os
import sqlite3
import time
from urllib.parse import urlparse, unquote
import requests


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT, 'mondrian.db')
ADVISOR_ARTWORKS_DIR = os.path.join(ROOT, 'mondrian', 'advisor_artworks')

os.makedirs(ADVISOR_ARTWORKS_DIR, exist_ok=True)

COMMONS_API = 'https://commons.wikimedia.org/w/api.php'

# Use a requests session with a browser-like User-Agent
SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
})

# Define specific artworks for each advisor
ADVISOR_ARTWORKS = {
    'ansel': [
        'File:Adams The Tetons and the Snake River.jpg',
        'File:Ansel Adams - National Archives 79-AA-Q04.jpg',
        'File:Ansel Adams - National Archives 79-AAB-02.jpg',
        'File:Clearing Winter Storm, Yosemite National Park, CA 1944.jpg',
        'File:Half Dome, Merced River, Winter - Ansel Adams.jpg',
    ],
    'watkins': [
        'File:Carleton Watkins - Cape Horn, Columbia River, Oregon - Google Art Project.jpg',
        'File:Carleton Watkins - El Capitan, Yosemite - Google Art Project.jpg',
        'File:Carleton Watkins - Three Brothers, Yosemite - Google Art Project.jpg',
        'File:Carleton Watkins - The Grizzly Giant Sequoia, Mariposa Grove, Yosemite.jpg',
    ],
    'weston': [
        'File:Edward Weston - Pepper No. 30, 1930.jpg',
        'File:Edward Weston, Shells, 1927.jpg',
        'File:Edward Weston - Nautilus, 1927.jpg',
    ],
    'cunningham': [
        'File:Imogen Cunningham - Magnolia Blossom.jpg',
        'File:Imogen Cunningham - Two Callas.jpg',
        'File:Imogen Cunningham, Triangles, 1928.jpg',
    ],
    'gilpin': [
        'File:Mission_Church_Taos_LC-USZC4-3921.jpg',
        'File:P1979-95-93_s.jpg',
        'File:The_prelude_LCCN95506525.jpg',
        'File:Laura_Gilpin_Sunday_After_Church,1919.jpg',
    ],
    'mondrian': [
        'File:Piet Mondriaan, 1930 - Mondrian Composition II in Red, Blue, and Yellow.jpg',
        'File:Piet Mondrian - Composition with Red, Yellow and Blue - 1935-1942.jpg',
        'File:Piet Mondrian, 1921 - Composition en rouge, jaune, bleu et noir.jpg',
        'File:Tableau I, by Piet Mondriaan.jpg',
        'File:Piet Mondrian - Broadway Boogie Woogie - 1942-43.jpg',
    ],
    'okeefe': [
        'File:Brooklyn Museum - Red Canna - Georgia O\'Keeffe - overall.jpg',
        'File:Georgia O\'Keeffe - Jimson Weed-White Flower No 1 - 2014.jpg',
        'File:Georgia O\'Keeffe, Sky Above Clouds IV, 1965.jpg',
        'File:Georgia O\'Keeffe - Cow\'s Skull, Red, White, and Blue - Google Art Project.jpg',
    ],
    'vangogh': [
        'File:Vincent van Gogh - The Starry Night - Google Art Project.jpg',
        'File:Van Gogh - Starry Night - Google Art Project.jpg',
        'File:Vincent Willem van Gogh 138.jpg',
        'File:Vincent van Gogh - Sunflowers - VGM F458.jpg',
        'File:Vincent van Gogh - Irises - Google Art Project.jpg',
        'File:Vincent van Gogh - Almond blossom - Google Art Project.jpg',
    ],
    'gehry': [
        'File:Guggenheim Museum Bilbao HDR 2.jpg',
        'File:Walt Disney Concert Hall, LA, CA, jjron 22.03.2012.jpg',
        'File:Fondation Louis Vuitton - panoramio (1).jpg',
        'File:Dancing House in Prague.jpg',
    ],
}


def download_url(url, dest_path, max_retries=3):
    """Download a file from URL to dest_path."""
    for attempt in range(max_retries):
        try:
            resp = SESSION.get(url, stream=True, timeout=30)
            if resp.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                return True
            else:
                print(f"  WARN: {url} returned {resp.status_code}")
                return False
        except Exception as e:
            print(f"  WARN: download attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return False


def get_commons_file_url(file_title):
    """Get the actual file URL from a Commons File: page title."""
    try:
        params = {
            'action': 'query',
            'titles': file_title,
            'prop': 'imageinfo',
            'iiprop': 'url',
            'format': 'json'
        }
        r = SESSION.get(COMMONS_API, params=params, timeout=15)
        if r.status_code != 200:
            return None

        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for page in pages.values():
            imageinfo = page.get('imageinfo')
            if imageinfo and isinstance(imageinfo, list) and len(imageinfo) > 0:
                return imageinfo[0].get('url')
        return None
    except Exception as e:
        print(f"  ERROR: Failed to get file URL for {file_title}: {e}")
        return None


def search_commons_category(category_name, limit=6):
    """Search a Commons category for image files."""
    try:
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': category_name,
            'cmnamespace': 6,  # File namespace
            'cmlimit': limit * 2,  # Get extra in case some fail
            'format': 'json'
        }
        r = SESSION.get(COMMONS_API, params=params, timeout=15)
        if r.status_code != 200:
            return []

        data = r.json()
        members = data.get('query', {}).get('categorymembers', [])
        return [m['title'] for m in members if 'title' in m][:limit]
    except Exception as e:
        print(f"  ERROR: Failed to search category {category_name}: {e}")
        return []


def download_advisor_artworks(advisor_id, advisor_name, commons_url):
    """Download artworks for a specific advisor."""
    print(f"\n{'='*60}")
    print(f"Processing: {advisor_name} ({advisor_id})")
    print(f"{'='*60}")

    # Create directory for this advisor's artworks
    advisor_dir = os.path.join(ADVISOR_ARTWORKS_DIR, advisor_id)
    os.makedirs(advisor_dir, exist_ok=True)

    # Get artwork file titles
    artwork_files = []

    # First, try specific artworks if defined
    if advisor_id in ADVISOR_ARTWORKS:
        curated = ADVISOR_ARTWORKS[advisor_id]
        print(f"Trying {len(curated)} curated artworks")

        # Test which curated files actually exist
        for file_title in curated:
            if get_commons_file_url(file_title):
                artwork_files.append(file_title)

        print(f"  {len(artwork_files)} curated artworks are accessible")

    # If we don't have enough, search the Commons category
    if len(artwork_files) < 3 and commons_url and '/wiki/Category:' in commons_url:
        category = commons_url.split('/wiki/')[-1]
        category = unquote(category)
        print(f"Searching Commons category for more: {category}")
        category_files = search_commons_category(category, limit=6)
        # Add files we don't already have
        for f in category_files:
            if f not in artwork_files:
                artwork_files.append(f)
        print(f"  Total files to download: {len(artwork_files)}")

    if not artwork_files:
        print(f"  No artworks found for {advisor_id}")
        return

    # Download each artwork
    downloaded = 0
    for idx, file_title in enumerate(artwork_files, 1):
        # Get the actual file URL
        print(f"\n[{idx}/{len(artwork_files)}] Processing: {file_title}")
        file_url = get_commons_file_url(file_title)

        if not file_url:
            print(f"  ✗ Could not get file URL")
            continue

        # Determine local filename
        filename = file_title.replace('File:', '').replace(' ', '_')
        # Sanitize filename
        filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            filename += '.jpg'

        dest_path = os.path.join(advisor_dir, filename)

        # Skip if already exists and is large enough
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
            print(f"  ✓ Already exists: {filename}")
            downloaded += 1
            continue

        # Download the file
        print(f"  Downloading: {file_url[:80]}...")
        if download_url(file_url, dest_path):
            size = os.path.getsize(dest_path)
            print(f"  ✓ Downloaded: {filename} ({size:,} bytes)")
            downloaded += 1
        else:
            print(f"  ✗ Failed to download")

        # Be nice to Wikimedia servers
        time.sleep(0.5)

    print(f"\n{advisor_name}: Downloaded {downloaded}/{len(artwork_files)} artworks")


def main():
    """Main function to download artworks for all advisors."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, commons_url FROM advisors ORDER BY id")
    advisors = cursor.fetchall()
    conn.close()

    print(f"Starting artwork download for {len(advisors)} advisors")
    print(f"Output directory: {ADVISOR_ARTWORKS_DIR}")

    for advisor in advisors:
        download_advisor_artworks(
            advisor['id'],
            advisor['name'],
            advisor['commons_url']
        )

    print("\n" + "="*60)
    print("✓ All advisor artworks downloaded!")
    print("="*60)


if __name__ == '__main__':
    main()
