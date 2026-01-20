# RunPod Deployment Guide for Mondrian

## Overview

This guide covers deploying the Mondrian photography analysis system on RunPod with GPU support.

## Architecture

The Mondrian system consists of three microservices:

1. **AI Advisor Service** (port 5100) - PyTorch-based vision-language model inference with CUDA
2. **Job Service** (port 5005) - Background job processing and queue management
3. **Summary Service** (port 5006) - Report generation and export

## Prerequisites

- RunPod account with GPU pod access
- Docker and docker-compose installed locally (for testing)
- NVIDIA GPU with at least 12GB VRAM (RTX 3060 or better recommended)
- At least 20GB disk space

## Quick Start

### Option 1: RunPod Web Template (Recommended)

1. **Build and Push Image:**
   ```bash
   # Build the Docker image
   docker build -t your-registry/mondrian:latest .
   
   # Push to your registry (Docker Hub, GHCR, etc.)
   docker push your-registry/mondrian:latest
   ```

2. **Deploy on RunPod:**
   - Go to RunPod.io and create a new GPU Pod
   - Select a template with CUDA 12.1+ support
   - Choose GPU: RTX 3060 (12GB) or better
   - Set Docker image: `your-registry/mondrian:latest`
   - Expose ports: 5100, 5005, 5006
   - Set environment variables (see below)
   - Start the pod

### Option 2: RunPod CLI

```bash
# Install RunPod CLI
pip install runpod

# Login
runpod login

# Create pod
runpod create pod \
  --name mondrian \
  --gpu-type "NVIDIA RTX 3060" \
  --image your-registry/mondrian:latest \
  --ports "5100:5100,5005:5005,5006:5006" \
  --volume mondrian-data:/app/data
```

## Environment Variables

Set these in your RunPod pod configuration:

```bash
# CUDA Configuration
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Model Cache
TRANSFORMERS_CACHE=/root/.cache/huggingface
HF_HOME=/root/.cache/huggingface

# Python
PYTHONUNBUFFERED=1

# Service URLs (internal)
AI_ADVISOR_URL=http://localhost:5100
JOB_SERVICE_URL=http://localhost:5005
SUMMARY_SERVICE_URL=http://localhost:5006
```

## Database Initialization

The first time you run the container, initialize the database:

```bash
# SSH into your RunPod instance
runpod ssh <pod-id>

# Initialize database
python3 init_database.py

# (Optional) Precompute embeddings for better performance
python3 tools/rag/compute_image_embeddings_to_db.py \
  --advisor_dir /app/mondrian/source/advisor/photographer/ansel/ \
  --advisor_id ansel
```

## Persistent Storage

Mount these volumes to preserve data between pod restarts:

- `/app/mondrian.db` - SQLite database with job history and embeddings
- `/app/logs` - Service logs
- `/app/uploads` - User-uploaded images
- `/app/models` - Downloaded model weights (optional, speeds up startup)
- `/root/.cache/huggingface` - HuggingFace model cache

## Resource Requirements

### Minimum Configuration
- GPU: RTX 3060 (12GB VRAM)
- CPU: 4 cores
- RAM: 16GB
- Storage: 20GB

### Recommended Configuration
- GPU: RTX 3090 or A5000 (24GB VRAM)
- CPU: 8 cores
- RAM: 32GB
- Storage: 50GB

## Health Checks

Monitor service health:

```bash
# Check AI Advisor Service
curl http://localhost:5100/health

# Check Job Service
curl http://localhost:5005/health

# Check Summary Service
curl http://localhost:5006/health
```

## API Endpoints

Once deployed, access the services:

### AI Advisor Service (5100)
- `POST /analyze` - Analyze an image
- `GET /health` - Health check
- `GET /model-info` - Model information

### Job Service (5005)
- `POST /jobs` - Create a new analysis job
- `GET /jobs/<job_id>` - Get job status
- `GET /jobs` - List all jobs

