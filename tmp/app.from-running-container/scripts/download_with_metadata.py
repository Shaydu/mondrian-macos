#!/usr/bin/env python3
"""
Download Advisor Artworks with Metadata from Wikimedia Commons

Fetches:
- High-resolution images
- Title, artist, date
- Description
- License information
- Automatically generates metadata.yaml

Usage:
    python3 scripts/download_with_metadata.py --advisor ansel
    python3 scripts/download_with_metadata.py --advisor all
"""

import os
import sys
import time
import yaml
import argparse
from pathlib import Path
from urllib.parse import urlparse, unquote
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'

# Use a requests session with browser-like User-Agent
SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
})

# Artworks to download (from original script)
ADVISOR_ARTWORKS = {
    'ansel': [
        # Iconic landscapes - Zone System mastery
        'File:Adams The Tetons and the Snake River.jpg',
        'File:Clearing Winter Storm, Yosemite National Park, CA 1944.jpg',
        'File:Half Dome, Merced River, Winter - Ansel Adams.jpg',
        
        # National Archives collection - diverse techniques
        'File:Ansel Adams - National Archives 79-AA-Q04.jpg',
        'File:Ansel Adams - National Archives 79-AAB-02.jpg',
        'File:Ansel Adams - National Archives 79-AA-G01.jpg',
        'File:Ansel Adams - National Archives 79-AA-G06.jpg',
        
        # High contrast and dramatic lighting
        'File:Ansel Adams, Moon and Half Dome.jpg',
        'File:Tenaya Creek, Dogwood, Rain - Ansel Adams.jpg',
        
        # Detailed texture work
        'File:Ansel Adams, Pine Cone and Eucalyptus Leaves, San Francisco, California.jpg',
        
        # f/64 Group examples - deep DOF
        'File:Ansel Adams - In Rocky Mountain National Park.jpg',
    ],
    'watkins': [
        'File:Carleton Watkins - Cape Horn, Columbia River, Oregon - Google Art Project.jpg',
        'File:Carleton Watkins - El Capitan, Yosemite - Google Art Project.jpg',
    ],
    'weston': [
        'File:Edward Weston - Pepper No. 30, 1930.jpg',
        'File:Edward Weston, Shells, 1927.jpg',
    ],
}


def get_file_metadata(file_title):
    """
    Fetch metadata for a Wikimedia Commons file.
    
    Returns dict with:
    - title: Display title
    - artist: Creator/photographer
    - date: Date created/taken
    - description: What the image shows
    - url: Direct image URL
    - license: License information
    """
    try:
        # Query for image info and metadata
        params = {
            'action': 'query',
            'titles': file_title,
            'prop': 'imageinfo|revisions',
            'iiprop': 'url|extmetadata|size',
            'iiurlwidth': 2000,  # Get high-res version
            'rvprop': 'content',
            'rvslots': 'main',
            'format': 'json'
        }
        
        response = SESSION.get(COMMONS_API, params=params, timeout=30)
        data = response.json()
        
        pages = data.get('query', {}).get('pages', {})
        if not pages:
            return None
        
        page = list(pages.values())[0]
        
        if 'missing' in page:
            print(f"      [!] File not found on Commons: {file_title}")
            return None
        
        imageinfo = page.get('imageinfo', [{}])[0]
        extmetadata = imageinfo.get('extmetadata', {})
        
        # Extract metadata
        metadata = {
            'filename': None,  # Will be set by caller
            'title': extmetadata.get('ObjectName', {}).get('value', ''),
            'artist': extmetadata.get('Artist', {}).get('value', ''),
            'date_taken': extmetadata.get('DateTimeOriginal', {}).get('value', '') or 
                         extmetadata.get('DateTime', {}).get('value', ''),
            'description': extmetadata.get('ImageDescription', {}).get('value', ''),
            'location': extmetadata.get('GPSLatitude', {}).get('value', ''),  # If available
            'license': extmetadata.get('LicenseShortName', {}).get('value', ''),
            'credit': extmetadata.get('Credit', {}).get('value', ''),
            'url': imageinfo.get('url', ''),
            'width': imageinfo.get('width', 0),
            'height': imageinfo.get('height', 0),
            'commons_url': f"https://commons.wikimedia.org/wiki/{file_title}"
        }
        
        # Clean HTML from description
        if metadata['description']:
            import re
            # Remove HTML tags
            metadata['description'] = re.sub(r'<[^>]+>', '', metadata['description'])
            # Decode HTML entities
            import html
            metadata['description'] = html.unescape(metadata['description'])
            # Truncate if too long
            if len(metadata['description']) > 500:
                metadata['description'] = metadata['description'][:497] + '...'
        
        # Clean artist field
        if metadata['artist']:
            metadata['artist'] = re.sub(r'<[^>]+>', '', metadata['artist'])
            metadata['artist'] = html.unescape(metadata['artist'])
        
        return metadata
        
    except Exception as e:
        print(f"      [!] Error fetching metadata: {e}")
        return None


