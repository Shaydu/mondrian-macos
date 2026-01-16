#!/bin/bash
# Test script to verify baseline analysis flow with database prompts

set -e

echo "========================================"
echo "Testing Baseline Analysis Flow"
echo "========================================"
echo ""

# Find a test image
TEST_IMAGE="source/test_image.jpg"
if [ ! -f "$TEST_IMAGE" ]; then
    # Try to find any image in source directory
    TEST_IMAGE=$(find source -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" | head -1)
    if [ -z "$TEST_IMAGE" ]; then
        echo "Error: No test image found in source directory"
        exit 1
    fi
fi

echo "Using test image: $TEST_IMAGE"
echo ""

# Check service health
echo "1. Checking AI Advisor service health..."
HEALTH=$(curl -s http://127.0.0.1:5100/health)
echo "$HEALTH" | python3 -m json.tool
echo ""

# Test analysis
echo "2. Uploading image for analysis..."
RESPONSE=$(curl -s -X POST http://127.0.0.1:5100/analyze \
  -F "image=@$TEST_IMAGE" \
  -F "advisor=ansel" \
  -F "enable_rag=false")

echo "Response received. Parsing..."
echo ""

# Save response to file
echo "$RESPONSE" | python3 -m json.tool > /tmp/test_analysis_response.json

# Extract key fields
echo "3. Analysis Results:"
echo "-------------------"
echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Advisor: {data.get('advisor', 'N/A')}\")
print(f\"Mode: {data.get('mode', 'N/A')}\")
print(f\"Parse Success: {data.get('parse_success', 'N/A')}\")
print(f\"Overall Score: {data.get('overall_score', 'N/A')}\")
print(f\"Dimensions: {len(data.get('analysis', {}).get('dimensions', []))}\")
print(f\"Analysis HTML length: {len(data.get('analysis_html', ''))}\")
print(f\"Summary HTML length: {len(data.get('summary_html', ''))}\")
print(f\"Advisor Bio HTML length: {len(data.get('advisor_bio_html', ''))}\")
print(f\"Full Response length: {len(data.get('full_response', ''))}\")
"
echo ""

# Save HTML outputs
echo "4. Saving HTML outputs..."
echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
with open('/tmp/test_analysis_detailed.html', 'w') as f:
    f.write(data.get('analysis_html', ''))
with open('/tmp/test_analysis_summary.html', 'w') as f:
    f.write(data.get('summary_html', ''))
with open('/tmp/test_advisor_bio.html', 'w') as f:
    f.write(data.get('advisor_bio_html', ''))
print('HTML files saved to /tmp/test_analysis_*.html')
"
echo ""

# Show first dimension details
echo "5. First Dimension Details:"
echo "---------------------------"
echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
dims = data.get('analysis', {}).get('dimensions', [])
if dims:
    dim = dims[0]
    print(f\"Name: {dim.get('name', 'N/A')}\")
    print(f\"Score: {dim.get('score', 'N/A')}/10\")
    print(f\"Comment: {dim.get('comment', 'N/A')[:100]}...\")
    print(f\"Recommendation: {dim.get('recommendation', 'N/A')[:100]}...\")
else:
    print('No dimensions found!')
"
echo ""

echo "========================================"
echo "Test Complete!"
echo "========================================"
echo ""
echo "Full response saved to: /tmp/test_analysis_response.json"
echo "HTML outputs saved to: /tmp/test_analysis_*.html"
echo ""
echo "You can view the HTML files with:"
echo "  xdg-open /tmp/test_analysis_detailed.html"
echo "  xdg-open /tmp/test_analysis_summary.html"
echo "  xdg-open /tmp/test_advisor_bio.html"
