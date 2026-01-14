#!/bin/bash
# Quick start script - Review your 27 images and create training data

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                 ANSEL ADAMS IMAGE TRAINING - QUICK START                   ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "You have 27 images ready to review in: ansel-images/"
echo ""
echo "What would you like to do?"
echo ""
echo "  1. Review images NOW (start interactive session)"
echo "  2. Check current status (see what you have)"
echo "  3. View all images first (open folder)"
echo "  4. Read instructions (open START_HERE.md)"
echo "  5. Exit"
echo ""
read -p "Choose (1-5): " choice

case $choice in
  1)
    echo ""
    echo "Starting interactive review..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "TIP: Use Mode 3 (Mixed) for best speed/quality balance"
    echo "     Pick 2-3 standout dimensions, auto-fill rest"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    sleep 2
    python review_images_interactive.py \
        --images-dir ./ansel-images \
        --output ansel_images_reviewed.jsonl

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Review complete! ✅"
    echo ""
    read -p "Combine with text training now? (y/n): " combine
    if [ "$combine" = "y" ]; then
        cat ansel_print_filtered_train.jsonl ansel_images_reviewed.jsonl > ansel_combined_nuanced.jsonl
        echo ""
        echo "✅ Combined training data saved to: ansel_combined_nuanced.jsonl"
        echo ""
        echo "Your training dataset:"
        echo "  - Text entries: 174"
        echo "  - Image entries: $(wc -l < ansel_images_reviewed.jsonl)"
        echo "  - Total: $(wc -l < ansel_combined_nuanced.jsonl)"
        echo ""
        echo "Ready for LoRA training! 🎉"
    fi
    ;;

  2)
    echo ""
    python check_training_status.py
    ;;

  3)
    echo ""
    echo "Opening image folder..."
    open ./ansel-images
    echo ""
    echo "Review the images, then come back and choose option 1"
    ;;

  4)
    echo ""
    echo "Opening instructions..."
    open START_HERE.md
    ;;

  5)
    echo ""
    echo "Goodbye!"
    exit 0
    ;;

  *)
    echo ""
    echo "Invalid choice. Please run again and choose 1-5."
    exit 1
    ;;
esac

echo ""
