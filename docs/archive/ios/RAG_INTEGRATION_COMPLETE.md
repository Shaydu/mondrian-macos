# RAG System Integration Complete ✅

## Overview
The RAG (Retrieval-Augmented Generation) system has been successfully integrated into the Mondrian monitoring service and will now start automatically with the main Mondrian system.

## Services Added to Monitoring

### 1. Caption Service (Port 5200)
- **Script**: `caption_service.py`
- **Health URL**: `http://127.0.0.1:5200/health`
- **Purpose**: Generates image captions using MLX vision model (Qwen3-VL-4B-Instruct-MLX)
- **Dependencies**: None
- **Status**: Auto-start enabled ✅

### 2. Embedding Service (Port 5300)
- **Script**: `embedding_service.py`
- **Health URL**: `http://127.0.0.1:5300/health`
- **Purpose**: Converts captions to 384-dimensional vectors using sentence-transformers
- **Dependencies**: None
- **Status**: Auto-start enabled ✅

### 3. RAG Service (Port 5400)
- **Script**: `rag_service.py`
- **Health URL**: `http://127.0.0.1:5400/health`
- **Purpose**: Orchestrates indexing and semantic search operations
- **Dependencies**: Caption Service, Embedding Service
- **Arguments**:
  - `--db ../mondrian.db`
  - `--caption_url http://127.0.0.1:5200`
  - `--embedding_url http://127.0.0.1:5300`
- **Status**: Auto-start enabled ✅

## Service Startup Order

The monitoring service now starts services in the following dependency order:

1. **Caption Service** (no dependencies)
2. **Embedding Service** (no dependencies)
3. **RAG Service** (depends on Caption & Embedding)
4. **AI Advisor Service** (existing)
5. **Job Service** (existing)

Each service has a 2-3 second grace period after startup to ensure proper initialization.

## Monitoring Features

All RAG services are now monitored with:

- **Health Checks**: Automatic health monitoring every 30 seconds
- **Auto-Restart**: Services automatically restart if health checks fail
- **Process Management**: Ensures single instance of each service
- **Graceful Shutdown**: Proper cleanup on monitoring service stop

## Configuration Changes

### Updated Files
- **File**: `mondrian/monitoring_service.py`
- **Version**: `v2.4-MONITORING-RAG`
- **Changes**:
  - Added 3 new services to `DEFAULT_CONFIG`
  - Updated `start_services()` method to include RAG services
  - Proper dependency ordering for service startup

## Testing the Integration

### Start the Monitoring Service
```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 monitoring_service.py
```

### Verify All Services Are Running
```bash
# Check health of all services
curl http://127.0.0.1:5200/health  # Caption Service
curl http://127.0.0.1:5300/health  # Embedding Service
curl http://127.0.0.1:5400/health  # RAG Service
curl http://127.0.0.1:5100/health  # AI Advisor
curl http://127.0.0.1:5005/health  # Job Service
curl http://127.0.0.1:5007/health  # Monitoring Service
```

### Test RAG Functionality

#### Index an Image
```bash
curl -X POST http://127.0.0.1:5400/index \
  -H "Content-Type: application/json" \
  -d '{"job_id": "test-001", "image_path": "source/my-image.jpg"}'
```

#### Search for Similar Images
```bash
curl -X POST http://127.0.0.1:5400/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sunset over mountains", "top_k": 10}'
```

## Database Schema

The RAG system uses the `image_captions` table in `mondrian.db`:

```sql
CREATE TABLE image_captions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    caption TEXT NOT NULL,
    embedding BLOB NOT NULL,  -- 384-dimensional vector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, image_path)
);
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         Mondrian Monitoring Service v2.4            │
│                  (Port 5007)                        │
└─────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬──────────────┐
        │               │               │              │
        ▼               ▼               ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────┐
│   Caption    │ │  Embedding   │ │AI Advisor  │ │   Job    │
│   Service    │ │   Service    │ │  Service   │ │ Service  │
│  (Port 5200) │ │ (Port 5300)  │ │(Port 5100) │ │(Port 5005)│
└──────┬───────┘ └──────┬───────┘ └────────────┘ └──────────┘
       │                │
       └────────┬───────┘
                ▼
        ┌──────────────┐
        │ RAG Service  │
        │ (Port 5400)  │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ mondrian.db  │
        │image_captions│
        └──────────────┘
```

## Benefits of Integration

1. **Automatic Startup**: All RAG services start automatically when Mondrian starts
2. **Health Monitoring**: Continuous health checks ensure services are running
3. **Auto-Recovery**: Services automatically restart if they crash or become unresponsive
4. **Centralized Management**: Single monitoring service manages all components
5. **Dependency Handling**: Services start in the correct order based on dependencies
6. **Production Ready**: Robust error handling and logging for production use

## Next Steps

The RAG system is now fully integrated and ready for use. You can:

1. **Test the System**: Use the test commands above to verify functionality
2. **Index Images**: Start indexing images from your Mondrian jobs
3. **Semantic Search**: Use natural language queries to find similar images
4. **Monitor Performance**: Check the monitoring dashboard at `http://127.0.0.1:5007/monitor`

## Files Modified

- `mondrian/monitoring_service.py` - Added RAG services to configuration and startup sequence

## Files Created (Previously)

- `mondrian/caption_service.py` - MLX-powered caption generation
- `mondrian/embedding_service.py` - Text embedding generation
- `mondrian/rag_service.py` - RAG orchestration
- `mondrian/migrations/add_image_captions.sql` - Database schema
- `mondrian/migrations/apply_image_captions.py` - Migration script
- `mondrian/test_rag_system.py` - Integration tests

---

**Status**: ✅ Complete and Ready for Production
**Date**: 2026-01-08
**Version**: Mondrian v2.4-MONITORING-RAG
