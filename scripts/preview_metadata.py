#!/usr/bin/env python3
"""
Preview Advisor Images and Metadata

Generates an HTML page showing all images with their metadata
for review before indexing/analysis.

Usage:
    python3 scripts/preview_metadata.py --advisor ansel
    python3 scripts/preview_metadata.py --metadata-file path/to/metadata.yaml
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def load_metadata(metadata_file):
    """Load metadata from YAML file."""
    with open(metadata_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('images', [])


def generate_html_preview(images, metadata_file, output_file):
    """Generate HTML preview page."""
    
    image_dir = Path(metadata_file).parent
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Metadata Preview</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
            line-height: 1.6;
            padding: 20px;
        }}
        
        .header {{
            max-width: 1200px;
            margin: 0 auto 40px;
            padding: 30px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
            color: #1d1d1f;
        }}
        
        .header .meta {{
            color: #86868b;
            font-size: 14px;
        }}
        
        .stats {{
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }}
        
        .stat {{
            padding: 15px 20px;
            background: #f5f5f7;
            border-radius: 8px;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: 600;
            color: #0071e3;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #86868b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .image-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .image-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }}
        
        .image-container {{
            position: relative;
            width: 100%;
            height: 400px;
            background: #000;
            overflow: hidden;
        }}
        
        .image-container img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}
        
        .image-number {{
            position: absolute;
            top: 15px;
            left: 15px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 14px;
        }}
        
        .content {{
            padding: 25px;
        }}
        
        .title {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #1d1d1f;
        }}
        
        .filename {{
            font-size: 12px;
            color: #86868b;
            font-family: "SF Mono", Monaco, monospace;
            margin-bottom: 15px;
        }}
        
        .metadata-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
            padding: 20px;
            background: #f5f5f7;
            border-radius: 8px;
        }}
        
        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .metadata-label {{
            font-size: 11px;
            color: #86868b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        
        .metadata-value {{
            font-size: 14px;
            color: #1d1d1f;
            font-weight: 500;
        }}
        
        .description {{
            margin: 20px 0;
            padding: 20px;
            background: #f5f5f7;
            border-radius: 8px;
            border-left: 4px solid #0071e3;
        }}
        
        .description-label {{
            font-size: 11px;
            color: #86868b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        
        .description-text {{
            font-size: 15px;
            line-height: 1.6;
            color: #1d1d1f;
        }}
        
        .techniques {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 15px;
        }}
        
        .technique-tag {{
            padding: 6px 12px;
            background: #0071e3;
            color: white;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
        }}
        
        .source-info {{
            margin-top: 20px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 8px;
            font-size: 13px;
            color: #86868b;
        }}
        
        .source-info a {{
            color: #0071e3;
            text-decoration: none;
        }}
        
        .source-info a:hover {{
            text-decoration: underline;
        }}
        
        .warning {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
        }}
        
        .warning strong {{
            color: #856404;
        }}
        
        .actions {{
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }}
        
        .button {{
            padding: 12px 24px;
            background: #0071e3;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }}
        
        .button:hover {{
            background: #0077ed;
        }}
        
        .button-secondary {{
            background: #f5f5f7;
            color: #1d1d1f;
        }}
        
        .button-secondary:hover {{
            background: #e8e8ed;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📸 Image Metadata Preview</h1>
        <div class="meta">
            Metadata file: <code>{metadata_file}</code><br>
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(images)}</div>
                <div class="stat-label">Total Images</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sum(1 for img in images if img.get('title'))}</div>
                <div class="stat-label">With Titles</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sum(1 for img in images if img.get('description'))}</div>
                <div class="stat-label">With Descriptions</div>
            </div>
        </div>
        
        <div class="warning">
            <strong>⚠️ Review Before Indexing:</strong> Check that all metadata is accurate. 
            You can edit the metadata.yaml file to add significance, techniques, or correct any errors.
        </div>
        
        <div class="actions">
            <a href="file://{metadata_file}" class="button">Edit Metadata YAML</a>
            <a href="#" class="button button-secondary" onclick="window.print(); return false;">Print/Save PDF</a>
        </div>
    </div>
    
    <div class="container">
"""
    
    # Add each image
    for i, img in enumerate(images, 1):
        filename = img.get('filename', 'unknown.jpg')
        image_path = image_dir / filename
        
        # Check if image exists
        if not image_path.exists():
            image_display = f'<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#fff;font-size:18px;">Image not found: {filename}</div>'
        else:
            # Use file:// URL for local preview
            image_url = f"file://{image_path.absolute()}"
            image_display = f'<img src="{image_url}" alt="{img.get("title", filename)}">'
        
        title = img.get('title', 'Untitled')
        date = img.get('date_taken', 'Unknown date')
        location = img.get('location', '')
        description = img.get('description', 'No description available')
        significance = img.get('significance', '')
        techniques = img.get('techniques', [])
        
        # Source info
        source = img.get('source', {})
        artist = source.get('artist', img.get('artist', 'Unknown'))
        license_info = source.get('license', '')
        commons_url = source.get('commons_url', '')
        
        html += f"""
        <div class="image-card">
            <div class="image-container">
                <div class="image-number">#{i}</div>
                {image_display}
            </div>
            
            <div class="content">
                <div class="title">{title or 'Untitled'}</div>
                <div class="filename">{filename}</div>
                
                <div class="metadata-grid">
                    <div class="metadata-item">
                        <div class="metadata-label">Artist</div>
                        <div class="metadata-value">{artist}</div>
                    </div>
                    <div class="metadata-item">
                        <div class="metadata-label">Date</div>
                        <div class="metadata-value">{date}</div>
                    </div>
"""
        
        if location:
            html += f"""
                    <div class="metadata-item">
                        <div class="metadata-label">Location</div>
                        <div class="metadata-value">{location}</div>
                    </div>
"""
        
        if license_info:
            html += f"""
                    <div class="metadata-item">
                        <div class="metadata-label">License</div>
                        <div class="metadata-value">{license_info}</div>
                    </div>
"""
        
        html += """
                </div>
"""
        
        if description:
            html += f"""
                <div class="description">
                    <div class="description-label">Description</div>
                    <div class="description-text">{description}</div>
                </div>
"""
        
        if significance:
            html += f"""
                <div class="description" style="border-left-color: #34c759;">
                    <div class="description-label">Historical Significance</div>
                    <div class="description-text">{significance}</div>
                </div>
"""
        
        if techniques:
            html += """
                <div class="metadata-label" style="margin-top: 15px;">Techniques</div>
                <div class="techniques">
"""
            for tech in techniques:
                html += f"""
                    <span class="technique-tag">{tech}</span>
"""
            html += """
                </div>
"""
        
        if commons_url:
            html += f"""
                <div class="source-info">
                    📚 Source: <a href="{commons_url}" target="_blank">View on Wikimedia Commons</a>
                </div>
"""
        
        html += """
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    # Save HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Preview advisor images and metadata")
    parser.add_argument('--advisor', type=str, help='Advisor ID (e.g., ansel)')
    parser.add_argument('--metadata-file', type=str, help='Path to metadata.yaml')
    args = parser.parse_args()
    
    # Determine metadata file
    if args.metadata_file:
        metadata_file = args.metadata_file
    elif args.advisor:
        metadata_file = os.path.join(
            ROOT, 'mondrian', 'source', 'advisor', 'photographer', args.advisor, 'metadata.yaml'
        )
    else:
        print("[✗] Specify either --advisor or --metadata-file")
        sys.exit(1)
    
    if not os.path.exists(metadata_file):
        print(f"[✗] Metadata file not found: {metadata_file}")
        sys.exit(1)
    
    print("=" * 70)
    print("Generating Image Preview")
    print("=" * 70)
    print(f"Metadata file: {metadata_file}")
    
    # Load metadata
    images = load_metadata(metadata_file)
    print(f"[✓] Loaded {len(images)} images")
    
    # Generate HTML preview
    output_file = os.path.join(ROOT, 'preview', 'metadata_preview.html')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"[→] Generating HTML preview...")
    html_file = generate_html_preview(images, metadata_file, output_file)
    
    print(f"[✓] Preview generated: {html_file}")
    print()
    print("Next steps:")
    print(f"  1. Open in browser: open {html_file}")
    print(f"  2. Review images and metadata")
    print(f"  3. Edit if needed: {metadata_file}")
    print(f"  4. Index when ready:")
    print(f"     python3 tools/rag/index_with_metadata.py --advisor {args.advisor or 'ADVISOR'} --metadata-file {metadata_file}")
    
    # Try to open in browser
    try:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(html_file)}")
        print()
        print("[✓] Opened in browser")
    except:
        pass


if __name__ == "__main__":
    main()

