# Technique-Based RAG - The Complete System

## 🎯 The Crux of the App

**This is what makes the advisor system unique**: We don't just compare images dimensionally - we **analyze and compare photographic TECHNIQUES**, then teach users the advisor's specific approaches.

### The Vision

**User uploads image** → **Detect their techniques** → **Compare to advisor's signature techniques** → **Grade based on advisor's approach** → **Recommend specific technical improvements**

Example:
> "You used shallow depth of field (f/2.8), but Ansel Adams' signature f/64 approach prioritizes deep DOF for front-to-back sharpness. Your composition (7/10) would improve to 9/10 by using f/11 or smaller, as seen in references like 'The Tetons and the Snake River' where everything from foreground rocks to distant mountains is perfectly sharp."

---

## 🔍 What We Analyze

### Ansel Adams Signature Techniques

1. **Zone System Tonal Range**
   - Full range from pure black to pure white
   - Rich midtones throughout
   - Grade: none/moderate/strong

2. **f/64 Deep Depth of Field**
   - Everything sharp from foreground to infinity
   - Large format precision
   - vs. modern shallow DOF trends

3. **Foreground Anchoring**
   - Strong foreground element (rocks, plants)
   - Establishes scale and depth
   - Lower third placement

4. **Compositional Techniques**
   - Rule of thirds
   - S-curves
   - Triangular composition
   - Leading lines

5. **Lighting Approaches**
   - Dramatic sidelight for texture
   - Golden hour warmth
   - High contrast (Zones II-IX)
   - Overcast diffusion

6. **Technical Precision**
   - Large format camera precision
   - Corrected perspective
   - Pre-visualization

---

## 📋 Complete Workflow

### Step 1: Download 10+ Advisor Images (Automatic Metadata!)

```bash
python3 scripts/download_with_metadata.py --advisor ansel
```

**Downloads:**
- 10+ curated Ansel Adams photographs
- Automatic metadata from Wikimedia (title, date, description)
- Diverse technique examples:
  - Iconic landscapes (Tetons, Clearing Winter Storm)
  - Zone System mastery examples
  - f/64 Group deep DOF
  - Texture and detail work
  - Various compositions and lighting

---

### Step 2: Review Images & Metadata

```bash
python3 scripts/preview_metadata.py --advisor ansel
```

Opens beautiful HTML preview showing:
- All 10+ images
- Titles and descriptions
- Historical context
- What you can enhance (significance, techniques)

---

### Step 3: Index with Dimensional Analysis

```bash
# Start AI service
python3 mondrian/ai_advisor_service.py --port 5100

# Index images (creates dimensional profiles)
python3 tools/rag/index_with_metadata.py \
  --advisor ansel \
  --metadata-file mondrian/source/advisor/photographer/ansel/metadata.yaml
```

**This creates:**
- Dimensional scores (8 dimensions × 10 images)
- Dimensional comments
- Metadata (titles, dates, significance)

---

### Step 4: Analyze Advisor Techniques (THE KEY STEP!)

```bash
python3 tools/rag/analyze_advisor_techniques.py --advisor ansel
```

**This is the crux!** The system analyzes the VISUAL content of each advisor image:

```
[1/10] Adams_The_Tetons_and_the_Snake_River.jpg
    [→] Detecting techniques...
    [✓] Detected techniques:
        Zone System: strong
        DOF: deep_dof_f64
        Foreground Anchor: strong
        Composition: rule_of_thirds
        Lighting: golden_hour
```

**Stores in database:**
```json
{
  "zone_system": "strong",
  "depth_of_field": "deep_dof_f64",
  "foreground_anchor": "strong",
  "composition": "rule_of_thirds",
  "lighting": "golden_hour",
  "technical_precision": "high"
}
```

**Now we know**: This advisor consistently uses deep DOF, strong foreground anchoring, Zone System, etc.

---

### Step 5: User Uploads Image (RAG Magic!)

```bash
curl -X POST http://localhost:5005/upload \
  -F "image=@user_landscape.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

**What happens:**

1. **Detect user's techniques**:
   ```json
   {
     "zone_system": "moderate",
     "depth_of_field": "shallow_dof",  // ← Different from Adams!
     "foreground_anchor": "none",       // ← Missing key technique!
     "composition": "rule_of_thirds",   // ← Match!
     "lighting": "overcast_diffused"
   }
   ```

2. **Find similar advisor images** (by dimensional scores)

3. **Compare techniques** (THIS IS THE CRUX):
   - User: shallow DOF
   - Adams (all 10 refs): deep DOF (f/64)
   - **Gap identified!**

4. **Generate technique-based feedback**:
   > "Your composition follows rule of thirds (7/10), which aligns well with Adams' approach seen in 'The Tetons and the Snake River'. However, you've used shallow depth of field (f/2.8), while Adams' signature f/64 technique—evident in all reference images—prioritizes front-to-back sharpness. 
   >
   > **Your DOF grade: 5/10** (doesn't match advisor's approach)
   >
   > **Recommendation**: Use f/11 or smaller aperture. This will bring your foreground and background into sharp focus, matching the deep DOF mastery shown in references. Additionally, you're missing foreground anchoring—consider including rocks or plants in the lower third to establish scale and depth, as Adams does in 9 out of 10 references."

---

## 🎨 The Power: Technique-Based Grading

### Traditional Dimensional RAG (What we had):
- "Your composition: 7/10"
- "Reference has 9/10"
- Generic advice

### Technique-Based RAG (What we have now):
- "You used shallow DOF (f/2.8)"
- "Adams uses deep DOF (f/64) in 10/10 references"
- **Grade adjusted because technique doesn't match advisor**
- **Specific recommendation**: "Use f/11 or smaller to match Adams' approach"

---

## 📊 Grading Logic

### Before (Dimensional Only):
```
Composition score: 7/10
Lighting score: 8/10
→ Generic comparison
```

### After (Technique-Based):
```
Composition: 7/10 base score
  ✓ Rule of thirds (matches advisor) → +1
  ✗ No foreground anchor (advisor uses in 9/10) → -1
  = Final: 7/10 with specific gap identified

