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

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# AI Advisor service URL
AI_ADVISOR_URL = "http://127.0.0.1:5100"

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
    
    def create_job(self, advisor: str, mode: str, image_path: str) -> str:
        """Create a new job"""
        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (id, filename, advisor, mode, status, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (job_id, image_path, advisor, mode, 'pending', now, now))
            conn.commit()
        
        logger.info(f"Created job {job_id}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT id, filename, status, advisor, mode, created_at, current_step, progress_percentage, enable_rag, 
                          prompt, llm_prompt, analysis_markdown, llm_thinking, analysis_html, advisor_bio, llm_outputs 
                   FROM jobs WHERE id = ?""",
                (job_id,)
            )
            row = cursor.fetchone()
        
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
            'llm_outputs': row[15] or ''
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
                SELECT id, filename, status, advisor, mode, created_at FROM jobs
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
                'created_at': row[5]
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
        "status": "healthy",
        "service": "job_service",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/advisors', methods=['GET'])
def get_advisors():
    """Get list of available advisors"""
    try:
        db_path = job_db.db_path if job_db else "mondrian.db"
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, name, bio, focus_areas FROM advisors ORDER BY id"
            )
            rows = cursor.fetchall()
        
        advisors = []
        for row in rows:
            advisor = {
                "id": row["id"],
                "name": row["name"],
                "bio": row["bio"] if row["bio"] else "",
                "focus_areas": []
            }
            
            # Parse focus_areas JSON if it exists
            if row["focus_areas"]:
                try:
                    advisor["focus_areas"] = json.loads(row["focus_areas"])
                except (json.JSONDecodeError, TypeError):
                    advisor["focus_areas"] = []
            
            advisors.append(advisor)
        
        return jsonify({
            "advisors": advisors,
            "count": len(advisors),
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching advisors: {e}")
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
        enable_rag = request.form.get('enable_rag', 'false').lower() in ('true', '1', 'yes')
        auto_analyze = request.form.get('auto_analyze', 'false').lower() in ('true', '1', 'yes')
        
        # Save file - extract just the basename to avoid path traversal issues
        import uuid
        from os.path import basename
        safe_filename = basename(file.filename)  # Extract just the filename, not the path
        unique_filename = f"{uuid.uuid4()}_{safe_filename}"
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        filepath = upload_dir / unique_filename
        file.save(str(filepath))
        
        # Create job
        job_id = job_db.create_job(advisor, mode, str(filepath))
        
        # Format response - keep job_id clean for URLs, add mode to display_id
        display_job_id = f"{job_id} ({mode})"
        base_url = f"http://{request.host.split(':')[0]}:5005"
        
        return jsonify({
            "job_id": job_id,
            "display_job_id": display_job_id,
            "filename": file.filename,
            "advisor": advisor,
            "advisors_used": [advisor],
            "status": "queued",
            "mode": mode,
            "enable_rag": enable_rag,
            "status_url": f"{base_url}/status/{job_id}",
            "stream_url": f"{base_url}/stream/{job_id}",
            "analysis_url": f"{base_url}/analysis/{job_id}"
        }), 201
    
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
            
            job_id_full = job.get('id', 'N/A')
            job_id_short = job_id_full[:8]
            html += f"""
                    <tr>
                        <td><span class="job-id"><a href="/jobs/{job_id_full}?view=detail" style="color: #666; text-decoration: none;">{job_id_short}...</a></span></td>
                        <td>{job.get('filename', 'N/A')}</td>
                        <td>{job.get('advisor', 'N/A')}</td>
                        <td><span class="mode-badge">{mode}</span></td>
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
    """Get job details - returns JSON or HTML based on view parameter"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    job = job_db.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    # Check if requesting HTML detail view
    view = request.args.get('view', 'json')
    if view == 'detail':
        return render_job_detail_html(job)
    
    return jsonify(job), 200


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
    
    def generate():
        """Generator function that yields SSE events"""
        import time
        from datetime import datetime
        
        last_status = job.get('status')
        last_progress = job.get('progress_percentage', 0)
        
        while True:
            job_data = job_db.get_job(job_id)
            if not job_data:
                break
            
            current_status = job_data.get('status')
            current_progress = job_data.get('progress_percentage', 0)
            
            # Send status update if changed
            if current_status != last_status or current_progress != last_progress:
                event_data = {
                    'status': current_status,
                    'progress_percentage': current_progress,
                    'current_step': job_data.get('current_step', ''),
                    'llm_thinking': job_data.get('llm_thinking', '')
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                last_status = current_status
                last_progress = current_progress
            
            # Check if job is complete
            if current_status in ['completed', 'failed']:
                # Send final event
                final_event = {
                    'type': 'done',
                    'status': current_status,
                    'job_id': job_id,
                    'analysis_html': job_data.get('analysis_html', ''),
                    'advisor_bio': job_data.get('advisor_bio', '')
                }
                yield f"data: {json.dumps(final_event)}\n\n"
                break
            
            time.sleep(1)  # Check every second
    
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
    """Get analysis results for a job"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    job = job_db.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    # Try to extract summary from llm_outputs if available
    summary = ''
    llm_outputs = job.get('llm_outputs', '')
    if llm_outputs:
        try:
            outputs_data = json.loads(llm_outputs)
            summary = outputs_data.get('summary', '')
        except:
            pass
    
    return {
        'job_id': job_id,
        'status': job.get('status'),
        'analysis_html': job.get('analysis_html', ''),
        'advisor_bio': job.get('advisor_bio', ''),
        'summary': summary,
        'summary_html': job.get('summary_html', '')
    }


@app.route('/summary/<job_id>', methods=['GET'])
def get_summary(job_id: str):
    """
    Get a critical recommendations summary (transparent proxy to summary service on port 5006).
    Returns HTML view of only the most important recommendations.
    """
    try:
        # Forward request to summary service on port 5006
        summary_url = f"http://127.0.0.1:5006/generate/{job_id}"
        resp = requests.get(summary_url, timeout=30)
        # Return response with same status code and content type
        return Response(
            resp.content,
            status=resp.status_code,
            headers={'Content-Type': resp.headers.get('Content-Type', 'text/html; charset=utf-8')}
        )
    except Exception as e:
        logger.error(f"[ERROR] Summary service proxy failed: {e}")
        raise


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
    
    while True:
        try:
            with sqlite3.connect(db_path) as conn:
                # Find pending jobs
                cursor = conn.execute("""
                    SELECT id, filename, advisor, mode FROM jobs 
                    WHERE status IN ('pending', 'queued')
                    LIMIT 1
                """)
                job = cursor.fetchone()
                
                if not job:
                    time.sleep(1)
                    continue
                
                job_id, filename, advisor, mode = job
                logger.info(f"Processing job {job_id}: {advisor} ({mode})")
                
                # Update job status
                conn.execute("""
                    UPDATE jobs SET status = ?, last_activity = ?
                    WHERE id = ?
                """, ('analyzing', datetime.now().isoformat(), job_id))
                conn.commit()
                
                # Call AI Advisor service
                try:
                    with open(filename, 'rb') as f:
                        response = requests.post(
                            f"{AI_ADVISOR_URL}/analyze",
                            files={'image': f},
                            data={
                                'advisor': advisor,
                                'mode': mode,
                                'enable_rag': 'false'
                            },
                            timeout=300,
                            stream=True
                        )
                    
                    if response.status_code == 200:
                        analysis_data = response.json()
                        
                        # Extract all analysis fields
                        analysis_html = analysis_data.get('analysis_html', '')
                        advisor_bio = analysis_data.get('advisor_bio', '')
                        thinking = analysis_data.get('llm_thinking', '')
                        prompt = analysis_data.get('prompt', '')
                        llm_prompt = analysis_data.get('llm_prompt', '')
                        full_response = analysis_data.get('full_response', '')
                        summary = analysis_data.get('summary', '')
                        
                        # Prepare llm_outputs as JSON string
                        llm_outputs = json.dumps({
                            'prompt': prompt,
                            'response': full_response,
                            'summary': summary,
                            'model': analysis_data.get('model', ''),
                            'timestamp': analysis_data.get('timestamp', '')
                        })
                        
                        # Create markdown summary for analysis_markdown field
                        analysis_markdown = f"""# {advisor.title()} Analysis\n\n## Summary\n{summary}\n\n## Full Analysis\n{full_response}"""
                        
                        # Update job with all results including summary
                        conn.execute("""
                            UPDATE jobs SET status = ?, analysis_html = ?, 
                                           advisor_bio = ?, llm_thinking = ?,
                                           prompt = ?, llm_prompt = ?, llm_outputs = ?,
                                           analysis_markdown = ?,
                                           last_activity = ?
                            WHERE id = ?
                        """, ('completed', analysis_html, advisor_bio, thinking,
                              prompt, llm_prompt, llm_outputs, analysis_markdown,
                              datetime.now().isoformat(), job_id))
                        conn.commit()
                        logger.info(f"Job {job_id} completed successfully with summary")
                    else:
                        error_msg = f"AI Advisor returned {response.status_code}"
                        conn.execute("""
                            UPDATE jobs SET status = ?, error = ?, last_activity = ?
                            WHERE id = ?
                        """, ('failed', error_msg, datetime.now().isoformat(), job_id))
                        conn.commit()
                        logger.error(f"Job {job_id} failed: {error_msg}")
                        
                except Exception as e:
                    error_msg = str(e)
                    conn.execute("""
                        UPDATE jobs SET status = ?, error = ?, last_activity = ?
                        WHERE id = ?
                    """, ('failed', error_msg, datetime.now().isoformat(), job_id))
                    conn.commit()
                    logger.error(f"Job {job_id} error: {e}")
                    
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(1)


def start_job_processor(db_path: str):
    """Start background job processor thread"""
    processor = threading.Thread(
        target=process_job_worker,
        args=(db_path,),
        daemon=True
    )
    processor.start()
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
    
    init_db(args.db)
    
    # Start background job processor
    start_job_processor(args.db)
    logger.info("Background job processor started")
    
    logger.info(f"Starting Flask server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
