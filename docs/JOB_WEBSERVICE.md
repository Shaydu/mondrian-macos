# Job Webservice Documentation

## Overview

The Mondrian Job Webservice is a Flask-based web application that provides a web interface and REST API for viewing, monitoring, and managing photography analysis jobs processed by the Mondrian AI backend.

**Service Name**: Mondrian Photography Job Service
**Version**: 2.3-DB-FIXED
**Default Port**: 5005
**Framework**: Flask (Python)
**Database**: SQLite (`mondrian.db`)

## Status

✅ **Currently Running**
- Process ID: Check with `ps aux | grep job_service`
- Port: 5005 (listening)
- Health: http://localhost:5005/health

## Quick Access

### Web Interface (HTML)
- **Jobs List**: http://localhost:5005/jobs?format=html
- **Monitoring Dashboard**: http://localhost:5007/monitor (if monitoring service is running)

### API Endpoints (JSON)
- **Service Info**: http://localhost:5005/
- **Health Check**: http://localhost:5005/health
- **Jobs List**: http://localhost:5005/jobs

## Starting the Service

### Option 1: Full System Startup (Recommended)
```bash
./mondrian.sh
```
This starts all services including:
- Job Service (port 5005)
- AI Advisor Service (port 5100)
- RAG Service (port 5400)
- Caption Service (port 5200)
- Embedding Service (port 5300)
- Monitoring Service (port 5007)

