# Mondrian Docker Deployment - Quick Reference

## Files Created

1. **Dockerfile** - Main container image definition
2. **docker-compose.yml** - Local development/testing setup
3. **.dockerignore** - Files excluded from Docker image
4. **runpod-entrypoint.sh** - RunPod initialization script
5. **docker-build.sh** - Quick build and test script
6. **runpod-template.yaml** - RunPod template configuration
7. **RUNPOD_DEPLOYMENT.md** - Complete deployment guide

## Quick Start

### Local Testing

```bash
# Build and test locally
./docker-build.sh

# Or use docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Deploy to RunPod

```bash
# 1. Build and tag image
docker build -t your-username/mondrian:latest .

# 2. Push to Docker Hub (or your registry)
docker push your-username/mondrian:latest

# 3. On RunPod:
#    - Create new GPU pod
#    - Image: your-username/mondrian:latest
#    - GPU: RTX 3060 or better (12GB+ VRAM)
#    - Expose ports: 5100, 5005, 5006
#    - Add volumes for persistence
```

## Environment Variables

Configure these in RunPod:

```bash
MODE=base              # base, rag, lora, or lora+rag
BACKEND=bnb            # bnb (default), vllm, or awq
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

## Service Ports

- **5100** - AI Advisor Service (main ML inference)
- **5005** - Job Service (background processing)
- **5006** - Summary Service (report generation)

## API Testing

```bash
# Health check
curl http://your-pod-url:5100/health

# Analyze image
curl -X POST http://your-pod-url:5100/analyze \
  -F "image=@photo.jpg" \
  -F "mode=base"

# Create job
curl -X POST http://your-pod-url:5005/jobs \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/uploads/photo.jpg", "mode": "rag"}'
```

## Troubleshooting

### Build fails
- Check CUDA version compatibility (need 12.1+)
- Ensure sufficient disk space (20GB+)

### Container OOM
- Reduce batch size in model config
- Use 4-bit quantization (BNB backend)
- Upgrade to larger GPU

### Services won't start
```bash
# Check logs
docker logs <container-id>

# Or in RunPod
tail -f /app/logs/*.log
```

## Resource Requirements

**Minimum:**
- GPU: RTX 3060 (12GB VRAM)
- RAM: 16GB
- Disk: 20GB

**Recommended:**
- GPU: RTX 3090/A5000 (24GB VRAM)
- RAM: 32GB
- Disk: 50GB

## Cost Estimation (RunPod)

- RTX 3060 (12GB): ~$0.29/hr spot, ~$0.44/hr on-demand
- RTX 3090 (24GB): ~$0.42/hr spot, ~$0.69/hr on-demand
- A5000 (24GB): ~$0.52/hr spot, ~$0.89/hr on-demand

**Tip:** Use spot instances for 50-70% cost savings

## Next Steps

1. Read [RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md) for detailed setup
2. Initialize database on first run
3. (Optional) Precompute embeddings for better performance
4. Configure monitoring and backups
5. Set up authentication for production use

## Support

- RunPod docs: https://docs.runpod.io/
- Check logs: `/app/logs/*.log`
- Test locally first with docker-compose
