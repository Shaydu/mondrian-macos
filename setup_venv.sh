#!/bin/bash
# Setup venv with system Python packages to avoid SSL issues
# This script links torch/torchvision from system Python to the venv

VENV_DIR="mondrian/venv"
VENV_SITE="$VENV_DIR/lib/python3.12/site-packages"
SYSTEM_SITE="/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages"

echo "Setting up venv with system Python packages..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating venv at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install packages from requirements.txt
echo "Installing packages from requirements.txt..."
pip install -r requirements.txt

# Link torch/torchvision from system Python to avoid SSL issues
echo "Linking torch packages from system Python..."
mkdir -p "$VENV_SITE"

packages_to_link=(
    "torch"
    "torchvision"
    "torchgen"
    "sympy"
    "networkx"
    "jinja2"
    "fsspec"
    "filelock"
    "setuptools"
    "mpmath"
)

for pkg in "${packages_to_link[@]}"; do
    if [ -e "$SYSTEM_SITE/$pkg" ]; then
        rm -rf "$VENV_SITE/$pkg" 2>/dev/null
        ln -sf "$SYSTEM_SITE/$pkg" "$VENV_SITE/$pkg" 2>/dev/null || \
        cp -r "$SYSTEM_SITE/$pkg" "$VENV_SITE/$pkg" 2>/dev/null
        echo "  ✓ Linked $pkg"
    fi
done

# Setup SSL certificates
echo "Setting up SSL certificates..."
mkdir -p "$VENV_DIR/etc/openssl"
ln -sf "$SYSTEM_SITE/certifi/cacert.pem" "$VENV_DIR/etc/openssl/cert.pem"
echo "  ✓ Linked SSL certificates"

# Test imports
echo "Testing critical imports..."
python -c "import torch; print(f'  ✓ torch {torch.__version__}')" || echo "  ✗ torch import failed"
python -c "import mlx.core; print('  ✓ mlx.core')" || echo "  ✗ mlx import failed"
python -c "from mlx_vlm import load; print('  ✓ mlx_vlm')" || echo "  ✗ mlx_vlm import failed"

echo "✓ venv setup complete!"
echo ""
echo "To use the venv, run:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To start services:"
echo "  ./mondrian.sh --restart --mode=lora --lora-path=./adapters/ansel"
