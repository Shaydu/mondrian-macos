#!/usr/bin/env python3
"""
Compute and store image embeddings for advisor images in mondrian.db (image_captions table).
Reusable for any advisor type (photographer, architect, painter, etc).

Usage:
    python compute_image_embeddings_to_db.py --advisor_dir /path/to/advisor/images --advisor_id ansel
"""

import os
import argparse
from pathlib import Path
import numpy as np
import sqlite3
import json
from PIL import Image, ImageStat, ImageEnhance
from tqdm import tqdm
import uuid
import cv2

# Example: using OpenAI CLIP (replace with mlx-vlm or your preferred model)
try:
    import torch
    import clip
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)
    def compute_embedding(image_path):
        image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            embedding = model.encode_image(image)
            embedding = embedding.cpu().numpy().squeeze()
        return embedding
except ImportError:
    # Fallback: dummy embedding (for testing only)
    def compute_embedding(image_path):
        return np.zeros(512)


# Always use the workspace root mondrian.db
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
DB_PATH = os.path.join(WORKSPACE_ROOT, 'mondrian.db')
print(f"[DEBUG] Using database: {DB_PATH}")

CREATE_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS image_captions (
    id TEXT PRIMARY KEY,
    job_id TEXT,
    image_path TEXT NOT NULL,
    caption TEXT NOT NULL,
    caption_type TEXT DEFAULT 'detailed',
    embedding BLOB,
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
'''

def ensure_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()

def insert_embedding(job_id, image_path, embedding, metadata):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO image_captions
        (id, job_id, image_path, caption, caption_type, embedding, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        job_id,
        str(image_path),
        '',  # No caption for now
        'embedding',
        embedding.tobytes(),
        json.dumps(metadata)
    ))
    conn.commit()
    conn.close()

# --- Creative attribute extraction ---
def extract_creative_attributes(img_path):
    attributes = {}
    try:
        # Exposure (mean brightness)
        with Image.open(img_path) as im:
            grayscale = im.convert('L')
            stat = ImageStat.Stat(grayscale)
            attributes['exposure'] = float(stat.mean[0])
            # Contrast (stddev of grayscale)
            attributes['contrast'] = float(stat.stddev[0])
            # Brightness (mean of RGB)
            if im.mode in ('RGB', 'RGBA'):
                stat_rgb = ImageStat.Stat(im)
                attributes['brightness'] = float(np.mean(stat_rgb.mean[:3]))
            else:
                attributes['brightness'] = float(stat.mean[0])
            # Sharpness (variance of Laplacian)
            img_cv = cv2.imread(str(img_path))
            if img_cv is not None:
                gray_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                attributes['sharpness'] = float(cv2.Laplacian(gray_cv, cv2.CV_64F).var())
                # Colorfulness (Hasler & Süsstrunk metric)
                (B, G, R) = cv2.split(img_cv.astype("float"))
                rg = np.abs(R - G)
                yb = np.abs(0.5 * (R + G) - B)
                std_rg, std_yb = np.std(rg), np.std(yb)
                mean_rg, mean_yb = np.mean(rg), np.mean(yb)
                colorfulness = np.sqrt(std_rg ** 2 + std_yb ** 2) + 0.3 * np.sqrt(mean_rg ** 2 + mean_yb ** 2)
                attributes['colorfulness'] = float(colorfulness)
    except Exception as e:
        attributes['attribute_error'] = str(e)
    return attributes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--advisor_dir", type=str, required=True, help="Path to advisor image directory")
    parser.add_argument("--advisor_id", type=str, required=True, help="Advisor ID (e.g., ansel)")
    args = parser.parse_args()

    img_exts = {".jpg", ".jpeg", ".png"}
    advisor_dir = Path(args.advisor_dir)
    image_files = [p for p in advisor_dir.rglob("*") if p.suffix.lower() in img_exts]

    ensure_table()
    print(f"Found {len(image_files)} images in {advisor_dir}")
    for img_path in tqdm(image_files):
        print(f"[DEBUG] Processing image: {img_path}")
        try:
            embedding = compute_embedding(img_path)
            metadata = {}
            try:
                with Image.open(img_path) as im:
                    metadata = {"width": im.width, "height": im.height, "mode": im.mode}
            except Exception:
                pass
            # Add creative attributes
            creative_attrs = extract_creative_attributes(img_path)
            metadata.update(creative_attrs)
            job_id = f"{args.advisor_id}-{img_path.stem}"
            print(f"[DEBUG] Inserting job_id: {job_id} to DB: {DB_PATH}")
            insert_embedding(job_id, img_path, embedding, metadata)
        except Exception as e:
            print(f"Failed to process {img_path}: {e}")

if __name__ == "__main__":
    main()
