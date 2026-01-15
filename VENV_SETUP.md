# Mondrian macOS Environment Setup

## Quick Start

```bash
# 1. Set up and activate venv
./setup_venv.sh
source mondrian/venv/bin/activate

# 2. Start services with LoRA
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel
```

## Environment Requirements

- **Python 3.12** (via /Library/Frameworks/Python.framework/Versions/3.12/)
- **macOS with Apple Silicon** (M1/M2/M3 for Metal GPU)
- **SSL Certificates** - Installed via `/Applications/Python\ 3.12/Install\ Certificates.command`

## Why the Custom Setup?

### SSL Certificate Issues
By default, pip has SSL certificate verification issues on macOS. Solution:
1. Run: `/Applications/Python\ 3.12/Install\ Certificates.command`
2. Link certs to venv: `ln -sf /path/to/certifi/cacert.pem mondrian/venv/etc/openssl/cert.pem`

### PyTorch/Torchvision Linking
Instead of installing torch via pip (which has SSL issues), we:
1. Ensure torch is installed in system Python
2. Link it to the venv using symlinks
3. This avoids SSL certificate verification while maintaining all dependencies

### Why PyTorch is Needed
- **MLX** performs the inference on GPU
- **PyTorch/torchvision** provides the image preprocessing pipeline
- **Transformers** uses torch for model setup (even though we use MLX for actual inference)

## Services

### Job Service (port 5005)
- Manages job queue
- Coordinates job scheduling

### AI Advisor Service (port 5100)
- Vision analysis with Qwen3-VL model
- Supports modes: `base`, `lora`, `rag`, `lora+rag`
- GPU-accelerated via MLX

## Modes

```bash
# Base model (no fine-tuning)
./mondrian.sh --restart --mode=base

# LoRA fine-tuned model
./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel

# RAG mode
./mondrian.sh --restart --mode=rag

# LoRA + RAG
./mondrian.sh --restart --mode=lora+rag --lora-path=./adapters/ansel
```

## Troubleshooting

### Services won't start
Check the logs:
```bash
tail -100 logs/ai_advisor_service_*.log
tail -100 logs/job_service_v2.3_*.log
```

### SSL certificate errors
```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

### Import errors for torch/torchvision
Ensure they're linked to venv:
```bash
ln -sf /Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/torch mondrian/venv/lib/python3.12/site-packages/
ln -sf /Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/torchvision mondrian/venv/lib/python3.12/site-packages/
```

### Port conflicts
If ports 5005 or 5100 are in use:
```bash
lsof -i :5005
lsof -i :5100
# Kill the process using the port
```

## Dependencies

See `requirements.txt` for full dependency list. Key packages:
- **MLX**: Apple Silicon optimized ML framework
- **Transformers**: Model architecture and preprocessing
- **PyTorch**: Required for transformers image processing
- **Flask**: Web framework for services
- **OpenCV**: Image processing utilities
