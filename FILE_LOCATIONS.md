# 📂 File Locations & Navigation

## 🎓 New Learning Documents (7 Files Created)

All in `/Users/shaydu/dev/mondrian-macos/docs/`

### Read First
1. **[INDEX_EMBEDDINGS_RESOURCES.md](docs/INDEX_EMBEDDINGS_RESOURCES.md)**
   - Master index with reading paths
   - Links to all resources
   - Learning outcomes by document
   - Navigation guide

### Quick Reads (2-15 minutes)
2. **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - 2 min
   - Overview of everything
   - Cost/benefit table
   - Key numbers

3. **[CLIP_LORA_PRIMER.md](docs/CLIP_LORA_PRIMER.md)** - 15 min
   - Beginner-friendly explanations
   - What is CLIP/LoRA
   - Real examples
   - Q&A

### Implementation Guides
4. **[EMBEDDING_PRECOMPUTATION_GUIDE.md](docs/EMBEDDING_PRECOMPUTATION_GUIDE.md)** - 30 min
   - Step-by-step setup
   - Performance metrics
   - Common questions
   - Verification steps

5. **[VISUAL_GUIDE.md](docs/VISUAL_GUIDE.md)** - 10 min
   - Flowcharts and diagrams
   - Architecture diagrams
   - Decision trees
   - Performance comparisons

### Technical Details
6. **[EMBEDDINGS_INTEGRATION_STATUS.md](docs/EMBEDDINGS_INTEGRATION_STATUS.md)** - 20 min
   - Status: 70% complete
   - What's missing (3 phases)
   - Benefits breakdown
   - Implementation checklist
   - Architecture decisions

7. **[README_EMBEDDINGS_SETUP.md](docs/README_EMBEDDINGS_SETUP.md)** - 5 min
   - Master summary
   - Links to everything
   - Quick action plan
   - What to do next

### Summary (Root Level)
8. **[EMBEDDINGS_COMPLETE_SUMMARY.md](EMBEDDINGS_COMPLETE_SUMMARY.md)** - 5 min
   - What was found
   - What was created
   - Next steps
   - Quick links

---

## 🛠️ Scripts & Tools

### Pre-computation Script (FOUND)
📍 **Location**: `tools/rag/compute_image_embeddings_to_db.py`
- **Size**: 149 lines
- **Status**: Production-ready ✅
- **Purpose**: Pre-compute CLIP embeddings for all advisor images
- **Usage**:
  ```bash
  python tools/rag/compute_image_embeddings_to_db.py \
    --advisor_dir mondrian/source/advisor/photographer/ansel/ \
    --advisor_id ansel
  ```

### Related Tools
📍 **Location**: `tools/rag/` directory
- `compute_image_embeddings.py` - Generates .npy files
- `ingest_npy_embeddings.py` - Ingests .npy into database
- `index_advisor_techniques.py` - Indexes techniques
- Other RAG utilities

---

## 📦 Scripts to Archive

### Old Edge Pipeline Utilities
📍 **Location**: `scripts/` directory

**Move to archive:**
```
scripts/edge.py
scripts/edge_pipeline.py
scripts/edge-pipeline-v14.py
scripts/edge_pipeline_v*_utils.py (all 115 versions!)
scripts/edge_utils.py
```

**Command:**
```bash
mkdir -p scripts/archive
mv scripts/edge*.py scripts/archive/
```

### Keep These (Actively Used)
```
scripts/caption_service.py ✅
scripts/embedding_service.py ✅
scripts/rag_service.py ✅
scripts/job_service_v2.3.py ✅
scripts/json_to_html_converter.py ✅
scripts/technique_rag.py ✅
scripts/sqlite_helper.py ✅
scripts/start_services.py ✅
scripts/monitoring_service.py ✅
scripts/preview_service.py ✅
... (and others actively imported)
```

---

## 🗄️ Database & Configuration

### Database
📍 **Location**: `mondrian.db`
- **Table**: `image_captions` (stores embeddings)
- **Table**: `dimensional_profiles` (stores dimensional scores)

### Model Files
📍 **Location**: `adapters/` directory
- Pre-trained LoRA weights
- Ready to use

### Source Data
📍 **Location**: `mondrian/source/advisor/`
```
📁 mondrian/source/advisor/
├── 📁 photographer/
│   ├── 📁 ansel/
│   ├── 📁 okeefe/
│   └── ... (other photographers)
├── 📁 architect/
│   └── ... (architects)
└── 📁 painter/
    └── ... (painters)
```

---

## 📖 How to Navigate

### If You Have 5 Minutes
Go to: `docs/QUICK_REFERENCE.md`

### If You Have 15 Minutes
Go to: `docs/CLIP_LORA_PRIMER.md`

