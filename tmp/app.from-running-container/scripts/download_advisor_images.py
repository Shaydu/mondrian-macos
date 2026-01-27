#!/usr/bin/env python3
"""Download advisor headshots and missing work-example images from Wikipedia / Wikimedia Commons.

Saves headshots to `mondrian/advisor_images/<advisor_id>.jpg` and missing job files
to `source/<filename>` so the API can serve them at `/advisor_image/...` and `/uploads/...`.
"""
import os
import sqlite3
import time
from urllib.parse import urlparse, unquote
import requests


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Use the repository-root mondrian.db (authoritative DB)
DB_PATH = os.path.join(ROOT, 'mondrian.db')
SOURCE_DIR = os.path.join(ROOT, 'source')
ADVISOR_IMAGES_DIR = os.path.join(ROOT, 'mondrian', 'advisor_images')

os.makedirs(SOURCE_DIR, exist_ok=True)
os.makedirs(ADVISOR_IMAGES_DIR, exist_ok=True)

WIKIPEDIA_SUMMARY = 'https://en.wikipedia.org/api/rest_v1/page/summary/'
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'

# Use a requests session with a browser-like User-Agent to avoid 403s
SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
})


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def download_url(url, dest_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            resp = SESSION.get(url, stream=True, timeout=15)
            if resp.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                return True
            else:
                print(f"WARN: {url} returned {resp.status_code}")
                return False
        except Exception as e:
            print(f"WARN: download attempt {attempt+1} failed for {url}: {e}")
            time.sleep(1)
    return False


def wikipedia_thumbnail_for_title(title):
    try:
        url = WIKIPEDIA_SUMMARY + requests.utils.requote_uri(title)
        r = SESSION.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        # Prefer originalimage then thumbnail
        img = data.get('originalimage') or data.get('thumbnail')
        if isinstance(img, dict):
            return img.get('source')
        return None
    except Exception as e:
        print(f"WARN: wikipedia summary fetch failed for {title}: {e}")
        return None


def commons_search_image_url(name):
    """Search Commons for file pages matching name, return first file URL found."""
    try:
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': name,
            'srnamespace': 6,  # File namespace
            'format': 'json',
            'srlimit': 10
        }
        r = SESSION.get(COMMONS_API, params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        results = data.get('query', {}).get('search', [])
        # Debug: show how many file pages found
        if results:
            print(f"Commons search found {len(results)} file pages for '{name}'")
        for res in results:
            title = res.get('title')  # e.g., 'File:Ansel_Adams_1975.jpg'
            if title:
                # Get imageinfo for this title
                params2 = {'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url', 'format': 'json'}
                r2 = SESSION.get(COMMONS_API, params=params2, timeout=10)
                if r2.status_code != 200:
                    continue
                j2 = r2.json()
                pages = j2.get('query', {}).get('pages', {})
                for p in pages.values():
                    ii = p.get('imageinfo')
                    if ii and isinstance(ii, list):
                        return ii[0].get('url')
        return None
    except Exception as e:
        print(f"WARN: commons search failed for {name}: {e}")
        return None


def commons_file_url_from_page(file_page_url):
    """Extract actual file URL from a Commons File: page URL."""
    try:
        # Extract the file title from the URL
        # e.g., https://commons.wikimedia.org/wiki/File:Ansel_Adams.jpg -> File:Ansel_Adams.jpg
        if '/wiki/File:' not in file_page_url:
            return None
        file_title = unquote(file_page_url.split('/wiki/')[-1])

        # Query the MediaWiki API to get the actual file URL
        params = {'action': 'query', 'titles': file_title, 'prop': 'imageinfo', 'iiprop': 'url', 'format': 'json'}
        r = SESSION.get(COMMONS_API, params=params, timeout=10)
        if r.status_code != 200:
            return None
        j = r.json()
        pages = j.get('query', {}).get('pages', {})
        for p in pages.values():
            ii = p.get('imageinfo')
            if ii and isinstance(ii, list) and len(ii) > 0:
                return ii[0].get('url')
        return None
    except Exception as e:
        print(f"WARN: commons file URL extraction failed for {file_page_url}: {e}")
        return None


def commons_category_file_url(category_title):
    """Return first file URL from a Commons category (if any)."""
    try:
        params = {'action': 'query', 'list': 'categorymembers', 'cmtitle': category_title, 'cmnamespace': 6, 'cmlimit': 10, 'format': 'json'}
        r = SESSION.get(COMMONS_API, params=params, timeout=10)
        if r.status_code != 200:
            return None
        j = r.json()
        members = j.get('query', {}).get('categorymembers', [])
        for m in members:
            title = m.get('title')
            if title:
                params2 = {'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url', 'format': 'json'}
                r2 = SESSION.get(COMMONS_API, params=params2, timeout=10)
                if r2.status_code != 200:
                    continue
                j2 = r2.json()
                pages = j2.get('query', {}).get('pages', {})
                for p in pages.values():
                    ii = p.get('imageinfo')
                    if ii and isinstance(ii, list):
                        return ii[0].get('url')
        return None
    except Exception as e:
        print(f"WARN: commons category lookup failed for {category_title}: {e}")
        return None


def ensure_headshot(advisor):
    aid = advisor['id']
    name = advisor['name']
    wikipedia_url = advisor.get('wikipedia_url') or ''
    commons_url = advisor.get('commons_url') or ''
    dest = os.path.join(ADVISOR_IMAGES_DIR, f"{aid}.jpg")
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"OK: headshot exists for {aid}")
        return True

    candidates = []
    # If commons_url is a direct file link or a File: page, use it
    if commons_url:
        if '/wiki/File:' in commons_url:
            # Extract actual file URL from Commons File: page
            file_url = commons_file_url_from_page(commons_url)
            if file_url:
                candidates.append(file_url)
        elif commons_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            # Direct image URL
            candidates.append(commons_url)
        elif '/wiki/Category:' in commons_url:
            cat_title = commons_url.split('/wiki/')[-1]
            file_url = commons_category_file_url(unquote(cat_title))
            if file_url:
                candidates.append(file_url)

    # Try wikipedia thumbnail derived from name or stored link
    try:
        if wikipedia_url:
            parsed = urlparse(wikipedia_url)
            title = unquote(parsed.path.split('/wiki/')[-1])
        else:
            title = name.replace(' ', '_')
    except Exception:
        title = name.replace(' ', '_')
    thumb = wikipedia_thumbnail_for_title(title)
    if thumb:
        candidates.append(thumb)

    # Fallback: Commons search by name
    commons_candidate = commons_search_image_url(name)
    if commons_candidate:
        candidates.append(commons_candidate)

    for url in [c for c in candidates if c]:
        print(f"Trying headshot URL for {aid}: {url}")
        if download_url(url, dest):
            print(f"Downloaded headshot for {aid} -> {dest}")
            return True

    print(f"FAILED: Could not obtain headshot for {aid}")
    return False


