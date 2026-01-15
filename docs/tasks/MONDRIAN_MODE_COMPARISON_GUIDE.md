# Mondrian Mode Comparison Guide

## Quick Start - Comparing Modes

You can now easily restart Mondrian services in different modes to compare outputs!

---

## Available Modes

### 1. **Base Mode** (default)
Base model only, no RAG, no LoRA

```bash
./mondrian.sh --restart --mode=base
```

### 2. **RAG Mode**
Base model with RAG (Retrieval-Augmented Generation) enabled

```bash
./mondrian.sh --restart --mode=rag
```

### 3. **LoRA Mode**
LoRA fine-tuned model (requires trained adapter)

```bash
./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
```

### 4. **LoRA + RAG Mode**
Combine LoRA fine-tuning with RAG

```bash
./mondrian.sh --restart --mode=lora+rag --lora-path=./models/qwen3-vl-4b-lora-ansel
```

### 5. **A/B Test Mode**
Randomly split traffic between base and LoRA models

```bash
# 50/50 split (default)
./mondrian.sh --restart --mode=ab-test --lora-path=./models/qwen3-vl-4b-lora-ansel

# 70% LoRA, 30% base
./mondrian.sh --restart --mode=ab-test --lora-path=./models/qwen3-vl-4b-lora-ansel --ab-split=0.7
```

---

## Comparing Outputs

### Workflow for Comparing RAG vs LoRA

#### Step 1: Test with RAG Mode
```bash
./mondrian.sh --restart --mode=rag
```

Then analyze some images via your iOS app or API and save the results.

#### Step 2: Test with LoRA Mode
```bash
./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
```

Analyze the **same images** and compare the outputs.

#### Step 3: Compare Results
Look at differences in:
- Analysis quality and depth
- Consistency with advisor style
- Format compliance (JSON structure)
- Processing speed
- Reference images (RAG provides these)

---

## Example Comparison Workflow

```bash
# 1. Start in base mode (baseline)
./mondrian.sh --restart --mode=base
# → Analyze image X, save result as "base_output.json"

# 2. Switch to RAG mode
./mondrian.sh --restart --mode=rag
# → Analyze same image X, save as "rag_output.json"

# 3. Switch to LoRA mode (when trained)
./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel
# → Analyze same image X, save as "lora_output.json"

# 4. Compare all three outputs
diff base_output.json rag_output.json
diff base_output.json lora_output.json
diff rag_output.json lora_output.json
```

---

## Service Status

### Check What's Running
```bash
lsof -i :5100  # AI Advisor Service
lsof -i :5005  # Job Service
```

### Stop All Services
```bash
./mondrian.sh --stop
```

### See All Options
```bash
./mondrian.sh --help
```

---

## Mode Comparison Matrix

| Mode        | Base Model | LoRA Adapter | RAG Context | Use Case |
|-------------|------------|--------------|-------------|----------|
| **base**    | ✓          | ✗            | ✗           | Baseline performance |
| **rag**     | ✓          | ✗            | ✓           | Context-aware analysis |
| **lora**    | ✓          | ✓            | ✗           | Domain-specialized model |
| **lora+rag**| ✓          | ✓            | ✓           | Best of both approaches |
| **ab-test** | ✓          | ✓ (split)    | ✗           | Gradual rollout testing |

---

## Important Notes

### LoRA Path
- The `--lora-path` must point to a directory containing:
  - `adapter_config.json`
  - `adapter_model.safetensors`
  - `training_args.json` (optional)

### RAG Mode
- RAG is also controlled by the `RAG_ENABLED` environment variable
- You can enable/disable RAG per-request via the API
- RAG mode here sets up the environment for RAG usage

### Performance
- **base**: Fastest (no overhead)
- **rag**: Slight overhead (similarity search + context)
- **lora**: Minimal overhead (~same as base)
- **lora+rag**: Combined overhead (RAG search + LoRA)

---

## Logs & Monitoring

Each mode logs its configuration at startup:

```
[MODE] Base model only (no RAG, no LoRA)
[INFO] Model Strategy: BASE
[INFO] Fine-Tuned: False
```

```
[MODE] LoRA fine-tuned model
[INFO] Model Strategy: FINE-TUNED
[INFO] Loading LoRA adapter from: ./models/qwen3-vl-4b-lora-ansel
[INFO] Fine-Tuned: True
```

Check logs to verify the correct mode is active.

---

## Troubleshooting

### Error: "Port still in use"
```bash
# Manually kill processes
lsof -ti :5100 | xargs kill -9
lsof -ti :5005 | xargs kill -9

# Then restart
./mondrian.sh --restart --mode=<your-mode>
```

### Error: "--lora-path required"
Make sure to provide the path when using lora modes:
```bash
./mondrian.sh --restart --mode=lora --lora-path=./models/your-lora-adapter
```

### Services won't start
Check if Python 3.12 is installed:
```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 --version
```

---

## Quick Reference Commands

```bash
# Base mode (default)
./mondrian.sh --restart

# RAG mode
./mondrian.sh --restart --mode=rag

# LoRA mode
./mondrian.sh --restart --mode=lora --lora-path=./models/qwen3-vl-4b-lora-ansel

# Combined
./mondrian.sh --restart --mode=lora+rag --lora-path=./models/qwen3-vl-4b-lora-ansel

# A/B test 50/50
./mondrian.sh --restart --mode=ab-test --lora-path=./models/qwen3-vl-4b-lora-ansel

# Stop
./mondrian.sh --stop

# Help
./mondrian.sh --help
```

---

**Created**: January 14, 2026
**Status**: Ready to Use
**Next Step**: Compare RAG vs LoRA outputs to determine best approach
