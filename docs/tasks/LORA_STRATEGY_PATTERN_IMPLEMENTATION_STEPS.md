# LoRA Strategy Pattern - Step-by-Step Implementation Guide

## Overview

This guide provides exact code snippets and line numbers for implementing the LoRA strategy pattern in your service. It's organized as a checklist you can follow.

---

## Phase 1: Add Command-Line Arguments

### Step 1.1: Locate the Argument Parser

**File**: `mondrian/ai_advisor_service.py`
**Around Line**: 78-89 (where existing args are defined)

**Current State**:
```python
parser.add_argument("--port", type=int, default=5100)
parser.add_argument("--job_service_url", type=str, default="http://127.0.0.1:5005")
parser.add_argument("--model_timeout", type=int, default=300)
parser.add_argument("--mlx_model", type=str, default="mlx-community/Qwen3-VL-8B-Instruct-4bit")
parser.add_argument("--rag_service_url", type=str, default="http://127.0.0.1:5400")
```

### Step 1.2: Add New Arguments

**Add after the existing arguments**:

```python
# LoRA Fine-tuning Support (Strategy Pattern)
parser.add_argument(
    "--lora_path",
    type=str,
    default=None,
    help="Path to LoRA adapter directory. If provided with --model_mode fine_tuned or ab_test, loads fine-tuned model."
)

parser.add_argument(
    "--model_mode",
    type=str,
    choices=["base", "fine_tuned", "ab_test"],
    default="base",
    help="Model selection strategy: 'base' (base model only), 'fine_tuned' (use LoRA adapter), 'ab_test' (A/B test with random split)"
)

parser.add_argument(
    "--ab_test_split",
    type=float,
    default=0.5,
    help="For A/B testing: fraction of requests to route to fine-tuned model (0.0 to 1.0). Default: 0.5 (50/50)"
)
```

**Checklist**:
- [ ] Arguments added after line ~89
- [ ] All three new arguments present
- [ ] Default values set correctly
- [ ] Help text is clear

---

## Phase 2: Extract Parsed Arguments

### Step 2.1: Locate Args Processing

**File**: `mondrian/ai_advisor_service.py`
**Around Line**: 89-96

**Current State**:
```python
args = parser.parse_args()

PORT = args.port
DB_PATH = DATABASE_PATH
JOB_SERVICE_URL = args.job_service_url
MODEL_TIMEOUT = args.model_timeout
MLX_MODEL = args.mlx_model
RAG_SERVICE_URL = args.rag_service_url
```

### Step 2.2: Add New Global Variables

**Add after the existing assignments**:

```python
# LoRA Strategy Pattern Configuration
LORA_PATH = args.lora_path
MODEL_MODE = args.model_mode
AB_TEST_SPLIT = args.ab_test_split

# LoRA Service State (set during initialization)
IS_FINE_TUNED = False  # Will be set by initialize_service()
```

**Checklist**:
- [ ] Three new global variable assignments added
- [ ] IS_FINE_TUNED initialized to False
- [ ] Variables placed after existing argument assignments

---

## Phase 3: Create Service Initialization Function

### Step 3.1: Locate Global Model Variables

**File**: `mondrian/ai_advisor_service.py`
**Find**: Where `MODEL` and `PROCESSOR` are declared (typically after imports)

**Current State** (likely around line 100-150):
```python
# Global model reference
MODEL = None
PROCESSOR = None
```

### Step 3.2: Add New Global for Fine-Tuned State

**Add after existing MODEL globals**:

```python
# LoRA Support: Track if model is fine-tuned
IS_FINE_TUNED = False
```

### Step 3.3: Create initialize_service Function

**Add this new function** (recommend placing after the global declarations, before Flask app creation):

