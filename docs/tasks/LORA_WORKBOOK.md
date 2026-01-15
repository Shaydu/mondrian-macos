# LoRA Fine-tuning Implementation Workbook

**Project**: Qwen3-VL-4B Fine-tuning on Photography Analysis Data

**Timeline**: 8-10 days

**Team**: [Your Name / Team]

---

## Phase 0: Data Audit & Linking (1 day)

**Objective**: Map analysis files to source images using database

### Pre-flight Checklist

- [ ] `mondrian.db` accessible at `./mondrian/mondrian.db`
- [ ] `mondrian/analysis_md/` contains ~80-90 JSON analysis files
- [ ] `mondrian/source/` contains ~80 source images
- [ ] Python 3.8+ installed
- [ ] Database schema understood (review `sqlite_helper.py`)

### Tasks

#### Task 0.1: Run Data Linker Script

```bash
cd /Users/shaydu/dev/mondrian-macos

python link_training_data.py \
    --db_path ./mondrian/mondrian.db \
    --source_dir ./mondrian/source \
    --analysis_dir ./mondrian/analysis_md \
    --advisor ansel \
    --output_dir ./training_data
```

**Expected Output**:
```
[OK] ansel: 60+ valid training examples
[SUCCESS] Manifest saved to ./training_data/training_data_manifest.json
```

**Verify**:
```bash
ls -la ./training_data/training_data_manifest.json
cat ./training_data/training_data_manifest.json | head -50
```

- [ ] Manifest file created
- [ ] Contains 60-80+ records for ansel advisor
- [ ] Records have required fields (image_path, analysis_path, job_id)

#### Task 0.2: Inspect Manifest

```bash
python -c "
import json
with open('./training_data/training_data_manifest.json') as f:
    m = json.load(f)
    print(f'Total advisors: {len(m[\"by_advisor\"])}')
    for adv, data in m['by_advisor'].items():
        print(f'  {adv}: {len(data[\"records\"])} examples')
"
```

- [ ] Manifest structure looks correct
- [ ] All advisor names expected (ansel, watkins, etc.)
- [ ] Minimum 60 examples for Ansel

**Notes**:
```
_________________________________________________________

_________________________________________________________
```

---

## Phase 1: Training Data Preparation (1 day)

**Objective**: Convert analysis markdown to training format

### Tasks

#### Task 1.1: Prepare Training Data

```bash
python prepare_training_data.py \
    --manifest ./training_data/training_data_manifest.json \
    --advisor ansel \
    --output_dir ./training_data \
    --train_split 0.8 \
    --val_split 0.2
```

**Expected Output**:
```
Prepared 60+ training examples (80/20 split)
Saved training_data_ansel_train.json
Saved training_data_ansel_val.json
Saved training_data_ansel_meta.json
```

**Verify**:
```bash
ls -la ./training_data/training_data_ansel_*.json

# Check train/val counts
python -c "
import json
for split in ['train', 'val']:
    with open(f'./training_data/training_data_ansel_{split}.json') as f:
        data = json.load(f)
        print(f'{split}: {len(data)} examples')
"
```

- [ ] Train file created with ~48+ examples (80%)
- [ ] Val file created with ~12+ examples (20%)
- [ ] Meta file created with statistics

#### Task 1.2: Validate Data Quality

```bash
python -c "
import json
with open('./training_data/training_data_ansel_train.json') as f:
    examples = json.load(f)
    for i, ex in enumerate(examples[:3]):
        print(f'Example {i+1}:')
        print(f'  Image: {ex[\"image_path\"]}')
        print(f'  Prompt len: {len(ex[\"prompt\"])}')
        print(f'  Response len: {len(str(ex[\"response\"]))}')
        print()
"
```

- [ ] All examples have image_path, prompt, response
- [ ] Prompts are substantial (>100 chars)
- [ ] Responses are substantial (>100 chars)
- [ ] Image paths exist

**Notes**:
```
_________________________________________________________

_________________________________________________________
```

---

## Phase 2: MLX Training Setup (2-3 days)

**Objective**: Implement MLX-native fine-tuning

### Pre-flight Checklist

- [ ] MLX installed: `pip install mlx>=0.15.0`
- [ ] mlx-vlm installed: `pip install mlx-vlm>=0.0.11`
- [ ] Other deps: `pip install numpy pillow tqdm`

### Investigation Tasks

#### Task 2.1: Investigate MLX-VLM LoRA Module

```bash
python -c "
import mlx_vlm
print('MLX-VLM modules:')
import pkgutil
for importer, modname, ispkg in pkgutil.iter_modules(mlx_vlm.__path__, prefix='mlx_vlm.'):
    print(f'  {modname} (package={ispkg})')
"
```

