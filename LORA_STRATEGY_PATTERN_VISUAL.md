# LoRA Strategy Pattern - Visual Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI Advisor Service                               │
│                   (ai_advisor_service.py)                           │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    ┌─────────┴──────────┐
                    │                    │
            Command Line Args      Configuration
                    │                    │
        ┌─────────┬─┴──────────┬────────┘
        │         │            │
    --port    --model_mode  --lora_path
               ├─ base       --ab_test_split
               ├─ fine_tuned
               └─ ab_test


┌────────────────────────────────────────────────────────────────────────────┐
│                         Strategy Initialization                             │
│                                                                              │
│  initialize_service(lora_path, model_mode, ab_test_split)                  │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
        │ BASE STRATEGY│    │ FINE_TUNED   │    │  AB_TEST     │
        │ (DEFAULT)    │    │ STRATEGY     │    │  STRATEGY    │
        └──────────────┘    └──────────────┘    └──────────────┘
                │                   │                   │
                ▼                   ▼                   ▼
        Load base model     Load base model     Load base model
        only                + LoRA adapter      + LoRA adapter
                                                (optional)
                │                   │                   │
                ▼                   ▼                   ▼
        IS_FINE_TUNED=False  IS_FINE_TUNED=True  MODEL_MODE="ab_test"
        MODEL_MODE="base"    MODEL_MODE="fine_tuned" AB_TEST_SPLIT=0.5
                │                   │                   │
                └───────────────────┼───────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │  Global Service State           │
                    │  ├─ MODEL                       │
                    │  ├─ PROCESSOR                   │
                    │  ├─ IS_FINE_TUNED              │
                    │  ├─ MODEL_MODE                 │
                    │  └─ AB_TEST_SPLIT              │
                    └─────────────────────────────────┘


┌────────────────────────────────────────────────────────────────────────────┐
│                     Request-Time Strategy Selection                         │
│                                                                              │
│  /analyze POST request arrives                                              │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        ┌────────────────────┐
                        │  MODEL_MODE check  │
                        └────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
            "base"            "fine_tuned"         "ab_test"
                │                   │                   │
        use_fine_tuned=False  use_fine_tuned=True    │
                │                   │          random()
                │                   │          <split?
                │                   │                   │
                ▼                   ▼                   ▼
            [log: BASE]         [log: FINE_TUNED]   Y→[log: FINE_TUNED]
                │                   │                   │
                └───────────────────┼─────────────────→ N→[log: BASE]
                                    │                   │
                                    └───────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │  Perform Analysis               │
                    │  (using selected model)         │
                    │  - Load image                   │
                    │  - Generate response            │
                    │  - Format output                │
                    │  - Store in database            │
                    └─────────────────────────────────┘
                                    │
                                    ▼
                        ┌─────────────────────┐
                        │  Return Response    │
                        │  (JSON/HTML)        │
                        └─────────────────────┘


┌────────────────────────────────────────────────────────────────────────────┐
│                    Model Loading Architecture                               │
│                                                                              │
│  get_mlx_model(lora_path=None, use_lora=False)                             │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │  1. Load Base Model             │
                    │     mlx_vlm.load(BASE_MODEL)    │
                    │  ✓ Qwen3-VL-8B-Instruct-4bit    │
                    │                                  │
                    │  Returns:                        │
                    │  - model (MLX model object)     │
                    │  - processor (image processor)  │
                    └─────────────────────────────────┘
                                    │
                                    ▼
                        ┌────────────────────┐
                        │  use_lora check?   │
                        └────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼ YES                       ▼ NO
        ┌────────────────────┐       ┌──────────────────────┐
        │  Load LoRA Adapter │       │  Return Base Model   │
        │                    │       │  IS_FINE_TUNED=False │
        │ 1. Check files:    │       │                      │
        │    adapter_config  │       │ (model, processor,   │
        │    adapter_model   │       │  False)              │
        │                    │       └──────────────────────┘
        │ 2. Load config.json│
        │                    │
        │ 3. Load weights    │
        │    mx.load(...)    │
        │                    │
        │ 4. Apply LoRA      │
        │    [TODO: mlx-vlm  │
        │     LoRA API]      │
        │                    │
        │ 5. Return          │
        │    IS_FINE_TUNED   │
        │    =True           │
        └────────────────────┘
                    │
                    ▼
        ┌────────────────────────┐
        │ Return Fine-Tuned Model│
        │ (model, processor,     │
        │  True)                 │
        └────────────────────────┘


┌────────────────────────────────────────────────────────────────────────────┐
│                    LoRA Adapter Application Flow                            │
│                                                                              │
│  [CRITICAL TODO - Needs Implementation]                                     │
└────────────────────────────────────────────────────────────────────────────┘