```python
def initialize_service(lora_path=None, model_mode="base", ab_test_split=0.5):
    """
    Initialize AI Advisor service with specified model strategy.
    
    Args:
        lora_path: Path to LoRA adapter directory (optional)
        model_mode: Model selection strategy - "base", "fine_tuned", or "ab_test"
        ab_test_split: For ab_test mode, fraction of requests to route to fine-tuned model
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global MODEL, PROCESSOR, IS_FINE_TUNED, MODEL_MODE, AB_TEST_SPLIT
    
    print(f"[INFO] Initializing service with model_mode={model_mode}")
    
    if model_mode == "base":
        # Strategy 1: Use base model only
        print("[INFO] Model Strategy: BASE (no fine-tuning)")
        MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=None, use_lora=False)
        MODEL_MODE = "base"
        
    elif model_mode == "fine_tuned":
        # Strategy 2: Use fine-tuned model (base + LoRA)
        if not lora_path:
            print("[ERROR] --model_mode fine_tuned requires --lora_path argument")
            return False
        
        print("[INFO] Model Strategy: FINE-TUNED")
        print(f"[INFO] Loading LoRA adapter from: {lora_path}")
        MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=lora_path, use_lora=True)
        
        if not IS_FINE_TUNED:
            print("[ERROR] Failed to load fine-tuned model")
            return False
        
        MODEL_MODE = "fine_tuned"
        
    elif model_mode == "ab_test":
        # Strategy 3: A/B test (randomly route between base and fine-tuned)
        if not lora_path:
            print("[WARNING] --model_mode ab_test requires --lora_path; falling back to base")
            MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=None, use_lora=False)
            MODEL_MODE = "base"
        else:
            print("[INFO] Model Strategy: A/B TEST")
            print(f"[INFO] Loading LoRA adapter from: {lora_path}")
            print(f"[INFO] Split: {ab_test_split*100:.1f}% fine-tuned, {(1-ab_test_split)*100:.1f}% base")
            MODEL, PROCESSOR, IS_FINE_TUNED = get_mlx_model(lora_path=lora_path, use_lora=True)
            MODEL_MODE = "ab_test"
            AB_TEST_SPLIT = ab_test_split
    
    else:
        print(f"[ERROR] Unknown model_mode: {model_mode}")
        return False
    
    print(f"[INFO] Service initialized successfully. Fine-tuned: {IS_FINE_TUNED}")
    return True
```

**Checklist**:
- [ ] Function includes docstring
- [ ] Handles all three model_mode cases
- [ ] Validates arguments (e.g., lora_path required for fine_tuned)
- [ ] Sets global variables correctly
- [ ] Includes appropriate logging
- [ ] Returns boolean success indicator

---

## Phase 4: Update get_mlx_model() Function

### Step 4.1: Locate the Function

**File**: `mondrian/ai_advisor_service.py`
**Search for**: `def get_mlx_model()`

**Current State** (example):
```python
def get_mlx_model():
    """Load MLX model and processor."""
    global MODEL, PROCESSOR
    
    print(f"[INFO] Loading model: {MLX_MODEL}")
    model, processor = load(MLX_MODEL)
    
    return model, processor
```

### Step 4.2: Add LoRA Support

**Replace the function** with this enhanced version:

```python
def get_mlx_model(lora_path=None, use_lora=False):
    """
    Load MLX model with optional LoRA adapter.
    
    Args:
        lora_path: Path to LoRA adapter directory (optional)
        use_lora: Whether to load and apply LoRA adapter (requires lora_path)
    
    Returns:
        tuple: (model, processor, is_fine_tuned)
            - model: MLX model object
            - processor: Image processor
            - is_fine_tuned: Boolean indicating if LoRA adapter was applied
    """
    print(f"[INFO] Loading base model: {MLX_MODEL}")
    model, processor = load(MLX_MODEL)
    
    is_fine_tuned = False
    
    # Load LoRA adapter if requested
    if lora_path and use_lora:
        try:
            print(f"[INFO] Loading LoRA adapter from: {lora_path}")
            
            # Verify required files exist
            adapter_config_path = os.path.join(lora_path, "adapter_config.json")
            adapter_weights_path = os.path.join(lora_path, "adapter_model.safetensors")
            
            if not os.path.exists(adapter_config_path):
                print(f"[ERROR] LoRA adapter config not found: {adapter_config_path}")
                return model, processor, False
            
            if not os.path.exists(adapter_weights_path):
                print(f"[ERROR] LoRA adapter weights not found: {adapter_weights_path}")
                return model, processor, False
            
            # Load adapter configuration
            with open(adapter_config_path, 'r') as f:
                lora_config = json.load(f)
            
            print(f"[INFO] LoRA Config: rank={lora_config.get('r')}, "
                  f"alpha={lora_config.get('lora_alpha')}, "
                  f"dropout={lora_config.get('lora_dropout')}")
            
            # TODO: Implement LoRA adapter application
            # ============================================
            # This is the critical step where LoRA weights are applied to the model.
            # The exact implementation depends on mlx-vlm's LoRA API.
            #
            # Expected approaches:
            # 1. Check if mlx_vlm has built-in LoRA support:
            #    from mlx_vlm.lora import apply_lora
            #    model = apply_lora(model, adapter_weights_path, lora_config)
            #
            # 2. Or manual application:
            #    lora_weights = mx.load(adapter_weights_path)
            #    for layer_name, layer in model.named_modules():
            #        if should_apply_lora(layer):
            #            inject_lora_weights(layer, lora_weights[layer_name])
            #
            # 3. Or if using mlx-vlm's training module:
            #    from mlx_vlm.training.lora import LoRALinear
            #    Replace linear layers with LoRALinear
            #
            # For now, this is a placeholder that needs investigation of mlx-vlm source
            # ============================================
            
            print("[WARNING] LoRA adapter loading not yet implemented")
            print("[WARNING] Using base model without LoRA adapters")
            is_fine_tuned = False
            
        except Exception as e:
            print(f"[ERROR] Failed to load LoRA adapter: {str(e)}")
            print("[WARNING] Falling back to base model")
            is_fine_tuned = False
    
    return model, processor, is_fine_tuned
```

