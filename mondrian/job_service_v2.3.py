#!/usr/bin/env python3
"""
Job Service for Mondrian on Linux
Manages background processing of analysis jobs
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

from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class JobDatabase:
    """Simple job tracking database"""
    
    def __init__(self, db_path: str = "mondrian.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    status TEXT,
                    advisor TEXT,
                    mode TEXT,
                    image_path TEXT,
                    result JSON,
                    error TEXT
                )
            """)
            conn.commit()
    
    def create_job(self, advisor: str, mode: str, image_path: str) -> str:
        """Create a new job"""
        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO jobs (id, created_at, updated_at, status, advisor, mode, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (job_id, now, now, 'pending', advisor, mode, image_path))
            conn.commit()
        
        logger.info(f"Created job {job_id}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, created_at, updated_at, status, advisor, mode, image_path, result, error FROM jobs WHERE id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'created_at': row[1],
            'updated_at': row[2],
            'status': row[3],
            'advisor': row[4],
            'mode': row[5],
            'image_path': row[6],
            'result': json.loads(row[7]) if row[7] else None,
            'error': row[8]
        }
    
    def update_job(self, job_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update job status"""
        now = datetime.now().isoformat()
        result_json = json.dumps(result) if result else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE jobs SET updated_at = ?, status = ?, result = ?, error = ?
                WHERE id = ?
            """, (now, status, result_json, error, job_id))
            conn.commit()
        
        logger.info(f"Updated job {job_id} to status {status}")
    
    def list_jobs(self, limit: int = 100) -> list:
        """List recent jobs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, created_at, updated_at, status, advisor, mode FROM jobs
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        
        return [
            {
                'id': row[0],
                'created_at': row[1],
                'updated_at': row[2],
                'status': row[3],
                'advisor': row[4],
                'mode': row[5]
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


@app.route('/jobs', methods=['GET'])
def list_jobs():
    """List recent jobs"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    limit = request.args.get('limit', 100, type=int)
    jobs = job_db.list_jobs(limit=limit)
    
    return jsonify({
        "jobs": jobs,
        "count": len(jobs),
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id: str):
    """Get job details"""
    if not job_db:
        return jsonify({"error": "Database not initialized"}), 503
    
    job = job_db.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(job), 200


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
    
    logger.info(f"Starting Flask server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