### Summary Service (5006)
- `POST /generate` - Generate summary report
- `GET /health` - Health check

## Inference Backends

The system supports multiple inference backends:

```bash
# BitsAndBytes (default - good balance)
python3 scripts/start_services.py start-comprehensive --backend bnb

# vLLM (fastest, requires more VRAM)
python3 scripts/start_services.py start-comprehensive --backend vllm

# AutoAWQ (quantized, saves VRAM)
python3 scripts/start_services.py start-comprehensive --backend awq
```

## LoRA Adapters

To use LoRA fine-tuned adapters:

```bash
# Mount your LoRA weights
docker run -v /path/to/lora:/app/lora_adapters ...

# Start with LoRA enabled
python3 scripts/start_services.py start-comprehensive \
  --mode lora \
  --lora-path /app/lora_adapters/ansel_adams
```

## Troubleshooting

### Out of Memory Errors

1. Reduce batch size in model config
2. Use 4-bit quantization (BNB backend)
3. Enable gradient checkpointing
4. Upgrade to larger GPU

### Slow Inference

1. Pre-download models before deployment
2. Use vLLM backend for production
3. Enable model caching
4. Precompute image embeddings

### Service Won't Start

Check logs:
```bash
tail -f /app/logs/ai_advisor_service_*.log
tail -f /app/logs/job_service_*.log
```

Common issues:
- CUDA version mismatch (ensure CUDA 12.1+)
- Insufficient VRAM (check with `nvidia-smi`)
- Missing dependencies (rebuild image)
- Port conflicts (check port availability)

## Scaling

### Horizontal Scaling

For high-traffic deployments:

1. Run multiple AI Advisor Service instances
2. Use a load balancer (Nginx, HAProxy)
3. Keep Job Service centralized with SQLite
4. Or migrate to PostgreSQL for distributed setups

### Vertical Scaling

- Upgrade to multi-GPU setup
- Use tensor parallelism with vLLM
- Enable pipeline parallelism for large models

## Cost Optimization

RunPod pricing tips:

1. **Use Spot Instances**: 50-80% cheaper than on-demand
2. **Auto-shutdown**: Configure idle timeout
3. **Model Caching**: Pre-bake models into image to save download time
4. **Right-size GPU**: RTX 3060 is sufficient for most workloads
5. **Reserved Instances**: Commit for longer periods for discounts

## Security

1. **API Authentication**: Add authentication middleware
2. **Rate Limiting**: Implement rate limits per IP/user
3. **Input Validation**: Validate all uploaded images
4. **Network Security**: Use private networking when possible
5. **Secrets Management**: Use environment variables for sensitive data

## Monitoring

Set up monitoring:

```bash
# Container stats
docker stats mondrian-services

# GPU utilization
nvidia-smi -l 1

# Service logs
docker logs -f mondrian-services

# Application metrics
curl http://localhost:5100/metrics  # If Prometheus enabled
```

## Backup Strategy

Regular backups of persistent data:

```bash
# Backup database
sqlite3 mondrian.db ".backup mondrian_backup.db"

# Or use automated script
crontab -e
0 */6 * * * sqlite3 /app/mondrian.db ".backup /app/backups/mondrian_$(date +\%Y\%m\%d_\%H\%M\%S).db"
```

## Updates and Maintenance

To update the deployment:

```bash
# Build new image
docker build -t your-registry/mondrian:v2 .

# Push to registry
docker push your-registry/mondrian:v2

# Update RunPod pod with new image
runpod update pod <pod-id> --image your-registry/mondrian:v2

# Or via web UI: Stop pod → Change image → Start pod
```

## Support

For issues specific to:
- **RunPod**: Check RunPod documentation and support
- **Mondrian**: Review logs and application documentation
- **CUDA/PyTorch**: Verify GPU compatibility and drivers

## License

See project LICENSE file for details.
