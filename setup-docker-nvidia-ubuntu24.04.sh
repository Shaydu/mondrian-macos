#!/bin/bash
# Docker + NVIDIA GPU Setup for Ubuntu 24.04

set -e

echo "================================"
echo "Docker + NVIDIA Setup (Ubuntu 24.04)"
echo "================================"
echo ""

# Step 1: Install Docker
echo "[1/3] Installing Docker..."
sudo apt-get update
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "✓ Docker installed"
echo ""

# Step 2: Install NVIDIA Container Toolkit (modern replacement for nvidia-docker2)
echo "[2/3] Installing NVIDIA Container Toolkit..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/ubuntu24.04/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

echo "✓ NVIDIA Container Toolkit installed"
echo ""

# Step 3: Configure Docker daemon
echo "[3/3] Configuring Docker daemon for GPU support..."
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

echo "✓ Docker daemon configured"
echo ""

# Step 4: Verify installation
echo "================================"
echo "Verification"
echo "================================"
echo ""

echo "Docker version:"
docker --version
echo ""

echo "NVIDIA Docker runtime:"
docker run --rm --runtime=nvidia nvidia/cuda:12.2.0-runtime-ubuntu22.04 nvidia-smi || echo "GPU test will work when NVIDIA drivers are installed"
echo ""

echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "You can now use Docker with GPU support:"
echo "  docker run --gpus all -it nvidia/cuda:12.2.0-runtime-ubuntu22.04"
echo ""
echo "To run Mondrian:"
echo "  docker build -t mondrian:latest ."
echo "  docker run --gpus all -p 5100:5100 -p 5005:5005 -p 5006:5006 mondrian:latest"
echo ""
