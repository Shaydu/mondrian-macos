# MLX Model Inference Crash - Root Cause

## Problem
The MLX model inference crashes the Flask process with a segmentation fault when processing `/analyze` requests. The error manifests as:
- `Connection aborted. RemoteDisconnected` on the client side
- No exception logged (process dies at C level)
- Flask server terminates abruptly

## Example Error
```
✗ FAILED: Connection error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
ℹ Service may have crashed during inference
```

## Root Cause
1. **MLX library limitation**: The `stream_generate()` function in `mlx-vlm` can crash when:
   - Streaming tokens from the vision model
   - Processing large images
   - Running on Metal GPU with certain configurations
   
2. **Python threading incompatibility**: The code explicitly disables timeout handling to preserve GPU access, which means:
   - No way to interrupt stuck operations
   - No way to catch crashes (they occur in C extension code)
   - Process termination is immediate and unrecoverable

3. **Metal GPU access**: On macOS, Metal GPU operations don't play well with Python multiprocessing/threading:
   - GPU handles can't be shared across processes
   - Threading doesn't work reliably
   - Result: crashes are silent and unhandled

## Evidence from Logs
Service log shows inference starts but never completes:
```
[INFO] Running MLX generation (timeout handling disabled to preserve GPU access)...
[INFO] GPU Device: Device(gpu, 0)
[INFO] Processing with image: /var/folders/px/.../analyze_image_temp.jpg
[INFO] Fetching model...
[INFO] MLX model loaded in 2.32s...
[Then silence - process crashes]
```

## Why It's Hard to Fix
1. **C-level crash**: Python exception handling can't catch segmentation faults
2. **GPU memory**: Can't safely restart in same process (GPU memory leaked)
3. **Timeout disabled**: Can't use threading timeouts (breaks Metal GPU)
4. **MLX limitation**: Not a bug in our code, upstream library issue

## Current Workaround
Tests use a 330-second timeout to detect crashes and move to next test.

## Potential Solutions (for future)
1. **Run model in subprocess**: Use `multiprocessing` with separate GPU initialization
   - Pro: Isolated crashes don't kill main service
   - Con: Can't share GPU handles across process boundary on Metal
   
2. **Use different backend**: PyTorch MPS instead of MLX
   - Pro: Better Metal GPU support
   - Con: Requires model conversion
   
3. **Limit inference**: Add input validation to prevent edge cases
   - Pro: Easy to implement
   - Con: May block legitimate use cases
   
4. **Contact MLX team**: Report the issue
   - Pro: Get upstream fix
   - Con: Might take time

## Impact
- All vision analysis requests with MLX models on macOS will eventually crash
- Testing is unreliable without process isolation or retry logic
- Production usage requires explicit error handling and service restart

## Recommendation
For testing purposes, implement health check + automatic restart:
- Detect when service becomes unresponsive
- Automatically restart the service  
- Retry the request
- This would allow tests to proceed despite crashes