### Option 2: Job Service Only
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3.12 job_service_v2.3.py --port 5005
```

### Option 3: Using Service Manager
```bash
cd /Users/shaydu/dev/mondrian-macos/scripts
python3.12 start_services.py
```

## Viewing Job Information

### 1. Jobs List View

**HTML Interface** (for humans):
```
http://localhost:5005/jobs?format=html
```

Features:
- Dark-themed UI with status counts
- RAG vs Baseline breakdown
- Sortable job table
- Filtering by status, advisor, RAG mode
- Real-time job progress updates
- Click-through to individual job details

**JSON API** (for programmatic access):
```bash
curl http://localhost:5005/jobs
```

Returns last 100 jobs with:
- Job ID (UUID)
- Filename
- Advisor name
- Status (queued, processing, analyzing, finalizing, done, error)
- Creation timestamp
- RAG enabled flag
- Critical recommendations

### 2. Individual Job Details

**Job Status** (includes thinking output):
```
http://localhost:5005/status/<job_id>
```

**Full Analysis Results**:
```
http://localhost:5005/analysis/<job_id>
```

**LLM Prompts and Outputs**:
```
http://localhost:5005/llm-outputs/<job_id>
```

**Specific Prompt for Job**:
```
http://localhost:5005/job/<job_id>/prompt
```

**LLM Thinking Process**:
```
http://localhost:5005/job/<job_id>/thinking
```

**Summary View**:
```
http://localhost:5005/summary/<job_id>
```

**Complete Job Data Package**:
```
http://localhost:5005/job/<job_id>/full-data
```

### 3. Real-time Job Monitoring

**SSE Stream** (Server-Sent Events):
```
http://localhost:5005/stream/<job_id>
```

This endpoint provides real-time updates as the job processes, including:
- Current processing step
- Step phase (dimensional analysis, RAG retrieval, etc.)
- Progress percentage
- Status changes
- Error messages

## API Endpoints Reference

### Core Endpoints

| Method | Endpoint | Description | Response Format |
|--------|----------|-------------|-----------------|
| GET | `/` | Service info and endpoint listing | JSON |
| GET | `/health` | Health check | JSON |
| GET | `/jobs` | List all jobs (last 100) | JSON/HTML |
| GET | `/status/<job_id>` | Job status with thinking output | JSON |
| GET | `/analysis/<job_id>` | Full analysis results | JSON |
| POST | `/upload` | Submit new analysis job | JSON |

### LLM Output Endpoints

| Method | Endpoint | Description | Response Format |
|--------|----------|-------------|-----------------|
| GET | `/llm-outputs/<job_id>` | All LLM prompts and outputs | JSON |
| GET | `/job/<job_id>/prompt` | Stored prompts for job | JSON |
| GET | `/job/<job_id>/thinking` | LLM thinking output | JSON/Text |
| GET | `/summary/<job_id>` | Analysis summary view | HTML |
| GET | `/job/<job_id>/full-data` | Complete job data package | JSON |

### Monitoring Endpoints

| Method | Endpoint | Description | Response Format |
|--------|----------|-------------|-----------------|
| GET | `/stream/<job_id>` | Real-time job progress (SSE) | Event Stream |
| GET | `/advisors` | List available advisors | JSON |

## Job Data Structure

### Job Record Fields

Jobs are stored in SQLite database with the following schema:

```python
{
    "id": "UUID",                      # Unique job identifier
    "filename": "string",              # Original image filename
    "advisor": "string",               # Advisor name (e.g., "ansel")
    "status": "string",                # queued|processing|analyzing|finalizing|done|error
    "created_at": "timestamp",         # Job creation time
    "last_activity": "timestamp",      # Last update time
    "completed_at": "timestamp",       # Completion time (if done)
    "enable_rag": "boolean",           # RAG mode enabled
    "critical_recommendations": "text", # Analysis output
    "llm_thinking": "text",            # Model thinking process
    "current_step": "string",          # Current processing step
    "step_phase": "string",            # Detailed phase info
    "error_message": "string"          # Error details (if failed)
}
```

## Viewing LLM Prompts and Outputs

### Method 1: Direct API Call

Get all LLM interactions for a job:
```bash
curl http://localhost:5005/llm-outputs/<job_id> | jq
```

### Method 2: Individual Components

**Get the prompt**:
```bash
curl http://localhost:5005/job/<job_id>/prompt
```

**Get the thinking output**:
```bash
curl http://localhost:5005/job/<job_id>/thinking
```

### Method 3: Full Job Data

Complete package with all metadata:
```bash
curl http://localhost:5005/job/<job_id>/full-data | jq
```

### Method 4: Web Interface

1. Open jobs list: http://localhost:5005/jobs?format=html
2. Click on a job ID
3. View sections:
   - Summary View (formatted analysis)
   - Detail View (complete data)
   - Thinking Output (LLM reasoning)
   - Prompts (system + user prompts)

## Summary vs Detail Views

### Summary View
**URL**: `/summary/<job_id>`

Provides:
- High-level analysis highlights
- Critical recommendations
- Advisor attribution
- RAG mode indicator
- Key metrics and scores

Designed for quick review and comparison.

### Detail View
**URL**: `/analysis/<job_id>` or `/job/<job_id>/full-data`

Provides:
- Complete dimensional profiles
- Full LLM thinking process
- All prompts and outputs
- Reference images (if RAG-enabled)
- Step-by-step processing log
- Error traces (if applicable)
- Metadata and timing information

Designed for deep analysis and debugging.

## Job Status Lifecycle

```
queued → processing → analyzing → finalizing → done
                                              ↘ error