- [ ] Verify `mlx_vlm.lora` module exists
- [ ] Verify `mlx_vlm.trainer` package exists

#### Task 2.2: Review LoRA API

```bash
python -c "
from mlx_vlm import lora
print('LoRA module functions:')
print(dir(lora))
"
```

**Document findings**:
```
LoRA module API:
_________________________________________________________

_________________________________________________________
```

#### Task 2.3: Implement train_mlx_lora.py

Review [`train_mlx_lora.py`](train_mlx_lora.py) - contains TODO sections:

1. **LoRA adapter application** (around line 300)
   - Implement using `mlx_vlm.lora` API
   - Freeze base model parameters
   - Create and apply LoRA adapters

2. **Training loop** (around line 350)
   - Implement forward pass
   - Compute loss for next-token prediction
   - Backward pass via `mx.value_and_grad()`
   - Parameter updates

3. **Validation loop** (optional, around line 400)
   - Compute validation loss without updating gradients
   - Log metrics

**Tasks**:
- [ ] Review TODOs in `train_mlx_lora.py`
- [ ] Fill in LoRA adapter creation
- [ ] Test training loop with small dataset
- [ ] Verify loss computation works
- [ ] Test checkpoint saving

**Implementation Notes**:
```
_________________________________________________________

_________________________________________________________
```

---

## Phase 3: First Fine-tuning Run (1 day)

**Objective**: Execute complete fine-tuning

### Pre-run Checklist

- [ ] Training data prepared (train/val JSON files)
- [ ] `train_mlx_lora.py` fully implemented
- [ ] 16GB+ GPU memory available
- [ ] 10GB+ free storage for checkpoints

### Tasks

#### Task 3.1: Dry Run (Small Dataset)

```bash
# First test with just 5 examples
python -c "
import json
with open('./training_data/training_data_ansel_train.json') as f:
    examples = json.load(f)
    
# Save 5-example subset
with open('./training_data/training_data_ansel_test_small.json', 'w') as f:
    json.dump(examples[:5], f)
    
print('Created test dataset with 5 examples')
"

# Run training on small dataset
python train_mlx_lora.py \
    --train_data ./training_data/training_data_ansel_test_small.json \
    --output_dir ./models/qwen3-vl-4b-lora-test \
    --epochs 1 \
    --batch_size 1
```

**Check**:
- [ ] Training starts without errors
- [ ] Loss is computed and printed
- [ ] Model checkpoints are created

#### Task 3.2: Full Fine-tuning Run

```bash
python train_mlx_lora.py \
    --base_model "Qwen/Qwen3-VL-4B-Instruct" \
    --train_data ./training_data/training_data_ansel_train.json \
    --val_data ./training_data/training_data_ansel_val.json \
    --output_dir ./models/qwen3-vl-4b-lora-ansel \
    --epochs 3 \
    --batch_size 2 \
    --learning_rate 2e-4 \
    --warmup_steps 100 \
    --save_freq 250
```

**Monitoring**:
- [ ] Training starts (watch initial loss)
- [ ] GPU memory usage reasonable (<14GB)
- [ ] Loss decreases over steps
- [ ] Validation loss decreases over epochs

**Duration**: 6-12 hours depending on data size

**After training**:
```bash
ls -la ./models/qwen3-vl-4b-lora-ansel/
# Should contain:
#   adapter_config.json
#   adapter_model.safetensors
#   training_args.json
#   training_log.jsonl
```

- [ ] adapter_config.json present
- [ ] adapter_model.safetensors present (150MB+)
- [ ] training_args.json present
- [ ] training_log.jsonl has loss history

**Training Results Summary**:
```
Final Training Loss: ____________
Final Validation Loss: ____________
Total Training Time: ____________
GPU Memory Peak: ____________
```

**Notes**:
```
_________________________________________________________

_________________________________________________________
```

---

## Phase 4: Evaluation (1-2 days)

**Objective**: Compare base vs fine-tuned model

### Tasks

#### Task 4.1: Run Evaluation

```bash
python evaluate_lora.py \
    --base_model "Qwen/Qwen3-VL-4B-Instruct" \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --val_data ./training_data/training_data_ansel_val.json \
    --output_report ./evaluation/comparison_report.json \
    --max_examples 10  # Limit for faster evaluation
```

**Verify**:
```bash
ls -la ./evaluation/comparison_report.json
cat ./evaluation/comparison_report.json | python -m json.tool | head -100
```

- [ ] Report file created
- [ ] Contains metrics for base model
- [ ] Contains metrics for fine-tuned model
- [ ] Contains comparison/improvements

