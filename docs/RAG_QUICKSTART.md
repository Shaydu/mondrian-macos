# RAG System Quick Start Guide

## Starting the System

Simply start the Mondrian monitoring service - all RAG services will start automatically:

```bash
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 monitoring_service.py
```

Or with the web dashboard:

```bash
python3 monitoring_service.py --web --port 5007
```

Then visit: http://127.0.0.1:5007/monitor

## Service Endpoints

| Service | Port | Health Check |
|---------|------|--------------|
| Caption Service | 5200 | http://127.0.0.1:5200/health |
| Embedding Service | 5300 | http://127.0.0.1:5300/health |
| RAG Service | 5400 | http://127.0.0.1:5400/health |
| AI Advisor | 5100 | http://127.0.0.1:5100/health |
| Job Service | 5005 | http://127.0.0.1:5005/health |
| Monitoring | 5007 | http://127.0.0.1:5007/health |

## Common Operations

### 1. Index a Single Image

```bash
curl -X POST http://127.0.0.1:5400/index \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-123",
    "image_path": "source/architecture-diagram.jpg"
  }'
```

**Response:**
```json
{
  "status": "success",
  "job_id": "job-123",
  "image_path": "source/architecture-diagram.jpg",
  "caption": "A detailed architecture diagram showing...",
  "indexed_at": "2026-01-08T12:34:56Z"
}
```

### 2. Search for Similar Images

```bash
curl -X POST http://127.0.0.1:5400/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "sunset over mountains",
    "top_k": 10
  }'
```

**Response:**
```json
{
  "status": "success",
  "query": "sunset over mountains",
  "results": [
    {
      "job_id": "job-456",
      "image_path": "source/mountain-sunset.jpg",
      "caption": "Beautiful sunset over mountain range...",
      "similarity": 0.92,
      "created_at": "2026-01-08T10:15:30Z"
    },
    ...
  ],
  "count": 10
}
```

### 3. Generate Caption Only

```bash
curl -X POST http://127.0.0.1:5200/caption \
  -H "Content-Type: application/json" \
  -d '{
    "image_path": "source/my-image.jpg"
  }'
```

### 4. Generate Embedding Only

```bash
curl -X POST http://127.0.0.1:5300/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "A beautiful sunset over the mountains"
  }'
```

## Integration with Mondrian Jobs

The RAG system can be used with Mondrian's job processing pipeline:

1. **After image generation**: Index the generated image for future search
2. **Before rendering**: Search for similar past renders to optimize settings
3. **Portfolio management**: Find images by semantic description

### Example: Auto-index after job completion

```python
import requests

def on_job_complete(job_id, output_image):
    """Index image after successful job completion"""
    response = requests.post(
        "http://127.0.0.1:5400/index",
        json={
            "job_id": job_id,
            "image_path": output_image
        }
    )
    return response.json()
```

## Monitoring & Debugging

### Check Service Status

```bash
# All services status
curl http://127.0.0.1:5007/stats | jq

# Individual service health
curl http://127.0.0.1:5400/health | jq
```

### View Logs

```bash
# Monitoring service logs
tail -f logs/monitoring_service.log

# Individual service logs (if running standalone)
tail -f logs/caption_service.log
tail -f logs/embedding_service.log
tail -f logs/rag_service.log
```

### Check Database

```bash
sqlite3 ../mondrian.db "SELECT COUNT(*) FROM image_captions;"
sqlite3 ../mondrian.db "SELECT job_id, caption FROM image_captions LIMIT 5;"
```

## Performance Notes

- **Caption Generation**: ~2-5 seconds per image (MLX on Apple Silicon)
- **Embedding Generation**: ~100ms per caption
- **Search**: ~50ms for 1000 images
- **Database**: 384-dim vectors stored as BLOB (~1.5KB per image)

## Troubleshooting

### Service Won't Start

1. Check if port is already in use:
   ```bash
   lsof -i :5400
   ```

2. Check logs for errors:
   ```bash
   tail -f logs/monitoring_service.log
   ```

3. Restart monitoring service:
   ```bash
   pkill -f monitoring_service
   python3 monitoring_service.py
   ```

### Search Returns No Results

1. Verify images are indexed:
   ```bash
   sqlite3 ../mondrian.db "SELECT COUNT(*) FROM image_captions;"
   ```

2. Check embedding service is running:
   ```bash
   curl http://127.0.0.1:5300/health
   ```

3. Try more general search terms

### Caption Quality Issues

The caption service uses Qwen3-VL-4B-Instruct-MLX. For better captions:
- Ensure images are high quality
- Images should be well-lit and in focus
- The model works best with clear subjects

## API Reference

### RAG Service API

#### POST /index
Index a single image

**Request:**
```json
{
  "job_id": "string (required)",
  "image_path": "string (required)"
}
```

#### POST /search
Search for similar images

**Request:**
```json
{
  "query": "string (required)",
  "top_k": "integer (optional, default: 10)"
}
```

#### GET /health
Health check

**Response:**
```json
{
  "status": "healthy",
  "caption_service": "http://127.0.0.1:5200",
  "embedding_service": "http://127.0.0.1:5300",
  "database": "connected"
}
```

## Advanced Usage

### Batch Indexing

```bash
# Index all images in a directory
for img in source/*.jpg; do
  curl -X POST http://127.0.0.1:5400/index \
    -H "Content-Type: application/json" \
    -d "{\"job_id\": \"batch-$(date +%s)\", \"image_path\": \"$img\"}"
  sleep 1
done
```

### Custom Similarity Threshold

```bash
# Only return results with similarity > 0.8
curl -X POST http://127.0.0.1:5400/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "architectural rendering",
    "top_k": 50,
    "min_similarity": 0.8
  }'
```

## Support

For issues or questions:
- Check logs in `logs/monitoring_service.log`
- Run integration tests: `python3 test_rag_system.py`
- Verify database schema: `sqlite3 ../mondrian.db ".schema image_captions"`

---

**Last Updated**: 2026-01-08
**Version**: Mondrian v2.4-MONITORING-RAG
