# RAG Metadata Workflow - Complete Guide

## 🎯 Overview

This workflow automatically downloads advisor images from Wikimedia Commons WITH metadata, lets you review them, then indexes them for RAG queries.

**No manual YAML editing required!** Metadata is fetched automatically.

---

## 📋 Workflow Steps

### Step 1: Download Images + Metadata (Automatic!)

```bash
# Download Ansel Adams images with automatic metadata from Wikimedia
python3 scripts/download_with_metadata.py --advisor ansel
```

**What this does:**
- ✅ Downloads 5 high-resolution Ansel Adams photographs
- ✅ Fetches metadata from Wikimedia Commons API:
  - Title (e.g., "The Tetons and the Snake River")
  - Artist/Creator
  - Date taken
  - Description
  - License information
- ✅ Saves images to `mondrian/source/advisor/photographer/ansel/`
- ✅ Generates `metadata.yaml` automatically

**Output:**
```
Downloaded 5 images for ansel
Metadata saved to: mondrian/source/advisor/photographer/ansel/metadata.yaml
```

---

### Step 2: Preview & Review

```bash
# Generate HTML preview page
python3 scripts/preview_metadata.py --advisor ansel
```

**What this does:**
- ✅ Generates beautiful HTML preview page
- ✅ Shows all images with their metadata
- ✅ Opens automatically in your browser
- ✅ Stats: how many images have titles, descriptions, etc.

**The preview shows:**
- 🖼️ Full image display
- 📝 Title, artist, date, location
- 📖 Description
- 🏛️ Historical significance (if available)
- 🎨 Techniques used (if available)
- 🔗 Link to Wikimedia Commons source

**Review checklist:**
- [ ] Are all images displaying correctly?
- [ ] Are titles accurate?
- [ ] Are descriptions meaningful?
- [ ] Do you want to add significance or techniques?

---

### Step 3: Edit Metadata (Optional)

If you want to enhance the metadata:

```bash
# Open the YAML file
open mondrian/source/advisor/photographer/ansel/metadata.yaml
```

**What you can add:**
- `significance`: Why this artwork matters historically
- `techniques`: Array of photographic techniques demonstrated
- `location`: More specific location info

**Example enhancement:**
```yaml
- filename: "Adams_The_Tetons_and_the_Snake_River.jpg"
  title: "The Tetons and the Snake River"
  date_taken: "1942"
  description: "Iconic landscape showing..."
  location: "Grand Teton National Park, Wyoming"
  
  # ADD THESE:
  significance: "One of Ansel Adams' most famous works, selected for the Voyager Golden Record"
  techniques:
    - "Zone System tonal control"
    - "Deep depth of field (f/64)"
    - "Foreground anchoring"
```

After editing, preview again:
```bash
python3 scripts/preview_metadata.py --advisor ansel
```

---

### Step 4: Index with Metadata

```bash
# Start AI service (if not running)
python3 mondrian/ai_advisor_service.py --port 5100

# In another terminal, index the images
python3 tools/rag/index_with_metadata.py \
  --advisor ansel \
  --metadata-file mondrian/source/advisor/photographer/ansel/metadata.yaml
```

**What this does:**
- ✅ Analyzes each image with AI
- ✅ Extracts dimensional profiles
- ✅ **Merges with metadata** from YAML
- ✅ Saves to database with rich context

**Database now contains:**
- Dimensional scores (8 dimensions)
- Dimensional comments
- **Image title** (not filename!)
- **Date and location**
- **Historical significance**
- **Techniques used**

---

### Step 5: Use RAG with Rich Metadata

```bash
curl -X POST http://localhost:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

**What the LLM now sees:**

Instead of:
> "Similar to 2.jpg (composition: 8.5/10)..."

You get:
> "Similar to **The Tetons and the Snake River** (1942), one of Ansel Adams' 
> most celebrated works that demonstrates his mastery of the Zone System 
> and f/64 Group principles. This iconic photograph, selected for the 
> Voyager Golden Record, achieves exceptional composition (8.5/10) through..."

---

## 🔄 Complete Example

```bash
# 1. Download images + metadata (automatic!)
python3 scripts/download_with_metadata.py --advisor ansel

