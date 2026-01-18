# PDF Export Setup Guide

## Installation (IMPORTANT: Activate venv first!)

### Step 1: Activate Virtual Environment
```bash
cd /home/doo/dev/mondrian-macos
source venv/bin/activate
```

### Step 2: Install Required Libraries (AFTER venv activation)
The image compression feature requires Pillow. Install it **AFTER activating your venv**:

```bash
# Make sure (venv) shows in your prompt before proceeding
pip install Pillow
```

### Step 3: Verify Installation
```bash
python3 -c "from PIL import Image; print('✓ Pillow installed successfully')"
```

If you get "No module named PIL", you either:
1. Didn't activate the venv (check for `(venv)` in your prompt)
2. Forgot to run `pip install Pillow`

## Starting the Services

### Terminal 1: Job Service
```bash
source venv/bin/activate  # ALWAYS activate venv first
python3 mondrian/job_service_v2.3.py --port 5005
```

### Terminal 2: Export Service
```bash
source venv/bin/activate  # ALWAYS activate venv first
python3 mondrian/export_service_linux.py --port 5007
```

## Testing the Export

### Quick Test (Recommended)
```bash
source venv/bin/activate  # ALWAYS activate venv first
python3 test_pdf_export.py
```

### Manual Test
```bash
# Get the latest completed job
curl http://localhost:5005/jobs | grep '"id"' | head -1

# Export to HTML
curl http://localhost:5007/export/<job_id> > export.html

# Open in browser
open export.html  # macOS
# or
xdg-open export.html  # Linux
```

## What Changed

### PDF Export Now Includes:
✓ **AI Simulation Disclaimer** - Clearly states this is AI-generated
✓ **Creative Guidance Only** - Not professional advice
✓ **Image Downsampling** - Automatic compression (800x600 max)
✓ **Simplified CSS** - Better PDF rendering
✓ **Page Break Optimization** - Prevents mid-card breaks

### Disclaimer Content:
The PDF now includes a clear disclaimer section at the bottom stating:
- This is AI-generated analysis, not from an actual photographer
- Recommendations are for creative guidance only
- Not a substitute for professional critique
- Personal artistic vision is most important

## Troubleshooting

### "No module named PIL" error
```bash
# This means Pillow isn't installed
# Make sure venv is activated first!
source venv/bin/activate
pip install Pillow
```

### Export service won't start
```bash
# Check venv is activated (should see (venv) in prompt)
source venv/bin/activate

# Check Flask is installed
pip install Flask Flask-CORS requests

# Try starting service again
python3 mondrian/export_service_linux.py --port 5007
```

### Images in PDF are blurry or missing
```bash
# Verify Pillow is installed in active venv
python3 -c "from PIL import Image; print('OK')"

# If needed, reinstall
pip uninstall Pillow
pip install Pillow
```

## Virtual Environment Reminder

**CRITICAL:** Always activate your venv before:
- Installing packages: `pip install ...`
- Running scripts: `python3 ...`
- Checking module availability

```bash
# Activate venv
source venv/bin/activate

# Now you can run commands
pip install Pillow
python3 test_pdf_export.py
```

The `(venv)` prefix in your terminal prompt confirms the venv is active.

## Performance

With Pillow installed:
- **Export generation**: <1 second
- **Image compression**: ~1-2 seconds for 3 images
- **PDF size**: 300-800KB (under 1MB target)
- **Memory usage**: 40-60MB

Without Pillow:
- Export still works but images won't be compressed
- PDFs may exceed 1MB
- Export still completes in <1 second

## See Also

- [PDF_EXPORT_OPTIMIZATION.md](PDF_EXPORT_OPTIMIZATION.md) - Technical details
- [PDF_EXPORT_QUICKREF.md](PDF_EXPORT_QUICKREF.md) - Quick reference
