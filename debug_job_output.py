#!/usr/bin/env python3
"""
Debug script to fetch latest job and write full output to HTML file
"""
import sqlite3
import json
import sys
from datetime import datetime

def get_latest_job(db_path="mondrian.db"):
    """Fetch the latest completed job from database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get latest job
    cursor.execute("""
        SELECT id, filename, advisor, status, analysis_markdown, llm_outputs, created_at
        FROM jobs
        ORDER BY created_at DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if not row:
        print("[ERROR] No jobs found in database")
        return None

    return dict(row)

def write_job_to_html(job_data, output_file="debug_job_latest.html"):
    """Write job data to HTML file for inspection"""

    job_id = job_data["id"]
    filename = job_data["filename"]
    advisor = job_data["advisor"]
    status = job_data["status"]
    analysis_html = job_data["analysis_markdown"]
    created_at = job_data["created_at"]

    # Parse LLM outputs if available
    llm_outputs = {}
    if job_data["llm_outputs"]:
        try:
            llm_outputs = json.loads(job_data["llm_outputs"])
        except json.JSONDecodeError:
            llm_outputs = {"error": "Could not parse LLM outputs"}

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Debug Output - {job_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            padding: 20px;
            background: #000000;
            color: #ffffff;
            line-height: 1.6;
        }}

        h1 {{
            color: #007AFF;
            margin-bottom: 20px;
            font-size: 28px;
        }}

        h2 {{
            color: #34C759;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 20px;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }}

        .job-metadata {{
            background: #1c1c1e;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            font-size: 14px;
        }}

        .metadata-item {{
            margin-bottom: 8px;
        }}

        .metadata-label {{
            color: #98989d;
            font-weight: bold;
        }}

        .metadata-value {{
            color: #d1d1d6;
            word-break: break-all;
        }}

        .section {{
            background: #1c1c1e;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}

        .analysis-content {{
            background: #0a0a0a;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #007AFF;
            overflow-x: auto;
        }}

        .llm-output {{
            background: #0a0a0a;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #34C759;
            overflow-x: auto;
            margin-bottom: 15px;
        }}

        .llm-output-title {{
            color: #34C759;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .llm-output-content {{
            color: #d1d1d6;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        img {{
            max-width: 100%;
            height: auto;
            margin: 20px 0;
            border-radius: 8px;
        }}

        pre {{
            background: #0a0a0a;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            color: #d1d1d6;
            font-size: 12px;
        }}

        .warning {{
            background: #663300;
            border-left: 3px solid #FF9500;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            color: #FFD60A;
        }}
    </style>
</head>
<body>
    <h1>Job Debug Output</h1>

    <div class="warning">
        <strong>⚠️ Debug Output:</strong> This file contains the complete raw output from the database for inspection.
    </div>

    <div class="job-metadata">
        <div class="metadata-item">
            <span class="metadata-label">Job ID:</span>
            <span class="metadata-value">{job_id}</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Filename:</span>
            <span class="metadata-value">{filename}</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Advisor:</span>
            <span class="metadata-value">{advisor}</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Status:</span>
            <span class="metadata-value">{status}</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Created:</span>
            <span class="metadata-value">{created_at}</span>
        </div>
    </div>

    <h2>📊 Analysis HTML Output (Raw from DB)</h2>
    <div class="section analysis-content">
        {analysis_html if analysis_html else '<p style="color: #98989d;">No analysis HTML available</p>'}
    </div>

    <h2>🔍 LLM Outputs by Advisor</h2>
    <div class="section">
        {_format_llm_outputs(llm_outputs)}
    </div>

</body>
</html>"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ Job output written to: {output_file}")
    print(f"   Job ID: {job_id}")
    print(f"   Status: {status}")
    return output_file

def _format_llm_outputs(llm_outputs):
    """Format LLM outputs for display"""
    if not llm_outputs or isinstance(llm_outputs, dict) and "error" in llm_outputs:
        return '<p style="color: #98989d;">No LLM outputs available</p>'

    html_parts = []

    if isinstance(llm_outputs, dict):
        for advisor_name, output in llm_outputs.items():
            html_parts.append(f"""
            <div class="llm-output">
                <div class="llm-output-title">📝 {advisor_name}</div>
                <div class="llm-output-content">{output}</div>
            </div>
            """)

    return "\n".join(html_parts) if html_parts else '<p style="color: #98989d;">No LLM outputs available</p>'

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "mondrian.db"

    print(f"[INFO] Fetching latest job from {db_path}...")
    job = get_latest_job(db_path)

    if job:
        output_file = write_job_to_html(job)
        print(f"[INFO] Open in browser: {output_file}")
    else:
        print("[ERROR] No job data found")
        sys.exit(1)
