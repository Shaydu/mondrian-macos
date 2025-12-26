#!/usr/bin/env python3
"""Download representative artworks from multiple sources including Met Museum API."""
import os
import sqlite3
import time
import requests
from urllib.parse import quote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT, 'mondrian.db')
ADVISOR_ARTWORKS_DIR = os.path.join(ROOT, 'mondrian', 'advisor_artworks')

os.makedirs(ADVISOR_ARTWORKS_DIR, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
})

# Metropolitan Museum of Art API
MET_SEARCH_API = "https://collectionapi.metmuseum.org/public/collection/v1/search"
MET_OBJECT_API = "https://collectionapi.metmuseum.org/public/collection/v1/objects"

# Art Institute of Chicago API
AIC_SEARCH_API = "https://api.artic.edu/api/v1/artworks/search"
AIC_IMAGE_URL = "https://www.artic.edu/iiif/2"

# Search queries for each advisor
ADVISOR_SEARCHES = {
    'ansel': {
        'met': 'Ansel Adams',
        'aic': 'Ansel Adams',
        'loc': 'ansel adams photographs'
    },
    'watkins': {
        'met': 'Carleton Watkins',
        'aic': 'Carleton Watkins',
        'loc': 'carleton watkins yosemite'
    },
    'weston': {
        'met': 'Edward Weston',
        'aic': 'Edward Weston',
        'loc': 'edward weston photographs'
    },
    'cunningham': {
        'met': 'Imogen Cunningham',
        'aic': 'Imogen Cunningham',
        'loc': 'imogen cunningham'
    },
    'gilpin': {
        'met': 'Laura Gilpin',
        'aic': 'Laura Gilpin',
        'loc': 'laura gilpin'
    },
    'mondrian': {
        'met': 'Piet Mondrian',
        'aic': 'Piet Mondrian',
    },
    'okeefe': {
        'met': 'Georgia O\'Keeffe',
        'aic': 'Georgia O\'Keeffe',
    },
    'vangogh': {
        'met': 'Vincent van Gogh',
        'aic': 'Vincent van Gogh',
    },
    'gehry': {
        'met': 'Frank Gehry',
        'aic': 'Frank Gehry',
    }
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
                return False
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"    Failed: {e}")
            time.sleep(1)
    return False


def search_met_museum(artist_name, limit=6):
    """Search Met Museum for artworks by artist."""
    print(f"  Searching Met Museum for: {artist_name}")
    artworks = []

    try:
        # Search for objects
        params = {'q': artist_name, 'hasImages': 'true'}
        resp = SESSION.get(MET_SEARCH_API, params=params, timeout=15)
        if resp.status_code != 200:
            return artworks

        data = resp.json()
        object_ids = data.get('objectIDs', [])[:limit * 2]  # Get extra in case some fail

        print(f"    Found {len(object_ids)} objects, checking images...")

        for obj_id in object_ids[:limit]:
            try:
                obj_resp = SESSION.get(f"{MET_OBJECT_API}/{obj_id}", timeout=10)
                if obj_resp.status_code == 200:
                    obj_data = obj_resp.json()
                    image_url = obj_data.get('primaryImage')
                    if image_url and obj_data.get('isPublicDomain'):
                        title = obj_data.get('title', f'met_{obj_id}')
                        artworks.append({
                            'url': image_url,
                            'title': title,
                            'source': 'met'
                        })
                        if len(artworks) >= limit:
                            break
                time.sleep(0.3)  # Be nice to the API
            except:
                continue

    except Exception as e:
        print(f"    Met search error: {e}")

    print(f"    Found {len(artworks)} Met artworks")
    return artworks


def search_aic(artist_name, limit=6):
    """Search Art Institute of Chicago."""
    print(f"  Searching Art Institute of Chicago for: {artist_name}")
    artworks = []

    try:
        params = {
            'q': artist_name,
            'query': {'term': {'is_public_domain': True}},
            'fields': 'id,title,image_id,artist_title',
            'limit': limit
        }
        resp = SESSION.get(AIC_SEARCH_API, params=params, timeout=15)
        if resp.status_code != 200:
            return artworks

        data = resp.json()
        for item in data.get('data', []):
            image_id = item.get('image_id')
            if image_id:
                # Construct IIIF image URL
                image_url = f"{AIC_IMAGE_URL}/{image_id}/full/843,/0/default.jpg"
                artworks.append({
                    'url': image_url,
                    'title': item.get('title', image_id),
                    'source': 'aic'
                })

    except Exception as e:
        print(f"    AIC search error: {e}")

    print(f"    Found {len(artworks)} AIC artworks")
    return artworks


def download_advisor_artworks(advisor_id, advisor_name):
    """Download artworks for a specific advisor from multiple sources."""
    print(f"\n{'='*60}")
    print(f"Processing: {advisor_name} ({advisor_id})")
    print(f"{'='*60}")

    advisor_dir = os.path.join(ADVISOR_ARTWORKS_DIR, advisor_id)
    os.makedirs(advisor_dir, exist_ok=True)

    # Check how many we already have
    existing = [f for f in os.listdir(advisor_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
    if len(existing) >= 3:
        print(f"  Already have {len(existing)} artworks, skipping")
        return len(existing)

    # Get search queries
    searches = ADVISOR_SEARCHES.get(advisor_id, {})
    if not searches:
        print(f"  No search queries defined for {advisor_id}")
        return 0

    # Collect artworks from various sources
    all_artworks = []

    # Try Met Museum
    if 'met' in searches:
        met_artworks = search_met_museum(searches['met'], limit=6)
        all_artworks.extend(met_artworks)

    # Try Art Institute of Chicago
    if 'aic' in searches and len(all_artworks) < 6:
        aic_artworks = search_aic(searches['aic'], limit=6)
        all_artworks.extend(aic_artworks)

    if not all_artworks:
        print(f"  No artworks found from any source")
        return 0

    # Download the artworks
    print(f"\n  Downloading {len(all_artworks)} artworks:")
    downloaded = len(existing)

    for idx, artwork in enumerate(all_artworks[:6], 1):
        # Create safe filename
        safe_title = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in artwork['title'])
        safe_title = safe_title[:50]  # Limit length
        filename = f"{artwork['source']}_{safe_title}.jpg"
        dest_path = os.path.join(advisor_dir, filename)

        # Skip if exists
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
            print(f"  [{idx}] ✓ Already exists: {filename}")
            continue

        print(f"  [{idx}] Downloading: {artwork['title'][:50]}...")
        if download_url(artwork['url'], dest_path):
            size = os.path.getsize(dest_path)
            if size > 10000:  # Valid image
                print(f"      ✓ Success ({size:,} bytes)")
                downloaded += 1
            else:
                os.remove(dest_path)
                print(f"      ✗ File too small, removed")
        else:
            print(f"      ✗ Download failed")

        time.sleep(0.5)  # Be nice to APIs

    print(f"\n  Total: {downloaded} artworks for {advisor_name}")
    return downloaded


def main():
    """Download artworks for all advisors."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM advisors ORDER BY id")
    advisors = cursor.fetchall()
    conn.close()

    print(f"Starting artwork download for {len(advisors)} advisors")
    print(f"Output directory: {ADVISOR_ARTWORKS_DIR}\n")

    total = 0
    for advisor in advisors:
        count = download_advisor_artworks(advisor['id'], advisor['name'])
        total += count

    print("\n" + "="*60)
    print(f"✓ Downloaded {total} total artworks!")
    print("="*60)


if __name__ == '__main__':
    main()