```

1. **queued**: Job submitted, waiting for processor
2. **processing**: Image loaded, preparing for analysis
3. **analyzing**: LLM actively analyzing image
4. **finalizing**: Generating outputs and reports
5. **done**: Successfully completed
6. **error**: Failed (see error_message field)

## RAG (Retrieval-Augmented Generation) Mode

Jobs can be submitted with RAG enabled or disabled:

- **RAG Enabled**: Uses dimensional profile comparison with reference images
- **Baseline**: Direct analysis without reference retrieval

The jobs list view shows RAG vs Baseline breakdown for comparison studies.

### Viewing RAG-specific Data

For RAG-enabled jobs:
```
GET /job/<job_id>/full-data
```

Includes:
- Retrieved reference images
- Similarity scores
- Dimensional profile comparisons
- Enhanced context in prompts

## Monitoring Service

**Port**: 5007
**Dashboard**: http://localhost:5007/monitor

Additional monitoring interface with:
- Active jobs list
- Service health checks
- Real-time statistics
- Auto-refresh every 10 seconds

### Monitoring Endpoints

| Endpoint | Description |
|----------|-------------|
| `/health` | Monitoring service health |
| `/jobs` | Active jobs list |
| `/stats` | Detailed statistics |
| `/monitor` | Interactive HTML dashboard |

## Troubleshooting

### Service Not Running

Check if service is running:
```bash
ps aux | grep job_service
```

Check if port is in use:
```bash
lsof -i :5005
```

### Start Service

```bash
cd /Users/shaydu/dev/mondrian-macos
./mondrian.sh
```

Or restart:
```bash
./mondrian.sh --restart
```

### Check Logs

Service logs are written to stdout/stderr. If started via script:
```bash
tail -f logs/job_service.log  # if logging to file
```

Or check process output:
```bash
ps aux | grep job_service  # get PID
tail -f /proc/<PID>/fd/1   # on Linux
```

### Database Issues

Check database:
```bash
sqlite3 mondrian.db "SELECT COUNT(*) FROM jobs;"
sqlite3 mondrian.db "SELECT id, filename, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;"
```

## Performance Considerations

- **Job List Limit**: Returns last 100 jobs by default
- **Database**: SQLite is single-file, suitable for moderate load
- **Concurrency**: Serial job processing (one at a time)
- **Timeout**: Jobs auto-marked as error after inactivity threshold
- **Streaming**: Use SSE endpoints for real-time updates vs polling

## Security Notes

- Service runs on localhost (127.0.0.1) by default
- No authentication implemented (local development use)
- Direct file system access for analysis results
- For production use, add:
  - API authentication
  - HTTPS/TLS
  - Rate limiting
  - Input validation
  - CORS configuration

## Related Services

The Job Service coordinates with:

- **AI Advisor Service** (port 5100): Handles actual image analysis
- **RAG Service** (port 5400): Provides retrieval-augmented generation
- **Caption Service** (port 5200): Generates image captions
- **Embedding Service** (port 5300): Creates dimensional embeddings
- **Monitoring Service** (port 5007): Provides monitoring dashboard

## File Locations

- **Service Code**: `/Users/shaydu/dev/mondrian-macos/mondrian/job_service_v2.3.py`
- **Database**: `/Users/shaydu/dev/mondrian-macos/mondrian.db`
- **Analysis Output**: `/Users/shaydu/dev/mondrian-macos/analysis_output/`
- **Startup Script**: `/Users/shaydu/dev/mondrian-macos/mondrian.sh`

## Additional Documentation

- [API Reference](./API.md)
- [RAG API Reference](./RAG_API_REFERENCE.md)
- [Status and Progress Explained](./STATUS_AND_PROGRESS_EXPLAINED.md)
- [Startup Fix README](../STARTUP_FIX_README.md)

## Quick Command Reference

```bash
# Check service status
curl http://localhost:5005/health

# List recent jobs (JSON)
curl http://localhost:5005/jobs

# List jobs (HTML in browser)
open http://localhost:5005/jobs?format=html

# Get job details
curl http://localhost:5005/status/<job_id>

# View LLM outputs
curl http://localhost:5005/llm-outputs/<job_id>

# Monitor job in real-time
curl http://localhost:5005/stream/<job_id>

# Submit new job
curl -X POST -F "file=@image.jpg" -F "advisor=ansel" http://localhost:5005/upload
```

## Version History

- **v2.3-DB-FIXED**: Current version with database integration
- **v2.2**: Previous iteration
- **v1.x**: Original implementation

---

**Last Updated**: 2026-01-13
**Service Port**: 5005
**Status**: ✅ Running and Operational
