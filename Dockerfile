FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    build-essential \
    libsqlite3-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libfontconfig1 \
    libfreetype6 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements_linux.txt ./

# Install Python dependencies
# Note: Installing torch separately for CUDA support
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN pip3 install --no-cache-dir transformers accelerate bitsandbytes

# Install remaining dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY mondrian/ ./mondrian/
COPY scripts/ ./scripts/

# Copy advisor source images and manifest
COPY advisor_image_manifest.yaml ./
COPY mondrian/source/advisor/ ./mondrian/source/advisor/

# Ensure advisor_images directory exists for runtime use
RUN mkdir -p mondrian/advisor_images

# Copy existing database if it exists
COPY mondrian.db* ./

# Copy only the trained LoRA adapter needed for inference (keep image lean)
COPY adapters/ansel_qwen3_4b_full_9dim/ ./adapters/ansel_qwen3_4b_full_9dim/

# Create necessary directories
RUN mkdir -p logs data models uploads temp

# Copy startup scripts
COPY start_mondrian.sh ./
COPY mondrian.sh ./
COPY docker-entrypoint.sh ./
RUN chmod +x start_mondrian.sh mondrian.sh docker-entrypoint.sh

# Expose all service ports
EXPOSE 5100 5005 5006 5007

# Health check for the main AI Advisor service
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:5100/health || exit 1

# Set entrypoint to docker script
ENTRYPOINT ["./docker-entrypoint.sh"]