def download_file(url, output_path):
    """Download file from URL to output_path."""
    try:
        response = SESSION.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"      [!] Download failed: {e}")
        return False


def sanitize_filename(filename):
    """Convert Wikimedia filename to safe local filename."""
    # Remove 'File:' prefix
    filename = filename.replace('File:', '')
    # Replace spaces and special chars
    filename = filename.replace(' ', '_')
    # Keep extension
    return filename


def download_advisor_artworks(advisor_id, output_dir):
    """
    Download artworks for an advisor with metadata.
    
    Returns list of metadata dicts for each downloaded image.
    """
    if advisor_id not in ADVISOR_ARTWORKS:
        print(f"[!] Unknown advisor: {advisor_id}")
        return []
    
    files = ADVISOR_ARTWORKS[advisor_id]
    os.makedirs(output_dir, exist_ok=True)
    
    metadata_list = []
    
    print(f"\nDownloading {len(files)} images for {advisor_id}...")
    
    for i, file_title in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {file_title}")
        
        # Get metadata
        print(f"      [→] Fetching metadata...")
        metadata = get_file_metadata(file_title)
        
        if not metadata:
            print(f"      [✗] Skipping (metadata failed)")
            continue
        
        # Determine output filename
        local_filename = sanitize_filename(file_title)
        output_path = os.path.join(output_dir, local_filename)
        metadata['filename'] = local_filename
        
        # Download image
        if os.path.exists(output_path):
            print(f"      [✓] Already exists: {local_filename}")
        else:
            print(f"      [→] Downloading image...")
            if download_file(metadata['url'], output_path):
                print(f"      [✓] Downloaded: {local_filename}")
            else:
                print(f"      [✗] Download failed")
                continue
        
        # Add to metadata list
        metadata_list.append(metadata)
        
        # Be nice to Wikimedia servers
        time.sleep(1)
    
    return metadata_list


def save_metadata_yaml(metadata_list, output_file):
    """Save metadata to YAML file."""
    # Prepare YAML structure
    yaml_data = {
        'images': []
    }
    
    for meta in metadata_list:
        # Create simplified metadata for YAML
        img_meta = {
            'filename': meta['filename'],
            'title': meta['title'],
            'date_taken': meta['date_taken'],
            'description': meta['description'],
            'location': meta.get('location', ''),
            'significance': '',  # To be filled manually or via AI
            'techniques': [],  # To be filled manually or via AI
            'source': {
                'commons_url': meta['commons_url'],
                'artist': meta['artist'],
                'license': meta['license'],
                'credit': meta['credit']
            }
        }
        yaml_data['images'].append(img_meta)
    
    # Save YAML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Advisor Image Metadata\n")
        f.write("# Downloaded from Wikimedia Commons with automatic metadata extraction\n")
        f.write(f"# Total images: {len(metadata_list)}\n\n")
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"\n[✓] Metadata saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Download advisor artworks with metadata")
    parser.add_argument('--advisor', type=str, required=True, 
                       help='Advisor ID (ansel, watkins, weston) or "all"')
    parser.add_argument('--output-dir', type=str, 
                       help='Override output directory')
    args = parser.parse_args()
    
    print("=" * 70)
    print("Download Advisor Artworks with Metadata")
    print("=" * 70)
    
    advisors_to_download = []
    if args.advisor == 'all':
        advisors_to_download = list(ADVISOR_ARTWORKS.keys())
    elif args.advisor in ADVISOR_ARTWORKS:
        advisors_to_download = [args.advisor]
    else:
        print(f"[✗] Unknown advisor: {args.advisor}")
        print(f"Available: {', '.join(ADVISOR_ARTWORKS.keys())}")
        sys.exit(1)
    
    for advisor_id in advisors_to_download:
        print(f"\n{'=' * 70}")
        print(f"Advisor: {advisor_id.upper()}")
        print(f"{'=' * 70}")
        
        # Determine output directory
        if args.output_dir:
            output_dir = args.output_dir
        else:
            output_dir = os.path.join(ROOT, 'mondrian', 'source', 'advisor', 'photographer', advisor_id)
        
        print(f"Output directory: {output_dir}")
        
        # Download images and get metadata
        metadata_list = download_advisor_artworks(advisor_id, output_dir)
        
        if not metadata_list:
            print(f"\n[✗] No images downloaded for {advisor_id}")
            continue
        
        # Save metadata YAML
        metadata_file = os.path.join(output_dir, 'metadata.yaml')
        save_metadata_yaml(metadata_list, metadata_file)
        
        print(f"\n[✓] Downloaded {len(metadata_list)} images for {advisor_id}")
        print(f"[✓] Metadata saved to: {metadata_file}")
        print(f"\nNext steps:")
        print(f"  1. Review images and metadata:")
        print(f"     python3 scripts/preview_metadata.py --advisor {advisor_id}")
        print(f"  2. Index images:")
        print(f"     python3 tools/rag/index_with_metadata.py --advisor {advisor_id} --metadata-file {metadata_file}")
    
    print(f"\n{'=' * 70}")
    print("Download Complete!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()

