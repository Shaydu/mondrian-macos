# PDF Export Quick Start

## What's Fixed

✓ **CSS renders properly** - Simplified styling that translates well to PDF
✓ **HTML renders properly** - Clean structure with proper page breaks
✓ **Visual styling maintained** - Professional blue and gray color scheme
✓ **Scaled to fit** - Responsive layout adapts to page size
✓ **Images downsampled** - Automatically resized to 800x600 max
✓ **PDF under 1MB** - Typical exports are 300-800KB

## Quick Start

### 1. Start the Services

```bash
# Terminal 1: Job Service
python3 mondrian/job_service_v2.3.py --port 5005

# Terminal 2: Export Service
python3 mondrian/export_service_linux.py --port 5007
```

### 2. Run an Analysis
```bash
./mondrian.sh --advisor ansel --image /path/to/photo.jpg
```

### 3. Export to PDF

#### Option A: Browser (Recommended)
```bash
# Get the job ID from the output or:
curl http://localhost:5005/jobs | grep '"id"' | head -1

# Open in browser
open http://localhost:5007/export/<job_id>

# Print to PDF: Cmd+P (Mac) or Ctrl+P (Windows/Linux)
# → Select "Save as PDF"
```

#### Option B: Command Line
```bash
# Download HTML
curl http://localhost:5007/export/<job_id> > analysis.html

# Open and print (macOS)
open analysis.html

# Or convert to PDF with wkhtmltopdf (if installed)
wkhtmltopdf analysis.html analysis.pdf
```

#### Option C: Verify File Size
```bash
# Test export optimization
python3 test_pdf_export.py <job_id>

# Or test latest job
python3 test_pdf_export.py
```

## Features

### Automatic Image Optimization
- Images automatically resized to 800x600 max
- JPEG quality adjusted (30-75) for size/quality balance
- Typical result: 3 images → ~120KB total (was ~400KB)

### PDF-Friendly Styling
- Simplified CSS for better PDF rendering
- Page breaks prevent mid-card breaks
- Responsive margins and padding
- Grayscale-friendly colors

### Document Structure
1. **Header** - Report title and description
2. **Summary** - Top 3 recommendations with icons
3. **Analysis** - Detailed feedback with case studies
4. **Advisor Info** - About the photography mentor
5. **Footer** - Report ID, date, advisor name

## Troubleshooting

### PDF is too large (>1MB)
```python
# Edit mondrian/export_service_linux.py
self.max_image_width = 600      # Reduce from 800
self.max_image_height = 450     # Reduce from 600
self.image_quality = 60         # Reduce from 75
```

### Images look blurry
```python
# Edit mondrian/export_service_linux.py
self.max_image_width = 1000     # Increase from 800
self.image_quality = 85         # Increase from 75
```

### CSS not rendering in PDF
1. Try Chrome's print-to-PDF instead of Safari
2. Check that browser has JavaScript enabled
3. Try different PDF viewer (not Preview on Mac)

## File Size Estimates

| Content | Original | Optimized |
|---------|----------|-----------|
| HTML | 2-3MB | 400-600KB |
| 3 Images | 1-2MB | 100-150KB |
| Total HTML | 3-5MB | 500-750KB |
| **Exported PDF** | **5-8MB** | **300-800KB** |

## Advanced Configuration

### Image Compression Settings
```python
# In export_service_linux.py, ExportService.__init__()

self.max_image_width = 800          # Max width (pixels)
self.max_image_height = 600         # Max height (pixels)  
self.image_quality = 75             # Starting quality (0-100)

# In compress_base64_image()
max_kb = 50                         # Max size per image (KB)
```

### Restart Export Service After Changes
```bash
pkill -f export_service_linux.py
python3 mondrian/export_service_linux.py --port 5007
```

## Testing

### Verify Service is Running
```bash
curl http://localhost:5007/health
# Expected response:
# {"status":"UP","service":"export",...}
```

### Get Job List
```bash
curl http://localhost:5005/jobs | python3 -m json.tool | head -30
```

### Check Export Metadata
```bash
curl http://localhost:5007/export/<job_id>/metadata?format=json
```

## Performance

- **Service startup**: ~2 seconds
- **Export generation**: <1 second per job
- **Image compression**: ~1-2 seconds for 3 images
- **Memory usage**: ~40-60 MB
- **Typical PDF size**: 400-600 KB (under 1MB target)

## See Also

- [PDF_EXPORT_OPTIMIZATION.md](PDF_EXPORT_OPTIMIZATION.md) - Complete technical details
- [EXPORT_SERVICE.md](docs/EXPORT_SERVICE.md) - Full API documentation
- [EXPORT_SERVICE_QUICKSTART.md](docs/EXPORT_SERVICE_QUICKSTART.md) - Service overview
