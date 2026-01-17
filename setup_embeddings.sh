#!/bin/bash
# Quick setup script for embedding-based retrieval

set -e

echo "=== Mondrian Embedding System Setup ==="
echo ""

# Check if we're in the right directory
if [ ! -f "mondrian.db" ]; then
    echo "❌ Error: mondrian.db not found. Please run this from the project root."
    exit 1
fi

echo "✓ Found mondrian.db"
echo ""

# Determine Python to use (prefer venv)
if [ -f "venv/bin/python3" ]; then
    PYTHON="venv/bin/python3"
    echo "Using venv Python: $PYTHON"
elif [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
    echo "Using venv Python: $PYTHON"
else
    PYTHON="python3"
    echo "⚠️  Virtual environment not found, using system Python"
fi
echo ""

# Check Python dependencies
echo "Checking dependencies..."

if $PYTHON -c "from transformers import CLIPProcessor, CLIPModel" 2>/dev/null; then
    echo "✓ CLIP (transformers) is installed"
else
    echo "❌ CLIP not available (transformers package issue)"
    exit 1
fi

if $PYTHON -c "from sentence_transformers import SentenceTransformer" 2>/dev/null; then
    echo "✓ sentence-transformers is installed"
else
    echo "⚠️  sentence-transformers not installed"
    echo ""
    read -p "Install sentence-transformers? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $PYTHON -m pip install sentence-transformers
        echo "✓ sentence-transformers installed"
    else
        echo "❌ sentence-transformers required for embedding system"
        exit 1
    fi
fi

echo ""
echo "Checking database schema..."

# Check if embedding columns exist
EMBEDDING_COUNT=$(sqlite3 mondrian.db "SELECT COUNT(*) FROM pragma_table_info('dimensional_profiles') WHERE name IN ('embedding', 'text_embedding');")

if [ "$EMBEDDING_COUNT" -eq "2" ]; then
    echo "✓ Database schema is ready (embedding columns exist)"
else
    echo "❌ Database schema missing embedding columns"
    echo "Expected 2 columns (embedding, text_embedding), found $EMBEDDING_COUNT"
    exit 1
fi

echo ""
echo "Checking current embedding status..."

# Count advisor images
TOTAL_IMAGES=$(sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel' AND composition_score IS NOT NULL;")
echo "  Total Ansel Adams advisor images: $TOTAL_IMAGES"

# Count images with embeddings
WITH_CLIP=$(sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel' AND embedding IS NOT NULL;")
WITH_TEXT=$(sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel' AND text_embedding IS NOT NULL;")
WITH_BOTH=$(sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel' AND embedding IS NOT NULL AND text_embedding IS NOT NULL;")

echo "  With CLIP embeddings: $WITH_CLIP"
echo "  With text embeddings: $WITH_TEXT"
echo "  With both embeddings: $WITH_BOTH"

echo ""

if [ "$WITH_BOTH" -eq "$TOTAL_IMAGES" ] && [ "$TOTAL_IMAGES" -gt "0" ]; then
    echo "✓ All advisor images already have embeddings!"
    echo ""
    read -p "Recompute embeddings anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "=== Setup Complete ==="
        echo ""
        echo "Embedding system is ready to use!"
        echo "Try an analysis in RAG mode to test:"
        echo "  curl -X POST http://localhost:5001/analyze ..."
        exit 0
    fi
    FORCE_FLAG="--force"
else
    FORCE_FLAG=""
fi

echo ""
echo "=== Computing Embeddings ==="
echo ""
echo "This will:"
echo "  1. Download CLIP model (~350MB, one time)"
echo "  2. Download text model (~80MB, one time)"
echo "  3. Compute embeddings for $TOTAL_IMAGES images"
echo "  4. Take ~5-10 minutes on GPU (longer on CPU)"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
$PYTHON scripts/compute_embeddings.py --advisor ansel $FORCE_FLAG

echo ""
echo "=== Verification ==="
echo ""

# Re-check embedding counts
FINAL_WITH_BOTH=$(sqlite3 mondrian.db "SELECT COUNT(*) FROM dimensional_profiles WHERE advisor_id='ansel' AND embedding IS NOT NULL AND text_embedding IS NOT NULL;")

if [ "$FINAL_WITH_BOTH" -eq "$TOTAL_IMAGES" ]; then
    echo "✓ Success! All $TOTAL_IMAGES images now have embeddings"
else
    echo "⚠️  Warning: Expected $TOTAL_IMAGES with embeddings, found $FINAL_WITH_BOTH"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "The embedding system is now active!"
echo ""
echo "When you run analyses in RAG mode, the system will automatically:"
echo "  • Compute CLIP embedding for user's image (~50-100ms)"
echo "  • Find visually similar advisor references"
echo "  • Use hybrid scoring (visual + dimensional gaps)"
echo ""
echo "Test it:"
echo "  1. Start the service: ./start_mondrian.sh"
echo "  2. Analyze an image in RAG mode"
echo "  3. Check logs for 'Using hybrid embedding retrieval'"
echo ""