#### Task 4.2: Analyze Results

```bash
python -c "
import json
with open('./evaluation/comparison_report.json') as f:
    report = json.load(f)
    
print('Base Model:')
print(f\"  Format Compliance: {report['metrics']['base_model']['format_compliance']*100:.1f}%\")
print(f\"  Avg Score: {report['metrics']['base_model'].get('avg_score', 'N/A')}\")
print()

if 'fine_tuned_model' in report['metrics']:
    print('Fine-tuned Model:')
    print(f\"  Format Compliance: {report['metrics']['fine_tuned_model']['format_compliance']*100:.1f}%\")
    print(f\"  Avg Score: {report['metrics']['fine_tuned_model'].get('avg_score', 'N/A')}\")
    
    if 'improvements' in report['metrics']:
        print()
        print('Improvements:')
        for key, val in report['metrics']['improvements'].items():
            print(f'  {key}: {val}')
"
```

**Evaluation Results**:
```
Base Model Format Compliance: ____________%
Fine-tuned Format Compliance: ____________%
Improvement: ____________%

Base Model Avg Score: ____________
Fine-tuned Avg Score: ____________
Score Improvement: ____________

Inference Time Comparison: ____________
```

**Success Criteria**:
- [ ] Base model format compliance ≥90%
- [ ] Fine-tuned model format compliance ≥95%
- [ ] Score improvement visible (or at minimum no regression)
- [ ] Inference time acceptable (<10% overhead)

#### Task 4.3: Manual Quality Review

Review 5 sample outputs from evaluation report:

```bash
python -c "
import json
with open('./evaluation/comparison_report.json') as f:
    report = json.load(f)
    
for i, sample in enumerate(report['sample_results'][:3]):
    print(f'\\n=== Sample {i+1}: {sample[\"image\"]} ===')
    print(f'Base Output (first 200 chars): {sample[\"base_model\"][\"output\"][:200]}...')
    if 'fine_tuned_model' in sample:
        print(f'Fine-tuned Output (first 200 chars): {sample[\"fine_tuned_model\"][\"output\"][:200]}...')
"
```

**Manual Assessment**:

Sample 1:
- [ ] Base model output valid JSON: Yes/No
- [ ] Fine-tuned output valid JSON: Yes/No  
- [ ] Fine-tuned more specific: Yes/No
- [ ] Notes: ___________________________________

Sample 2:
- [ ] Base model output valid JSON: Yes/No
- [ ] Fine-tuned output valid JSON: Yes/No
- [ ] Fine-tuned more specific: Yes/No
- [ ] Notes: ___________________________________

**Overall Assessment**:
```
Does fine-tuned model show improvement?
___________________________________________________________
```

---

## Phase 5: Service Integration (1 day)

**Objective**: Integrate fine-tuned model with AI advisor service

### Pre-flight Checklist

- [ ] Fine-tuned model ready at `./models/qwen3-vl-4b-lora-ansel/`
- [ ] Service currently runs with base model
- [ ] [`LORA_SERVICE_INTEGRATION.md`](LORA_SERVICE_INTEGRATION.md) reviewed

### Tasks

#### Task 5.1: Modify ai_advisor_service.py

**Changes Required** (see [LORA_SERVICE_INTEGRATION.md](LORA_SERVICE_INTEGRATION.md)):

1. Add CLI arguments:
   - [ ] `--lora_path`
   - [ ] `--model_mode` (base, fine_tuned, ab_test)
   - [ ] `--ab_test_split`

2. Update `get_mlx_model()` function:
   - [ ] Check LoRA adapter files
   - [ ] Load LoRA config
   - [ ] Apply LoRA adapters (TODO implementation)
   - [ ] Return model, processor, is_fine_tuned flag

3. Update service initialization:
   - [ ] Call `get_mlx_model()` with appropriate args
   - [ ] Store model mode globally

**Implementation Checklist**:
- [ ] Added `--lora_path` argument
- [ ] Added `--model_mode` argument
- [ ] Updated `get_mlx_model()` to load LoRA
- [ ] Service initializes correctly

#### Task 5.2: Test Base Model (Backward Compatibility)

```bash
# Start service without --lora_path (should use base model)
python mondrian/ai_advisor_service.py --port 5100 &
SERVICE_PID=$!

# Wait for startup
sleep 5

# Test API
curl -X POST http://localhost:5100/analyze \
    -H "Content-Type: application/json" \
    -d '{"image": "test.jpg", "advisor": "ansel"}'

# Stop service
kill $SERVICE_PID
```

