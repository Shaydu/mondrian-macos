# Training Data Sources & Expansion Strategy

**Goal**: Scale from 16 training examples to 500+ with proper dimensional analysis

---

## Available Data Sources

### 1. CADB (Composition Assessment Dataset) ⭐ PRIORITY

**What it is:**
- 1,000+ images with composition quality scores (1-10)
- Free dataset from BCMI lab
- GitHub: `github.com/bcmi/Image-Composition-Assessment-Dataset`

**Advantages:**
- ✅ Large scale (1,000+ images)
- ✅ Composition scores as ground truth
- ✅ Can validate your model's composition dimension
- ✅ Generates training data in 2-4 hours

**How to use:**
```bash
# Download CADB and prepare for analysis
python scripts/training/download_cadb_dataset.py

# This creates:
# - training/cadb/images/        (1000+ photos)
# - training/cadb/metadata/       (composition scores)
# - scripts/training/analyze_cadb_batch.py  (analysis script)

# Then analyze all images
python scripts/training/analyze_cadb_batch.py

# Output: augmented_training_data_cadb.jsonl (1000+ examples)
```

**Expected Result:**
- 1,000 training examples with:
  - ✅ 9-dimensional scores (from AI advisor)
  - ✅ Composition validated against CADB ground truth (±1.0 tolerance)
  - ✅ All other dimensions analyzed fresh
  - ✅ Recommendations and citations ready

---

### 2. Wikimedia Commons Expansion (Quality First)

**What it is:**
- High-quality photographs from masters: Adams, Watkins, Weston, Lange, Cartier-Bresson, etc.
- Free public domain / CC licensed images
- Already have scripts to download from Wikimedia

**Advantages:**
- ✅ Highest quality (masterworks)
- ✅ Your existing photographers + new ones
- ✅ Small amount needed (50-100) for high impact
- ✅ Human-curated quality

**How to use:**
```bash
# Download more from existing photographers
python scripts/training/download_wikimedia_photographers.py

# Download from specific photographer
python scripts/training/download_wikimedia_photographers.py \
  --photographer ansel_adams --count 50

# Output: training/wikimedia_expanded/images/
```

**Speed:**
- 50 images: ~30 minutes
- 100 images: ~1 hour (includes download + analysis)

---

### 3. AVA Dataset (Aesthetic Visual Analysis)

**What it is:**
- 255,000+ images with crowdsourced aesthetic ratings
- Hugging Face: `qingrui/AVA_dataset`
- General image aesthetics (not photo-specific)

**Advantages:**
- ✅ Massive scale
- ✅ Already on Hugging Face
- ✅ Well-structured metadata

**Disadvantages:**
- ❌ Generic aesthetics, not photography-specific
- ❌ Variable quality
- ❌ Would need analysis of all images

**Usage:**
```python
from datasets import load_dataset
ava = load_dataset("qingrui/AVA_dataset")  # ~50 GB
```

---

### 4. Photo-Critique Dataset (Hugging Face)

**What it is:**
- ~5,000 image-critique pairs
- Hugging Face: `defog/photo-critique`
- Images + human critique text

**Advantages:**
- ✅ Already has critique text
- ✅ Photography-specific feedback

**Disadvantages:**
- ❌ Text feedback, not dimensional scores
- ❌ Would need to parse critique → dimensions
- ❌ Only 5,000 images

---

### 5. Unsplash / Pexels / Pixabay (Scale)

**What it is:**
- Free stock photos (1M+ available)
- APIs available with rate limiting

**Advantages:**
- ✅ Unlimited scale
- ✅ APIs available

**Disadvantages:**
- ❌ Variable quality
- ❌ Need to analyze all
- ❌ No ground truth scores

---

## Recommended Approach: Phased Expansion

### Phase 1: CADB Foundation (Target: +1,000 examples)
**Duration**: 2-4 hours of GPU time  
**Effort**: 30 minutes setup + let it run

```bash
# Step 1: Download and prepare
python scripts/training/download_cadb_dataset.py --analyze

# Step 2: Start AI advisor service
python mondrian/job_service_v2.3.py --port 5005

# Step 3: Run batch analysis (in another terminal)
python scripts/training/analyze_cadb_batch.py

# Step 4: Validate and merge training data
python scripts/training/merge_training_datasets.py \
  --existing training/20260121-qwen3-vl-4b/training_data_train.jsonl \
  --cadb training/cadb/augmented_training_data_cadb.jsonl \
  --output training/20260122-combined/training_data_combined.jsonl
```

**Result**: 16 + 1,000 = **1,016 examples**

---

### Phase 2: Quality Focus (Target: +100 examples)
**Duration**: 2-3 hours  
**Effort**: 15 minutes setup + analyze

```bash
# Download more masterworks
python scripts/training/download_wikimedia_photographers.py

# This downloads:
# - 100 more Ansel Adams
# - 50 more Henri Cartier-Bresson  
# - 50 more Dorothea Lange
# - 75 more Vivian Maier
# - 50 each for other photographers
# Total: ~350 more high-quality images

# Analyze them
python scripts/training/batch_analyze_images.py \
  --source training/wikimedia_expanded/images \
  --output training/wikimedia_expanded/augmented_training_data.jsonl
```

**Result**: 1,016 + 350 = **1,366 examples**