**Checklist**:
- [ ] Function signature updated with `lora_path` and `use_lora` parameters
- [ ] Returns tuple with three elements (is_fine_tuned added)
- [ ] Validates adapter files exist
- [ ] Loads and logs adapter configuration
- [ ] Has clear TODO for LoRA application implementation
- [ ] Includes error handling and fallback logic
- [ ] Graceful degradation if LoRA loading fails

---

## Phase 5: Update Service Startup

### Step 5.1: Locate Service Startup Code

**File**: `mondrian/ai_advisor_service.py`
**Find**: The `if __name__ == "__main__":` block or where model is initialized

**Current State** (example):
```python
if __name__ == "__main__":
    # Load model
    MODEL, PROCESSOR = get_mlx_model()
    print(f"[INFO] Model loaded")
    
    # Start Flask
    app.run(host="0.0.0.0", port=PORT, debug=False)
```

### Step 5.2: Update Model Loading

**Replace the model loading section**:

```python
if __name__ == "__main__":
    # Initialize service with selected model strategy
    success = initialize_service(
        lora_path=LORA_PATH,
        model_mode=MODEL_MODE,
        ab_test_split=AB_TEST_SPLIT
    )
    
    if not success:
        print("[ERROR] Failed to initialize service")
        sys.exit(1)
    
    print(f"[INFO] Model Strategy: {MODEL_MODE}")
    print(f"[INFO] Fine-Tuned: {IS_FINE_TUNED}")
    print(f"[INFO] Service ready on http://0.0.0.0:{PORT}")
    
    # Start Flask
    app.run(host="0.0.0.0", port=PORT, debug=False)
```

**Checklist**:
- [ ] Calls `initialize_service()` with correct arguments
- [ ] Checks success return value
- [ ] Exits with error code if initialization fails
- [ ] Logs model configuration
- [ ] Service starts only after successful initialization

---

## Phase 6: Update /analyze Endpoint (A/B Testing Support)

### Step 6.1: Locate the /analyze Endpoint

**File**: `mondrian/ai_advisor_service.py`
**Find**: `@app.route('/analyze', methods=['POST'])`

**Current State** (simplified):
```python
@app.route('/analyze', methods=['POST'])
def analyze():
    global MODEL, PROCESSOR
    
    data = request.get_json()
    job_id = str(uuid.uuid4())
    
    # ... analysis logic ...
    
    return analysis_result
```

### Step 6.2: Add Strategy Selection Logic

**Add at the beginning of the function** (after getting request data):