- [ ] Service starts without `--lora_path`
- [ ] API responds with valid JSON
- [ ] No errors in logs

#### Task 5.3: Test Fine-tuned Model

```bash
# Start service with --lora_path
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode fine_tuned &
SERVICE_PID=$!

# Wait for startup
sleep 5

# Test API
curl -X POST http://localhost:5100/analyze \
    -H "Content-Type: application/json" \
    -d '{"image": "test.jpg", "advisor": "ansel"}'

# Stop service
kill $SERVICE_PID
```

- [ ] Service starts with `--lora_path`
- [ ] API responds with valid JSON
- [ ] Response quality acceptable (spot check)

#### Task 5.4: Test A/B Mode (Optional)

```bash
# Start service in A/B test mode
python mondrian/ai_advisor_service.py \
    --port 5100 \
    --lora_path ./models/qwen3-vl-4b-lora-ansel \
    --model_mode ab_test \
    --ab_test_split 0.5 &
SERVICE_PID=$!

# Make multiple requests and check which model was used
for i in {1..10}; do
    curl -X POST http://localhost:5100/analyze ... > result_$i.json
done

kill $SERVICE_PID

# Check database to see model_used values
```

- [ ] A/B mode requests alternate between models
- [ ] Database tracks model_used field

**Integration Notes**:
```
_________________________________________________________

_________________________________________________________
```

---

## Phase 6: Iteration & Production (Ongoing)

**Objective**: Establish continuous improvement workflow

### Set Up Version Management

```bash
# Create versions directory
mkdir -p models/versions

# Save v1
cp -r ./models/qwen3-vl-4b-lora-ansel ./models/versions/qwen3-vl-4b-lora-ansel-v1

# Create symlink for active model
ln -s ./models/versions/qwen3-vl-4b-lora-ansel-v1 ./models/qwen3-vl-4b-lora-ansel-active
```

- [ ] Version directory created
- [ ] v1 saved

### Future Iterations

For each new fine-tuning cycle:

1. **Collect new data**
   - [ ] Run analysis workflow to generate new outputs
   - [ ] Add to `mondrian/analysis_md/`

2. **Re-link data**
   ```bash
   python link_training_data.py --advisor ansel --output_dir ./training_data
   ```
   - [ ] Manifest updated with new examples

3. **Prepare training data**
   ```bash
   python prepare_training_data.py --manifest training_data_manifest.json
   ```
   - [ ] New train/val split created

4. **Fine-tune v2**
   ```bash
   python train_mlx_lora.py --output_dir ./models/qwen3-vl-4b-lora-ansel-v2
   ```
   - [ ] v2 model trained

5. **Evaluate v2**
   ```bash
   python evaluate_lora.py --lora_path ./models/qwen3-vl-4b-lora-ansel-v2
   ```
   - [ ] v2 metrics compared to v1

6. **Deploy if improved**
   - [ ] If metrics better: switch active model to v2
   - [ ] If metrics worse: keep v1

---

## Final Checklist

### All Phases Complete

- [ ] **Phase 0**: Data linked via database (60-80+ examples)
- [ ] **Phase 1**: Training data prepared (train/val split)
- [ ] **Phase 2**: MLX training script implemented
- [ ] **Phase 3**: First fine-tuning completed successfully
- [ ] **Phase 4**: Evaluation shows improvements
- [ ] **Phase 5**: Service integrated and tested
- [ ] **Phase 6**: Iteration workflow established

### Documentation

- [ ] Guide reviewed: [`mondrian/docs/LORA_FINETUNING_GUIDE.md`](mondrian/docs/LORA_FINETUNING_GUIDE.md)
- [ ] Integration guide reviewed: [`LORA_SERVICE_INTEGRATION.md`](LORA_SERVICE_INTEGRATION.md)
- [ ] Index reviewed: [`LORA_DOCUMENTATION_INDEX.md`](LORA_DOCUMENTATION_INDEX.md)
- [ ] Team trained on new workflow

### Production Ready

- [ ] Model checkpoints versioned
- [ ] Rollback strategy tested
- [ ] Monitoring in place
- [ ] Database updated with model_used tracking
- [ ] Team knows how to update model

---

## Post-Implementation Review

**Completion Date**: _______________

**Total Time Spent**: _______________

**Major Challenges**:
```
_________________________________________________________

_________________________________________________________
```

**Lessons Learned**:
```
_________________________________________________________

_________________________________________________________
```

**Recommendations for Next Iteration**:
```
_________________________________________________________

_________________________________________________________
```

**Team Feedback**:
```
_________________________________________________________

_________________________________________________________
```

---

**Workbook Completed**: _______________

**Sign-off**: _______________