### If You Have 30 Minutes
1. Read: `docs/QUICK_REFERENCE.md` (2 min)
2. Follow: `docs/EMBEDDING_PRECOMPUTATION_GUIDE.md` (28 min)

### If You Have 1 Hour
1. Read: `docs/INDEX_EMBEDDINGS_RESOURCES.md` (2 min)
2. Read: `docs/QUICK_REFERENCE.md` (2 min)
3. Read: `docs/CLIP_LORA_PRIMER.md` (15 min)
4. Follow: `docs/EMBEDDING_PRECOMPUTATION_GUIDE.md` (28 min)
5. Skim: `docs/EMBEDDINGS_INTEGRATION_STATUS.md` (13 min)

### If You Have 2 Hours (Power User)
Read all 7 guides in order:
1. `docs/INDEX_EMBEDDINGS_RESOURCES.md`
2. `docs/QUICK_REFERENCE.md`
3. `docs/CLIP_LORA_PRIMER.md`
4. `docs/VISUAL_GUIDE.md`
5. `docs/EMBEDDING_PRECOMPUTATION_GUIDE.md`
6. `docs/EMBEDDINGS_INTEGRATION_STATUS.md`
7. `docs/README_EMBEDDINGS_SETUP.md`

Then run pre-computation script and plan Phase 1.

---

## ✅ Quick Checklist

### What To Do Right Now

- [ ] Open `docs/QUICK_REFERENCE.md` (2 min)
- [ ] Open `docs/CLIP_LORA_PRIMER.md` (15 min optional)
- [ ] Run: `python tools/rag/compute_image_embeddings_to_db.py --advisor_dir mondrian/source/advisor/photographer/ansel/ --advisor_id ansel`
- [ ] Verify: `sqlite3 mondrian.db "SELECT COUNT(*) FROM image_captions;"`
- [ ] ✅ You're done! 5x faster embeddings

### What To Do This Week

- [ ] Implement Phase 1 (independent embeddings)
  - Add to `BaselineStrategy`
  - Add to `LoRAStrategy`
  - Test combinations
- [ ] Benchmark improvements
- [ ] Archive old scripts (optional)

### What To Do Next Week (Optional)

- [ ] Implement Phase 2 (batch indexing)
- [ ] Create setup automation
- [ ] Documentation for users

---

## 🔗 All Files at a Glance

| File | Location | Purpose | Time |
|------|----------|---------|------|
| Master Index | `docs/INDEX_EMBEDDINGS_RESOURCES.md` | Navigation | 2 min |
| Quick Ref | `docs/QUICK_REFERENCE.md` | Overview | 2 min |
| Primer | `docs/CLIP_LORA_PRIMER.md` | Learning | 15 min |
| Precomp Guide | `docs/EMBEDDING_PRECOMPUTATION_GUIDE.md` | Setup | 30 min |
| Visual Guide | `docs/VISUAL_GUIDE.md` | Diagrams | 10 min |
| Status | `docs/EMBEDDINGS_INTEGRATION_STATUS.md` | Technical | 20 min |
| Setup Guide | `docs/README_EMBEDDINGS_SETUP.md` | Summary | 5 min |
| This File | `.` root directory | Locations | 5 min |
| **Pre-comp Script** | `tools/rag/compute_image_embeddings_to_db.py` | **Action** | **30 min** |

---

## 🎯 Start Here (Pick One)

**Option A: Just Give Me The Script (2 min)**
1. Run the script: `python tools/rag/compute_image_embeddings_to_db.py ...`
2. Done!

**Option B: Quick Understanding (5 min)**
1. Read: `docs/QUICK_REFERENCE.md`
2. Run the script
3. Done!

**Option C: Full Learning (1 hour)**
1. Read: `docs/CLIP_LORA_PRIMER.md`
2. Read: `docs/EMBEDDING_PRECOMPUTATION_GUIDE.md`
3. Run the script
4. Verify it works
5. Read: `docs/EMBEDDINGS_INTEGRATION_STATUS.md`
6. Plan Phase 1 implementation

**Recommended**: Option C (best value)

---

## 📞 Get Help

**Understanding CLIP/Embeddings?**
→ `docs/CLIP_LORA_PRIMER.md`

**How to run pre-computation?**
→ `docs/EMBEDDING_PRECOMPUTATION_GUIDE.md`

**What's the full picture?**
→ `docs/VISUAL_GUIDE.md`

**What should I implement next?**
→ `docs/EMBEDDINGS_INTEGRATION_STATUS.md`

**Where do I start?**
→ `docs/INDEX_EMBEDDINGS_RESOURCES.md`

---

**Everything is ready. Start with any link above. Most recommended: `docs/QUICK_REFERENCE.md`**

