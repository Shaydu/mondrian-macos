#!/bin/bash
# Test MLX Metal Access from Terminal.app
# Run this from Terminal.app (NOT from Cursor)

echo "========================================="
echo "MLX Metal Device Test"
echo "========================================="
echo ""
echo "Testing if MLX can access Metal GPU..."
echo ""

python3 -c "
import sys
print('Python version:', sys.version)
print()

try:
    print('[1/3] Importing mlx.core...')
    import mlx.core as mx
    print('      ✓ Import successful')
    print()
    
    print('[2/3] Creating array (triggers Metal initialization)...')
    x = mx.zeros((1,))
    print('      ✓ Array created:', x)
    print()
    
    print('[3/3] Checking device...')
    print('      Device:', mx.default_device())
    print()
    
    print('========================================')
    print('SUCCESS! MLX Metal is working!')
    print('========================================')
    print()
    print('You can now run:')
    print('  cd mondrian && python3 start_services.py')
    print('  cd .. && python3 batch_analyze_advisor_images.py --advisor ansel')
    
except Exception as e:
    print('      ✗ FAILED')
    print()
    print('Error:', e)
    print()
    import traceback
    traceback.print_exc()
    print()
    print('========================================')
    print('MLX Metal is NOT working')
    print('========================================')
    print()
    print('Next steps:')
    print('  1. Try upgrading MLX: pip3 install --upgrade mlx mlx-vlm')
    print('  2. Or install Ollama: brew install ollama')
    sys.exit(1)
"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "Next: Run the batch analysis"
    echo "  python3 batch_analyze_advisor_images.py --advisor ansel"
else
    echo ""
    echo "MLX test failed. See error above."
fi

exit $exit_code

