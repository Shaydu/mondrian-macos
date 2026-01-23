#!/usr/bin/env python3
"""
Real-time monitoring dashboard for CADB image processing
Shows each image being processed with its analysis results
"""

import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime
import threading

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def load_current_data(data_file):
    """Load current analysis data"""
    try:
        with open(data_file) as f:
            return json.load(f)
    except:
        return []

def format_dimension(dim):
    """Format dimension for display"""
    name = dim.get('name', '?')
    score = dim.get('score', '?')
    comment = dim.get('comment', '')[:40]

    # Color code based on score
    if isinstance(score, (int, float)):
        if score >= 8:
            color = '\033[92m'  # Green
        elif score >= 6:
            color = '\033[93m'  # Yellow
        else:
            color = '\033[91m'  # Red
        reset = '\033[0m'
    else:
        color = reset = ''

    return f"  {color}[{score:>2}]{reset} {name:20} {comment}"

def get_image_filename(image_path):
    """Extract filename from path"""
    return Path(image_path).name

def display_dashboard(data_file, selected_images_file):
    """Display real-time processing dashboard"""

    # Load selected images for category mapping
    selected_images = {}
    if Path(selected_images_file).exists():
        with open(selected_images_file) as f:
            for img in json.load(f):
                selected_images[img['image_id']] = img

    last_count = 0

    while True:
        clear_screen()

        # Load current data
        data = load_current_data(data_file)
        current_count = len(data)

        print(f"\n{'='*80}")
        print(f"CADB IMAGE PROCESSING MONITOR")
        print(f"{'='*80}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Processed: {current_count}/200 images ({current_count*100//200}%)")

        # Progress bar
        filled = (current_count * 50) // 200
        bar = '█' * filled + '░' * (50 - filled)
        print(f"[{bar}] {current_count}/200")
        print(f"{'='*80}\n")

        if data:
            # Show last 5 processed images
            print(f"RECENT PROCESSING:")
            print(f"{'-'*80}")

            for entry in data[-5:]:
                image_id = entry.get('image_id', '?')
                image_path = entry.get('image_path', '')
                filename = get_image_filename(image_path)

                # Get metadata
                meta = selected_images.get(image_id, {})
                cadb_score = meta.get('cadb_score', '?')

                # Get analysis
                messages = entry.get('messages', [])
                analysis = {}
                for msg in messages:
                    if msg.get('role') == 'assistant':
                        try:
                            analysis = json.loads(msg.get('content', '{}'))
                        except:
                            pass

                dimensions = analysis.get('dimensions', [])
                overall = analysis.get('overall_score', '?')

                print(f"\n{image_id:6} | {filename:20} | CADB: {cadb_score:>3} | Overall: {overall}")

                for dim in dimensions:
                    print(format_dimension(dim))

            print(f"\n{'-'*80}")
            print(f"\nSUMMARY:")
            print(f"  Total analyzed: {current_count}")
            print(f"  Remaining: {200 - current_count}")

            if current_count > last_count:
                print(f"  ✓ +{current_count - last_count} new image(s) processed")
                last_count = current_count

        print(f"\n{'-'*80}")
        print(f"Updating every 5 seconds... (Press Ctrl+C to stop)")
        print(f"{'='*80}\n")

        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Monitor CADB processing in real-time")
    parser.add_argument(
        "--data",
        type=Path,
        default="training/cadb_analyzed/cadb_training_data.json",
        help="Path to analysis data file"
    )
    parser.add_argument(
        "--selected-images",
        type=Path,
        default="training/cadb_selected_images.json",
        help="Path to selected images file"
    )

    args = parser.parse_args()

    if not args.data.exists():
        print(f"Error: Data file not found: {args.data}")
        sys.exit(1)

    display_dashboard(args.data, args.selected_images)

if __name__ == "__main__":
    main()