---

### Phase 3: Custom Dataset (Optional, Target: +500 examples)
**Duration**: Variable  
**Effort**: High, but most flexible

```bash
# Download images from Unsplash API
python scripts/training/download_unsplash_dataset.py \
  --keywords photography composition landscape portrait \
  --count 500

# Analyze
python scripts/training/batch_analyze_images.py \
  --source training/unsplash/images \
  --output training/unsplash/augmented_training_data.jsonl
```

**Result**: 1,366 + 500 = **1,866 examples**

---

## Implementation Details

### Batch Analysis with AI Advisor

Once you have images, analyze them:

```python
# scripts/training/batch_analyze_images.py

import json
from pathlib import Path
from mondrian.ai_advisor_service_linux import QwenAdvisor

# Initialize advisor
advisor = QwenAdvisor(
    model_name="Qwen/Qwen2-VL-7B-Instruct",
    adapter_path=None,  # Start with base model
    load_in_4bit=True
)

# Analyze each image
examples = []
for image_path in images:
    # Get analysis
    analysis = advisor.analyze_image(
        str(image_path),
        advisor="ansel",
        mode="rag"
    )
    
    # Extract dimensions
    dimensions = analysis.get('dimensions', [])
    
    # Create training example
    example = {
        "messages": [
            {
                "role": "user",
                "content": f"<image>\nAnalyze this photograph..."
            },
            {
                "role": "assistant",
                "content": json.dumps({
                    "dimensions": dimensions,
                    "overall_score": analysis.get('overall_score'),
                    "key_strengths": analysis.get('key_strengths'),
                    "priority_improvements": analysis.get('priority_improvements')
                })
            }
        ],
        "image_path": str(image_path)
    }
    examples.append(example)

# Save
with open("augmented_training_data.jsonl", 'w') as f:
    for ex in examples:
        f.write(json.dumps(ex) + '\n')
```

### Merging Datasets

```python
# scripts/training/merge_training_datasets.py

def merge_datasets(*jsonl_files):
    """Merge multiple JSONL training files."""
    all_examples = []
    
    for file_path in jsonl_files:
        with open(file_path) as f:
            for line in f:
                all_examples.append(json.loads(line))
    
    return all_examples
```

---

## Validation & Quality Assurance

### For CADB Dataset:
```python
# Validate composition scores match ground truth
cadb_mapping = load_json("training/cadb/metadata/cadb_composition_mapping.json")

for example in training_examples:
    cadb_score = cadb_mapping[example['image_name']]['composition_score']
    model_score = example['dimensions']['Composition']['score']
    
    error = abs(cadb_score - model_score)
    if error > 1.0:
        print(f"⚠️  Large error for {example['image_name']}: {error:.1f}")
```

### For All Datasets:
```python
# Check data quality
- All 9 dimensions present ✓
- Scores in range 1-10 ✓
- Comments < 500 chars ✓
- Recommendations actionable ✓
- No duplicate images ✓
- Image files exist ✓
```

---

## Dataset Combinations & Size Estimates

| Combination | Examples | GPU Time | Quality |
|---|---|---|---|
| Current only | 16 | - | ⭐⭐⭐⭐⭐ |
| + CADB | 1,016 | 4 hrs | ⭐⭐⭐⭐ |
| + Wikimedia | 1,366 | 6 hrs | ⭐⭐⭐⭐ |
| + Unsplash | 1,866 | 8 hrs | ⭐⭐⭐ |
| + AVA sample | 2,866 | 12 hrs | ⭐⭐ |

**Recommendation**: Stop at **1,366 examples** (CADB + Wikimedia)
- Good balance of quality & quantity
- All examples analyzed with same AI advisor
- Composition scores validated
- ~6 hours of GPU time

---

## Next Steps

1. **Start CADB Download**
   ```bash
   python scripts/training/download_cadb_dataset.py
   ```

2. **Review CADB Images** (optional)
   ```bash
   ls -lh training/cadb/images/ | head -20
   ```

3. **Batch Analyze** (requires AI advisor running)
   ```bash
   python mondrian/job_service_v2.3.py &
   python scripts/training/analyze_cadb_batch.py
   ```

4. **Fine-tune on Combined Dataset**
   ```bash
   python train_lora_qwen3vl.py \
     --train-jsonl training/cadb/augmented_training_data_cadb.jsonl \
     --val-jsonl training/20260121-qwen3-vl-4b/augmented_training_data_val.jsonl
   ```

---

## Troubleshooting

**Q: CADB download fails**  
A: Download manually from `github.com/bcmi/Image-Composition-Assessment-Dataset`

**Q: Batch analysis too slow**  
A: Use `--sample N` flag to test on first N images

**Q: Composition scores don't match CADB**  
A: This is OK! Your AI advisor might score differently. Document the difference:
   ```
   CADB Score: 8.0
   Advisor Score: 7.5
   Difference: -0.5 (acceptable)
   ```

**Q: Images are too large for GPU**  
A: Add `--max-size 800` flag to resize before analysis

---

## Resources

- CADB: https://github.com/bcmi/Image-Composition-Assessment-Dataset
- AVA: https://www.ava-net.top/
- Photo-Critique: https://huggingface.co/datasets/defog/photo-critique
- Unsplash API: https://unsplash.com/developers