```python
@app.route('/analyze', methods=['POST'])
def analyze():
    global MODEL, PROCESSOR, IS_FINE_TUNED, MODEL_MODE, AB_TEST_SPLIT
    
    data = request.get_json()
    job_id = str(uuid.uuid4())
    
    # --- New: Strategy-based model selection ---
    use_fine_tuned = False
    model_label = "base"
    
    if MODEL_MODE == "base":
        use_fine_tuned = False
        model_label = "base"
    
    elif MODEL_MODE == "fine_tuned":
        use_fine_tuned = True
        model_label = "fine_tuned"
    
    elif MODEL_MODE == "ab_test":
        # Random routing based on split ratio
        import random
        use_fine_tuned = random.random() < AB_TEST_SPLIT
        model_label = "fine_tuned" if use_fine_tuned else "base"
    
    # Log which model is being used
    print(f"[INFO] Job {job_id}: Using {model_label} model")
    
    # Optional: Store in database for analytics
    # This requires adding a 'model_used' column to the jobs table
    # update_job_status(job_id, model_used=model_label)
    
    # --- Continue with existing analysis logic ---
    
    # ... rest of analysis ...
    
    return analysis_result
```

**Checklist**:
- [ ] Added model selection logic at endpoint start
- [ ] Handles all three MODEL_MODE cases
- [ ] A/B test uses random.random() with AB_TEST_SPLIT
- [ ] Logs which model was used for this request
- [ ] Does not break existing analysis logic
- [ ] Model selection is per-request (allows A/B test traffic split)

---

## Phase 7: Test the Implementation

### Test 7.1: Test Base Mode (Backward Compatibility)

```bash
# Should work exactly like before (no changes needed)
python mondrian/ai_advisor_service.py --port 5100

# Service should start and be ready
# API calls should work normally
```

**Verify**:
- [ ] Service starts without errors
- [ ] Log shows: "Model Strategy: BASE"
- [ ] Log shows: "Fine-Tuned: False"
- [ ] /analyze endpoint works
- [ ] Responses are valid JSON

### Test 7.2: Test Fine-Tuned Mode (Without Real LoRA)

```bash
# This will fail because LoRA adapter doesn't exist yet
# But it tests the strategy pattern infrastructure
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/fake-lora \
    --model_mode fine_tuned

# Expected: Service exits with error because LoRA files don't exist
```

**Verify**:
- [ ] Service attempts to load LoRA
- [ ] Detects missing adapter files
- [ ] Exits with error (as designed)
- [ ] Falls back gracefully (if error handling updated)

### Test 7.3: Test A/B Test Mode

```bash
# Should work even without LoRA (uses base model)
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --model_mode ab_test \
    --ab_test_split 0.5

# Service should start
# Make requests and check logs for random model selection
```

**Verify**:
- [ ] Service starts successfully
- [ ] Log shows: "Model Strategy: A/B TEST"
- [ ] Log shows: "Split: 50.0% fine-tuned, 50.0% base"
- [ ] Multiple requests show mix of base and fine-tuned in logs
- [ ] Service uses base model when fine-tuned not available

### Test 7.4: Verify Backward Compatibility

```bash
# Existing code should work unchanged
python mondrian/ai_advisor_service.py --port 5100

# Should be identical to original behavior
curl -X POST http://localhost:5100/analyze \
    -H "Content-Type: application/json" \
    -d '{"image": "test.jpg", "advisor": "ansel"}'
```

**Verify**:
- [ ] No regression in existing functionality
- [ ] Response format unchanged
- [ ] Performance unchanged
- [ ] All existing features work

---

## Phase 8: Implement LoRA Adapter Application (TODO)

### Step 8.1: Research MLX-VLM LoRA API

**Investigation needed**:

1. **Check if built-in support exists**:
   ```bash
   grep -r "lora" /path/to/mlx_vlm/source/
   grep -r "LoRA" /path/to/mlx_vlm/source/
   ```

2. **Look for examples**:
   - MLX-VLM GitHub: https://github.com/Blaizzy/mlx-vlm
   - Check `training/` or `lora/` directories
   - Look for example scripts

3. **Check documentation**:
   - MLX-VLM docs
   - MLX-LM-LoRA reference: https://github.com/ml-explore/mlx-lm-lora

### Step 8.2: Implement LoRA Application

**Once API is understood**, replace the TODO in `get_mlx_model()` with:

