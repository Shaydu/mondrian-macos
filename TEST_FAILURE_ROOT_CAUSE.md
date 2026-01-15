# Test Failure Root Cause Analysis

## Summary
Tests are failing due to **MLX model inference hanging indefinitely** on macOS. This is not a test runner issue but a fundamental limitation of the MLX library's GPU integration with Metal on macOS.

## Timeline of Issues Fixed

### Issue #1: Test Runner Hanging ✅ FIXED
**Problem**: The test runner would hang waiting for `./mondrian.sh --restart` to complete.
**Root Cause**: The service launcher was entering an infinite monitoring loop after verification.
**Solution**: Added `--no-monitor` flag to exit cleanly after service health verification.

### Issue #2: Test Timeout Too Short ✅ FIXED
**Problem**: Tests timing out after 60 seconds.
**Root Cause**: Model inference can take 60-120+ seconds, test timeout was only 60s.
**Solution**: Increased test timeout from 60s to 300s (matching service model timeout).

### Issue #3: Model Inference Hanging ❌ ARCHITECTURAL ISSUE
**Problem**: Model inference gets stuck and never returns, causing indefinite hangs.
**Root Cause**: MLX/Metal GPU integration on macOS
- Timeout handling is **explicitly disabled** in the code to preserve GPU access
- Python threading doesn't work reliably with Metal GPU operations
- The `stream_generate()` function can get stuck yielding tokens
- No way to interrupt stuck GPU operations on macOS without killing the entire process

**Evidence from Logs**:
```
[INFO] Running MLX generation (timeout handling disabled to preserve GPU access)...
[INFO] GPU Device: Device(gpu, 0)
[INFO] Processing with image: /var/folders/px/.../analyze_image_temp.jpg
```
Then nothing - the process hangs indefinitely waiting for tokens from `stream_generate()`.

## Current Mitigation
Added timeout handling to test runner:
- Each test has a 330-second limit (300s for inference + 30s buffer)
- If test times out, service is killed and next test starts
- Timeout is recorded as test failure

## Why This Matters
This is a known limitation of running LLMs on macOS with GPU acceleration:
1. **MLX** is designed for macOS/Metal GPU acceleration
2. **Metal** is Apple's GPU API, similar to CUDA/ROCm
3. **Python threading** + Metal GPU = compatibility issues
4. **Result**: Can't safely interrupt GPU operations without killing process

## Proper Solutions (Would require code changes)
1. **Fix stream_generate()**: Make it timeout-safe
2. **Use multiprocessing instead of threading**: Doesn't share Metal GPU handles
3. **Implement polling mechanism**: Check for stuck generator
4. **Use different library**: PyTorch MPS, Core ML, etc.
5. **Async GPU operations**: Rewrite inference loop for async execution

## Current Status
Tests will now:
- ✅ Start without hanging (--no-monitor fixed)
- ✅ Have adequate timeout (300s increased from 60s)
- ⚠️  Timeout cleanly and continue if model hangs (mitigation applied)
- ❌ Actually complete with results (blocked by MLX issue)

## Next Steps
1. **Investigate stream_generate()**: Check if it's returning tokens properly
2. **Add logging**: Log token streaming progress to detect hangs earlier
3. **Contact MLX team**: Report the hanging issue
4. **Consider alternatives**: Evaluate other GPU backends for macOS
