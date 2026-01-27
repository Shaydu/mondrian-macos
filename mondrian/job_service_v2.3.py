#!/usr/bin/env python3
"""
Job Service for Mondrian on Linux
Manages background processing of analysis jobs with AI Advisor integration
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
import sqlite3
from typing import Optional, Dict, Any
import uuid
import threading
import time
import requests

from flask import Flask, request, jsonify, Response, send_file
from flask_cors import CORS
from PIL import Image
from io import BytesIO

# Configure logging
from mondrian.logging_config import setup_service_logging
logger = setup_service_logging('job_service_v2.3')

# AI Advisor service URL
AI_ADVISOR_URL = "http://127.0.0.1:5100"

# Helper function to resize images for thumbnails
def resize_image_for_web(image_path: str, max_width: int = 800, max_height: int = 800, quality: int = 85) -> BytesIO:
    """
    Resize image to web-friendly dimensions while maintaining aspect ratio.
    Returns BytesIO object containing JPEG data.
    """
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate new dimensions maintaining aspect ratio
            width, height = img.size
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save to BytesIO as JPEG
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            return output
    except Exception as e:
        logger.error(f"Error resizing image {image_path}: {e}")
        # Return original file as fallback
        with open(image_path, 'rb') as f:
            output = BytesIO(f.read())
            output.seek(0)
            return output

# Helper function to get base URL for image serving
def get_base_url():
    """Get base URL for generating full image URLs"""
    # Check for environment variable first (for Cloudflare Tunnel, etc.)
    base_url = os.environ.get('MONDRIAN_BASE_URL')
    if base_url:
        return base_url.rstrip('/')
    
    # Use Flask request host URL if available
    try:
        if request:
            return request.host_url.rstrip('/')
    except RuntimeError:
        pass
    
    # Auto-detect local network IP
    import socket
    try:
        # Connect to external address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return f"http://{local_ip}:5005"
    except Exception:
        # Last resort - try to get hostname
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return f"http://{local_ip}:5005"

class JobDatabase:
    """Simple job tracking database"""
    
    def __init__(self, db_path: str = "mondrian.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema - add missing columns if needed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if error column exists
            cursor.execute("PRAGMA table_info(jobs)")
            columns = {row[1] for row in cursor.fetchall()}
            
            # Add missing columns
            if 'error' not in columns:
                logger.info("Adding 'error' column to jobs table")
                conn.execute("ALTER TABLE jobs ADD COLUMN error TEXT DEFAULT NULL")
                conn.commit()
            
            if 'analysis_html' not in columns:
                logger.info("Adding 'analysis_html' column to jobs table")
                conn.execute("ALTER TABLE jobs ADD COLUMN analysis_html TEXT DEFAULT NULL")
                conn.commit()
            
            if 'advisor_bio' not in columns:
                logger.info("Adding 'advisor_bio' column to jobs table")
                conn.execute("ALTER TABLE jobs ADD COLUMN advisor_bio TEXT DEFAULT NULL")
                conn.commit()
            
            if 'retry_count' not in columns:
                logger.info("Adding 'retry_count' column to jobs table")
                conn.execute("ALTER TABLE jobs ADD COLUMN retry_count INTEGER DEFAULT 0")
                conn.commit()

            if 'model' not in columns:
                logger.info("Adding 'model' column to jobs table")
                conn.execute("ALTER TABLE jobs ADD COLUMN model TEXT DEFAULT NULL")
                conn.commit()

            if 'adapter' not in columns:
                logger.info("Adding 'adapter' column to jobs table")
                conn.execute("ALTER TABLE jobs ADD COLUMN adapter TEXT DEFAULT NULL")
                conn.commit()
    
    def create_job(self, advisor: str, mode: str, image_path: str, enable_rag: bool = True) -> str:
        """Create a new job"""
        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (id, filename, advisor, mode, status, created_at, last_activity, enable_rag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, image_path, advisor, mode, 'pending', now, now, 1 if enable_rag else 0))
            conn.commit()
        
        logger.info(f"Created job {job_id} (RAG={'enabled' if enable_rag else 'disabled'})")
        
        # Verify job was created (catch database write issues early)
        try:
            verify_job = self.get_job(job_id)
            if verify_job:
                logger.info(f"✓ Verified job exists in DB: {job_id}")
            else:
                logger.error(f"❌ Job verification failed: {job_id} not found immediately after creation!")
        except Exception as e:
            logger.error(f"❌ Error verifying job creation: {e}")
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # Better error messages
                cursor = conn.execute(
                    """SELECT id, filename, status, advisor, mode, created_at, current_step, progress_percentage, enable_rag,
                              prompt, llm_prompt, analysis_markdown, llm_thinking, analysis_html, advisor_bio, llm_outputs,
                              summary_html, advisor_bio_html, model, adapter
                       FROM jobs WHERE id = ?""",
                    (job_id,)
                )
                row = cursor.fetchone()
        except sqlite3.DatabaseError as e:
            logger.error(f"Database error retrieving job {job_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving job {job_id}: {e}")
            return None

        if not row:
            return None

        return {
            'id': row[0],
            'filename': row[1],
            'status': row[2],
            'advisor': row[3],
            'mode': row[4],
            'created_at': row[5],
            'current_step': row[6],
            'progress_percentage': row[7],
            'enable_rag': bool(row[8]),
            'prompt': row[9] or '',
            'llm_prompt': row[10] or '',
            'analysis_markdown': row[11] or '',
            'llm_thinking': row[12] or '',
            'analysis_html': row[13] or '',
            'advisor_bio': row[14] or '',
            'llm_outputs': row[15] or '',
            'summary_html': row[16] or '',
            'advisor_bio_html': row[17] or '',
            'model': row[18] or '',
            'adapter': row[19] or ''
        }
    
    def update_job(self, job_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update job status"""
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE jobs SET status = ?, last_activity = ?
                WHERE id = ?
            """, (status, now, job_id))
            conn.commit()
        
        logger.info(f"Updated job {job_id} to status {status}")
    
    def list_jobs(self, limit: int = 100) -> list:
        """List recent jobs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, filename, status, advisor, mode, created_at, model, adapter FROM jobs
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

        return [
            {
                'id': row[0],
                'filename': row[1],
                'status': row[2],
                'advisor': row[3],
                'mode': row[4],
                'created_at': row[5],
                'model': row[6],
                'adapter': row[7]
            }
            for row in rows
        ]
    
    def clear_jobs(self):
        """Clear all jobs"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM jobs")
            conn.commit()
        
        logger.info("Cleared all jobs")


# Flask app setup
app = Flask(__name__)
CORS(app)

# Global job database
job_db = None

def init_db(db_path: str = "mondrian.db"):
    """Initialize job database"""
    global job_db
    job_db = JobDatabase(db_path)
    logger.info(f"Job database initialized at {db_path}")


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "UP",
        "service": "job_service",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/advisors', methods=['GET'])
def get_advisors():
    """Get list of available (enabled) advisors with representative works"""
    try:
        import base64
        
        db_path = job_db.db_path if job_db else "mondrian.db"
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Only fetch enabled advisors - strict check: enabled = 1 only
            cursor = conn.execute("""
                SELECT a.id, a.name, a.bio, a.focus_areas, a.category 
                FROM advisors a
                INNER JOIN advisor_config ac ON a.id = ac.advisor_id
                WHERE ac.enabled = 1
                ORDER BY a.id
            """)
            rows = cursor.fetchall()
        
        advisors = []
        for row in rows:
            advisor_id = row["id"]
            
            advisor = {
                "id": advisor_id,
                "name": row["name"],
                "specialty": row["category"] if row["category"] else "Photography",
                "bio": row["bio"] if row["bio"] else "",
                "focus_areas": []
            }
            
            # Parse focus_areas JSON if it exists
            if row["focus_areas"]:
                try:
                    advisor["focus_areas"] = json.loads(row["focus_areas"])
                except (json.JSONDecodeError, TypeError):
                    advisor["focus_areas"] = []
            
            # Add representative works with base64-encoded images
            artworks_list = []
            possible_dirs = [
                f"mondrian/source/advisor/photographer/{advisor_id}",
                f"mondrian/source/advisor/painter/{advisor_id}",
                f"mondrian/source/advisor/architect/{advisor_id}",
                f"training/datasets/{advisor_id}-images",
            ]
            
            for dir_path in possible_dirs:
                if os.path.isdir(dir_path):
                    images = sorted([f for f in os.listdir(dir_path) 
                                   if f.lower().endswith(('.jpg', '.jpeg', '.png')) 
                                   and f.lower() != 'headshot.jpg'])
                    
                    # Create artwork entries for up to 4 images with full URLs
                    base_url = get_base_url()
                    for idx, image_file in enumerate(images[:4], 1):
                        # Determine MIME type
                        mime_type = 'image/jpeg' if image_file.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
                        
                        artworks_list.append({
                            "title": image_file.replace('.jpg', '').replace('.png', '').replace('_', ' '),
                            "year": "",
                            "url": f"{base_url}/advisor_artwork/{advisor_id}/{idx-1}",
                            "mime_type": mime_type
                        })
                    break
            
            advisor["artworks"] = artworks_list
            advisor["image_url"] = f"{base_url}/advisor_image/{advisor_id}"
            advisors.append(advisor)
        
        return jsonify({
            "advisors": advisors,
            "count": len(advisors),
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching advisors: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/advisors/<advisor_id>', methods=['GET'])
def get_advisor_detail(advisor_id):
    """Get detailed information for a specific advisor with images and representative works"""
    try:
        import base64
        
        db_path = job_db.db_path if job_db else "mondrian.db"
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Check that advisor is enabled before returning details
            cursor = conn.execute("""
                SELECT a.id, a.name, a.bio, a.focus_areas, a.category, a.years, a.wikipedia_url, a.commons_url
                FROM advisors a
                INNER JOIN advisor_config ac ON a.id = ac.advisor_id
                WHERE a.id = ? AND ac.enabled = 1
            """,
                (advisor_id,)
            )
            row = cursor.fetchone()
        
        if not row:
            return jsonify({"error": f"Advisor '{advisor_id}' not found or not enabled"}), 404
        
        # Parse focus_areas JSON
        focus_areas_list = []
        if row["focus_areas"]:
            try:
                focus_areas_data = json.loads(row["focus_areas"])
                if isinstance(focus_areas_data, list):
                    focus_areas_list = focus_areas_data
            except (json.JSONDecodeError, TypeError):
                focus_areas_list = []
        
        # Get available artwork files for this advisor
        artworks_list = []
        possible_dirs = [
            f"mondrian/source/advisor/photographer/{advisor_id}",
            f"mondrian/source/advisor/painter/{advisor_id}",
            f"mondrian/source/advisor/architect/{advisor_id}",
            f"training/datasets/{advisor_id}-images",
        ]
        
        for dir_path in possible_dirs:
            if os.path.isdir(dir_path):
                # Get image files from directory (skip headshot)
                images = sorted([f for f in os.listdir(dir_path) 
                               if f.lower().endswith(('.jpg', '.jpeg', '.png')) 
                               and f.lower() != 'headshot.jpg'])
                
                # Create artwork entries for ALL images with full URLs
                base_url = get_base_url()
                for idx, image_file in enumerate(images):
                    # Determine MIME type
                    mime_type = 'image/jpeg' if image_file.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
                    
                    artworks_list.append({
                        "title": image_file.replace('.jpg', '').replace('.png', '').replace('_', ' '),
                        "year": "",
                        "url": f"{base_url}/advisor_artwork/{advisor_id}/{idx}",
                        "mime_type": mime_type
                    })
                break
        
        # Fallback: add at least one artwork entry if none found
        if not artworks_list:
            base_url = get_base_url()
            artworks_list.append({
                "title": "Representative Work",
                "year": "",
                "url": f"{base_url}/advisor_artwork/{advisor_id}/1"
            })
        
        # Build advisor response
        base_url = get_base_url()
        
        # Build "Learn More" section with references
        learn_more = {}
        if row["wikipedia_url"]:
            learn_more["wikipedia"] = {
                "title": "Wikipedia",
                "url": row["wikipedia_url"],
                "description": f"Learn more about {row['name']} on Wikipedia"
            }
        if row["commons_url"]:
            learn_more["gallery"] = {
                "title": "Gallery",
                "url": row["commons_url"],
                "description": f"View {row['name']}'s work"
            }
        
        advisor = {
            "id": row["id"],
            "name": row["name"],
            "specialty": row["category"] if row["category"] else "Photography",
            "bio": row["bio"] if row["bio"] else "",
            "focus_areas": focus_areas_list,
            "image_url": f"{base_url}/advisor_image/{advisor_id}",
            "artworks": artworks_list,
            "learn_more": learn_more
        }
        
        return jsonify({
            "advisor": advisor,
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching advisor detail for {advisor_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/advisor_image/<advisor_id>', methods=['GET'])
def get_advisor_headshot(advisor_id):
    """Serve advisor headshot image - try multiple locations"""
    try:
        import os
        
        # Try multiple possible locations for advisor headshot, in order of priority
        possible_paths = [
            # First priority: training datasets (most recent/curated)
            f"training/datasets/{advisor_id}-images/headshot.jpg",
            f"training/datasets/{advisor_id}-images/headshot.png",
            
            # Second priority: source advisor directories  
            f"mondrian/source/advisor/photographer/{advisor_id}/headshot.jpg",
            f"mondrian/source/advisor/photographer/{advisor_id}/headshot.png",
            f"mondrian/source/advisor/painter/{advisor_id}/headshot.jpg",
            f"mondrian/source/advisor/painter/{advisor_id}/headshot.png",
            f"mondrian/source/advisor/architect/{advisor_id}/headshot.jpg",
            f"mondrian/source/advisor/architect/{advisor_id}/headshot.png",
            
            # Third priority: dedicated advisor_images directory
            f"mondrian/advisor_images/{advisor_id}.jpg",
            f"mondrian/advisor_images/{advisor_id}.png",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Serving advisor headshot from {path}")
                resized = resize_image_for_web(path, max_width=400, max_height=400)
                return send_file(resized, mimetype='image/jpeg')
        
        # If no headshot found, try to use first image from advisor directory as fallback
        logger.warning(f"No dedicated headshot found for advisor {advisor_id}, trying to use first representative work")
        advisor_dirs = [
            f"mondrian/source/advisor/photographer/{advisor_id}",
            f"mondrian/source/advisor/painter/{advisor_id}",
            f"mondrian/source/advisor/architect/{advisor_id}",
            f"training/datasets/{advisor_id}-images",
        ]
        
        for dir_path in advisor_dirs:
            if os.path.isdir(dir_path):
                images = sorted([f for f in os.listdir(dir_path) 
                               if f.lower().endswith(('.jpg', '.jpeg', '.png')) 
                               and f.lower() != 'headshot.jpg'])
                if images:
                    image_path = os.path.join(dir_path, images[0])
                    logger.info(f"Using first representative work as headshot: {image_path}")
                    resized = resize_image_for_web(image_path, max_width=400, max_height=400)
                    return send_file(resized, mimetype='image/jpeg')
        
        # If still no image found, return 404
        logger.warning(f"No headshot or representative work found for advisor {advisor_id}")
        return jsonify({"error": f"No headshot image found for advisor {advisor_id}"}), 404
    
    except Exception as e:
        logger.error(f"Error serving advisor headshot: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/advisor_artwork/<advisor_id>/<int:artwork_id>', methods=['GET'])
def get_advisor_artwork(advisor_id, artwork_id):
    """Serve advisor representative work/artwork"""
    try:
        import os
        
        # Try multiple possible locations for advisor artwork
        possible_dirs = [
            f"mondrian/source/advisor/photographer/{advisor_id}",
            f"mondrian/source/advisor/painter/{advisor_id}",
            f"mondrian/source/advisor/architect/{advisor_id}",
            f"training/datasets/{advisor_id}-images",
        ]
        
        for dir_path in possible_dirs:
            if os.path.isdir(dir_path):
                # Get image files from directory (skip headshot)
                images = sorted([f for f in os.listdir(dir_path) 
                               if f.lower().endswith(('.jpg', '.jpeg', '.png')) 
                               and f.lower() != 'headshot.jpg'])
                
                if artwork_id <= len(images):
                    image_file = images[artwork_id - 1]
                    image_path = os.path.join(dir_path, image_file)
                    logger.info(f"Serving artwork {artwork_id} from {image_path}")
                    resized = resize_image_for_web(image_path, max_width=1200, max_height=1200)
                    return send_file(resized, mimetype='image/jpeg')
        
        # If no images found, return 404
        logger.warning(f"No artwork {artwork_id} found for advisor {advisor_id}")
        return jsonify({"error": f"No artwork found for advisor {advisor_id}"}), 404
    
    except Exception as e:
        logger.error(f"Error serving advisor artwork: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/advisor_artwork/<advisor_id>/lightbox/<int:artwork_id>', methods=['GET'])
def get_advisor_artwork_lightbox_info(advisor_id, artwork_id):
    """Get lightbox navigation info for advisor artwork - supports left/right arrow navigation"""
    try:
        import os
        
        # Try multiple possible locations for advisor artwork
        possible_dirs = [
            f"mondrian/source/advisor/photographer/{advisor_id}",
            f"mondrian/source/advisor/painter/{advisor_id}",
            f"mondrian/source/advisor/architect/{advisor_id}",
            f"training/datasets/{advisor_id}-images",
        ]
        
        for dir_path in possible_dirs:
            if os.path.isdir(dir_path):
                # Get image files from directory (skip headshot)
                images = sorted([f for f in os.listdir(dir_path) 
                               if f.lower().endswith(('.jpg', '.jpeg', '.png')) 
                               and f.lower() != 'headshot.jpg'])
                
                if artwork_id <= len(images) and artwork_id >= 1:
                    current_idx = artwork_id - 1
                    current_image = images[current_idx]
                    base_url = get_base_url()
                    
                    # Build lightbox metadata
                    lightbox_info = {
                        "current": {
                            "id": artwork_id,
                            "title": current_image.replace('.jpg', '').replace('.png', '').replace('_', ' '),
                            "url": f"{base_url}/advisor_artwork/{advisor_id}/{artwork_id}",
                            "filename": current_image
                        },
                        "navigation": {
                            "has_previous": current_idx > 0,
                            "has_next": current_idx < len(images) - 1,
                            "previous_id": artwork_id - 1 if current_idx > 0 else None,
                            "next_id": artwork_id + 1 if current_idx < len(images) - 1 else None
                        },
                        "progress": {
                            "current": artwork_id,
                            "total": len(images),
                            "percent": int((artwork_id / len(images)) * 100)
                        },
                        "all_items": [
                            {
                                "id": idx + 1,
                                "title": img.replace('.jpg', '').replace('.png', '').replace('_', ' '),
                                "url": f"{base_url}/advisor_artwork/{advisor_id}/{idx + 1}",
                                "filename": img
                            } for idx, img in enumerate(images)
                        ]
                    }
                    
                    logger.info(f"Serving lightbox info for artwork {artwork_id} of {len(images)}")
                    return jsonify(lightbox_info), 200
        
        # If no images found, return 404
        logger.warning(f"No artwork {artwork_id} found for advisor {advisor_id} (lightbox)")
        return jsonify({"error": f"No artwork found for advisor {advisor_id}"}), 404
    
    except Exception as e:
        logger.error(f"Error serving advisor artwork lightbox info: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/reference-image/<filename>', methods=['GET'])
def get_reference_image(filename):
    """Serve reference images for RAG analysis results. Supports ?size=full for lightbox view."""
    try:
        # Log the request for debugging
        remote_addr = request.environ.get('REMOTE_ADDR', 'unknown')
        logger.info(f"[DEBUG] Reference image request: {filename} from {remote_addr}")
        
        # Check for size parameter (for lightbox full-size view)
        size = request.args.get('size', 'thumb')
        
        # Get the current working directory to construct absolute paths
        cwd = os.getcwd()
        
        # Search for the image file in advisor directories
        possible_dirs = [
            os.path.join(cwd, "mondrian/source/advisor/photographer/ansel"),
            os.path.join(cwd, "mondrian/source/advisor/photographer"),
            os.path.join(cwd, "mondrian/source/advisor/painter"),
            os.path.join(cwd, "mondrian/source/advisor/architect"),
            os.path.join(cwd, "training/datasets")
        ]
        
        image_path = None
        for base_dir in possible_dirs:
            # Try direct path
            test_path = os.path.join(base_dir, filename)
            if os.path.exists(test_path) and os.path.isfile(test_path):
                image_path = test_path
                logger.info(f"[DEBUG] Found image at: {image_path}")
                break
                
            # Try subdirectories (one level deep)
            if os.path.isdir(base_dir):
                try:
                    for subdir in os.listdir(base_dir):
                        subdir_path = os.path.join(base_dir, subdir)
                        if os.path.isdir(subdir_path):
                            test_path = os.path.join(subdir_path, filename)
                            if os.path.exists(test_path) and os.path.isfile(test_path):
                                image_path = test_path
                                logger.info(f"[DEBUG] Found image in subdirectory: {image_path}")
                                break
                except OSError as e:
                    logger.debug(f"Could not search directory {base_dir}: {e}")
                if image_path:
                    break
        
        if not image_path:
            logger.warning(f"Reference image not found: {filename} (searched {len(possible_dirs)} directories)")
            return jsonify({"error": "Image not found"}), 404
        
        # Choose size based on parameter
        if size == 'full':
            logger.info(f"Serving reference image (full size for lightbox): {image_path}")
            resized = resize_image_for_web(image_path, max_width=1200, max_height=9999, quality=95)
        else:
            logger.info(f"Serving reference image (thumbnail): {image_path}")
            resized = resize_image_for_web(image_path, max_width=254, max_height=9999, quality=95)
        
        return send_file(resized, mimetype='image/jpeg')
        
    except Exception as e:
        logger.error(f"Failed to serve reference image {filename}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_image():
    """Upload image and queue for analysis"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    try:
        # Get file - iOS uses 'image' field name, curl might use 'file'
        file = None
        if 'image' in request.files:
            file = request.files['image']
        elif 'file' in request.files:
            file = request.files['file']
        
        if not file or file.filename == '':
            return jsonify({"error": "No file provided"}), 400
        
        advisor = request.form.get('advisor', 'ansel')
        mode = request.form.get('mode', 'baseline')
        enable_rag = request.form.get('enable_rag', 'true').lower() in ('true', '1', 'yes')
        auto_analyze = request.form.get('auto_analyze', 'true').lower() in ('true', '1', 'yes')
        
        # Save file - extract just the basename to avoid path traversal issues
        import uuid
        from os.path import basename
        safe_filename = basename(file.filename)  # Extract just the filename, not the path
        unique_filename = f"{uuid.uuid4()}_{safe_filename}"
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        filepath = upload_dir / unique_filename
        file.save(str(filepath))
        
        # Create job with enable_rag parameter
        job_id = job_db.create_job(advisor, mode, str(filepath), enable_rag=enable_rag)
        logger.info(f"[UPLOAD] Job created: {job_id} (DB: {job_db.db_path})")
        
        # If auto_analyze is true, update status to 'queued' to trigger immediate processing
        if auto_analyze:
            with sqlite3.connect(job_db.db_path) as conn:
                conn.execute("""
                    UPDATE jobs SET status = 'queued' WHERE id = ?
                """, (job_id,))
                conn.commit()
            logger.info(f"[UPLOAD] Job queued: {job_id}")
        
        # Format response - use get_base_url() helper for consistency
        base_url = get_base_url()
        
        response_data = {
            "job_id": job_id,
            "filename": unique_filename,
            "advisor": advisor,
            "advisors_used": [advisor],
            "status": "queued",
            "status_url": f"{base_url}/status/{job_id}",
            "stream_url": f"{base_url}/stream/{job_id}"
        }
        logger.info(f"[UPLOAD] Returning response: {response_data}")
        return jsonify(response_data), 201
    
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/jobs', methods=['GET'])
def list_jobs():
    """List recent jobs"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    limit = request.args.get('limit', 100, type=int)
    format_type = request.args.get('format', 'json').lower()
    jobs = job_db.list_jobs(limit=limit)
    
    # Return JSON by default
    if format_type != 'html':
        return jsonify({
            "jobs": jobs,
            "count": len(jobs),
            "timestamp": datetime.now().isoformat()
        }), 200
    
    # Return HTML format
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mondrian Jobs</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { color: #333; margin-bottom: 20px; font-size: 28px; }
            .stats { display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }
            .stat-card {
                background: white;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                flex: 1;
                min-width: 150px;
            }
            .stat-label { color: #999; font-size: 12px; text-transform: uppercase; }
            .stat-value { font-size: 24px; font-weight: bold; color: #333; margin-top: 5px; }
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
            }
            thead {
                background: #f8f8f8;
                border-bottom: 2px solid #e0e0e0;
            }
            th {
                padding: 12px 15px;
                text-align: left;
                font-weight: 600;
                color: #333;
                font-size: 13px;
                text-transform: uppercase;
            }
            td {
                padding: 12px 15px;
                border-bottom: 1px solid #f0f0f0;
                color: #666;
            }
            tbody tr:hover { background: #fafafa; }
            .status-badge {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .status-pending { background: #fff3cd; color: #856404; }
            .status-running { background: #cfe2ff; color: #084298; }
            .status-completed { background: #d1e7dd; color: #0f5132; }
            .status-failed { background: #f8d7da; color: #842029; }
            .mode-badge {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                background: #e7f3ff;
                color: #0056b3;
            }
            .progress-bar {
                width: 100%;
                height: 6px;
                background: #e0e0e0;
                border-radius: 3px;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: #4CAF50;
                transition: width 0.3s;
            }
            .timestamp { font-size: 12px; color: #999; }
            .job-id { font-family: monospace; font-size: 11px; color: #999; }
            .empty { text-align: center; padding: 40px; color: #999; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mondrian Job Management</h1>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-label">Total Jobs</div>
                    <div class="stat-value">""" + str(len(jobs)) + """</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Completed</div>
                    <div class="stat-value">""" + str(sum(1 for j in jobs if j.get('status') == 'completed')) + """</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Running</div>
                    <div class="stat-value">""" + str(sum(1 for j in jobs if j.get('status') == 'running')) + """</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Failed</div>
                    <div class="stat-value">""" + str(sum(1 for j in jobs if j.get('status') == 'failed')) + """</div>
                </div>
            </div>
            
            """
    
    if not jobs:
        html += '<div class="empty">No jobs found</div>'
    else:
        html += """
            <table>
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Filename</th>
                        <th>Advisor</th>
                        <th>Mode</th>
                        <th>Model</th>
                        <th>Adapter</th>
                        <th>Status</th>
                        <th>Progress</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
        """
        for job in jobs:
            status = job.get('status', 'unknown')
            mode = job.get('mode', 'standard')
            progress = job.get('progress_percentage', 0)
            created = job.get('created_at', 'N/A')
            if created != 'N/A':
                created = created.split('.')[0]  # Remove milliseconds

            # Extract model and adapter display names
            model = job.get('model', '') or 'N/A'
            if model and model != 'N/A' and '/' in model:
                model = model.split('/')[-1]  # Get friendly name from "Qwen/Qwen3-VL-4B-Thinking"

            adapter = job.get('adapter', '') or 'N/A'
            if adapter and adapter != 'N/A':
                import os
                # Extract meaningful part from "./adapters/ansel_qwen3_4b_thinking/epoch_10"
                adapter = os.path.basename(os.path.dirname(adapter))

            job_id_full = job.get('id', 'N/A')
            job_id_short = job_id_full[:8]
            html += f"""
                    <tr>
                        <td><span class="job-id"><a href="/jobs/{job_id_full}?view=detail" style="color: #666; text-decoration: none;">{job_id_short}...</a></span></td>
                        <td>{job.get('filename', 'N/A')}</td>
                        <td>{job.get('advisor', 'N/A')}</td>
                        <td><span class="mode-badge">{mode}</span></td>
                        <td><small>{model}</small></td>
                        <td><small>{adapter}</small></td>
                        <td><span class="status-badge status-{status}">{status}</span></td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {progress}%"></div>
                            </div>
                            <span style="font-size: 11px; color: #999;">{progress}%</span>
                        </td>
                        <td><span class="timestamp">{created}</span></td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        """
    
    html += """
        </div>
        <script>
            // Auto-refresh every 3 seconds
            setInterval(function() {
                location.reload();
            }, 3000);
        </script>
    </body>
    </html>
    """
    
    return Response(html, mimetype='text/html')