def ensure_job_file(filename, advisor_name):
    dest = os.path.join(SOURCE_DIR, filename)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return True
    # Attempt to find an image on Commons by advisor name
    url = commons_search_image_url(advisor_name)
    if not url:
        # fallback to wikipedia thumbnail for advisor page
        title = advisor_name.replace(' ', '_')
        url = wikipedia_thumbnail_for_title(title)
    if not url:
        print(f"No candidate found to satisfy missing job file {filename} for {advisor_name}")
        return False
    print(f"Downloading sample for {advisor_name}: {url} -> {filename}")
    return download_url(url, dest)


def main():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, wikipedia_url, commons_url FROM advisors")
    advisors = cursor.fetchall()

    for adv in advisors:
        advisor = dict(adv)
        print(f"\n=== Processing advisor {advisor['id']} ({advisor['name']}) ===")
        ensure_headshot(advisor)

        # Get up to 5 completed job filenames for this advisor
        cursor2 = conn.cursor()
        cursor2.execute("""
            SELECT filename FROM jobs
            WHERE status='done'
            AND (advisor = ? OR advisor LIKE ? || ',%' OR advisor LIKE '%,' || ? OR advisor LIKE '%,' || ? || ',%')
            ORDER BY created_at DESC
            LIMIT 5
        """, (advisor['id'], advisor['id'], advisor['id'], advisor['id']))
        rows = cursor2.fetchall()
        if not rows:
            print(f"No completed jobs found for {advisor['id']}, skipping sample downloads.")
            continue

        for r in rows:
            filename = r['filename']
            if ensure_job_file(filename, advisor['name']):
                print(f"OK: ensured sample file {filename}")
            else:
                print(f"WARN: could not ensure sample file {filename}")

    conn.close()


if __name__ == '__main__':
    main()
