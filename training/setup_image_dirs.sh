#!/bin/bash
# Setup script for image training directories

echo "Setting up image training directories..."
echo ""

cd "$(dirname "$0")"

# Create user_images directories
mkdir -p user_images/good
mkdir -p user_images/bad

echo "✅ Directories created:"
echo "   - training/user_images/good/  (for positive training examples)"
echo "   - training/user_images/bad/   (for negative training examples)"
echo ""
echo "Existing directories:"
echo "   - training/ansel_ocr/extracted_photos/ (17 Ansel photos)"
echo "   - training/datasets/ (training scripts and data)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Add photos to directories:"
echo "   - Copy 50-100 GOOD photos to: training/user_images/good/"
echo "   - Copy 50-100 BAD photos to:  training/user_images/bad/"
echo ""
echo "2. Review and label images:"
echo "   cd datasets"
echo "   python review_images_interactive.py"
echo ""
echo "3. Check your progress:"
echo "   python check_training_status.py"
echo ""
echo "📖 For detailed instructions, see: datasets/DIRECTORY_SETUP.md"
echo ""