@app.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id: str):
    """Get job details - returns JSON job metadata (excludes HTML content)
    
    Query params:
        view: 'json' (default) or 'detail' (HTML debug view)
    
    For HTML content, use dedicated endpoints:
        - GET /summary/{job_id} - Quick preview HTML (top 3 recommendations)
        - GET /analysis/{job_id} - Full detailed analysis HTML
    """
    if not job_db:
        logger.error(f"[STATUS] Job database not initialized when checking job {job_id}")
        return jsonify({"error": "Database not initialized"}), 503
    
    job = job_db.get_job(job_id)
    
    if not job:
        logger.warning(f"[STATUS] Job not found: {job_id} (checking DB at {job_db.db_path})")
        # Additional debugging
        try:
            with sqlite3.connect(job_db.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM jobs")
                count = cursor.fetchone()[0]
                logger.warning(f"[STATUS] Total jobs in database: {count}")
        except Exception as e:
            logger.error(f"[STATUS] Failed to check job count: {e}")
        return jsonify({"error": "Job not found"}), 404
    
    # Check if requesting HTML detail view (for debugging)
    view = request.args.get('view', 'json')
    if view == 'detail':
        return render_job_detail_html(job)
    
    # Always exclude large HTML fields to optimize polling performance
    # Clients must use /summary/{job_id} or /analysis/{job_id} to get HTML
    job_response = {k: v for k, v in job.items() if k not in ('analysis_html', 'summary_html')}
    return jsonify(job_response), 200


def render_job_detail_html(job):
    """Render detailed job view as HTML"""
    status = job.get('status', 'unknown')
    prompt = job.get('prompt', '')
    llm_prompt = job.get('llm_prompt', '')
    analysis = job.get('analysis_markdown', '')
    thinking = job.get('llm_thinking', '')
    
    # Escape HTML in content
    def escape_html(text):
        if not text:
            return ''
        return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Job {job.get('id', 'Unknown')[:8]}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
                background: #f5f5f5;
                padding: 20px;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ 
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .back-link {{ 
                display: inline-block;
                margin-bottom: 15px;
                color: #0066cc;
                text-decoration: none;
                font-size: 14px;
            }}
            .back-link:hover {{ text-decoration: underline; }}
            h1 {{ color: #333; margin-bottom: 15px; }}
            .meta {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }}
            .meta-item {{
                background: #f8f8f8;
                padding: 10px;
                border-radius: 4px;
                border-left: 3px solid #0066cc;
            }}
            .meta-label {{ 
                color: #999;
                font-size: 11px;
                text-transform: uppercase;
                margin-bottom: 3px;
            }}
            .meta-value {{ 
                color: #333;
                font-size: 14px;
                font-weight: 500;
            }}
            .status-badge {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
            }}
            .status-completed {{ background: #d1e7dd; color: #0f5132; }}
            .status-running {{ background: #cfe2ff; color: #084298; }}
            .status-pending {{ background: #fff3cd; color: #856404; }}
            .status-failed {{ background: #f8d7da; color: #842029; }}
            .section {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .section-title {{
                font-size: 16px;
                font-weight: 600;
                color: #333;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #f0f0f0;
            }}
            .content {{
                background: #f8f8f8;
                padding: 15px;
                border-radius: 4px;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
                font-size: 13px;
                line-height: 1.5;
                color: #333;
            }}
            .empty {{ color: #999; font-style: italic; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/jobs?format=html" class="back-link">← Back to Jobs</a>
                <h1>Job Details</h1>
                <div class="meta">
                    <div class="meta-item">
                        <div class="meta-label">Job ID</div>
                        <div class="meta-value" style="font-family: monospace;">{escape_html(job.get('id', 'N/A'))}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Status</div>
                        <div class="meta-value"><span class="status-badge status-{status}">{status}</span></div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Advisor</div>
                        <div class="meta-value">{escape_html(job.get('advisor', 'N/A'))}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Mode</div>
                        <div class="meta-value">{escape_html(job.get('mode', 'N/A'))}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Created</div>
                        <div class="meta-value">{escape_html(job.get('created_at', 'N/A').split('.')[0])}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Image</div>
                        <div class="meta-value" style="font-size: 12px; word-break: break-all;">{escape_html(job.get('filename', 'N/A'))}</div>
                    </div>
                </div>
            </div>
    """
    
    # System Prompt
    if prompt:
        html += f"""
            <div class="section">
                <div class="section-title">System Prompt</div>
                <div class="content">{escape_html(prompt)}</div>
            </div>
        """
    
    # LLM Prompt
    if llm_prompt:
        html += f"""
            <div class="section">
                <div class="section-title">LLM Prompt (Sent to Model)</div>
                <div class="content">{escape_html(llm_prompt)}</div>
            </div>
        """
    
    # Analysis Output
    if analysis:
        html += f"""
            <div class="section">
                <div class="section-title">Analysis Output (Summary & Details)</div>
                <div class="content">{escape_html(analysis)}</div>
            </div>
        """
    
    # LLM Thinking
    if thinking:
        html += f"""
            <div class="section">
                <div class="section-title">LLM Internal Thinking</div>
                <div class="content">{escape_html(thinking)}</div>
            </div>
        """
    
    if not (prompt or llm_prompt or analysis or thinking):
        html += """
            <div class="section">
                <div class="content empty">No analysis data available yet. Job may still be processing.</div>
            </div>
        """
    
    html += """
            <script>
                setInterval(function() {
                    // Auto-refresh every 5 seconds if job is still running
                    var statusElement = document.querySelector('.status-badge');
                    if (statusElement && (statusElement.textContent === 'PENDING' || statusElement.textContent === 'RUNNING' || statusElement.textContent === 'ANALYZING')) {
                        location.reload();
                    }
                }, 5000);
            </script>
        </div>
    </body>
    </html>
    """
    
    return Response(html, mimetype='text/html')


@app.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get job status - alias for /jobs/<job_id> for backwards compatibility"""
    return get_job(job_id)


@app.route('/stream/<job_id>', methods=['GET'])
def stream_job_updates(job_id: str):
    """Stream job updates via Server-Sent Events (SSE)"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503

    job = job_db.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Compute base_url outside generator (request context available here)
    base_url = f"http://{request.host.split(':')[0]}:5005"

    def generate():
        """Generator function that yields SSE events"""
        import time
        from datetime import datetime

        # Send connected event
        connected_event = {
            "type": "connected",
            "job_id": job_id
        }
        yield f"event: connected\ndata: {json.dumps(connected_event)}\n\n"

        last_status = job.get('status')
        last_progress = job.get('progress_percentage', 0)
        last_thinking = job.get('llm_thinking', '')
        last_step = job.get('current_step', '')
        last_update_time = time.time()
        update_interval = 3  # Send status updates every 3 seconds for iOS UI

        # Send initial status update immediately after connected
        initial_update_event = {
            "type": "status_update",
            "job_id": job_id,
            "timestamp": datetime.now().timestamp(),
            "job_data": {
                "status": last_status,
                "progress_percentage": last_progress,
                "current_step": last_step,
                "llm_thinking": last_thinking,
                "current_advisor": 1,
                "total_advisors": 1,
                "step_phase": "analyzing" if last_status == "analyzing" else "processing",
                "analysis_url": f"{base_url}/analysis/{job_id}"
            }
        }
        yield f"event: status_update\ndata: {json.dumps(initial_update_event)}\n\n"
        logger.debug(f"🔄 Initial stream update: status={last_status}, progress={last_progress}%, step={last_step}")

        while True:
            job_data = job_db.get_job(job_id)
            if not job_data:
                break
            
            current_status = job_data.get('status')
            current_progress = job_data.get('progress_percentage', 0)
            current_thinking = job_data.get('llm_thinking', '')
            current_step = job_data.get('current_step', '')
            current_time = time.time()
            
            # Send status update if changed OR if periodic update interval reached (for progress/step updates)
            status_changed = (current_status != last_status or
                            current_progress != last_progress or
                            current_step != last_step or
                            current_thinking != last_thinking)

            periodic_update = (current_time - last_update_time) >= update_interval and current_status == "analyzing"

            if status_changed or periodic_update:
                
                status_update_event = {
                    "type": "status_update",
                    "job_id": job_id,
                    "timestamp": datetime.now().timestamp(),
                    "job_data": {
                        "status": current_status,
                        "progress_percentage": current_progress,
                        "current_step": current_step,
                        "llm_thinking": current_thinking,
                        "current_advisor": 1,
                        "total_advisors": 1,
                        "step_phase": "analyzing" if current_status == "analyzing" else "processing",
                        "analysis_url": f"{base_url}/analysis/{job_id}"
                    }
                }
                yield f"event: status_update\ndata: {json.dumps(status_update_event)}\n\n"
                logger.debug(f"🔄 Stream update: status={current_status}, progress={current_progress}%, thinking_len={len(current_thinking)}")
                
                last_status = current_status
                last_progress = current_progress
                last_thinking = current_thinking
                last_step = current_step
                last_update_time = current_time
            
            # Check if job is complete
            if current_status in ['completed', 'failed', 'done']:
                # Send analysis_complete event
                if current_status == 'completed':
                    analysis_complete_event = {
                        "type": "analysis_complete",
                        "job_id": job_id,
                        "analysis_html": job_data.get('analysis_html', '')
                    }
                    yield f"event: analysis_complete\ndata: {json.dumps(analysis_complete_event)}\n\n"
                
                # Send final done event
                done_event = {
                    "type": "done",
                    "job_id": job_id
                }
                yield f"event: done\ndata: {json.dumps(done_event)}\n\n"
                break
            
            time.sleep(0.5)  # Check every 0.5 seconds for responsiveness
    
    return app.response_class(
        generate(),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route('/analysis/<job_id>', methods=['GET'])
def get_analysis(job_id: str):
    """Get analysis results for a job - returns full HTML analysis"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    job = job_db.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    # Return the full analysis HTML with proper content-type
    analysis_html = job.get('analysis_html', '')
    
    if not analysis_html:
        return jsonify({"error": "No analysis available"}), 404
    
    return Response(
        analysis_html,
        mimetype='text/html; charset=utf-8',
        headers={'Cache-Control': 'no-cache'}
    )


@app.route('/summary/<job_id>', methods=['GET'])
def get_summary(job_id: str):
    """
    Get a critical recommendations summary HTML.
    Returns HTML view of only the most important recommendations (top 3).
    """
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    job = job_db.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if job['status'] != 'completed':
        return jsonify({"error": "Job not completed"}), 400
    
    summary_html = job.get('summary_html', '')
    
    if not summary_html:
        return jsonify({"error": "No summary available"}), 404
    
    return Response(
        summary_html,
        mimetype='text/html; charset=utf-8',
        headers={'Cache-Control': 'no-cache'}
    )


@app.route('/jobs', methods=['POST'])
def create_job():
    """Create a new job"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    try:
        data = request.get_json() or {}
        
        advisor = data.get('advisor', 'ansel')
        mode = data.get('mode', 'baseline')
        image_path = data.get('image_path', '')
        
        if not image_path:
            return jsonify({"error": "image_path required"}), 400
        
        job_id = job_db.create_job(advisor, mode, image_path)
        
        return jsonify({
            "job_id": job_id,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/jobs/<job_id>', methods=['PUT'])
def update_job(job_id: str):
    """Update job status"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    try:
        data = request.get_json() or {}
        
        status = data.get('status', 'pending')
        result = data.get('result')
        error = data.get('error')
        
        job_db.update_job(job_id, status, result, error)
        
        job = job_db.get_job(job_id)
        return jsonify(job), 200
        
    except Exception as e:
        logger.error(f"Error updating job: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/jobs', methods=['DELETE'])
def clear_jobs():
    """Clear all jobs (admin endpoint)"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    job_db.clear_jobs()
    
    return jsonify({
        "message": "All jobs cleared",
        "timestamp": datetime.now().isoformat()
    }), 200


def process_job_worker(db_path: str):
    """Background worker that processes pending jobs"""
    logger.info("Job processor started")

    # Wait for AI Advisor service to be ready before processing jobs
    ai_ready = False
    wait_attempts = 0
    max_wait_attempts = 300  # Up to 5 minutes (30s * 10 attempts per second)

    logger.info(f"Waiting for AI Advisor at {AI_ADVISOR_URL}...")
    while not ai_ready and wait_attempts < max_wait_attempts:
        try:
            response = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "UP":
                    logger.info("✓ AI Advisor service is ready - starting job processing")
                    ai_ready = True
                    break
        except Exception as e:
            logger.debug(f"Health check attempt {wait_attempts}: {e}")

        wait_attempts += 1
        if wait_attempts % 20 == 0:  # Log every 2 seconds
            logger.info(f"Waiting for AI Advisor service... ({wait_attempts // 10}s)")
        time.sleep(0.1)

    if not ai_ready:
        logger.warning(f"AI Advisor service did not become ready after {max_wait_attempts * 0.1}s")
        logger.warning("Job processor continuing anyway - jobs will fail until service is ready")

    logger.info("[PROCESSOR] Entering main processing loop")
    loop_count = 0
    while True:
        try:
            with sqlite3.connect(db_path) as conn:
                # Find pending jobs or jobs with retries available
                # Include 'analyzing' status for recovery (in case of connection drops)
                # Fetch all needed fields in one query to avoid race conditions
                cursor = conn.execute("""
                    SELECT id, filename, advisor, mode, error, COALESCE(retry_count, 0), status, last_activity FROM jobs
                    WHERE (status IN ('pending', 'queued', 'analyzing') AND COALESCE(retry_count, 0) = 0)
                       OR (status = 'failed' AND COALESCE(retry_count, 0) < 3)
                    ORDER BY created_at ASC
                    LIMIT 1
                """)
                job = cursor.fetchone()

                loop_count += 1
                if loop_count % 10 == 0:
                    logger.debug(f"[PROCESSOR] Loop {loop_count}: {'found job' if job else 'no jobs'}")

                if not job:
                    time.sleep(1)
                    continue

                job_id, filename, advisor, mode, previous_error, retry_count, current_status, last_activity = job

                # If job is stuck in analyzing state, log recovery attempt
                if current_status == 'analyzing':
                    logger.warning(f"Recovering stuck job {job_id} from 'analyzing' state (last activity: {last_activity})")

                if retry_count > 0:
                    logger.info(f"Processing job {job_id}: {advisor} ({mode}) - RETRY {retry_count}/3 (prev error: {previous_error})")
                else:
                    logger.info(f"Processing job {job_id}: {advisor} ({mode})")
                
                # Update job status with current step
                advisor_title = advisor.replace('_', ' ').title()
                initial_message = f"Summoning {advisor_title}..."
                conn.execute("""
                    UPDATE jobs SET status = ?, current_step = ?, progress_percentage = ?, last_activity = ?, error = ?
                    WHERE id = ?
                """, ('analyzing', initial_message, 10, datetime.now().isoformat(), None, job_id))
                conn.commit()
                
                # Update analyzing status
                conn.execute("""
                    UPDATE jobs SET current_step = ?, progress_percentage = ?, last_activity = ?
                    WHERE id = ?
                """, (f"Analyzing with {advisor_title}...", 30, datetime.now().isoformat(), job_id))
                conn.commit()
                
                # Call AI Advisor service
                try:
                    # Get enable_rag from job record
                    cursor = conn.execute("SELECT enable_rag FROM jobs WHERE id = ?", (job_id,))
                    enable_rag_row = cursor.fetchone()
                    enable_rag = bool(enable_rag_row[0]) if enable_rag_row else False
                    
                    with open(filename, 'rb') as f:
                        response = requests.post(
                            f"{AI_ADVISOR_URL}/analyze",
                            files={'image': f},
                            data={
                                'advisor': advisor,
                                'mode': mode,
                                'enable_rag': str(enable_rag).lower()
                            },
                            timeout=300
                        )
                    
                    if response.status_code == 200:
                        # Update processing status
                        conn.execute("""
                            UPDATE jobs SET current_step = ?, progress_percentage = ?, last_activity = ?
                            WHERE id = ?
                        """, ("Processing analysis...", 70, datetime.now().isoformat(), job_id))
                        conn.commit()
                        
                        analysis_data = response.json()
                        
                        # Extract all analysis fields
                        analysis_html = analysis_data.get('analysis_html', '')
                        summary_html = analysis_data.get('summary_html', '')
                        advisor_bio = analysis_data.get('advisor_bio', '')
                        advisor_bio_html = analysis_data.get('advisor_bio_html', '')
                        thinking = analysis_data.get('llm_thinking', '')
                        prompt = analysis_data.get('prompt', '')
                        llm_prompt = analysis_data.get('llm_prompt', '')
                        full_response = analysis_data.get('full_response', '')
                        summary = analysis_data.get('summary', '')
                        model = analysis_data.get('model', '')
                        adapter = analysis_data.get('adapter', '')

                        # Prepare llm_outputs as JSON string
                        llm_outputs = json.dumps({
                            'prompt': prompt,
                            'response': full_response,
                            'summary': summary,
                            'model': model,
                            'timestamp': analysis_data.get('timestamp', '')
                        })

                        # Create markdown summary for analysis_markdown field
                        analysis_markdown = f"""# {advisor.title()} Analysis\n\n## Summary\n{summary}\n\n## Full Analysis\n{full_response}"""

                        # Update job with all results including summary_html and advisor_bio_html
                        conn.execute("""
                            UPDATE jobs SET status = ?, current_step = ?, progress_percentage = ?,
                                           analysis_html = ?, summary_html = ?,
                                           advisor_bio = ?, advisor_bio_html = ?, llm_thinking = ?,
                                           prompt = ?, llm_prompt = ?, llm_outputs = ?,
                                           analysis_markdown = ?, model = ?, adapter = ?,
                                           last_activity = ?
                            WHERE id = ?
                        """, ('completed', 'Analysis complete', 100,
                              analysis_html, summary_html, advisor_bio, advisor_bio_html,
                              thinking, prompt, llm_prompt, llm_outputs, analysis_markdown,
                              model, adapter,
                              datetime.now().isoformat(), job_id))
                        conn.commit()
                        logger.info(f"Job {job_id} completed successfully with summary")
                    else:
                        error_msg = f"AI Advisor returned {response.status_code}"
                        # Increment retry count for transient failures
                        current_retry = retry_count + 1
                        if current_retry < 3:
                            conn.execute("""
                                UPDATE jobs SET status = ?, error = ?, retry_count = ?, last_activity = ?
                                WHERE id = ?
                            """, ('queued', error_msg, current_retry, datetime.now().isoformat(), job_id))
                            logger.warning(f"Job {job_id} failed temporarily: {error_msg} - will retry ({current_retry}/3)")
                        else:
                            conn.execute("""
                                UPDATE jobs SET status = ?, error = ?, retry_count = ?, last_activity = ?
                                WHERE id = ?
                            """, ('failed', error_msg, current_retry, datetime.now().isoformat(), job_id))
                            logger.error(f"Job {job_id} failed permanently after {current_retry} retries: {error_msg}")
                        conn.commit()
                        
                except Exception as e:
                    error_msg = str(e)
                    # Increment retry count for transient failures
                    current_retry = retry_count + 1
                    if current_retry < 3 and "Connection refused" in error_msg:
                        conn.execute("""
                            UPDATE jobs SET status = ?, error = ?, retry_count = ?, last_activity = ?
                            WHERE id = ?
                        """, ('queued', error_msg, current_retry, datetime.now().isoformat(), job_id))
                        logger.warning(f"Job {job_id} connection failed: {e} - will retry ({current_retry}/3)")
                    else:
                        conn.execute("""
                            UPDATE jobs SET status = ?, error = ?, retry_count = ?, last_activity = ?
                            WHERE id = ?
                        """, ('failed', error_msg, current_retry, datetime.now().isoformat(), job_id))
                        logger.error(f"Job {job_id} error: {e}")
                    
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(1)


def check_and_recover_stale_jobs(db_path: str, stale_threshold_minutes: int = 5):
    """Check for jobs stuck in analyzing/processing state and recover them"""
    try:
        from datetime import datetime, timedelta
        
        with sqlite3.connect(db_path) as conn:
            # Find jobs that have been in analyzing/processing state too long
            stale_cutoff = (datetime.now() - timedelta(minutes=stale_threshold_minutes)).isoformat()
            
            cursor = conn.execute("""
                SELECT id, status, last_activity, filename, advisor, mode, COALESCE(retry_count, 0) as retry_count
                FROM jobs
                WHERE status IN ('analyzing', 'processing')
                  AND last_activity < ?
            """, (stale_cutoff,))
            
            stale_jobs = cursor.fetchall()
            
            for job in stale_jobs:
                job_id = job[0]
                status = job[1]
                last_activity = job[2]
                filename = job[3]
                retry_count = job[6]
                
                logger.warning(f"🔧 Detected stale job {job_id[:8]}... stuck in '{status}' for >5min (last activity: {last_activity})")
                
                # Mark as failed or queued for retry
                current_retry = retry_count + 1
                if current_retry < 3:
                    error_msg = f"Job timed out after 5 minutes in '{status}' state"
                    conn.execute("""
                        UPDATE jobs SET status = 'queued', error = ?, retry_count = ?, 
                                       last_activity = ?, current_step = 'Recovering from timeout...'
                        WHERE id = ?
                    """, (error_msg, current_retry, datetime.now().isoformat(), job_id))
                    logger.info(f"   ↳ Queued for retry {current_retry}/3")
                else:
                    error_msg = f"Job permanently failed after timing out (5+ minutes in '{status}' state)"
                    conn.execute("""
                        UPDATE jobs SET status = 'failed', error = ?, retry_count = ?, 
                                       last_activity = ?, current_step = 'Failed: Timeout'
                        WHERE id = ?
                    """, (error_msg, current_retry, datetime.now().isoformat(), job_id))
                    logger.error(f"   ↳ Marked as failed after {current_retry} retries")
                
                conn.commit()
                
    except Exception as e:
        logger.error(f"Error checking for stale jobs: {e}")


def monitor_queue_status(db_path: str):
    """Background monitor that logs queue status every 3-5 seconds for iOS UI monitoring"""
    logger.info("Queue status monitor started")
    
    check_counter = 0  # Check for stale jobs every 15 iterations (60 seconds)
    
    while True:
        try:
            # Periodically check for stale jobs
            check_counter += 1
            if check_counter >= 15:
                check_and_recover_stale_jobs(db_path, stale_threshold_minutes=5)
                check_counter = 0
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get queue statistics
                cursor = conn.execute("SELECT COUNT(*) as total FROM jobs")
                total = cursor.fetchone()['total']
                
                cursor = conn.execute("SELECT COUNT(*) as count FROM jobs WHERE status = 'pending'")
                pending = cursor.fetchone()['count']
                
                cursor = conn.execute("SELECT COUNT(*) as count FROM jobs WHERE status = 'queued'")
                queued = cursor.fetchone()['count']
                
                cursor = conn.execute("SELECT COUNT(*) as count FROM jobs WHERE status = 'processing'")
                processing = cursor.fetchone()['count']
                
                cursor = conn.execute("SELECT COUNT(*) as count FROM jobs WHERE status = 'analyzing'")
                analyzing = cursor.fetchone()['count']
                
                cursor = conn.execute("SELECT COUNT(*) as count FROM jobs WHERE status IN ('completed', 'done')")
                completed = cursor.fetchone()['count']
                
                cursor = conn.execute("SELECT COUNT(*) as count FROM jobs WHERE status = 'failed'")
                failed = cursor.fetchone()['count']
                
                # Log queue status
                logger.info(f"📊 Queue: {total} total | {pending} pending | {queued} queued | {processing} processing | {analyzing} analyzing | {completed} completed | {failed} failed")
                
                # Get active jobs
                cursor = conn.execute("""
                    SELECT id, filename, status, advisor, mode, current_step, llm_thinking 
                    FROM jobs 
                    WHERE status IN ('processing', 'analyzing') 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """)
                active_jobs = cursor.fetchall()
                
                if active_jobs:
                    logger.info("  Active jobs:")
                    for job in active_jobs:
                        job_id_short = job['id'][:8]
                        filename = job['filename'].split('/')[-1][:40] if job['filename'] else 'unknown'
                        mode = job['mode'] or 'baseline'
                        step = job['current_step'] or 'Starting...'
                        thinking_len = len(job['llm_thinking'] or '')
                        
                        logger.info(f"    • {job_id_short}... ({job['status']}) {filename} [{mode}]")
                        logger.info(f"      Step: {step}")
                        if thinking_len > 0:
                            thinking_preview = (job['llm_thinking'][:60] + '...') if thinking_len > 60 else job['llm_thinking']
                            logger.info(f"      🧠 Thinking ({thinking_len} chars): {thinking_preview}")
                
        except Exception as e:
            logger.error(f"Queue monitor error: {e}")
        
        time.sleep(4)  # Log status every 4 seconds


def start_job_processor(db_path: str):
    """Start background job processor thread"""
    processor = threading.Thread(
        target=process_job_worker,
        args=(db_path,),
        daemon=True
    )
    processor.start()
    
    # Also start queue status monitor
    monitor = threading.Thread(
        target=monitor_queue_status,
        args=(db_path,),
        daemon=True
    )
    monitor.start()
    
    return processor


@app.errorhandler(500)
def handle_error(e):
    """Handle errors"""
    logger.error(f"Server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Job Service for Mondrian')
    parser.add_argument('--port', type=int, default=5005, help='Service port')
    parser.add_argument('--db', default='mondrian.db', help='Database path')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    
    args = parser.parse_args()
    
    logger.info("Starting Job Service")
    logger.info(f"Port: {args.port}")
    logger.info(f"Database: {args.db}")
    
    # Use the database path from CLI argument (Docker entrypoint passes --db=/app/mondrian.db)
    # DO NOT override with config table as it may contain outdated paths
    db_path = args.db
    
    # Only try to read from config if using the default path and it's a fresh installation
    if db_path == 'mondrian.db':
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT value FROM config WHERE key = 'db_path'")
                config_db_path = cursor.fetchone()
                if config_db_path and config_db_path[0] != db_path:
                    # Config has a different path - only use it if it's also valid
                    config_path = config_db_path[0]
                    if os.path.exists(config_path):
                        db_path = config_path
                        logger.info(f"Using database path from config: {db_path}")
        except Exception as e:
            logger.debug(f"Could not read db_path from config: {e}")
    else:
        logger.info(f"Using database path from CLI argument: {db_path}")
    
    init_db(db_path)
    
    # Start background job processor
    start_job_processor(db_path)
    logger.info("Background job processor started")
    
    logger.info(f"Starting Flask server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
