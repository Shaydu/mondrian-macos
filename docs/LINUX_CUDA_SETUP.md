# Mondrian Linux/CUDA Setup Guide

This guide covers setting up Mondrian on Linux with NVIDIA GPU acceleration (CUDA).

## Hardware Requirements

- **GPU**: NVIDIA GPU with at least 8GB VRAM (tested on RTX 3060 12GB)
- **RAM**: 16GB+ recommended
- **Storage**: 20GB+ for models and dependencies

## Software Requirements

- Linux (Ubuntu 20.04+ recommended)
- Python 3.10 or 3.12
- NVIDIA Driver 525+ 
- CUDA Toolkit 12.1+

## Quick Start

### 1. Install NVIDIA Drivers and CUDA

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nvidia-driver-535 nvidia-cuda-toolkit

# Verify installation
nvidia-smi
nvcc --version
```

### 2. Clone and Setup Repository

```bash
git clone <repository-url>
cd mondrian-macos
git checkout linux-cuda-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
```

### 3. Install PyTorch with CUDA

Check https://pytorch.org/get-started/locally/ for the latest command:

```bash
# For CUDA 12.1 (adjust based on your CUDA version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### 4. Install Dependencies

```bash
pip install -r requirements_linux.txt
```

### 5. Verify Installation

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

### 6. Start Services

```bash
cd mondrian
python start_services_linux.py
```

## Service Configuration

### AI Advisor Service (Linux)

The Linux version uses PyTorch/Transformers instead of MLX:

```bash
python ai_advisor_service_linux.py \
    --port 5100 \
    --model "Qwen/Qwen2-VL-7B-Instruct" \
    --load_in_4bit
```

#### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--port` | 5100 | Service port |
| `--model` | Qwen/Qwen2-VL-7B-Instruct | HuggingFace model ID |
| `--load_in_4bit` | True | Use 4-bit quantization (recommended for 12GB VRAM) |
| `--load_in_8bit` | False | Use 8-bit quantization |
| `--lora_path` | None | Path to PEFT LoRA adapter |
| `--model_mode` | base | Model strategy: base, fine_tuned, ab_test |

### VRAM Usage (RTX 3060 12GB)

| Configuration | VRAM Usage | Notes |
|--------------|------------|-------|
| Qwen2-VL-7B 4-bit | ~4-5 GB | Recommended |
| Qwen2-VL-7B 8-bit | ~8-9 GB | Better quality |
| Qwen2-VL-7B fp16 | ~14 GB | Won't fit |
| + CLIP for RAG | +400 MB | Optional |

## Model Download

Models are automatically downloaded from HuggingFace on first run. To pre-download:

```bash
# Set cache directory (optional)
export HF_HOME=/path/to/cache

# Pre-download model
python -c "from transformers import Qwen2VLForConditionalGeneration, AutoProcessor; Qwen2VLForConditionalGeneration.from_pretrained('Qwen/Qwen2-VL-7B-Instruct'); AutoProcessor.from_pretrained('Qwen/Qwen2-VL-7B-Instruct')"
```

## LoRA Adapters

The Linux version uses PEFT format for LoRA adapters. If you have MLX-format adapters from macOS, they need to be converted or retrained.

### Using PEFT Adapters

```bash
python ai_advisor_service_linux.py \
    --model_mode fine_tuned \
    --lora_path /path/to/peft/adapter
```

### Adapter Format

PEFT adapters require:
- `adapter_config.json` with PEFT configuration
- `adapter_model.safetensors` or `adapter_model.bin`

## Troubleshooting

### CUDA Out of Memory

1. Ensure `--load_in_4bit` is enabled
2. Close other GPU applications
3. Reduce batch size if processing multiple images

```bash
# Check GPU memory
nvidia-smi
```

### Model Loading Fails

1. Check HuggingFace authentication:
```bash
huggingface-cli login
```

2. Verify disk space for model cache (~10GB per model)

### Slow Performance

1. Verify GPU is being used:
```bash
curl http://localhost:5100/health | jq '.using_gpu'
```

2. Check if running on CPU (will show `using_gpu: false`)

## API Compatibility

The Linux service maintains API compatibility with the macOS version:

- Same endpoints (`/analyze`, `/health`, `/model-status`)
- Same request/response formats
- Same RAG and LoRA support

## File Differences from macOS

| macOS | Linux |
|-------|-------|
| `ai_advisor_service.py` | `ai_advisor_service_linux.py` |
| `start_services.py` | `start_services_linux.py` |
| `requirements.txt` | `requirements_linux.txt` |
| MLX/Metal backend | PyTorch/CUDA backend |
| mlx-vlm models | HuggingFace models |

## Testing

Run the existing test suite:

```bash
# API tests
python test/test_api_direct.py

# RAG tests
cd test/rag-embeddings
./run_embedding_tests.sh
```

## Performance Comparison

Typical inference times (RTX 3060, 4-bit quantization):

| Task | Time |
|------|------|
| Image analysis (baseline) | 15-25s |
| RAG Pass 1 (dimensional extraction) | 10-15s |
| RAG Pass 2 (full analysis) | 15-25s |
| Total RAG analysis | 25-40s |

These times are comparable to Apple Silicon performance with MLX.