Input: Base Model + Adapter Weights

                    ┌──────────────────┐
                    │  Base Model      │
                    │                  │
                    │  ├─ vision_tower │
                    │  ├─ mlp_head     │
                    │  ├─ decoder      │
                    │  ├─ ... (many    │
                    │  │   layers)     │
                    │  └─ ...          │
                    └──────────────────┘
                            ▲
                            │
                    ┌──────────────────┐
                    │ LoRA Adapter     │
                    │                  │
                    │ ├─ lora_config   │
                    │ │  (r=16,        │
                    │ │   alpha=32)    │
                    │ │                │
                    │ └─ lora_weights  │
                    │    {layer_id:    │
                    │     {A, B}}      │
                    └──────────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │ Application      │
                    │ Strategy         │
                    │                  │
                    │ For each layer:  │
                    │  weight += (B@A) │
                    │  output += LoRA_ │
                    │          output  │
                    └──────────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │ Fine-Tuned Model │
                    │                  │
                    │ Base weights +   │
                    │ LoRA deltas      │
                    │                  │
                    │ ~150MB adapter   │
                    └──────────────────┘

Output: Combined Model for Inference


┌────────────────────────────────────────────────────────────────────────────┐
│                   Strategy Comparison Matrix                                │
└────────────────────────────────────────────────────────────────────────────┘

Strategy      Model              Inference     Use Case
────────────────────────────────────────────────────────────────────────
base          Base model only    2-3s          Default, general purpose,
              (no adapters)                    backward compatible

fine_tuned    Base + LoRA        2-3s          Production deployment,
              adapters           (stable,      when metrics improve,
                                 reliable)    advisor-specific

ab_test       Base + LoRA        2-3s          Safe rollout, testing,
              (random split)     (per          comparing performance,
                                  request)    gradual migration


┌────────────────────────────────────────────────────────────────────────────┐
│                    Deployment Timeline Example                              │
└────────────────────────────────────────────────────────────────────────────┘

Day 1:  Deploy with ab_test --ab_test_split 0.05  (5% fine-tuned)
        ├─ Monitor logs, metrics
        └─ Compare quality, speed

Day 2:  Increase to ab_test --ab_test_split 0.10  (10% fine-tuned)
        ├─ Monitor logs, metrics
        └─ Compare quality, speed

Day 3:  Increase to ab_test --ab_test_split 0.25  (25% fine-tuned)
        ├─ Monitor logs, metrics
        └─ Compare quality, speed

Day 4:  Increase to ab_test --ab_test_split 0.50  (50% fine-tuned)
        ├─ Monitor logs, metrics
        └─ Compare quality, speed

Day 5:  If all metrics good:
        └─ Deploy with fine_tuned mode (100% fine-tuned)

        If issues occur:
        └─ Revert to base mode (instant rollback)


┌────────────────────────────────────────────────────────────────────────────┐
│                    Error Handling & Fallback                                │
└────────────────────────────────────────────────────────────────────────────┘

Scenario: --model_mode fine_tuned but LoRA loading fails

    initialize_service()
            │
            ├─ Check lora_path provided ✓
            ├─ Call get_mlx_model(lora_path, use_lora=True)
            │   ├─ Load base model ✓
            │   ├─ Check adapter_config.json
            │   │   └─ NOT FOUND ✗
            │   ├─ Log error
            │   └─ Return (model, processor, False)
            │
            ├─ Check IS_FINE_TUNED == False ✗
            ├─ Log error and exit with code 1
            └─ Service fails to start
                (USER ACTION: Fix LoRA path or use --model_mode base)

Alternative: Graceful fallback

    initialize_service()
            │
            ├─ Check lora_path provided ✓
            ├─ Call get_mlx_model(lora_path, use_lora=True)
            │   ├─ Load base model ✓
            │   ├─ Try LoRA loading
            │   │   └─ FAILS ✗
            │   ├─ Log warning: "Falling back to base model"
            │   └─ Return (model, processor, False)
            │
            ├─ Log warning: "Requested fine_tuned but using base"
            ├─ Set MODEL_MODE = "base"
            └─ Service continues with base model
                (SERVICE AVAILABLE: Users not affected)


```

---

## Key Design Principles

### 1. **Strategy Pattern**
- Selection happens at **startup** (via command-line args)
- Not changeable at runtime (for stability)
- Clean separation of concerns

### 2. **Backward Compatibility**
- Default: `--model_mode base` (existing behavior)
- No `--lora_path` → always base model
- Existing clients unaffected

### 3. **Graceful Degradation**
- LoRA loading fails? Fall back to base
- Missing adapter files? Use base model
- Network issues? Use what's loaded

### 4. **Observability**
- Every request logs which model was used
- Model selection tracked in database
- Enables A/B test analytics

### 5. **Testability**
- Each strategy independently testable
- Easy to verify behavior
- Rollback is instant

---

## Implementation Order (Recommended)

```
1. Add command-line arguments       (30 min)
2. Add global variables             (10 min)
3. Implement initialize_service()   (45 min)
4. Update service startup code      (15 min)
5. Implement strategy in /analyze   (30 min)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUBTOTAL Phase 1: 2 hours

6. Implement LoRA adapter loading   (2-3 hours)
   (requires MLX-VLM investigation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUBTOTAL Phase 2: 2-3 hours

7. Test all three strategies        (1 hour)
8. Add database tracking (optional) (1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL: 4-5 hours
```

---

Created: January 14, 2026
Status: Architecture Reference
