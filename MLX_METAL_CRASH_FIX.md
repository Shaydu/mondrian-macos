# MLX Metal Device Crash - Diagnosis and Fix

## Problem Summary

The AI Advisor Service is crashing when trying to use MLX because MLX cannot enumerate Metal devices on your system. This causes an `NSRangeException` crash:

```
*** -[__NSArray0 objectAtIndex:]: index 0 beyond bounds for empty array
```

**Root Cause**: MLX's Metal device initialization is trying to access index 0 of an empty Metal devices array.

## Your System

- **Hardware**: Apple M1 Pro with 16 GPU cores
- **Metal Support**: ✓ Supported (confirmed via `system_profiler`)
- **MLX Version**: 0.30.1
- **Problem**: MLX cannot enumerate Metal devices despite Metal being available

## Why This Happens

**CRITICAL DISCOVERY**: You're running Python from **Cursor IDE** (Electron app), not directly from Terminal!

The crash happens because:
1. ✅ Metal framework IS available on your M1 Pro
2. ✅ Metal IS supported (confirmed via `system_profiler`)
3. ❌ **But Cursor/Electron may not have GPU entitlements**
4. ❌ Python processes launched from Cursor inherit limited entitlements
5. ❌ MLX tries to enumerate Metal devices → gets EMPTY array
6. ❌ MLX crashes trying to access `device[0]` without bounds checking

**This is NOT a memory issue** - it's a native code crash (C++/Objective-C) that Python cannot catch because it happens in `libmlx.dylib` before Python's exception handler can intervene.

## Attempted Fixes

### ❌ Fix 1: Set CPU Backend (Failed)
Tried setting `mx.set_default_device(mx.cpu)` but the crash happens during `import mlx.core` before we can set the device.

### ❌ Fix 2: Environment Variable (Failed)
Tried setting `MLX_USE_CPU=1` but MLX doesn't respect this variable.

### ❌ Fix 3: Upgrade MLX (Blocked)
Cannot upgrade MLX due to pip SSL/permissions issues:
```
PermissionError: [Errno 1] Operation not permitted
```

## Solutions

### Solution 0: Run from Terminal.app Instead of Cursor (EASIEST - Try This First!)

**The crash may be because Python is running from Cursor IDE which doesn't have GPU entitlements.**

1. **Open Terminal.app** (not Cursor's integrated terminal)

2. **Navigate to project**:
```bash
cd /Users/shaydu/dev/mondrian-macos
```

3. **Test MLX directly**:
```bash
python3 -c "import mlx.core as mx; print(mx.zeros((1,))); print('SUCCESS!')"
```

4. **If that works, run the services from Terminal**:
```bash
cd mondrian
python3 start_services.py
```

5. **Then run batch analysis from Terminal**:
```bash
cd /Users/shaydu/dev/mondrian-macos
python3 batch_analyze_advisor_images.py --advisor ansel
```

**Why this works**: Terminal.app has proper GPU entitlements, so Python processes launched from it can access Metal devices.

---

### Solution 1: Fix Pip and Upgrade MLX (If Terminal.app doesn't work)

1. **Fix pip permissions**:
```bash
# Fix pip cache permissions
sudo chown -R $(whoami) ~/Library/Caches/pip

# Or use sudo with -H flag
sudo -H pip3 install --upgrade mlx mlx-vlm
```

2. **Upgrade to latest MLX** (should fix Metal enumeration):
```bash
pip3 install --upgrade mlx mlx-vlm mlx-lm
```

3. **Test MLX**:
```bash
python3 -c "import mlx.core as mx; print(mx.zeros((1,))); print('SUCCESS')"
```

### Solution 2: Reinstall MLX Completely

```bash
# Uninstall all MLX packages
pip3 uninstall -y mlx mlx-vlm mlx-lm mlx-metal

# Reinstall latest versions
pip3 install mlx mlx-vlm mlx-lm
```

### Solution 3: Use Ollama Instead of MLX

If MLX continues to fail, switch to Ollama:

1. **Install Ollama**:
```bash
# Download from https://ollama.ai
# Or use homebrew
brew install ollama
```

2. **Start Ollama**:
```bash
ollama serve
```

3. **Pull vision model**:
```bash
ollama pull qwen3-vl:4b
```

4. **Modify start_services.py** to disable MLX:
```python
# In mondrian/start_services.py, find the ai_advisor start command and remove --use_mlx
# Change from:
"--use_mlx",
# To: (remove that line)
```

### Solution 4: Run Without MLX/Ollama (Fallback)

If you need to proceed immediately without fixing MLX:

1. **Disable AI Advisor Service** temporarily
2. **Use pre-computed dimensional profiles** from database
3. **Skip batch analysis** of new advisor images

## Current Status

- ✅ Verified: 12 advisor images need dimensional profiles
- ✅ Diagnosed: MLX Metal device crash
- ❌ Blocked: Cannot upgrade MLX due to pip permissions
- ⏸️  Pending: Batch analysis cannot proceed until MLX is fixed

## Next Steps

**Choose one path**:

### Path A: Fix MLX (Best for long-term)
```bash
# 1. Fix pip permissions
sudo chown -R $(whoami) ~/Library/Caches/pip

# 2. Upgrade MLX
pip3 install --upgrade mlx mlx-vlm

# 3. Test
python3 -c "import mlx.core as mx; print(mx.zeros((1,)))"

# 4. If successful, restart services
cd /Users/shaydu/dev/mondrian-macos/mondrian
python3 start_services.py --stop
python3 start_services.py

# 5. Run batch analysis
cd /Users/shaydu/dev/mondrian-macos
python3 batch_analyze_advisor_images.py --advisor ansel
```

### Path B: Switch to Ollama (Faster alternative)
```bash
# 1. Install Ollama
brew install ollama

# 2. Start Ollama
ollama serve &

# 3. Pull model
ollama pull qwen3-vl:4b

# 4. Modify mondrian/start_services.py to remove --use_mlx flag

# 5. Restart services and run batch analysis
```

### Path C: Skip for now
```bash
# Continue with other tasks, come back to this later
# Note: RAG system won't work without dimensional profiles
```

## Files Modified

- `/Users/shaydu/dev/mondrian-macos/mondrian/ai_advisor_service.py`
  - Added MLX CPU backend fallback (doesn't work due to crash timing)
  - Added better error messages

## Questions?

1. Do you have sudo access to fix pip permissions?
2. Would you prefer to use Ollama instead of MLX?
3. Should we skip batch analysis for now and work on other features?

---

**Created**: 2026-01-09  
**Status**: Blocked on MLX Metal device enumeration bug