Lighting: 8/10 base score
  ✓ Good tonal range → keep
  ✗ Zone System not as strong as refs → room to improve
  
Depth of Field: NEW METRIC!
  ✗ Shallow DOF (f/2.8) vs. advisor's f/64
  = Major technique gap
  → Recommendation: "Use f/11+ for Adams' style"
```

---

## 🚀 Complete Example Session

```bash
# 1. Download 10 images with auto-metadata
python3 scripts/download_with_metadata.py --advisor ansel
# → 10 images downloaded
# → Metadata auto-fetched from Wikimedia

# 2. Preview in browser
python3 scripts/preview_metadata.py --advisor ansel
# → Opens HTML preview
# → Review images and metadata

# 3. Index for dimensional analysis
python3 tools/rag/index_with_metadata.py --advisor ansel --metadata-file ...
# → 10 dimensional profiles created

# 4. Analyze techniques (THE CRUX!)
python3 tools/rag/analyze_advisor_techniques.py --advisor ansel
# → Detects techniques in all 10 images
# → Stores technique patterns

# 5. User uploads with RAG
curl -X POST http://localhost:5005/upload \
  -F "image=@user_image.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"

# → System compares user techniques to advisor techniques
# → Grades based on technique alignment
# → Provides specific technical recommendations
```

---

## 💡 Why This is Powerful

### Teaching Through Technique Comparison

**User learns:**
- "Adams uses f/64 in 10/10 references" → Pattern recognition
- "Your f/2.8 doesn't match this approach" → Gap identification
- "Use f/11+ to match the technique" → Actionable advice
- "See 'The Tetons' for example" → Visual reference

**Not just:**
- "Your score is 7/10" → Vague
- "Try harder" → Not actionable

### Advisor-Specific Grading

**Ansel Adams grading:**
- Deep DOF highly valued
- Zone System usage critical
- Foreground anchoring expected

**vs. Modern Portrait grading (future):**
- Shallow DOF highly valued
- Bokeh quality matters
- Subject isolation critical

**Same image, different grades based on advisor's philosophy!**

---

## 🔧 Technical Architecture

```
User Image
    ↓
[Detect user techniques]
    ↓ 
{zone_system: moderate, dof: shallow, ...}
    ↓
[Find similar advisor images by dimensions]
    ↓
[Retrieve advisor techniques from DB]
    ↓
{zone_system: strong, dof: deep_dof_f64, ...}
    ↓
[Compare techniques]
    ↓
Gaps: {dof: mismatch, foreground: missing}
    ↓
[Build RAG prompt with technique comparison]
    ↓
LLM: "You used f/2.8 but Adams uses f/64 in all refs..."
    ↓
Output: Technique-based feedback with specific recommendations
```

---

## 📈 Roadmap

### Phase 1: ✅ Complete
- [x] Download 10 images
- [x] Automatic metadata
- [x] Preview system
- [x] Dimensional indexing
- [x] Technique detection script
- [x] Technique-based prompt augmentation

### Phase 2: In Progress
- [ ] Test with real images
- [ ] Refine technique detection prompts
- [ ] Validate grading adjustments
- [ ] Add more Ansel Adams images (20+)

### Phase 3: Future
- [ ] Add other advisors (Mondrian, O'Keeffe)
- [ ] Technique detection for user images
- [ ] Automatic technique comparison
- [ ] Visual technique highlighting in UI

---

## 🎯 The Key Insight

**The crux of the app isn't just comparing images—it's teaching photography through the master's specific techniques.**

Every recommendation should answer:
1. What technique did you use?
2. What technique does the advisor use?
3. Why is the advisor's technique better for this style?
4. How do you apply it? (specific, actionable)
5. Which reference image shows this technique best?

**This transforms feedback from generic to masterclass-quality teaching.**

---

## Next Steps

```bash
# Try it now!
python3 scripts/download_with_metadata.py --advisor ansel
python3 scripts/preview_metadata.py --advisor ansel
# Review, then index and analyze!
```

**Your users will learn not just what's wrong, but HOW to shoot like Ansel Adams.** 🎉

