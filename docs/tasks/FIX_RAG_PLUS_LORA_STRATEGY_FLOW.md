# Fix: rag+lora Mode Not Using Correct Strategy

## Issue

When sending `mode=rag+lora` in API requests, the system was showing "Analyzing image..." instead of using the RAG+LoRA strategy flow (which displays a summary view).

## Root Cause

**API Validation vs Strategy Context Mismatch**

The API accepts the mode as **`rag+lora`** (with plus sign):
```python
# API validation accepts:
if mode_param in ['baseline', 'rag', 'lora', 'rag+lora', 'ab_test']
```

But the strategy context expects **`rag_lora`** (with underscore):
```python
# Strategy context STRATEGIES dict:
STRATEGIES = {
    "baseline": BaselineStrategy,
    "rag": RAGStrategy,
    "lora": LoRAStrategy,
    "rag_lora": RAGLoRAStrategy  # ← underscore, not plus!
}
```

When `rag+lora` was passed directly to the strategy:
```python
context.set_strategy(mode, advisor)  # mode = "rag+lora"
# But context expects "rag_lora"
# Result: ValueError or fallback to baseline
```

## Solution

Normalize the mode before passing to strategy context by converting `+` to `_`:

```python
# Normalize mode name for strategy context (convert + to _)
# API accepts 'rag+lora' but strategy context expects 'rag_lora'
normalized_mode = mode.replace('+', '_')

# Pass normalized mode to strategy
context.set_strategy(normalized_mode, advisor)  # Use normalized mode for strategy
```

## Changes Made

**File:** `mondrian/ai_advisor_service.py`

1. After mode extraction (around line 1279):
   - Added mode normalization: `normalized_mode = mode.replace('+', '_')`
   - Added debug logging to show normalization
   - Updated print statement to show both original and normalized mode

2. At strategy initialization (around line 1446):
   - Changed: `context.set_strategy(mode, advisor)`
   - To: `context.set_strategy(normalized_mode, advisor)`

## Flow Now Correct

```
Client sends: mode=rag+lora
       ↓
API receives and validates: ✅ "rag+lora" is valid
       ↓
Mode is normalized: "rag+lora" → "rag_lora"
       ↓
Strategy context receives: ✅ "rag_lora" 
       ↓
RAGLoRAStrategy is selected: ✅ Correct strategy
       ↓
Analysis uses RAG + LoRA flow: ✅ Shows summary view
```

## API/Strategy Naming Convention

- **API Level** (client-facing): Uses **plus sign** `rag+lora`
  - More intuitive for users
  - Matches HTML/UI conventions
  
- **Strategy Level** (internal): Uses **underscore** `rag_lora`
  - Python-friendly (valid variable names)
  - Matches class/module naming

- **Normalization**: Happens at the boundary between API and strategy layers

## Supported Modes

All modes now map correctly:

| API Mode | Strategy Mode | Class |
|----------|---------------|-------|
| `baseline` | `baseline` | BaselineStrategy |
| `rag` | `rag` | RAGStrategy |
| `lora` | `lora` | LoRAStrategy |
| `rag+lora` | `rag_lora` | RAGLoRAStrategy ✅ |
| `ab_test` | `ab_test` | (handled separately) |

## Testing

```bash
# Send rag+lora mode
curl -F "file=@image.jpg" \
     -F "advisor=ansel" \
     -F "mode=rag+lora" \
     -F "auto_analyze=true" \
     http://localhost:5005/upload

# Expected in logs:
# [AI SERVICE] Mode parameter from request: 'rag+lora'
# [AI SERVICE] Normalized mode: 'rag+lora' → 'rag_lora'
# [Context] Using requested mode: rag_lora
# [STRATEGY] ✓ Analysis complete. Overall grade: ...

# Should now see:
# ✅ Summary view displayed
# ✅ RAG + LoRA analysis results
# ✅ Correct badges showing "RAG+LORA" mode
```

## Why This Matters

- **Consistency**: RAG+LoRA now flows through the correct strategy
- **Display**: Shows proper summary view instead of "Analyzing image..."
- **Analysis**: Uses combined RAG + LoRA analysis method
- **Badges**: Shows correct mode indicator in UI
