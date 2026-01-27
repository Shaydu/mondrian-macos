#!/usr/bin/env python3
"""Update advisor artworks from Wikimedia Commons URLs with metadata.

Usage:
    python3 update_advisor_artworks.py gilpin https://commons.wikimedia.org/wiki/File:...jpg [more URLs...]

This script:
1. Removes existing artworks for the specified advisor
2. Downloads new artworks from Wikimedia Commons URLs
3. Stores metadata (source URLs) for linking to full-resolution images
"""
import os
import sys
import json
import sqlite3
import time
from urllib.parse import unquote
import requests


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT, 'mondrian.db')
ADVISOR_ARTWORKS_DIR = os.path.join(ROOT, 'mondrian', 'advisor_artworks')

os.makedirs(ADVISOR_ARTWORKS_DIR, exist_ok=True)

COMMONS_API = 'https://commons.wikimedia.org/w/api.php'

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
})


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


def get_commons_file_info(file_page_url):
    """Get file info from a Commons File: page URL.

    Returns dict with:
        - file_url: Direct URL to the full-resolution file
        - page_url: Original Commons page URL
        - title: File title
        - thumbnail_url: URL to a thumbnail version
    """
    try:
        # Extract the file title from the URL
        if '/wiki/File:' not in file_page_url:
            return None
        file_title = unquote(file_page_url.split('/wiki/')[-1])

        # Query the MediaWiki API to get file info
        params = {
            'action': 'query',
            'titles': file_title,
            'prop': 'imageinfo',
            'iiprop': 'url|size',
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
                info = imageinfo[0]
                return {
                    'file_url': info.get('url'),
                    'page_url': file_page_url,
                    'title': file_title,
                    'thumbnail_url': info.get('thumburl', info.get('url')),
                    'width': info.get('width'),
                    'height': info.get('height'),
                }
        return None
    except Exception as e:
        print(f"  ERROR: Failed to get file info for {file_page_url}: {e}")
        return None


def update_advisor_artworks(advisor_id, commons_urls):
    """Update artworks for a specific advisor.

    Args:
        advisor_id: The advisor ID (e.g., 'gilpin')
        commons_urls: List of Wikimedia Commons File: page URLs
    """
    print(f"\n{'='*60}")
    print(f"Updating artworks for advisor: {advisor_id}")
    print(f"{'='*60}")

    advisor_dir = os.path.join(ADVISOR_ARTWORKS_DIR, advisor_id)
    os.makedirs(advisor_dir, exist_ok=True)

    # Remove existing artwork files
    existing_files = [f for f in os.listdir(advisor_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
    if existing_files:
        print(f"\nRemoving {len(existing_files)} existing artwork files...")
        for filename in existing_files:
            filepath = os.path.join(advisor_dir, filename)
            os.remove(filepath)
            print(f"  ✗ Removed: {filename}")

    # Also remove existing metadata file if present
    metadata_file = os.path.join(advisor_dir, 'metadata.json')
    if os.path.exists(metadata_file):
        os.remove(metadata_file)
        print(f"  ✗ Removed: metadata.json")

    # Download new artworks
    print(f"\nDownloading {len(commons_urls)} new artworks...")
    metadata = []
    downloaded = 0

    for idx, commons_url in enumerate(commons_urls, 1):
        print(f"\n[{idx}/{len(commons_urls)}] Processing: {commons_url}")

        # Get file info from Commons
        file_info = get_commons_file_info(commons_url)
        if not file_info:
            print(f"  ✗ Could not get file info")
            continue

        file_url = file_info['file_url']
        if not file_url:
            print(f"  ✗ No file URL found")
            continue

        # Create safe filename from the Commons title
        filename = file_info['title'].replace('File:', '').replace(' ', '_')
        filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            filename += '.jpg'

        dest_path = os.path.join(advisor_dir, filename)

        # Download the file
        print(f"  Downloading: {file_url[:80]}...")
        if download_url(file_url, dest_path):
            size = os.path.getsize(dest_path)
            print(f"  ✓ Downloaded: {filename} ({size:,} bytes)")

            # Store metadata
            metadata.append({
                'filename': filename,
                'source_url': file_info['page_url'],
                'full_res_url': file_info['file_url'],
                'width': file_info['width'],
                'height': file_info['height'],
                'order': idx
            })
            downloaded += 1
        else:
            print(f"  ✗ Failed to download")

        time.sleep(0.5)  # Be nice to Wikimedia servers

    # Save metadata file
    if metadata:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"\n✓ Saved metadata for {len(metadata)} artworks to metadata.json")

    print(f"\n{'='*60}")
    print(f"✓ Successfully updated {downloaded}/{len(commons_urls)} artworks for {advisor_id}")
    print(f"{'='*60}")

    return downloaded


def main():
    """Main function."""
    if len(sys.argv) < 3:
        print("Usage: python3 update_advisor_artworks.py <advisor_id> <commons_url1> [commons_url2] ...")
        print("\nExample:")
        print("  python3 update_advisor_artworks.py gilpin \\")
        print("    https://commons.wikimedia.org/wiki/File:Mission_Church_Taos_LC-USZC4-3921.jpg \\")
        print("    https://commons.wikimedia.org/wiki/File:P1979-95-93_s.jpg")
        sys.exit(1)

    advisor_id = sys.argv[1]
    commons_urls = sys.argv[2:]

    # Verify advisor exists in database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM advisors WHERE id = ?", (advisor_id,))
    advisor = cursor.fetchone()
    conn.close()

    if not advisor:
        print(f"ERROR: Advisor '{advisor_id}' not found in database")
        sys.exit(1)

    print(f"Found advisor: {advisor[1]} ({advisor[0]})")

    # Update artworks
    update_advisor_artworks(advisor_id, commons_urls)


if __name__ == '__main__':
    main()