```python
# Example 1: If mlx_vlm has built-in LoRA support
from mlx_vlm.lora import apply_lora_adapters
lora_weights = mx.load(adapter_weights_path)
model = apply_lora_adapters(model, lora_weights, lora_config)
is_fine_tuned = True

# Example 2: If manual application is needed
lora_weights = mx.load(adapter_weights_path)
for layer_id, adapter_pair in lora_weights.items():
    # Find corresponding layer in model
    # Apply: layer.weight += (B @ A) @ layer.weight
    pass
is_fine_tuned = True
```

**Checklist**:
- [ ] LoRA application code replaces TODO
- [ ] Loads adapter weights correctly
- [ ] Applies to correct model layers
- [ ] Sets is_fine_tuned = True on success
- [ ] Handles errors gracefully
- [ ] Function still returns (model, processor, is_fine_tuned)

---

## Phase 9: Add Database Tracking (Optional)

### Step 9.1: Add Column to Database Schema

```sql
ALTER TABLE jobs ADD COLUMN model_used TEXT DEFAULT 'base';
```

**Values**:
- `'base'` - Base model used
- `'fine_tuned'` - Fine-tuned model used
- `'ab_test_base'` - Base selected in A/B test
- `'ab_test_fine_tuned'` - Fine-tuned selected in A/B test

### Step 9.2: Update Job Status Function

```python
def update_job_status(job_id, model_used=None, **kwargs):
    """Update job status, optionally tracking which model was used."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if model_used is not None:
        updates.append("model_used = ?")
        params.append(model_used)
    
    # ... other updates as before ...
    
    if updates:
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params + [job_id])
        conn.commit()
    
    conn.close()
```

### Step 9.3: Log Model Usage in /analyze

```python
# In the /analyze endpoint, after model selection:
update_job_status(job_id, model_used=model_label)
```

---

## Testing Checklist - Final

- [ ] **Phase 1 (Args)**
  - [ ] Service starts with no args (backward compat)
  - [ ] Service accepts --model_mode base
  - [ ] Service accepts --model_mode fine_tuned
  - [ ] Service accepts --model_mode ab_test

- [ ] **Phase 2 (Variables)**
  - [ ] LORA_PATH variable set correctly
  - [ ] MODEL_MODE variable set correctly
  - [ ] AB_TEST_SPLIT variable set correctly

- [ ] **Phase 3 (Initialize Function)**
  - [ ] initialize_service() called at startup
  - [ ] Returns success for valid configs
  - [ ] Returns failure for invalid configs
  - [ ] Logs appropriate messages

- [ ] **Phase 4 (get_mlx_model Enhancement)**
  - [ ] Works with lora_path=None
  - [ ] Works with use_lora=False
  - [ ] Returns (model, processor, bool)
  - [ ] Validates adapter files
  - [ ] Gracefully handles missing files

- [ ] **Phase 5 (Startup)**
  - [ ] initialize_service called with args
  - [ ] Exits if initialization fails
  - [ ] Logs final configuration

- [ ] **Phase 6 (Endpoint)**
  - [ ] Model selection logic works
  - [ ] A/B test randomly selects models
  - [ ] Logs model selection
  - [ ] Endpoint functionality unchanged

- [ ] **Phase 7 (Testing)**
  - [ ] Base mode test passes
  - [ ] Fine-tuned mode test passes (errors appropriately)
  - [ ] A/B test mode passes
  - [ ] Backward compatibility maintained

- [ ] **Phase 8 (LoRA Application)**
  - [ ] LoRA API researched
  - [ ] TODO replaced with implementation
  - [ ] Adapter loading tested with real LoRA

- [ ] **Phase 9 (Database)**
  - [ ] Column added (optional)
  - [ ] Model usage tracked (optional)
  - [ ] Analytics queries work (optional)

---

## Summary

**Total Implementation Steps**: 9 phases
**Estimated Time**: 4-6 hours
**Critical Path**: Phases 1-7 enable strategy pattern; Phase 8 enables actual LoRA

**Next Action**: 
Would you like me to implement these changes to `ai_advisor_service.py`? I can:
1. Make all Phase 1-7 changes (strategy pattern infrastructure)
2. Add placeholders for Phase 8 (LoRA application)
3. Test the implementation

---

Created: January 14, 2026
Status: Ready for Implementation
Complexity: Medium (straightforward code changes, infrastructure pattern)
