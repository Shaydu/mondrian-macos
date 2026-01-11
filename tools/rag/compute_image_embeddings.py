#!/usr/bin/env python3
"""
General-purpose image embedding script for advisor images.
Usage:
    python compute_image_embeddings.py --advisor_dir /path/to/advisor/images

This script computes embeddings for all images in the given directory (recursively),
and saves each embedding as a .npy file next to the image.

You can reuse this for any advisor type (photographer, architect, painter, etc.).
"""
import os
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
from tqdm import tqdm

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--advisor_dir", type=str, required=True, help="Path to advisor image directory")
    args = parser.parse_args()

    img_exts = {".jpg", ".jpeg", ".png"}
    advisor_dir = Path(args.advisor_dir)
    image_files = [p for p in advisor_dir.rglob("*") if p.suffix.lower() in img_exts]

    print(f"Found {len(image_files)} images in {advisor_dir}")
    for img_path in tqdm(image_files):
        emb_path = img_path.with_suffix(img_path.suffix + ".npy")
        if emb_path.exists():
            continue  # Skip if already computed
        try:
            embedding = compute_embedding(img_path)
            np.save(emb_path, embedding)
        except Exception as e:
            print(f"Failed to process {img_path}: {e}")

if __name__ == "__main__":
    main()