# 2. Preview in browser
python3 scripts/preview_metadata.py --advisor ansel

# 3. [Optional] Edit metadata.yaml to add significance/techniques
open mondrian/source/advisor/photographer/ansel/metadata.yaml

# 4. Index with metadata
python3 mondrian/ai_advisor_service.py --port 5100  # Terminal 1
python3 tools/rag/index_with_metadata.py \
  --advisor ansel \
  --metadata-file mondrian/source/advisor/photographer/ansel/metadata.yaml  # Terminal 2

# 5. Test RAG
curl -X POST http://localhost:5005/upload \
  -F "image=@source/mike-shrub.jpg" \
  -F "advisor=ansel" \
  -F "enable_rag=true"
```

---

## 📊 Supported Advisors

Currently configured in `download_with_metadata.py`:

- **ansel** - 5 Ansel Adams photographs
- **watkins** - 2 Carleton Watkins works
- **weston** - 2 Edward Weston photographs

**Add more:**
```bash
# Download all configured advisors
python3 scripts/download_with_metadata.py --advisor all
```

---

## 🎨 Customization

### Add New Advisors

Edit `scripts/download_with_metadata.py`:

```python
ADVISOR_ARTWORKS = {
    'ansel': [...],
    'your_advisor': [
        'File:Famous Artwork Title.jpg',
        'File:Another Famous Work.jpg',
    ]
}
```

Then run:
```bash
python3 scripts/download_with_metadata.py --advisor your_advisor
```

### Manual Images (Not from Wikimedia)

If you have your own images:

1. Create `metadata.yaml` manually:
```yaml
images:
  - filename: "my_image.jpg"
    title: "My Artwork"
    date_taken: "2024"
    description: "..."
    significance: "..."
    techniques: []
```

2. Preview and index as usual

---

## 🔍 Troubleshooting

**Images not downloading?**
```bash
# Check network connectivity
curl https://commons.wikimedia.org/

# Try with verbose output
python3 scripts/download_with_metadata.py --advisor ansel --verbose
```

**Metadata missing?**
- Some Wikimedia files lack complete metadata
- Edit `metadata.yaml` manually to fill gaps
- Or add significance/techniques after download

**Preview not opening?**
```bash
# Manually open the preview file
open preview/metadata_preview.html
```

**Indexing fails?**
- Ensure AI service is running on port 5100
- Check that image files match filenames in metadata.yaml
- Verify database exists and has schema

---

## 📚 What You Get

### Automatic Metadata
- Title, artist, date (from Wikimedia)
- Description (from Wikimedia)
- License info (for attribution)
- High-resolution images

### Optional Enhancements
- Historical significance (add manually or via AI)
- Techniques demonstrated (add manually or via AI)
- Specific location details

### In RAG Queries
- LLM references actual artwork titles
- Historical context in feedback
- Meaningful comparisons to master works
- Educational value beyond technical feedback

---

## 🎯 Benefits

**Before:** 
- "Your image is similar to 2.jpg"
- No context about why it matters
- Filenames are meaningless

**After:**
- "Your image shares qualities with The Tetons and the Snake River (1942)"
- Historical significance explained
- Techniques referenced by name
- Learning about photography history while improving

---

## Next Steps

1. ✅ **Download images**: `python3 scripts/download_with_metadata.py --advisor ansel`
2. ✅ **Review in browser**: `python3 scripts/preview_metadata.py --advisor ansel`  
3. ⚙️ **Index when ready**: `python3 tools/rag/index_with_metadata.py ...`
4. 🚀 **Use RAG**: Upload images with `enable_rag=true`

**Your feedback will now reference actual artworks with historical context!** 🎉




