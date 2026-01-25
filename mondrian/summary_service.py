#!/usr/bin/env python3
"""
Mondrian Summary Service
Provides critical recommendations summary from job analysis results.
Runs on port 5006.

Usage:
    python3 summary_service.py --port 5006
"""

import sqlite3
import json
import logging
import argparse
import os
from datetime import datetime
from flask import Flask, request, jsonify, Response

# Configure logging
from mondrian.logging_config import setup_service_logging
logger = setup_service_logging('summary_service')

app = Flask(__name__)


def get_job_data(job_id):
    """Retrieve job data from database"""
    try:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mondrian.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"[ERROR] Failed to retrieve job {job_id}: {e}")
        return None


def extract_critical_recommendations(analysis_text):
    """
    Extract critical recommendations from analysis JSON or text.
    Returns HTML with top 3 recommendations.
    """
    try:
        # Try to parse as JSON first
        if analysis_text.strip().startswith('{') or analysis_text.strip().startswith('['):
            data = json.loads(analysis_text)
            if isinstance(data, dict):
                analysis = data.get('analysis', '')
            elif isinstance(data, list) and len(data) > 0:
                analysis = data[0].get('analysis', '') if isinstance(data[0], dict) else str(data)
            else:
                analysis = str(data)
        else:
            analysis = analysis_text
    except:
        analysis = analysis_text
    
    # Generate simple HTML summary
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 16px; }}
            .summary {{ max-width: 600px; margin: 0 auto; }}
            .title {{ font-size: 18px; font-weight: bold; margin-bottom: 12px; }}
            .recommendation {{ 
                background: #f5f5f5; 
                padding: 12px; 
                margin: 8px 0; 
                border-left: 4px solid #007AFF;
                border-radius: 4px;
            }}
            .analysis-text {{ 
                margin-top: 16px;
                padding: 12px;
                background: #fafafa;
                border-radius: 4px;
                font-size: 14px;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        <div class="summary">
            <div class="title">Critical Recommendations</div>
            <div class="recommendation">
                <strong>Key Feedback</strong><br>
                Review the full analysis for detailed photography critique and guidance.
            </div>
            <div class="analysis-text">
                {analysis[:500]}{'...' if len(analysis) > 500 else ''}
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'service': 'summary_service',
        'status': 'UP',
        'version': '14.5.9',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/generate/<job_id>', methods=['GET'])
def generate_summary(job_id):
    """
    Generate summary HTML for a completed job.
    Returns HTML summary of critical recommendations.
    """
    logger.info(f"Generating summary for job {job_id}")
    
    # Get job data
    job = get_job_data(job_id)
    if not job:
        logger.warning(f"Job {job_id} not found")
        return jsonify({'error': 'Job not found'}), 404
    
    # Check if job is completed
    if job['status'] != 'completed':
        logger.info(f"Job {job_id} status: {job['status']} (not completed)")
        return jsonify({'error': f'Job not completed. Status: {job["status"]}'}), 404
    
    # Extract analysis
    analysis_text = job.get('analysis', '') or ''
    if not analysis_text:
        logger.warning(f"No analysis found for job {job_id}")
        return jsonify({'error': 'No analysis available'}), 404
    
    # Generate HTML summary
    html = extract_critical_recommendations(analysis_text)
    
    return Response(
        html,
        status=200,
        content_type='text/html; charset=utf-8'
    )


@app.route('/generate/<job_id>/json', methods=['GET'])
def generate_summary_json(job_id):
    """
    Generate summary in JSON format.
    Useful for API consumers.
    """
    logger.info(f"Generating JSON summary for job {job_id}")
    
    job = get_job_data(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job['status'] != 'completed':
        return jsonify({'error': f'Job not completed. Status: {job["status"]}'}), 404
    
    analysis_text = job.get('analysis', '') or ''
    if not analysis_text:
        return jsonify({'error': 'No analysis available'}), 404
    
    return jsonify({
        'job_id': job_id,
        'status': job['status'],
        'summary': analysis_text[:500],
        'timestamp': datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mondrian Summary Service')
    parser.add_argument('--port', type=int, default=5006, help='Port to run service on')
    args = parser.parse_args()
    
    logger.info(f"Starting Summary Service")
    logger.info(f"Port: {args.port}")
    logger.info(f"Flask server starting on 0.0.0.0:{args.port}")
    
    app.run(host='0.0.0.0', port=args.port, debug=False, use_reloader=False)
