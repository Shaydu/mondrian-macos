# Quick Fix: Run Services from Terminal.app

## Problem
The AI Advisor Service returns 500 errors because it's running from Cursor (no GPU access) and crashes when trying to load the MLX model.

## Solution
Restart services from Terminal.app (which has GPU entitlements):

### Step 1: Open Terminal.app
- Press `⌘ + Space`
- Type "Terminal"
- Press Enter

### Step 2: Restart Services
```bash
cd /Users/shaydu/dev/mondrian-macos
./restart_services_from_terminal.sh
```

This will:
1. Stop existing services (running from Cursor)
2. Start new services with GPU access
3. Wait for initialization
4. Test the AI Advisor Service

### Step 3: Run Batch Analysis
```bash
cd /Users/shaydu/dev/mondrian-macos
python3 batch_analyze_advisor_images.py --advisor ansel
```

## Expected Output
```
[1/12] af.jpg
  [INFO] Analyzing: af.jpg
  [OK] Analysis complete: af.jpg
  [OK] Valid profile: comp=8.5, light=9.0, overall=8.7
```

## If It Still Fails
See `MLX_METAL_CRASH_FIX.md` for alternative solutions (upgrade MLX, install Ollama, etc.)

## Why This Works
- **Cursor**: Electron app, limited GPU entitlements → MLX crashes
- **Terminal.app**: Native macOS app, full GPU entitlements → MLX works

The services will keep running in Terminal.app's background, and you can continue using Cursor for editing code.


