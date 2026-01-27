#!/bin/bash

# Test the exact iOS workflow against local container
# This simulates what your iOS app does

set -e

echo "=========================================="
echo "Testing iOS Workflow on Local Container"
echo "=========================================="
echo ""

# Find a test image
TEST_IMAGE="source/mike-shrub-01004b68.jpg"
if [ ! -f "$TEST_IMAGE" ]; then
    echo "❌ Test image not found: $TEST_IMAGE"
    echo "Please provide a path to a test image:"
    read -r TEST_IMAGE
    if [ ! -f "$TEST_IMAGE" ]; then
        echo "❌ Image still not found, exiting"
        exit 1
    fi
fi

echo "Using test image: $TEST_IMAGE"
echo ""

# Step 1: Submit job (like iOS app does)
echo "1️⃣  Submitting analysis job..."
JOB_RESPONSE=$(curl -s -X POST http://localhost:5005/analyze \
  -F "image=@${TEST_IMAGE}" \
  -F "advisor=ansel" \
  -F "mode=rag")

JOB_ID=$(echo "$JOB_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))" 2>/dev/null)

if [ -z "$JOB_ID" ]; then
    echo "❌ Failed to submit job"
    echo "Response: $JOB_RESPONSE"
    exit 1
fi

echo "✓ Job submitted: $JOB_ID"
echo ""

# Step 2: Poll for completion (like iOS app does)
echo "2️⃣  Polling for job completion..."
MAX_ATTEMPTS=60
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    STATUS_RESPONSE=$(curl -s http://localhost:5005/job/${JOB_ID})
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
    
    if [ "$STATUS" = "completed" ]; then
        echo "✓ Job completed successfully!"
        break
    elif [ "$STATUS" = "failed" ] || [ "$STATUS" = "cancelled" ]; then
        echo "❌ Job failed with status: $STATUS"
        ERROR=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error', 'Unknown error'))" 2>/dev/null)
        echo "Error: $ERROR"
        exit 1
    fi
    
    echo "  Status: $STATUS (attempt $((ATTEMPT + 1))/$MAX_ATTEMPTS)"
    sleep 5
    ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
    echo "❌ Timeout waiting for job completion"
    exit 1
fi

echo ""

# Step 3: Fetch results (like iOS app does)
echo "3️⃣  Fetching analysis results..."
RESULT_RESPONSE=$(curl -s http://localhost:5005/job/${JOB_ID})

# Save full response to file
echo "$RESULT_RESPONSE" > /tmp/mondrian_test_result.json
echo "✓ Full result saved to: /tmp/mondrian_test_result.json"
echo ""

# Step 4: Analyze the result
echo "4️⃣  Analysis Summary:"
echo "----------------------------------------"

# Extract key fields
OVERALL_SCORE=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('llm_outputs', {}).get('summary', 'N/A'))" 2>/dev/null | head -c 100)
DIMENSIONS=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; r=json.load(sys.stdin); dims=r.get('llm_outputs', {}).get('response', '{}'); import json; d=json.loads(dims) if isinstance(dims, str) else dims; print(len(d.get('dimensions', [])))" 2>/dev/null)

echo "Job ID: $JOB_ID"
echo "Summary: $OVERALL_SCORE"
echo "Dimensions analyzed: $DIMENSIONS"
echo ""

# Step 5: Check for critical issues
echo "5️⃣  Checking for issues..."

# Check for JSON parsing errors
if echo "$RESULT_RESPONSE" | grep -q "parse_error"; then
    echo "❌ JSON PARSING ERROR DETECTED"
    echo "$RESULT_RESPONSE" | python3 -c "import sys, json; r=json.load(sys.stdin); print('Error:', r.get('llm_outputs', {}).get('parse_error', 'Unknown'))" 2>/dev/null
    exit 1
fi

# Check for citation violations
VIOLATIONS=$(echo "$RESULT_RESPONSE" | grep -o "Duplicate.*citation" | wc -l)
if [ "$VIOLATIONS" -gt 0 ]; then
    echo "⚠️  Found $VIOLATIONS citation violations in logs"
fi

# Check for repetition
RESPONSE_TEXT=$(echo "$RESULT_RESPONSE" | python3 -c "import sys, json; r=json.load(sys.stdin); resp=r.get('llm_outputs', {}).get('response', ''); print(resp if isinstance(resp, str) else json.dumps(resp))" 2>/dev/null)
REPEATED_RECS=$(echo "$RESPONSE_TEXT" | grep -o "Consider how you could strengthen" | wc -l)
if [ "$REPEATED_RECS" -gt 1 ]; then
    echo "❌ REPETITION DETECTED: Template recommendation copied $REPEATED_RECS times"
    exit 1
fi

echo "✓ No critical issues detected"
echo ""

# Step 6: Display HTML (like iOS would render)
echo "6️⃣  HTML result:"
HTML_URL="http://localhost:5005/job/${JOB_ID}/html"
echo "View in browser: $HTML_URL"
echo ""

echo "=========================================="
echo "✅ iOS Workflow Test Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  - View HTML: $HTML_URL"
echo "  - Check logs: docker logs -f mondrian-test"
echo "  - Full JSON: cat /tmp/mondrian_test_result.json | jq"
echo ""
