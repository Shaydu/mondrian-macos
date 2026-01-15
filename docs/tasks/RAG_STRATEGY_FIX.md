# Bug Fix: RAG Strategy undefined variable

## Issue
The RAG strategy was throwing an internal server error (500) with the message:
```
NameError: name 'similar_images' is not defined
```

## Root Cause
When I added the JSON response conversion logic to the RAG strategy, I didn't remove the reference to an undefined variable `similar_images` from the metadata section. This variable was from earlier code that was never implemented (as noted by the TODO comment).

The RAG strategy has the following note:
```python
# TODO: Implement proper two-pass RAG analysis
# For now, RAG falls back to baseline (no similar image retrieval)
```

But the metadata section was still trying to reference `similar_images` which was never defined, causing a NameError.

## Fix
Removed the undefined reference to `similar_images_count` from the metadata dictionary in `mondrian/strategies/rag.py`:

**Before:**
```python
metadata={
    "raw_response_length": len(response) if response else 0,
    "similar_images_count": len(similar_images) if similar_images else 0
}
```

**After:**
```python
metadata={
    "raw_response_length": len(response) if response else 0
}
```

## Testing
After this fix, RAG mode should work without the 500 error. Test with:
```bash
python3 test_lora_e2e.py --image source/mike-shrub-01004b68.jpg --advisor ansel --mode rag
```

## File Modified
- `mondrian/strategies/rag.py`
